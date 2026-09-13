from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from database import get_db
from auth_utils import hash_password, verify_password, create_token, verify_token, PLAN_LIMITS
from datetime import datetime

router = APIRouter()

class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str = ""

class LoginRequest(BaseModel):
    email: str
    password: str

def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token required")
    token = authorization.split(" ", 1)[1]
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload

@router.post("/register")
def register(req: RegisterRequest):
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Mật khẩu phải ít nhất 6 ký tự")
    if "@" not in req.email:
        raise HTTPException(status_code=400, detail="Email không hợp lệ")
    
    db = get_db()
    try:
        # Check existing
        existing = db.execute("SELECT id FROM users WHERE email=?", (req.email,)).fetchone()
        if existing:
            raise HTTPException(status_code=400, detail="Email đã được đăng ký")
        
        # Create user
        cursor = db.execute("""
            INSERT INTO users (email, password_hash, full_name, plan)
            VALUES (?, ?, ?, 'free')
        """, (req.email.lower().strip(), hash_password(req.password), req.full_name))
        user_id = cursor.lastrowid
        
        # Create subscription
        db.execute("""
            INSERT INTO subscriptions (user_id, plan, monthly_limit, reset_date)
            VALUES (?, 'free', 10, ?)
        """, (user_id, datetime.now().strftime("%Y-%m")))
        
        db.commit()
        token = create_token(user_id, req.email)
        return {"token": token, "message": "Đăng ký thành công!"}
    finally:
        db.close()

@router.post("/login")
def login(req: LoginRequest):
    db = get_db()
    try:
        user = db.execute("SELECT * FROM users WHERE email=?", (req.email.lower().strip(),)).fetchone()
        if not user or not verify_password(req.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Email hoặc mật khẩu không đúng")
        if not user["is_active"]:
            raise HTTPException(status_code=403, detail="Tài khoản đã bị vô hiệu hóa")
        
        token = create_token(user["id"], user["email"], bool(user["is_admin"]))
        sub = db.execute("SELECT * FROM subscriptions WHERE user_id=?", (user["id"],)).fetchone()
        
        return {
            "token": token,
            "user": {
                "id": user["id"],
                "email": user["email"],
                "full_name": user["full_name"],
                "plan": user["plan"],
                "is_admin": bool(user["is_admin"]),
                "usage_count": user["usage_count"],
                "monthly_usage": sub["usage_this_month"] if sub else 0,
                "monthly_limit": sub["monthly_limit"] if sub else 10,
            }
        }
    finally:
        db.close()

@router.get("/me")
def get_me(authorization: str = Header(None)):
    payload = get_current_user(authorization)
    db = get_db()
    try:
        user = db.execute("SELECT * FROM users WHERE id=?", (payload["user_id"],)).fetchone()
        sub = db.execute("SELECT * FROM subscriptions WHERE user_id=?", (payload["user_id"],)).fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "plan": user["plan"],
            "is_admin": bool(user["is_admin"]),
            "usage_count": user["usage_count"],
            "monthly_usage": sub["usage_this_month"] if sub else 0,
            "monthly_limit": sub["monthly_limit"] if sub else 10,
            "plan_label": PLAN_LIMITS.get(user["plan"], {}).get("label", "Free")
        }
    finally:
        db.close()
