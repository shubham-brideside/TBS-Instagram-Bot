from sqlalchemy import BigInteger, String, Boolean, ForeignKey
from sqlalchemy.orm import mapped_column, Mapped
from models import Base
from models import TimestampMixin
from typing import Optional


class Pipeline(Base, TimestampMixin):
    __tablename__ = "pipelines"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, index=True)
    category: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    organization_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("organizations.id"), nullable=True, index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    team_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)
    organization: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    team: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    owner_user_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True, index=True)
    
    def __repr__(self):
        return f"<Pipeline(id={self.id}, name='{self.name}')>"

