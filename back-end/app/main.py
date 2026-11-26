from contextlib import asynccontextmanager

import uvicorn

from fastapi import FastAPI, Request
from fastapi.responses import ORJSONResponse
from fastapi.middleware.cors import CORSMiddleware

from core import settings, postgres_helper
from core.helpers import mongo_db_helper

from api import router as v1_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting lifespan")
    await mongo_db_helper.connect()
    postgres_helper.create_db_and_tables()
    yield
    await mongo_db_helper.dispose()


app = FastAPI(lifespan=lifespan, default_response_class=ORJSONResponse)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.run.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}


@app.post("/mcp", tags=["MCP"])
async def mcp_root_endpoint(
    request: Request,
    session: postgres_helper.SessionDep
):
    from api.v1.ai.mcp_server import handle_mcp_request
    body = await request.json()
    return handle_mcp_request(body, session)


app.include_router(router=v1_router)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.run.host,
        port=settings.run.port,
        reload=settings.logger.reload,
        log_level=settings.logger.log_level,
    )
