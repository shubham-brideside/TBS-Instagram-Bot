from sqlalchemy.orm import Session
from sqlalchemy import text
from models import BridesideVendor
from database.connection import SessionLocal
from typing import Optional
from utils.logger import logger


def get_brideside_vendor_by_username(username) -> BridesideVendor:
    session: Session = SessionLocal()
    try:
        vendor = session.query(BridesideVendor).filter_by(username=username).first()
        return vendor
    finally:
        session.close()


def get_brideside_vendor_by_ig_account_id(ig_account_id: str) -> Optional[BridesideVendor]:
    """Get brideside vendor by Instagram account ID (recipient)"""
    session: Session = SessionLocal()
    try:
        logger.info(f"🔍 Searching for vendor with ig_account_id: '{ig_account_id}' (type: {type(ig_account_id)})")
        
        # Check which database we're connected to
        db_name_result = session.execute(text("SELECT DATABASE()")).first()
        logger.info(f"📊 Connected to database: {db_name_result[0] if db_name_result else 'Unknown'}")
        
        # First, try with raw SQL to verify the connection and data
        raw_result = session.execute(
            text("SELECT id, username, ig_account_id FROM brideside_vendors WHERE ig_account_id = :ig_id"),
            {"ig_id": ig_account_id}
        ).first()
        
        if raw_result:
            logger.info(f"✅ Raw SQL found vendor: ID={raw_result[0]}, username={raw_result[1]}, ig_account_id={raw_result[2]}")
        else:
            logger.warning(f"⚠️ Raw SQL found no vendor with ig_account_id='{ig_account_id}'")
            # Check all vendors with raw SQL
            all_raw = session.execute(text("SELECT id, username, ig_account_id FROM brideside_vendors")).fetchall()
            logger.info(f"Total vendors in DB (raw SQL): {len(all_raw)}")
            for row in all_raw:
                logger.info(f"  Vendor ID={row[0]}, username={row[1]}, ig_account_id='{row[2]}' (type: {type(row[2])})")
        
        # Now try with SQLAlchemy ORM
        vendor = session.query(BridesideVendor).filter_by(ig_account_id=ig_account_id).first()
        if vendor:
            logger.info(f"✅ ORM found vendor: ID={vendor.id}, username={vendor.username}, ig_account_id={vendor.ig_account_id}")
        else:
            logger.warning(f"⚠️ ORM found no vendor with ig_account_id='{ig_account_id}'. Checking all vendors...")
            # Debug: Check what ig_account_ids exist
            all_vendors = session.query(BridesideVendor).all()
            logger.info(f"Total vendors in DB (ORM): {len(all_vendors)}")
            for v in all_vendors:
                logger.info(f"  Vendor ID={v.id}, username={v.username}, ig_account_id='{v.ig_account_id}' (type: {type(v.ig_account_id)})")
        
        # If raw SQL found it but ORM didn't, try to get by ID from raw result
        if raw_result and not vendor:
            logger.warning(f"⚠️ Raw SQL found vendor but ORM didn't. Trying to fetch by ID: {raw_result[0]}")
            vendor = session.query(BridesideVendor).filter_by(id=raw_result[0]).first()
            if vendor:
                logger.info(f"✅ Found vendor by ID: ID={vendor.id}, username={vendor.username}, ig_account_id={vendor.ig_account_id}")
        
        return vendor
    except Exception as e:
        logger.error(f"❌ Error querying vendor by ig_account_id '{ig_account_id}': {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None
    finally:
        session.close()


def is_sender_a_brideside_vendor(sender_id: str) -> bool:
    """Check if sender ID exists in brideside_vendors table"""
    session: Session = SessionLocal()
    try:
        vendor = session.query(BridesideVendor).filter_by(ig_account_id=sender_id).first()
        return vendor is not None
    finally:
        session.close()


def get_instagram_credentials_by_account_id(ig_account_id: str) -> Optional[tuple[str, str]]:
    """Get Instagram account ID and access token by account ID"""
    session: Session = SessionLocal()
    try:
        vendor = session.query(BridesideVendor).filter_by(ig_account_id=ig_account_id).first()
        if vendor and vendor.access_token:
            return (vendor.ig_account_id, vendor.access_token)
        return None
    finally:
        session.close()


def update_brideside_vendor_access_token(vendor_id: int, new_access_token: str) -> bool:
    """Update access token for a brideside vendor"""
    session: Session = SessionLocal()
    try:
        vendor = session.query(BridesideVendor).filter_by(id=vendor_id).first()
        if vendor:
            vendor.access_token = new_access_token
            # updated_at will be automatically updated by TimestampMixin
            session.commit()
            logger.info(f"✅ Updated access_token and updated_at for vendor {vendor_id}")
            return True
        logger.warning(f"⚠️ Vendor {vendor_id} not found for token update")
        return False
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Error updating access token for vendor {vendor_id}: {e}")
        return False
    finally:
        session.close()


def get_brideside_vendor_by_id(vendor_id: int) -> Optional[BridesideVendor]:
    """Get brideside vendor by ID"""
    session: Session = SessionLocal()
    try:
        vendor = session.query(BridesideVendor).filter_by(id=vendor_id).first()
        return vendor
    finally:
        session.close()

