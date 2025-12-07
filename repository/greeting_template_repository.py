from models.greeting_template import GreetingTemplate
from database.connection import SessionLocal
from sqlalchemy.orm import Session

def get_greeting_templates_by_user_id(brideside_user_id: int) -> list[str]:
    session: Session = SessionLocal()
    try:
        templates = (
            session.query(GreetingTemplate.template_text)
            .filter(GreetingTemplate.brideside_vendor_id == brideside_user_id)
            .order_by(GreetingTemplate.template_order)
            .all()
        )
        return [t[0] for t in templates]
    finally:
        session.close()
