"""Database engine and session helpers."""

from sqlmodel import SQLModel, create_engine

from app.core.config import settings
import app.database.models # run the class bodies/definitions so registration happens

connect_args = (
    {"check_same_thread": False} # sqlite only, postgres doesn't need check_same_thread
)

engine = create_engine(url=settings.database_url, connect_args=connect_args)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)