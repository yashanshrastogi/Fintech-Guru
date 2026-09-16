from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.database import engine, Base
import logging
import os

from app.config import settings
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# Remove Base.metadata.create_all(bind=engine) as we now use Alembic

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Deterministic financial affordability engine with hard safety boundaries",
    version=settings.VERSION
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin).rstrip("/") for origin in settings.CORS_ORIGINS] if settings.CORS_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Payload Size Limiter (e.g., 5MB max for non-file endpoints, we'll just check content-length loosely)
@app.middleware("http")
async def limit_upload_size(request: Request, call_next):
    if request.url.path == f"{settings.API_V1_STR}/evidence/upload":
        # Evidence has its own limits
        return await call_next(request)
    
    content_length = request.headers.get('content-length')
    if content_length and int(content_length) > 1_048_576: # 1MB limit for standard JSON POST
        return JSONResponse(status_code=413, content={"detail": "Payload too large"})
    return await call_next(request)

# Set up structured logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("fintech-guru-api")

@app.get("/api/v1/health")
def health_check():
    return {"status": "ok"}

@app.get("/api/v1/ready")
def ready_check():
    # Verify DB connectivity or other readiness checks
    return {"status": "ready"}

@app.get("/api/v1/version")
def version_check():
    return {"version": "2.0.0"}

# We will include routers here
from app.api.router import api_router
app.include_router(api_router, prefix="/api/v1")
