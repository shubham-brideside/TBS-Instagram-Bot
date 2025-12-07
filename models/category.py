from sqlalchemy import BigInteger, String
from sqlalchemy.orm import mapped_column, Mapped
from models import Base
from typing import Optional


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    def __repr__(self):
        return f"<Category(id={self.id}, name='{self.name}')>"

