from sqlalchemy import BigInteger, String, Integer, Boolean, ForeignKey
from sqlalchemy.orm import mapped_column, Mapped
from models import Base
from models import TimestampMixin
from typing import Optional


class Stage(Base, TimestampMixin):
    __tablename__ = "stages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, index=True)
    pipeline_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("pipelines.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    stage_order: Mapped[int] = mapped_column(Integer, nullable=False)
    probability: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    active_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    
    def __repr__(self):
        return f"<Stage(id={self.id}, name='{self.name}', pipeline_id={self.pipeline_id})>"

