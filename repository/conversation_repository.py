from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from models import InstagramConversationSummary, InstagramConversationMessage
from database.connection import SessionLocal
from contextlib import contextmanager
from datetime import datetime
from utils.logger import logger  # Add logger import


@contextmanager
def get_db_session():
    """Context manager for database sessions."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


class ConversationRepository:
    """Repository for handling Instagram conversation data."""
    
    @staticmethod
    def get_conversation_summary_by_deal_id(deal_id: int) -> Optional[InstagramConversationSummary]:
        """Get conversation summary by Instagram user ID."""
        with get_db_session() as session:
            summary = session.query(InstagramConversationSummary).filter_by(
                deal_id=deal_id
            ).first()
            if summary:
                logger.info(f"Found existing conversation summary for deal_id {deal_id}")
            else:
                logger.info(f"No conversation summary found for deal_id {deal_id}")
            return summary
    
    @staticmethod
    def create_conversation_summary(
        instagram_username: str,
        instagram_user_id: int,
        deal_id: int,
        conversation_summary: str = ""
    ) -> InstagramConversationSummary:
        """Create a new conversation summary."""
        with get_db_session() as session:
            try:
                summary = InstagramConversationSummary(
                    instagram_username=instagram_username,
                    instagram_user_id=instagram_user_id,
                    deal_id=deal_id,
                    deals_conversation_summary=conversation_summary,
                    is_active=True
                )
                session.add(summary)
                session.commit()
                session.refresh(summary)
                logger.info(f"✅ Created new conversation summary for instagram_user_id {instagram_user_id}, deal_id {deal_id}")
                return summary
            except Exception as e:
                logger.error(f"❌ Failed to create conversation summary: {e}")
                session.rollback()
                raise
    
    @staticmethod
    def update_conversation_summary(
        instagram_user_id: int,
        deal_id: int,
        new_summary: str
    ) -> bool:
        """Update conversation summary for a user and deal."""
        with get_db_session() as session:
            try:
                summary = session.query(InstagramConversationSummary).filter_by(
                    instagram_user_id=instagram_user_id,
                    deal_id=deal_id
                ).first()
                
                if summary:
                    setattr(summary, 'deals_conversation_summary', new_summary)
                    setattr(summary, 'is_active', True)
                    setattr(summary, 'updated_at', datetime.now())
                    session.commit()
                    logger.info(f"✅ Updated conversation summary for instagram_user_id {instagram_user_id}, deal_id {deal_id}")
                    return True
                logger.warning(f"⚠️ No conversation summary found to update for instagram_user_id {instagram_user_id}, deal_id {deal_id}")
                return False
            except Exception as e:
                logger.error(f"❌ Error updating conversation summary: {e}")
                session.rollback()
                return False
    
    @staticmethod
    def save_conversation_messages(
        conversation_summary_id: int,
        user_message: str,
        bot_response: str
    ) -> bool:
        """Save both user message and bot response to the database."""
        with get_db_session() as session:
            try:
                # Save user message
                user_msg = InstagramConversationMessage(
                    conversation_summary_id=conversation_summary_id,
                    message_type='input',
                    message_content=user_message,
                    message_timestamp=datetime.now(),
                    is_processed=True
                )
                session.add(user_msg)
                
                # Save bot response
                bot_msg = InstagramConversationMessage(
                    conversation_summary_id=conversation_summary_id,
                    message_type='output',
                    message_content=bot_response,
                    message_timestamp=datetime.now(),
                    is_processed=True
                )
                session.add(bot_msg)
                
                session.commit()
                logger.info(f"✅ Saved conversation messages for summary_id {conversation_summary_id}")
                return True
            except Exception as e:
                logger.error(f"❌ Error saving conversation messages: {e}")
                session.rollback()
                return False
    
    @staticmethod
    def get_conversation_history(
        user_id: int, 
        limit: int = 50
    ) -> List[InstagramConversationMessage]:
        """Get conversation history for a user."""
        with get_db_session() as session:
            summary = session.query(InstagramConversationSummary).filter_by(
                instagram_user_id=str(user_id)
            ).first()
            
            if not summary:
                return []
            
            return session.query(InstagramConversationMessage).filter_by(
                conversation_summary_id=summary.id
            ).order_by(InstagramConversationMessage.message_timestamp.desc()).limit(limit).all()
    
    @staticmethod
    def get_or_create_conversation_summary(
        instagram_username: str,
        instagram_user_id: int,  # Change type hint to int
        deal_id: int
    ) -> InstagramConversationSummary:
        """Get existing conversation summary or create a new one."""
        with get_db_session() as session:
            summary = session.query(InstagramConversationSummary).filter_by(
                instagram_user_id=instagram_user_id  # Use integer directly
            ).first()
            
            if not summary:
                summary = InstagramConversationSummary(
                    instagram_username=instagram_username,
                    instagram_user_id=instagram_user_id,  # Use integer directly
                    deal_id=deal_id,
                    deals_conversation_summary="",
                    is_active=True
                )
                session.add(summary)
                session.commit()
                session.refresh(summary)
            
            return summary
    
    @staticmethod
    def get_conversation_summary_text(user_id: int) -> str:
        """Get the conversation summary text for a user."""
        summary = ConversationRepository.get_conversation_summary_by_deal_id(user_id)
        return getattr(summary, 'deals_conversation_summary', '') if summary else ""
    
    @staticmethod
    def append_to_conversation_summary(
        user_id: int, 
        new_content: str
    ) -> bool:
        """Append new content to existing conversation summary."""
        with get_db_session() as session:
            summary = session.query(InstagramConversationSummary).filter_by(
                instagram_user_id=str(user_id)
            ).first()
            
            if summary:
                current_summary = getattr(summary, 'deals_conversation_summary') or ""
                updated_summary = f"{current_summary}\n{new_content}".strip()
                setattr(summary, 'deals_conversation_summary', updated_summary)
                setattr(summary, 'updated_at', datetime.now())
                session.commit()
                return True
            return False 