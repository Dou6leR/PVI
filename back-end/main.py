from contextlib import asynccontextmanager

import uvicorn

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from fastapi.middleware.cors import CORSMiddleware

from core import settings, postgres_helper

from api import router as v1_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting lifespan")
    postgres_helper.create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan, default_response_class=ORJSONResponse)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.run.allowed_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router=v1_router)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.run.host,
        port=settings.run.port,
        reload=settings.logger.reload,
        log_level=settings.logger.log_level,
    )

