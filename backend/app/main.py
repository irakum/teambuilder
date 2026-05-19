import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.exception_handlers import register_exception_handlers
from app.api.routers import sessions, participants, distribution, auth, dashboard

app = FastAPI(
    title="TeamBuilder API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(sessions.router, prefix="/api")
app.include_router(participants.router, prefix="/api")
app.include_router(distribution.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")


@app.get("/api/health", tags=["health"])
async def health():
    return {"status": "ok"}


os.makedirs(settings.export_dir, exist_ok=True)
