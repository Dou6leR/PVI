from typing import Annotated
from fastapi import Depends
from sqlmodel import Session, create_engine, SQLModel
from core import settings




class PostgresHelper:
    def __init__(self):
        self.SessionDep = Annotated[Session, Depends(self.get_session)]
        self.engine = create_engine(settings.postgres_config.url)

    def create_db_and_tables(self):
        SQLModel.metadata.create_all(self.engine)

    def get_session(self):
        with Session(self.engine) as session:
            yield session


postgres_helper = PostgresHelper()
