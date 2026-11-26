from fastapi.security import HTTPBasic

from pydantic import BaseModel
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


class RunConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    allowed_origin: str = "http://127.0.0.1:5500"
    allowed_origins: list[str] = [
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:80",
        "http://127.0.0.1:80",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    def get_cors_origins(self) -> list[str]:
        origins = set(self.allowed_origins)
        if self.allowed_origin:
            origins.add(self.allowed_origin)
        return list(origins)


class Logger(BaseModel):
    name: str = "CMS"
    log_file: str = "app.log"
    log_level: str = "info"
    reload: bool = True


class ApiV1Prefix(BaseModel):
    prefix: str = "/v1"
    student: str = "/student"
    message: str = "/message"
    ai: str = "/ai"


class AIConfig(BaseModel):
    provider: str = "auto"  # "auto", "ollama", "gemini"
    api_key: str = ""
    model: str = "gemini-3.8-flash"
    embedding_model: str = "text-embedding-004"
    ollama_url: str = "http://ollama:11434"
    ollama_model: str = "qwen3.5:4b"
    ollama_embedding_model: str = "bge-m3"


class ApiPrefix(BaseModel):
    prefix: str = "/api"
    v1: ApiV1Prefix = ApiV1Prefix()


class PostgresConfig(BaseSettings):
    url: str = "postgresql://postgres:7119@localhost:5432/CMS"


class MongoDatabaseConfig(BaseModel):
    host: str = "mongo:27018"
    database_name: str = "cms"
    test_database_name: str = "test_cms"
    url: str = "mongodb://localhost:27018"

    @property
    def test_url(self) -> str:
        mongo_db_uri = f"mongodb://{self.host}/{self.test_database_name}"
        return mongo_db_uri


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env"),
        case_sensitive=False,
        env_nested_delimiter="__",
        env_prefix="APP_CONFIG__",
    )
    TESTING: bool = False
    postgres_config: PostgresConfig = PostgresConfig()
    mongo_db: MongoDatabaseConfig = MongoDatabaseConfig()
    run: RunConfig = RunConfig()
    api: ApiPrefix = ApiPrefix()
    logger: Logger = Logger()
    security: HTTPBasic = HTTPBasic()
    ai: AIConfig = AIConfig()


settings = Settings()
