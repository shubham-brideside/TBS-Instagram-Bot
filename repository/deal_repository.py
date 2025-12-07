
from sqlalchemy.orm import Session
from models import Deal
from database.connection import SessionLocal
from utils.logger import logger  # <-- Add this import
from services.crm_service import crm_service

def deal_exists(deal_name, contacted_to):
    session: Session = SessionLocal()
    try:
        existing_deal = session.query(Deal).filter_by(
            name=deal_name,
            contacted_to=contacted_to
        ).first()
        return existing_deal is not None
    except Exception as e:
        logger.error(f"Error checking deal existence: {e}")
        return False
    finally:
        session.close()
        
def get_deal_by_user_name(user_name, brideside_user_id) -> Deal:
    """
    Get deal by username and brideside_user_id.
    This combination should be unique due to the unique constraint.
    Returns the single matching deal or None if not found.
    """
    session: Session = SessionLocal()
    try:
        deal = session.query(Deal).filter_by(
            name=user_name,
            contacted_to=brideside_user_id
        ).first()
        return deal
    except Exception as e:
        logger.error(f"Error getting deal by user name: {e}")
        raise
    finally:
        session.close()

def get_all_deals_by_user_name(user_name, brideside_user_id) -> list[Deal]:
    """
    Get all deals by username and brideside_user_id.
    This is useful for identifying duplicates before applying unique constraint.
    """
    session: Session = SessionLocal()
    try:
        deals = session.query(Deal).filter_by(
            name=user_name,
            contacted_to=brideside_user_id
        ).all()
        return deals
    except Exception as e:
        logger.error(f"Error getting all deals by user name: {e}")
        raise
    finally:
        session.close()

def get_deal_by_id(deal_id) -> Deal:
    session: Session = SessionLocal()
    try:
        deal = session.query(Deal).filter_by(id=deal_id).first()
        return deal
    except Exception as e:
        logger.error(f"Error getting deal by ID: {e}")
        raise
    finally:
        session.close()

def create_deal(deal_name, pipeline_id, organization_id, contacted_to, pipedrive_deal_id=None,
                person_id=None, stage_id=None, category_id=None, value=0.0, status="IN_PROGRESS",
                source="Direct", sub_source="Instagram", event_type=None, event_date=None,
                event_dates=None, venue=None, phone_number=None, contact_number=None):
    from models.deal import DealStatus, DealSubSource
    from sqlalchemy import text
    
    session: Session = SessionLocal()
    try:
        # Convert string enums to enum values
        status_enum = DealStatus[status.upper()] if status else DealStatus.IN_PROGRESS
        
        sub_source_enum = None
        if sub_source:
            try:
                sub_source_enum = DealSubSource[sub_source.upper()]
            except (KeyError, AttributeError):
                logger.warning(f"Invalid sub_source: {sub_source}, using None")
        
        # Get category name if category_id is provided, otherwise use a default
        category_name = "Photography"  # Default
        if category_id:
            # Query category name from database
            result = session.execute(
                text("SELECT name FROM categories WHERE id = :cat_id"),
                {"cat_id": category_id}
            ).first()
            if result:
                category_name = result[0]
        
        # Ensure contact_number is set (required field)
        if not contact_number:
            contact_number = phone_number or ""
        
        new_deal = Deal(
            name=deal_name,
            value=value,
            contact_number=contact_number,
            category=category_name,
            pipeline_id=pipeline_id,
            organization_id=organization_id,
            person_id=person_id,
            stage_id=stage_id,
            category_id=category_id,
            contacted_to=contacted_to,
            pipedrive_deal_id=pipedrive_deal_id,
            status=status_enum,
            deal_source=source,  # Set deal_source field
            deal_sub_source=sub_source_enum,
            event_type=event_type,
            event_date=event_date,
            event_dates=event_dates,
            venue=venue,
            phone_number=phone_number
        )
        session.add(new_deal)
        session.commit()
        logger.info(f"Deal created: {deal_name} (ID: {new_deal.id})")
        return new_deal.id
    except Exception as e:
        logger.error(f"Error creating deal: {e}")
        session.rollback()
        return None
    finally:
        session.close()

def update_deal_fields(deal_id: int, **kwargs):
    """Update deal fields with extracted information from conversations."""
    session: Session = SessionLocal()
    try:
        deal = session.query(Deal).filter_by(id=deal_id).first()
        if not deal:
            logger.error(f"Deal with ID {deal_id} not found")
            return False
        
        updated_fields = []
        
        # Update fields if they have values and the current field is empty
        if kwargs.get('full_name') and (deal.user_name is None or str(deal.user_name).strip() == ""):
            deal.user_name = kwargs['full_name']
            updated_fields.append('user_name')
        
        if kwargs.get('event_type') and (deal.event_type is None or str(deal.event_type).strip() == ""):
            deal.event_type = kwargs['event_type']
            updated_fields.append('event_type')
        
        if kwargs.get('event_date') and (deal.event_date is None or str(deal.event_date).strip() == "" or deal.event_date != kwargs['event_date']):
            deal.event_date = kwargs['event_date']
            updated_fields.append('event_date')
        
        if kwargs.get('venue') and (deal.venue is None or str(deal.venue).strip() == "" or deal.venue != kwargs['venue']):
            deal.venue = kwargs['venue']
            updated_fields.append('venue')
        
        phone_number_added = False
        if kwargs.get('phone_number') and (deal.phone_number is None or str(deal.phone_number).strip() == "" or deal.phone_number != kwargs['phone_number']):
            deal.phone_number = kwargs['phone_number']
            updated_fields.append('phone_number')
            phone_number_added = True

        # Persist final_thank_you_sent flag if provided
        if 'final_thank_you_sent' in kwargs:
            new_flag = bool(kwargs['final_thank_you_sent'])
            if getattr(deal, 'final_thank_you_sent', False) != new_flag:
                deal.final_thank_you_sent = new_flag  # type: ignore[attr-defined]
                updated_fields.append('final_thank_you_sent')
        
        # Persist contact_number_asked flag if provided
        if 'contact_number_asked' in kwargs:
            new_flag = bool(kwargs['contact_number_asked'])
            if getattr(deal, 'contact_number_asked', False) != new_flag:
                deal.contact_number_asked = new_flag  # type: ignore[attr-defined]
                updated_fields.append('contact_number_asked')
        
        # Persist event_date_asked flag if provided
        if 'event_date_asked' in kwargs:
            new_flag = bool(kwargs['event_date_asked'])
            if getattr(deal, 'event_date_asked', False) != new_flag:
                deal.event_date_asked = new_flag  # type: ignore[attr-defined]
                updated_fields.append('event_date_asked')
        
        # Persist venue_asked flag if provided
        if 'venue_asked' in kwargs:
            new_flag = bool(kwargs['venue_asked'])
            if getattr(deal, 'venue_asked', False) != new_flag:
                deal.venue_asked = new_flag  # type: ignore[attr-defined]
                updated_fields.append('venue_asked')
        
        if updated_fields:
            # Check if we need to move to Qualified stage BEFORE committing
            should_move_to_qualified = False
            qualified_stage_id = None
            
            if phone_number_added and deal.pipeline_id and deal.stage_id:
                try:
                    # Get current stage name BEFORE commit
                    from sqlalchemy import text
                    stage_result = session.execute(
                        text("SELECT name FROM stages WHERE id = :stage_id"),
                        {"stage_id": deal.stage_id}
                    ).fetchone()
                    
                    if stage_result and stage_result[0] and stage_result[0].lower() == "lead in":
                        logger.info(f"Phone number added to deal {deal_id} in 'Lead In' stage - will move to 'Qualified' stage")
                        
                        # Get "Qualified" stage ID
                        qualified_stage_result = session.execute(
                            text("SELECT id FROM stages WHERE pipeline_id = :pipeline_id AND LOWER(name) = 'qualified' AND active_flag = 1"),
                            {"pipeline_id": deal.pipeline_id}
                        ).fetchone()
                        
                        if qualified_stage_result:
                            qualified_stage_id = qualified_stage_result[0]
                            should_move_to_qualified = True
                            logger.info(f"Found 'Qualified' stage ID: {qualified_stage_id} for pipeline {deal.pipeline_id}")
                        else:
                            logger.warning(f"Could not find 'Qualified' stage in pipeline {deal.pipeline_id}")
                    else:
                        logger.debug(f"Deal {deal_id} is not in 'Lead In' stage (current stage: {stage_result[0] if stage_result else 'unknown'}), skipping stage update")
                except Exception as e:
                    logger.error(f"Error checking stage for deal {deal_id}: {e}")
            
            # Commit the database changes
            session.commit()
            logger.info(f"Deal {deal_id} updated with fields: {', '.join(updated_fields)}")
            
            # After commit, call backend API to update stage (this will trigger activity creation)
            if should_move_to_qualified and qualified_stage_id:
                try:
                    logger.info(f"Calling backend API to move deal {deal_id} to 'Qualified' stage (stage_id: {qualified_stage_id})")
                    if crm_service.update_deal_stage(deal_id, qualified_stage_id):
                        logger.info(f"✅ Successfully moved deal {deal_id} to 'Qualified' stage via backend API - activities should be created")
                    else:
                        logger.error(f"❌ Failed to move deal {deal_id} to 'Qualified' stage via backend API")
                except Exception as e:
                    logger.error(f"Error calling backend API to move deal {deal_id} to 'Qualified' stage: {e}")
            
            return True
        else:
            logger.info(f"No new fields to update for deal {deal_id}")
            return True
            
    except Exception as e:
        logger.error(f"Error updating deal fields: {e}")
        session.rollback()
        return False
    finally:
        session.close()

def update_deal_fields_force(deal_id: int, **kwargs):
    """Update deal fields by overwriting existing values (for user update requests)."""
    session: Session = SessionLocal()
    try:
        deal = session.query(Deal).filter_by(id=deal_id).first()
        if not deal:
            logger.error(f"Deal with ID {deal_id} not found")
            return False
        
        updated_fields = []
        
        # Update fields if they have values (overwrite existing values)
        if kwargs.get('full_name'):
            old_value = deal.user_name
            deal.user_name = kwargs['full_name']
            updated_fields.append(f'user_name: "{old_value}" → "{kwargs["full_name"]}"')
        
        if kwargs.get('event_type'):
            old_value = deal.event_type
            deal.event_type = kwargs['event_type']
            updated_fields.append(f'event_type: "{old_value}" → "{kwargs["event_type"]}"')
        
        if kwargs.get('event_date'):
            old_value = deal.event_date
            deal.event_date = kwargs['event_date']
            updated_fields.append(f'event_date: "{old_value}" → "{kwargs["event_date"]}"')
        
        if kwargs.get('venue'):
            old_value = deal.venue
            deal.venue = kwargs['venue']
            updated_fields.append(f'venue: "{old_value}" → "{kwargs["venue"]}"')
        
        if kwargs.get('phone_number'):
            old_value = deal.phone_number
            deal.phone_number = kwargs['phone_number']
            updated_fields.append(f'phone_number: "{old_value}" → "{kwargs["phone_number"]}"')

        # Force-update final_thank_you_sent if provided
        if 'final_thank_you_sent' in kwargs:
            old_value = getattr(deal, 'final_thank_you_sent', False)
            new_value = bool(kwargs['final_thank_you_sent'])
            deal.final_thank_you_sent = new_value  # type: ignore[attr-defined]
            updated_fields.append(f'final_thank_you_sent: "{old_value}" → "{new_value}"')
        
        # Force-update contact_number_asked if provided
        if 'contact_number_asked' in kwargs:
            old_value = getattr(deal, 'contact_number_asked', False)
            new_value = bool(kwargs['contact_number_asked'])
            deal.contact_number_asked = new_value  # type: ignore[attr-defined]
            updated_fields.append(f'contact_number_asked: "{old_value}" → "{new_value}"')
        
        # Force-update event_date_asked if provided
        if 'event_date_asked' in kwargs:
            old_value = getattr(deal, 'event_date_asked', False)
            new_value = bool(kwargs['event_date_asked'])
            deal.event_date_asked = new_value  # type: ignore[attr-defined]
            updated_fields.append(f'event_date_asked: "{old_value}" → "{new_value}"')
        
        # Force-update venue_asked if provided
        if 'venue_asked' in kwargs:
            old_value = getattr(deal, 'venue_asked', False)
            new_value = bool(kwargs['venue_asked'])
            deal.venue_asked = new_value  # type: ignore[attr-defined]
            updated_fields.append(f'venue_asked: "{old_value}" → "{new_value}"')
        
        if updated_fields:
            session.commit()
            logger.info(f"Deal {deal_id} forcefully updated with fields: {', '.join(updated_fields)}")
            return True
        else:
            logger.info(f"No fields provided to update for deal {deal_id}")
            return True
            
    except Exception as e:
        logger.error(f"Error forcefully updating deal fields: {e}")
        session.rollback()
        return False
    finally:
        session.close()