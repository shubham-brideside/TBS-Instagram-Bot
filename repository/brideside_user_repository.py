from sqlalchemy.orm import Session
from models import BridesideUser
from database.connection import SessionLocal
from typing import Optional
from utils.logger import logger


def get_brideside_user_by_username(username) -> BridesideUser:
    session: Session = SessionLocal()
    try:
        user = session.query(BridesideUser).filter_by(username=username).first()
        return user
    finally:
        session.close()


def get_brideside_user_by_ig_account_id(ig_account_id: str) -> Optional[BridesideUser]:
    """Get brideside user by Instagram account ID (recipient)"""
    session: Session = SessionLocal()
    try:
        user = session.query(BridesideUser).filter_by(ig_account_id=ig_account_id).first()
        return user
    finally:
        session.close()


def is_sender_a_brideside_user(sender_id: str) -> bool:
    """Check if sender ID exists in brideside_users table"""
    session: Session = SessionLocal()
    try:
        user = session.query(BridesideUser).filter_by(ig_account_id=sender_id).first()
        return user is not None
    finally:
        session.close()


def get_instagram_credentials_by_account_id(ig_account_id: str) -> Optional[tuple[str, str]]:
    """Get Instagram account ID and access token by account ID"""
    session: Session = SessionLocal()
    try:
        user = session.query(BridesideUser).filter_by(ig_account_id=ig_account_id).first()
        if user and user.access_token:
            return (user.ig_account_id, user.access_token)
        return None
    finally:
        session.close()


def update_brideside_user_access_token(user_id: int, new_access_token: str) -> bool:
    """Update access token for a brideside user"""
    session: Session = SessionLocal()
    try:
        user = session.query(BridesideUser).filter_by(id=user_id).first()
        if user:
            user.access_token = new_access_token
            # updated_at will be automatically updated by TimestampMixin
            session.commit()
            logger.info(f"✅ Updated access_token and updated_at for user {user_id}")
            return True
        logger.warning(f"⚠️ User {user_id} not found for token update")
        return False
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Error updating access token for user {user_id}: {e}")
        return False
    finally:
        session.close()


def get_brideside_user_by_id(user_id: int) -> Optional[BridesideUser]:
    """Get brideside user by ID"""
    session: Session = SessionLocal()
    try:
        user = session.query(BridesideUser).filter_by(id=user_id).first()
        return user
    finally:
        session.close()
    