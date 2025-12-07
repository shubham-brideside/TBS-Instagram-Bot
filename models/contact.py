from sqlalchemy import Column, Integer, String, DateTime, func
from models import Base
from models import TimestampMixin

class Contact(Base, TimestampMixin):
    __tablename__ = "contacts"
    id = Column(Integer, primary_key=True, index=True)
    contact_name = Column(String(255), unique=True, index=True)
    pipedrive_contact_id = Column(String(100))