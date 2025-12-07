from sqlalchemy.orm import Session
from models.processed_message import ProcessedMessage
from database.connection import SessionLocal
from utils.logger import logger
from sqlalchemy.exc import IntegrityError

def is_message_processed(message_id: str) -> bool:
    """Check if a message ID has already been processed."""
    session: Session = SessionLocal()
    try:
        processed_message = session.query(ProcessedMessage).filter_by(message_id=message_id).first()
        return processed_message is not None
    finally:
        session.close()

def mark_message_as_processed(message_id: str, message_text: str, message_reply: str, brideside_user_id: int, instagram_username: str) -> bool:
    """Mark a message ID as processed. Returns True if successful, False if already exists."""
    session: Session = SessionLocal()
    try:
        processed_message = session.query(ProcessedMessage).filter_by(message_id=message_id).first()
        if processed_message:
            processed_message.message_text = message_text
            processed_message.brideside_vendor_id = brideside_user_id
            processed_message.instagram_username = instagram_username
            session.commit()
        else:
            new_processed_message = ProcessedMessage(message_id=message_id, message_text=message_text, message_reply=message_reply, brideside_vendor_id=brideside_user_id, instagram_username=instagram_username)
            session.add(new_processed_message)
            session.commit()
            session.refresh(new_processed_message)
            
        logger.info(f"Message ID '{message_id}' marked as processed")
        return True
    except IntegrityError:
        # Message already exists due to unique constraint
        logger.info(f"Message ID '{message_id}' already processed")
        session.rollback()
        return False
    except Exception as e:
        logger.error(f"DB error while marking message as processed: {e}")
        session.rollback()
        return False
    finally:
        session.close()

def cleanup_old_processed_messages(days_old: int = 7):
    """Clean up processed messages older than specified days to prevent table bloat."""
    session: Session = SessionLocal()
    try:
        from datetime import datetime, timedelta
        from models.timestamp_mixin import IST
        
        cutoff_date = datetime.now(IST) - timedelta(days=days_old)
        deleted_count = session.query(ProcessedMessage).filter(
            ProcessedMessage.created_at < cutoff_date
        ).delete()
        session.commit()
        logger.info(f"Cleaned up {deleted_count} processed messages older than {days_old} days")
        return deleted_count
    except Exception as e:
        logger.error(f"DB error while cleaning up processed messages: {e}")
        session.rollback()
        return 0
    finally:
        session.close() 