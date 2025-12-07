from sqlalchemy.orm import Session
from models import InstagramUser
from database.connection import SessionLocal
from utils.logger import logger  # <-- Import the logger

def update_user_connection_status(user_id):
    session: Session = SessionLocal()
    try:
        user = session.query(InstagramUser).filter_by(id=user_id).first()
        if user:
            user.is_connected = True
            session.commit()
    except Exception as e:
        logger.error(f"DB error: {e}")  # <-- Use logger
        session.rollback()
    finally:
        session.close()

def is_user_present(instagram_username, brideside_user_id=None):
    session: Session = SessionLocal()
    try:
        if brideside_user_id:
            # Check if user exists for specific brideside user
            user = session.query(InstagramUser).filter_by(
                instagram_username=instagram_username,
                contacted_to=brideside_user_id
            ).first()
        else:
            # Check if user exists at all (for backward compatibility)
            user = session.query(InstagramUser).filter_by(instagram_username=instagram_username).first()
        return user
    except Exception as e:
        logger.error(f"DB error: {e}")
        return False
    finally:
        session.close()

def create_instagram_user(instagram_username, contacted_to=None):
    session: Session = SessionLocal()
    try:
        new_user = InstagramUser(
            instagram_username=instagram_username,
            contacted_to=contacted_to
        )
        session.add(new_user)
        session.commit()
        logger.info(f"User '{instagram_username}' created with contacted_to={contacted_to}")
        return new_user.id
    except Exception as e:
        logger.error(f"Error creating user '{instagram_username}': {e}")
        session.rollback()
        return None
    finally:
        session.close()

def update_instagram_user_contacted_to(instagram_username, brideside_user_id):
    """Update the contacted_to field for an existing Instagram user."""
    session: Session = SessionLocal()
    try:
        user = session.query(InstagramUser).filter_by(instagram_username=instagram_username).first()
        if user:
            user.contacted_to = brideside_user_id
            session.commit()
            logger.info(f"Updated contacted_to for '{instagram_username}' to {brideside_user_id}")
            return True
        else:
            logger.warning(f"Instagram user '{instagram_username}' not found for contacted_to update")
            return False
    except Exception as e:
        logger.error(f"Error updating contacted_to for '{instagram_username}': {e}")
        session.rollback()
        return False
    finally:
        session.close()

def get_instagram_user_by_username(instagram_username):
    """Get Instagram user by username with contacted_to information."""
    session: Session = SessionLocal()
    try:
        user = session.query(InstagramUser).filter_by(instagram_username=instagram_username).first()
        return user
    except Exception as e:
        logger.error(f"Error getting Instagram user '{instagram_username}': {e}")
        return None
    finally:
        session.close()

