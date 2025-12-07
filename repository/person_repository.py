from sqlalchemy.orm import Session
from models.person import Person
from database.connection import SessionLocal
from utils.logger import logger
from typing import Optional
from datetime import date


def get_person_id_by_username(username: str) -> Optional[int]:
    """Get person ID by username (name field)."""
    session: Session = SessionLocal()
    try:
        person = session.query(Person).filter_by(name=username).first()
        return person.id if person else None
    except Exception as e:
        logger.error(f"Error getting person by username '{username}': {e}")
        return None
    finally:
        session.close()


def get_person_by_username(username: str) -> Optional[Person]:
    """Get person by username (name field)."""
    session: Session = SessionLocal()
    try:
        person = session.query(Person).filter_by(name=username).first()
        return person
    except Exception as e:
        logger.error(f"Error getting person by username '{username}': {e}")
        return None
    finally:
        session.close()


def create_person_entry(name: str, instagram_id: Optional[str] = None, 
                       organization_id: Optional[int] = None,
                       owner_id: Optional[int] = None,
                       category_id: Optional[int] = None,
                       lead_date: Optional[date] = None,
                       person_source: Optional[str] = None,
                       sub_source: Optional[str] = None) -> Optional[int]:
    """Create a new person entry and return the person ID."""
    from models.person import PersonSource, PersonSubSource
    
    session: Session = SessionLocal()
    try:
        # Check if person already exists
        existing_person = session.query(Person).filter_by(name=name).first()
        if existing_person:
            logger.info(f"Person '{name}' already exists with ID {existing_person.id}")
            return existing_person.id
        
        # Convert string enums to enum values
        person_source_enum = None
        if person_source:
            try:
                person_source_enum = PersonSource[person_source.upper()] if person_source else None
            except (KeyError, AttributeError):
                logger.warning(f"Invalid person_source: {person_source}, using None")
        
        sub_source_enum = None
        if sub_source:
            try:
                sub_source_enum = PersonSubSource[sub_source.upper()] if sub_source else None
            except (KeyError, AttributeError):
                logger.warning(f"Invalid sub_source: {sub_source}, using None")
        
        new_person = Person(
            name=name,
            instagram_id=instagram_id,
            organization_id=organization_id,
            owner_id=owner_id,
            category_id=category_id,
            lead_date=lead_date or date.today(),
            person_source=person_source_enum,
            sub_source=sub_source_enum,
            is_deleted=False
        )
        session.add(new_person)
        session.commit()
        logger.info(f"Person '{name}' created with ID {new_person.id}")
        return new_person.id
    except Exception as e:
        logger.error(f"Error creating person '{name}': {e}")
        session.rollback()
        return None
    finally:
        session.close()


def update_person_fields(person_id: int, instagram_id: Optional[str] = None,
                        phone: Optional[str] = None, email: Optional[str] = None) -> bool:
    """Update person fields."""
    session: Session = SessionLocal()
    try:
        person = session.query(Person).filter_by(id=person_id).first()
        if not person:
            logger.warning(f"Person with ID {person_id} not found")
            return False
        
        if instagram_id is not None:
            person.instagram_id = instagram_id
        if phone is not None:
            person.phone = phone
        if email is not None:
            person.email = email
        
        session.commit()
        logger.info(f"Updated person {person_id} fields")
        return True
    except Exception as e:
        logger.error(f"Error updating person {person_id}: {e}")
        session.rollback()
        return False
    finally:
        session.close()

