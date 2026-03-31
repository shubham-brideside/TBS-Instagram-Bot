"""Read organization fields used by webhook / deal creation."""

from typing import Optional

from sqlalchemy.orm import Session

from database.connection import SessionLocal
from models.organization import Organization
from utils.logger import logger


def get_organization_owner_id(organization_id: Optional[int]) -> Optional[int]:
    """Return organizations.owner_id for the given organization primary key, or None."""
    if organization_id is None:
        return None
    session: Session = SessionLocal()
    try:
        org = session.query(Organization).filter_by(id=organization_id).first()
        if not org:
            logger.warning("Organization id=%s not found", organization_id)
            return None
        if org.owner_id is None:
            logger.warning("Organization id=%s has no owner_id", organization_id)
            return None
        return int(org.owner_id)
    except Exception as e:
        logger.error("Error loading organization owner_id for id=%s: %s", organization_id, e)
        return None
    finally:
        session.close()
