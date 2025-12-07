from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from models import Base
from models import TimestampMixin


class InstagramConversationSummary(Base, TimestampMixin):
    """Model for storing Instagram conversation summaries by deal."""
    __tablename__ = 'instagram_conversation_summaries'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    instagram_username = Column(String(255), nullable=False, index=True)
    instagram_user_id = Column(Integer, ForeignKey("instagram_users.id"))
    deal_id = Column(Integer, ForeignKey('deals.id'), nullable=False, index=True)
    deals_conversation_summary = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    deal = relationship("Deal", back_populates="conversation_summaries")
    conversation_messages = relationship("InstagramConversationMessage", back_populates="conversation_summary")
    
    def __repr__(self):
        return f"<InstagramConversationSummary(id={self.id}, instagram_username='{self.instagram_username}', deal_id={self.deal_id})>"
