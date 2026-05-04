from sqlalchemy import BigInteger, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import mapped_column, Mapped, relationship
from models import Base
from models import TimestampMixin
from typing import Optional
from datetime import datetime


class User(Base, TimestampMixin):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(6), nullable=True)
    password_set: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    manager_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True, index=True)
    role_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    # Hub presales routing: DIRECT vs AUTO_DIVERT (Instagram mirror deals use DIRECT only).
    tbs_presales_deal_lane: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    is_tbs_user: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    tbs_default_pipeline_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("pipelines.id"), nullable=True, index=True
    )

    # Self-referential relationship for manager
    manager = relationship("User", remote_side=[id], backref="subordinates")

