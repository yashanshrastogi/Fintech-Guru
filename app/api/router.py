from fastapi import APIRouter
from app.api.endpoints import profile, affordability, what_if, evidence, assistant, auth
api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(profile.router, prefix="/profile", tags=["profile"])
api_router.include_router(affordability.router, prefix="/affordability", tags=["affordability"])
api_router.include_router(what_if.router, prefix="/what-if", tags=["what-if"])
api_router.include_router(evidence.router, prefix="/evidence", tags=["evidence"])
api_router.include_router(assistant.router, prefix="/assistant", tags=["assistant"])
