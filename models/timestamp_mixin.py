from sqlalchemy import DateTime
from sqlalchemy.orm import mapped_column, Mapped
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))

def now_ist() -> datetime:
    return datetime.now(IST)

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_ist)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_ist, onupdate=now_ist)