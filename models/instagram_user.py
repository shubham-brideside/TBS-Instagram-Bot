from sqlalchemy import Column, Integer, String, Boolean, DateTime, func, ForeignKey, UniqueConstraint
from models import Base
from models import TimestampMixin

class InstagramUser(Base, TimestampMixin):
    __tablename__ = "instagram_users"
    id = Column(Integer, primary_key=True, index=True)
    instagram_username = Column(String(255), index=True)  # Removed unique=True
    contacted_to = Column(Integer, ForeignKey("brideside_vendors.id"), nullable=True)
    
    # Composite unique constraint to ensure one Instagram user per brideside user
    __table_args__ = (
        UniqueConstraint('instagram_username', 'contacted_to', name='ix_instagram_users_username_contacted_to'),
    )