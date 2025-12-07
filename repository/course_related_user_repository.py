from sqlalchemy.orm import Session
from models import CourseRelatedUser
from database.connection import SessionLocal
from utils.logger import logger

def is_course_related_user(instagram_username: str) -> bool:
    """Check if a user is already in the course_related_users table."""
    session: Session = SessionLocal()
    try:
        user = session.query(CourseRelatedUser).filter_by(instagram_username=instagram_username).first()
        return user is not None
    except Exception as e:
        logger.error(f"DB error checking course related user '{instagram_username}': {e}")
        return False
    finally:
        session.close()

def create_course_related_user(instagram_username: str, brideside_user_id: int) -> bool:
    """Add a user to the course_related_users table."""
    session: Session = SessionLocal()
    try:
        # Check if user already exists
        existing_user = session.query(CourseRelatedUser).filter_by(instagram_username=instagram_username).first()
        if existing_user:
            logger.info(f"User '{instagram_username}' already exists in course_related_users")
            return True
        
        new_user = CourseRelatedUser(
            instagram_username=instagram_username,
            brideside_vendor_id=brideside_user_id
        )
        session.add(new_user)
        session.commit()
        logger.info(f"User '{instagram_username}' added to course_related_users for brideside_user_id {brideside_user_id}")
        return True
    except Exception as e:
        logger.error(f"Error creating course related user '{instagram_username}': {e}")
        session.rollback()
        return False
    finally:
        session.close()

def get_course_related_users_by_brideside_user(brideside_user_id: int):
    """Get all course related users for a specific brideside user."""
    session: Session = SessionLocal()
    try:
        users = session.query(CourseRelatedUser).filter_by(brideside_vendor_id=brideside_user_id).all()
        return users
    except Exception as e:
        logger.error(f"DB error getting course related users for brideside_user_id {brideside_user_id}: {e}")
        return []
    finally:
        session.close()
