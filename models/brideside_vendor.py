from sqlalchemy import JSON, BigInteger, String, Text, ForeignKey
from sqlalchemy.orm import mapped_column, Mapped
from models import Base
from models import TimestampMixin
from typing import List, Optional


class BridesideVendor(Base, TimestampMixin):
    __tablename__ = "brideside_vendors"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, index=True)
    username: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    organization_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    pipeline_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    ig_account_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, unique=True)
    access_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    business_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    services: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    account_owner: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True, index=True)

