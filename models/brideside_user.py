from sqlalchemy import JSON, Integer, String, DateTime, func, Text
from sqlalchemy.orm import mapped_column, Mapped
from models import Base
from models import TimestampMixin
from typing import List, Optional


class BridesideUser(Base, TimestampMixin):
    __tablename__ = "brideside_users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    username: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    organization_id: Mapped[str] = mapped_column(String(100))
    pipeline_id: Mapped[str] = mapped_column(String(100))
    ig_account_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, unique=True)
    access_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    business_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    services: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)      