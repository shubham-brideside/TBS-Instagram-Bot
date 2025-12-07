from sqlalchemy import BigInteger, String, Integer, DECIMAL
from sqlalchemy.orm import mapped_column, Mapped
from models import Base
from models import TimestampMixin
from typing import Optional


class Source(Base, TimestampMixin):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, index=True)
    commission_percentage: Mapped[int] = mapped_column(Integer, nullable=False)
    fixed_commission_amount: Mapped[Optional[float]] = mapped_column(DECIMAL(38, 2), nullable=True)
    type: Mapped[str] = mapped_column(String(255), nullable=False)
    
    def __repr__(self):
        return f"<Source(id={self.id}, type='{self.type}')>"

