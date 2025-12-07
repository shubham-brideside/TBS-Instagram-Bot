from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from models import Base
from models import TimestampMixin
from sqlalchemy.orm import relationship

class InstagramConversationMessage(Base, TimestampMixin):
    """Model for storing individual Instagram conversation messages."""
    __tablename__ = 'instagram_conversation_messages'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_summary_id = Column(Integer, ForeignKey('instagram_conversation_summaries.id'))
    message_type = Column(String(50), nullable=False)  # 'input' or 'output'
    message_content = Column(Text, nullable=False)
    message_timestamp = Column(DateTime, nullable=False)
    is_processed = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    conversation_summary = relationship("InstagramConversationSummary", back_populates="conversation_messages")
    
    def __repr__(self):
        return f"<InstagramConversationMessage(id={self.id}, type='{self.message_type}', summary_id={self.conversation_summary_id})>"
