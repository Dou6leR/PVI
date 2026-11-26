from fastapi import APIRouter
from core import settings
from .students import router as student_router
from .messages import router as message_router
from .ai import router as ai_router

router = APIRouter(prefix=settings.api.v1.prefix)

router.include_router(student_router, prefix=settings.api.v1.student)
router.include_router(message_router, prefix=settings.api.v1.message)
router.include_router(ai_router, prefix=settings.api.v1.ai)
