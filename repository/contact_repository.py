from sqlalchemy.orm import Session
from models.contact import Contact
from database.connection import SessionLocal
from utils.logger import logger  # <-- Add this import

def get_contact_id_by_username(username):
    session: Session = SessionLocal()
    try:
        contact = session.query(Contact).filter_by(contact_name=username).first()
        return contact.pipedrive_contact_id if contact else None
    finally:
        session.close()

def create_contact_entry(contact_name, pipedrive_contact_id):
    session: Session = SessionLocal()
    try:
        new_contact = Contact(contact_name=contact_name, 
                              pipedrive_contact_id=pipedrive_contact_id)
        session.add(new_contact)
        session.commit()
        logger.info(f"Contact '{contact_name}' created with Pipedrive ID {pipedrive_contact_id}")
    except Exception as e:
        logger.error(f"DB error: {e}")
        session.rollback()
    finally:
        session.close()