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


class Logger(BaseModel):
    name: str = "CMS"
    log_file: str = "app.log"
    log_level: str = "info"
    reload: bool = True


class ApiV1Prefix(BaseModel):
    prefix: str = "/v1"
    student: str = "/student"
    message: str = "/message"


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


settings = Settings()
