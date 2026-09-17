"""FastAPI Main Application for Zhijuan Hermes Service."""
from __future__ import annotations
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .settings import settings
from .health import router as health_router
from .routes.exams import router as exams_router
from .routes.curriculum import router as curriculum_router

app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    description="知卷 Hermes AI 原创命题后端服务",
)

# Enable CORS for frontend workbench
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(exams_router)
app.include_router(curriculum_router)

@app.get("/")
def root():
    return {
        "message": "知卷 Hermes AI 原创命题服务就绪",
        "docs_url": "/docs",
        "version": settings.app_version,
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("services.api.main:app", host=settings.host, port=settings.port, reload=True)
