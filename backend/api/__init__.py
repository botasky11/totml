from fastapi import APIRouter
from .experiments import router as experiments_router

api_router = APIRouter()
api_router.include_router(experiments_router, prefix="/experiments", tags=["experiments"])

__all__ = ["api_router"]
