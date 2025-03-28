from fastapi import APIRouter

from .v1 import router as v1_router

from core import settings

router = APIRouter(prefix=settings.api.prefix)

router.include_router(v1_router)
