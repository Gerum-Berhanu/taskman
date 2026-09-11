from sqlmodel import Field
from app.models.base import BaseTable


class Workspace(BaseTable, table=True):
    __tablename__: str = "workspaces"

    name: str = Field(max_length=255)
    