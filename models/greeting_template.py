from sqlalchemy import Column, Integer, BigInteger, String, ForeignKey
from database.connection import Base

class GreetingTemplate(Base):
    __tablename__ = "greeting_templates"

    id = Column(Integer, primary_key=True, index=True)
    brideside_vendor_id = Column(BigInteger, ForeignKey("brideside_vendors.id"), nullable=False)
    template_text = Column(String(1000), nullable=False)
    template_order = Column(Integer, default=0)
