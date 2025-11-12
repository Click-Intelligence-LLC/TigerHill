from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn
from datetime import datetime

from .database import init_db
from .routers import sessions, stats, comparison, sessions_v3, import_v3
from .services.importer import router as import_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化数据库
    await init_db()
    yield

app = FastAPI(
    title="Gemini CLI Dashboard API",
    description="Gemini CLI 会话数据分析和可视化后端服务",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://localhost:8001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由，统一增加 /api 前缀以兼容前端配置
# app.include_router(sessions.router, prefix="/api")  # Disabled: uses old schema (v1/v2)
app.include_router(sessions_v3.router, prefix="/api")  # V3 unified interaction model
app.include_router(stats.router, prefix="/api")  # Updated to use V3 schema
# app.include_router(comparison.router, prefix="/api")  # Disabled: depends on old sessions router
app.include_router(import_router, prefix="/api")  # Old importer (v2 schema) - for backward compatibility
app.include_router(import_v3.router, prefix="/api")  # V3 importer (unified interaction model)

@app.get("/")
async def root():
    return {"message": "Gemini CLI Dashboard API 服务运行正常"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)