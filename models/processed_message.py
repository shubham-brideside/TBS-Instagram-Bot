from sqlalchemy import Column, ForeignKey, BigInteger, Text, String
from sqlalchemy.orm import Mapped, mapped_column
from models import Base
from models import TimestampMixin

class ProcessedMessage(Base, TimestampMixin):
    __tablename__ = "processed_messages"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, index=True)
    message_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    message_reply: Mapped[str] = mapped_column(Text, nullable=False)
    brideside_vendor_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("brideside_vendors.id"), nullable=False, index=True)
    instagram_username: Mapped[str] = mapped_column(Text, nullable=False)
