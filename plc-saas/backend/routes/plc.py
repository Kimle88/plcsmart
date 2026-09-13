from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
import httpx
import os
import json
from datetime import datetime
from database import get_db
from auth_utils import verify_token

router = APIRouter()

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"

def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token required")
    payload = verify_token(authorization.split(" ", 1)[1])
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload

class GenerateRequest(BaseModel):
    prompt: str
    prog_type: str = ""
    cpu_model: str = ""
    block_type: str = ""

class SaveHistoryRequest(BaseModel):
    title: str
    description: str = ""
    prog_type: str = ""
    cpu_model: str = ""
    block_type: str = ""
    scl_code: str = ""
    ladder_json: str = ""
    io_list: str = ""

class ChatRequest(BaseModel):
    messages: list
    system: str = ""

@router.post("/generate")
async def generate_plc(req: GenerateRequest, authorization: str = Header(None)):
    payload = get_current_user(authorization)
    user_id = payload["user_id"]

    db = get_db()
    try:
        # Check usage limit
        sub = db.execute("SELECT * FROM subscriptions WHERE user_id=?", (user_id,)).fetchone()
        if sub:
            current_month = datetime.now().strftime("%Y-%m")
            # Reset monthly usage if new month
            if sub["reset_date"] != current_month:
                db.execute("UPDATE subscriptions SET usage_this_month=0, reset_date=? WHERE user_id=?",
                          (current_month, user_id))
                db.commit()
                sub = db.execute("SELECT * FROM subscriptions WHERE user_id=?", (user_id,)).fetchone()
            
            if sub["usage_this_month"] >= sub["monthly_limit"]:
                raise HTTPException(
                    status_code=429,
                    detail=f"Đã đạt giới hạn {sub['monthly_limit']} lần/tháng. Nâng cấp gói để dùng thêm!"
                )

        # Proxy to Anthropic
        if not ANTHROPIC_API_KEY:
            raise HTTPException(status_code=500, detail="API Key chưa được cấu hình trên server")

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                ANTHROPIC_URL,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01"
                },
                json={
                    "model": "claude-sonnet-4-5",
                    "max_tokens": 8000,
                    "messages": [{"role": "user", "content": req.prompt}]
                }
            )

        if response.status_code != 200:
            err_detail = response.text[:500]
            raise HTTPException(status_code=502, detail=f"Anthropic: {response.status_code} - {err_detail}")

        # Update usage
        db.execute("UPDATE subscriptions SET usage_this_month=usage_this_month+1 WHERE user_id=?", (user_id,))
        db.execute("UPDATE users SET usage_count=usage_count+1 WHERE id=?", (user_id,))
        db.commit()

        return response.json()
    finally:
        db.close()

@router.post("/chat")
async def chat_plc(req: ChatRequest, authorization: str = Header(None)):
    payload = get_current_user(authorization)
    
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=500, detail="API Key chưa được cấu hình")

    async with httpx.AsyncClient(timeout=60) as client:
        body = {
            "model": "claude-sonnet-4-5",
            "max_tokens": 1000,
            "messages": req.messages[-10:]
        }
        if req.system:
            body["system"] = req.system

        response = await client.post(
            ANTHROPIC_URL,
            headers={
                "Content-Type": "application/json",
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "anthropic-beta": "pdfs-2024-09-25"
            },
            json=body
        )

    if response.status_code != 200:
        try:
            err_body = response.json()
            err_msg = err_body.get("error", {}).get("message", response.text[:300])
        except Exception:
            err_msg = response.text[:300]
        raise HTTPException(status_code=502, detail=f"Anthropic API: {err_msg}")
    return response.json()

@router.post("/history/save")
def save_history(req: SaveHistoryRequest, authorization: str = Header(None)):
    payload = get_current_user(authorization)
    db = get_db()
    try:
        cursor = db.execute("""
            INSERT INTO plc_history 
            (user_id, title, description, prog_type, cpu_model, block_type, scl_code, ladder_json, io_list)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (payload["user_id"], req.title, req.description, req.prog_type,
              req.cpu_model, req.block_type, req.scl_code, req.ladder_json, req.io_list))
        db.commit()
        return {"id": cursor.lastrowid, "message": "Đã lưu chương trình"}
    finally:
        db.close()

@router.get("/history")
def get_history(authorization: str = Header(None)):
    payload = get_current_user(authorization)
    db = get_db()
    try:
        rows = db.execute("""
            SELECT id, title, description, prog_type, cpu_model, block_type, created_at
            FROM plc_history WHERE user_id=? ORDER BY created_at DESC LIMIT 50
        """, (payload["user_id"],)).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()

@router.get("/history/{history_id}")
def get_history_detail(history_id: int, authorization: str = Header(None)):
    payload = get_current_user(authorization)
    db = get_db()
    try:
        row = db.execute("""
            SELECT * FROM plc_history WHERE id=? AND user_id=?
        """, (history_id, payload["user_id"])).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Không tìm thấy")
        return dict(row)
    finally:
        db.close()

@router.delete("/history/{history_id}")
def delete_history(history_id: int, authorization: str = Header(None)):
    payload = get_current_user(authorization)
    db = get_db()
    try:
        db.execute("DELETE FROM plc_history WHERE id=? AND user_id=?",
                  (history_id, payload["user_id"]))
        db.commit()
        return {"message": "Đã xóa"}
    finally:
        db.close()
# ── Thêm vào cuối file plc.py ──

class AnalyzePDFRequest(BaseModel):
    pdf_base64: str
    filename: str = ""

@router.post("/analyze-pdf")
async def analyze_pdf(req: AnalyzePDFRequest, authorization: str = Header(None)):
    """Phân tích tài liệu PDF PLC qua Anthropic API và trả về symbols/rules"""
    payload = get_current_user(authorization)

    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=500, detail="API Key chưa được cấu hình")

    prompt_text = """Bạn là chuyên gia PLC. Phân tích tài liệu PLC này và trả về JSON (chỉ JSON, không markdown):
{
  "brand": "siemens|mitsubishi|ab|general",
  "plc_type": "tên loại PLC cụ thể",
  "summary": "mô tả ngắn nội dung tài liệu (2-3 câu)",
  "symbols": [
    {"name": "tên lệnh/ký hiệu", "type": "contact|coil|timer|counter|function|block", "description": "mô tả cách dùng", "syntax": "cú pháp ví dụ"}
  ],
  "addressing": "quy tắc đặt địa chỉ I/O (ví dụ: X0=input, Y0=output, M=memory...)",
  "special_rules": ["quy tắc đặc biệt cần biết khi lập trình PLC này"]
}
Trích xuất tối đa 25 symbols/lệnh quan trọng nhất. Chỉ trả JSON."""

    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            ANTHROPIC_URL,
            headers={
                "Content-Type": "application/json",
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "anthropic-beta": "pdfs-2024-09-25"
            },
            json={
                "model": "claude-sonnet-4-5",
                "max_tokens": 2000,
                "messages": [{
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": req.pdf_base64
                            }
                        },
                        {"type": "text", "text": prompt_text}
                    ]
                }]
            }
        )

    if response.status_code != 200:
        detail = response.text[:200]
        raise HTTPException(status_code=502, detail=f"Anthropic API lỗi: {detail}")

    return response.json()


class KBAnalyzeRequest(BaseModel):
    pdf_base64: str
    filename: str = ""

@router.post("/kb-analyze")
async def kb_analyze(req: KBAnalyzeRequest, authorization: str = Header(None)):
    """Phân tích PDF tài liệu PLC - không tính vào usage limit"""
    get_current_user(authorization)  # chỉ xác thực, không tính usage

    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=500, detail="API Key chưa được cấu hình")

    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            ANTHROPIC_URL,
            headers={
                "Content-Type": "application/json",
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "anthropic-beta": "pdfs-2024-09-25"
            },
            json={
                "model": "claude-sonnet-4-5",
                "max_tokens": 2048,
                "messages": [{
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": req.pdf_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": """Analyze this PLC documentation and return ONLY valid JSON (no markdown, no explanation):
{"brand":"siemens|mitsubishi|ab|general","plc_type":"specific PLC model name","summary":"brief 2-3 sentence description","symbols":[{"name":"instruction name","type":"contact|coil|timer|counter|function","description":"how to use","syntax":"usage example"}],"addressing":"I/O addressing rules (e.g. X0=input, Y0=output, M=memory...)","special_rules":["important programming rule 1","rule 2"]}
Extract up to 25 most important symbols/instructions. Return ONLY the JSON object."""
                        }
                    ]
                }]
            }
        )

    if response.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Lỗi từ Anthropic API: {response.text[:300]}")

    return response.json()
