# PLC AI Studio SaaS – Hướng dẫn triển khai

## Cấu trúc project
```
plc-saas/
├── backend/
│   ├── main.py              # FastAPI app chính
│   ├── database.py          # SQLite database + init
│   ├── auth_utils.py        # JWT + password hashing
│   ├── routes/
│   │   ├── auth.py          # Đăng ký / Đăng nhập
│   │   ├── plc.py           # API proxy + lịch sử
│   │   └── admin.py         # Quản lý user/stats
│   └── requirements.txt
├── frontend/
│   ├── index.html           # Trang Login/Register
│   ├── app.html             # PLC AI Studio chính
│   └── admin.html           # Admin Dashboard
└── README.md
```

---

## Bước 1: Cài đặt local

```bash
cd backend
pip install -r requirements.txt

# Tạo file .env
cp .env.example .env
# Sửa file .env với API key của bạn

# Chạy server
uvicorn main:app --reload --port 8000
```

Truy cập: http://localhost:8000
Admin: admin@plcai.com / admin123

---

## Bước 2: Deploy lên Railway.app (MIỄN PHÍ)

1. Tạo tài khoản tại https://railway.app
2. Tạo project mới → Deploy from GitHub
3. Hoặc dùng Railway CLI:
   ```bash
   npm install -g @railway/cli
   railway login
   railway init
   railway up
   ```
4. Set Environment Variables trong Railway dashboard:
   - `ANTHROPIC_API_KEY` = sk-ant-api03-...
   - `SECRET_KEY` = your-secret-key-here
   - `ADMIN_EMAIL` = your-admin@email.com
   - `ADMIN_PASSWORD` = your-admin-password

---

## Bước 3: Cấu hình file Procfile (Railway)

Tạo file `Procfile` trong thư mục backend:
```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

---

## Gói subscription

| Gói        | Giới hạn       | Mô tả           |
|------------|----------------|-----------------|
| Free       | 10 lần/tháng   | Dùng thử        |
| Pro        | 100 lần/tháng  | Cá nhân/SME     |
| Enterprise | Không giới hạn | Doanh nghiệp    |

Admin có thể thay đổi gói của user trong Admin Dashboard.

---

## API Endpoints

### Auth
- POST /api/auth/register
- POST /api/auth/login
- GET  /api/auth/me

### PLC
- POST /api/plc/generate     # Tạo chương trình PLC
- POST /api/plc/chat         # Chat AI
- GET  /api/plc/history      # Lịch sử
- POST /api/plc/history/save # Lưu chương trình
- GET  /api/plc/history/{id} # Chi tiết
- DEL  /api/plc/history/{id} # Xóa

### Admin (cần quyền admin)
- GET /api/admin/stats
- GET /api/admin/users
- PUT /api/admin/users/plan
- PUT /api/admin/users/update
- DEL /api/admin/users/{id}
