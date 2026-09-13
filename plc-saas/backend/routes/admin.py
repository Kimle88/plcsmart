from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from database import get_db
from auth_utils import verify_token, PLAN_LIMITS

router = APIRouter()

def get_admin_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token required")
    payload = verify_token(authorization.split(" ", 1)[1])
    if not payload or not payload.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin only")
    return payload

class UpdatePlanRequest(BaseModel):
    user_id: int
    plan: str

class UpdateUserRequest(BaseModel):
    user_id: int
    is_active: bool = None
    is_admin: bool = None
    full_name: str = None

@router.get("/stats")
def get_stats(authorization: str = Header(None)):
    get_admin_user(authorization)
    db = get_db()
    try:
        total_users = db.execute("SELECT COUNT(*) as c FROM users WHERE is_admin=0").fetchone()["c"]
        active_users = db.execute("SELECT COUNT(*) as c FROM users WHERE is_active=1 AND is_admin=0").fetchone()["c"]
        total_programs = db.execute("SELECT COUNT(*) as c FROM plc_history").fetchone()["c"]
        total_usage = db.execute("SELECT SUM(usage_count) as c FROM users").fetchone()["c"] or 0
        
        plan_counts = db.execute("""
            SELECT plan, COUNT(*) as cnt FROM users WHERE is_admin=0 GROUP BY plan
        """).fetchall()
        
        recent_users = db.execute("""
            SELECT email, full_name, plan, created_at FROM users 
            WHERE is_admin=0 ORDER BY created_at DESC LIMIT 5
        """).fetchall()

        return {
            "total_users": total_users,
            "active_users": active_users,
            "total_programs": total_programs,
            "total_api_calls": total_usage,
            "plans": {r["plan"]: r["cnt"] for r in plan_counts},
            "recent_users": [dict(r) for r in recent_users]
        }
    finally:
        db.close()

@router.get("/users")
def list_users(authorization: str = Header(None)):
    get_admin_user(authorization)
    db = get_db()
    try:
        rows = db.execute("""
            SELECT u.id, u.email, u.full_name, u.plan, u.is_active, u.is_admin,
                   u.usage_count, u.created_at,
                   s.usage_this_month, s.monthly_limit
            FROM users u
            LEFT JOIN subscriptions s ON u.id = s.user_id
            ORDER BY u.created_at DESC
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()

@router.put("/users/plan")
def update_plan(req: UpdatePlanRequest, authorization: str = Header(None)):
    get_admin_user(authorization)
    if req.plan not in PLAN_LIMITS:
        raise HTTPException(status_code=400, detail="Plan không hợp lệ")
    
    limit = PLAN_LIMITS[req.plan]["monthly_limit"]
    db = get_db()
    try:
        db.execute("UPDATE users SET plan=? WHERE id=?", (req.plan, req.user_id))
        db.execute("UPDATE subscriptions SET plan=?, monthly_limit=? WHERE user_id=?",
                  (req.plan, limit, req.user_id))
        db.commit()
        return {"message": f"Đã cập nhật plan → {req.plan}"}
    finally:
        db.close()

@router.put("/users/update")
def update_user(req: UpdateUserRequest, authorization: str = Header(None)):
    get_admin_user(authorization)
    db = get_db()
    try:
        if req.is_active is not None:
            db.execute("UPDATE users SET is_active=? WHERE id=?", (int(req.is_active), req.user_id))
        if req.is_admin is not None:
            db.execute("UPDATE users SET is_admin=? WHERE id=?", (int(req.is_admin), req.user_id))
        if req.full_name is not None:
            db.execute("UPDATE users SET full_name=? WHERE id=?", (req.full_name, req.user_id))
        db.commit()
        return {"message": "Đã cập nhật"}
    finally:
        db.close()

@router.delete("/users/{user_id}")
def delete_user(user_id: int, authorization: str = Header(None)):
    get_admin_user(authorization)
    db = get_db()
    try:
        db.execute("DELETE FROM plc_history WHERE user_id=?", (user_id,))
        db.execute("DELETE FROM subscriptions WHERE user_id=?", (user_id,))
        db.execute("DELETE FROM users WHERE id=? AND is_admin=0", (user_id,))
        db.commit()
        return {"message": "Đã xóa user"}
    finally:
        db.close()
