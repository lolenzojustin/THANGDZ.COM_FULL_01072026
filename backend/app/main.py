# backend/app/main.py
# Trigger reload: database is running
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.api import auth, posts, guides, services, orders, payments, admin
from app.core.database import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup database, create tables, and seed data automatically
    init_db()
    yield

# Khoi tao ung dung FastAPI voi root_path la /api de khop voi cau hinh Nginx hoac config chung
app = FastAPI(
    title="Personal Website API",
    description="API cho website ca nhan thuong hieu, blog, huong dan va thanh toan.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

import os

# Cấu hình CORS (Cross-Origin Resource Sharing)
# Cho phep Front-end Next.js goi API tu bat ky port dev nao o local (vi du: 3000, 3001)
origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
]

env_origins = os.getenv("CORS_ORIGINS")
if env_origins:
    origins.extend([origin.strip() for origin in env_origins.split(",") if origin.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

uploads_dir = Path(__file__).resolve().parent / "uploads"
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

# Them cac API routers vao ung dung
app.include_router(auth.router)
app.include_router(posts.router)
app.include_router(guides.router)
app.include_router(services.router)
app.include_router(orders.router)
app.include_router(payments.router)
app.include_router(admin.router)

@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "healthy",
        "service": "Personal Web API Backend",
        "database": "connected"
    }

@app.get("/", tags=["System"])
def root():
    return {"message": "Chao mung ban den voi Personal Web API. Truy cap /docs de xem tai lieu API."}
