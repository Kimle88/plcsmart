from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from database import init_db
from routes import auth, plc, admin

app = FastAPI(title="PLCSmart SaaS", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    init_db()

app.include_router(auth.router,  prefix="/api/auth",  tags=["Auth"])
app.include_router(plc.router,   prefix="/api/plc",   tags=["PLC"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])

frontend_path = os.path.join(os.path.dirname(__file__), "../frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

@app.get("/")
def root():
    # Landing page cho visitors
    lp = os.path.join(frontend_path, "landing.html")
    if os.path.exists(lp):
        return FileResponse(lp)
    return FileResponse(os.path.join(frontend_path, "index.html"))

@app.get("/login")
@app.get("/register")
def auth_page():
    return FileResponse(os.path.join(frontend_path, "index.html"))

@app.get("/app")
def plc_app():
    return FileResponse(os.path.join(frontend_path, "app.html"))

@app.get("/admin")
def admin_page():
    return FileResponse(os.path.join(frontend_path, "admin.html"))

@app.get("/health")
def health():
    return {"status": "ok", "service": "PLCSmart", "version": "2.0.0"}
