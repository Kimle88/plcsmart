import hashlib
import hmac
import os
import json
import base64
import time

SECRET_KEY = os.environ.get("SECRET_KEY", "plc-ai-studio-secret-change-in-production")

def hash_password(password: str) -> str:
    salt = os.urandom(16).hex()
    h = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return f"{salt}:{h.hex()}"

def verify_password(password: str, password_hash: str) -> bool:
    try:
        salt, h = password_hash.split(":")
        check = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return hmac.compare_digest(check.hex(), h)
    except:
        return False

def create_token(user_id: int, email: str, is_admin: bool = False) -> str:
    payload = {
        "user_id": user_id,
        "email": email,
        "is_admin": is_admin,
        "exp": int(time.time()) + 86400 * 7  # 7 days
    }
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
    sig = hmac.new(SECRET_KEY.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{sig}"

def verify_token(token: str) -> dict | None:
    try:
        payload_b64, sig = token.rsplit(".", 1)
        expected = hmac.new(SECRET_KEY.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(base64.urlsafe_b64decode(payload_b64 + "=="))
        if payload.get("exp", 0) < int(time.time()):
            return None
        return payload
    except:
        return None

# Plan limits
PLAN_LIMITS = {
    "free":       {"monthly_limit": 10,    "label": "Free"},
    "pro":        {"monthly_limit": 100,   "label": "Pro"},
    "enterprise": {"monthly_limit": 999999,"label": "Enterprise"},
}
