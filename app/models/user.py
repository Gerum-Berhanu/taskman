from sqlmodel import Field

from app.models.base import BaseTable


class User(BaseTable, table=True):
    __tablename__: str = "users"
    
    email: str = Field(unique=True, index=True)
    hashed_password: str
    is_active: bool = Field(default=True)