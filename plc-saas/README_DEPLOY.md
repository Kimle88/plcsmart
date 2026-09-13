# PLCSmart — Deployment Guide

## Deploy lên Railway (Khuyến nghị)

### Bước 1: Push lên GitHub
```bash
cd plc-saas
git init
git add .
git commit -m "PLCSmart v2.0 - Initial deploy"
git remote add origin https://github.com/YOUR_USERNAME/plcsmart.git
git push -u origin main
```

### Bước 2: Tạo project trên Railway
1. Vào https://railway.app → Login bằng GitHub
2. **New Project** → **Deploy from GitHub repo**
3. Chọn repo `plcsmart`
4. Railway tự detect Python → build tự động

### Bước 3: Cấu hình Environment Variables
Vào **Settings → Variables** trong Railway, thêm:

| Variable | Value |
|----------|-------|
| `ANTHROPIC_API_KEY` | `sk-ant-api03-...` |
| `SECRET_KEY` | Random 32 chars (dùng: https://randomkeygen.com) |
| `ADMIN_EMAIL` | `admin@yourcompany.com` |
| `ADMIN_PASSWORD` | `StrongPassword123!` |

### Bước 4: Set root directory
Vào **Settings → Source** → **Root Directory** = `backend`

### Bước 5: Deploy
Railway tự động deploy sau khi push code.
URL app: `https://plcsmart-xxx.railway.app`

### Bước 6: Custom Domain (tùy chọn)
1. Mua domain tại Namecheap (~$10/năm)
2. Vào Railway → Settings → Networking → Custom Domain
3. Thêm CNAME record theo hướng dẫn Railway

## Local Development
```bash
cd backend
pip install -r requirements.txt
set ANTHROPIC_API_KEY=sk-ant-...
uvicorn main:app --port 8000 --reload
```
