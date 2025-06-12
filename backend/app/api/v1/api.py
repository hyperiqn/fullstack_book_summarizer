# app/api/v1/api.py 
from fastapi import APIRouter

from app.api.v1.endpoints import auth
from app.api.v1.endpoints import documents

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])