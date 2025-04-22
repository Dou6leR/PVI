from typing import Annotated, Optional
from fastapi import Depends

from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from sqlmodel import Session, create_engine, SQLModel

from core import settings
from core.models import all_document_models
from core.logger import logger


class PostgresHelper:
    def __init__(self):
        self.SessionDep = Annotated[Session, Depends(self.get_session)]
        self.engine = create_engine(settings.postgres_config.url)

    def create_db_and_tables(self):
        SQLModel.metadata.create_all(self.engine)

    def get_session(self):
        with Session(self.engine) as session:
            yield session


class MongoDbHelper:
    def __init__(self, db_url: str, db_name: str):
        self.db_url: str = db_url
        self.db_name: str = db_name
        self.client: Optional[AsyncIOMotorClient] = None

    async def connect(self):
        """Starts the MongoDB client and connects to the database."""
        self.client = AsyncIOMotorClient(
            self.db_url,
            uuidRepresentation="standard",
        )
        try:
            # Initialize Beanie with the correct database
            await init_beanie(
                database=self.client[self.db_name], document_models=all_document_models
            )
            logger.info(f"MongoDB connected to {self.db_name}.")
        except Exception as e:
            print(f"Error initializing MongoDB: {e}")

    async def dispose(self):
        """Closes the MongoDB client."""
        if self.client:
            self.client.close()
            logger.info(f"MongoDB connection to {self.db_name} closed.")

    async def drop_database(self):
        """
        Drops the entire database.
        Works only for test databases
        """
        if not self.client:
            raise Exception("MongoDB client is not connected. Call `connect` first.")
        try:
            if "test" in self.db_name:
                await self.client.drop_database(self.db_name)
                logger.info(f"Database {self.db_name} dropped successfully.")
        except Exception as e:
            logger.error(f"Error dropping database {self.db_name}: {e}")


postgres_helper = PostgresHelper()

mongo_db_helper = MongoDbHelper(
    db_url=settings.mongo_db.url,
    db_name=settings.mongo_db.database_name,
)
