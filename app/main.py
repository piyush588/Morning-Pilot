"""Morning Pilot — FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import health, profile, briefing, conversation
from app.core.scheduler import start_scheduler, stop_scheduler
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start scheduler on boot, stop on shutdown."""
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="Morning Pilot",
    description="Your news, spoken, and you can talk back.",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow the frontend on any origin during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(health.router)
app.include_router(profile.router)
app.include_router(briefing.router)
app.include_router(conversation.router)

# Serve frontend static files
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    import os

    port = settings.effective_port
    is_prod = bool(os.environ.get("PORT"))

    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=port,
        reload=not is_prod,
    )
