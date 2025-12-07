from sqlalchemy import BigInteger, String, ForeignKey
from sqlalchemy.orm import mapped_column, Mapped
from models import Base
from models import TimestampMixin
from typing import Optional


class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    owner_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True, index=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    google_calendar_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    def __repr__(self):
        return f"<Organization(id={self.id}, name='{self.name}', category='{self.category}')>"

