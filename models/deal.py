from sqlalchemy import Column, Integer, BigInteger, String, DECIMAL, ForeignKey, TIMESTAMP, Date, Boolean, UniqueConstraint, Enum, JSON, SmallInteger
from sqlalchemy.orm import relationship
from models import Base 
from datetime import datetime
from models import TimestampMixin
from typing import Optional
import enum


class DealStatus(enum.Enum):
    WON = "WON"
    LOST = "LOST"
    IN_PROGRESS = "IN_PROGRESS"


class DealLabel(enum.Enum):
    DIRECT = "DIRECT"
    DIVERT = "DIVERT"
    DESTINATION = "DESTINATION"
    PARTY_MAKEUP = "PARTY_MAKEUP"
    PRE_WEDDING = "PRE_WEDDING"


class LostReason(enum.Enum):
    SLOT_NOT_OPENED = "SLOT_NOT_OPENED"
    NOT_INTERESTED = "NOT_INTERESTED"
    DATE_POSTPONED = "DATE_POSTPONED"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    GHOSTED = "GHOSTED"
    BUDGET = "BUDGET"
    BOOKED_SOMEONE_ELSE = "BOOKED_SOMEONE_ELSE"


class DealSubSource(enum.Enum):
    INSTAGRAM = "INSTAGRAM"
    WHATSAPP = "WHATSAPP"
    LANDING_PAGE = "LANDING_PAGE"
    EMAIL = "EMAIL"


class CreatedBy(enum.Enum):
    USER = "USER"
    BOT = "BOT"


class Deal(Base, TimestampMixin):
    __tablename__ = "deals"

    id = Column(BigInteger, primary_key=True, autoincrement=True, index=True)
    name = Column(String(100), nullable=False)
    value = Column(DECIMAL(12, 2), nullable=False)
    deal_value = Column(DECIMAL(10, 2), nullable=True)  # Legacy field
    contact_number = Column(String(20), nullable=False)
    phone_number = Column(String(255), nullable=True)
    
    # Status and categorization
    status = Column(Enum(DealStatus), nullable=False, default=DealStatus.IN_PROGRESS)
    category = Column(String(50), nullable=False)
    label = Column(Enum(DealLabel), nullable=True)
    deal_source = Column(String(50), nullable=True)
    deal_sub_source = Column(Enum(DealSubSource), nullable=True)
    lost_reason = Column(Enum(LostReason), nullable=True)
    
    # Event information
    event_type = Column(String(255), nullable=True)
    event_date = Column(Date, nullable=True)
    event_dates = Column(JSON, nullable=True)  # Multiple dates support
    venue = Column(String(255), nullable=True)
    expected_gathering = Column(Integer, nullable=True)
    budget = Column(DECIMAL(10, 2), nullable=True)
    
    # Relationships
    person_id = Column(BigInteger, ForeignKey("persons.id"), nullable=True, index=True)
    organization_id = Column(BigInteger, ForeignKey("organizations.id"), nullable=True, index=True)
    pipeline_id = Column(BigInteger, ForeignKey("pipelines.id"), nullable=True, index=True)
    stage_id = Column(BigInteger, ForeignKey("stages.id"), nullable=True, index=True)
    source_id = Column(BigInteger, ForeignKey("sources.id"), nullable=True, index=True)
    category_id = Column(BigInteger, ForeignKey("categories.id"), nullable=True, index=True)
    contacted_to = Column(BigInteger, ForeignKey("brideside_vendors.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Deal diversion fields
    is_diverted = Column(SmallInteger, nullable=False, default=0)
    referenced_deal_id = Column(BigInteger, ForeignKey("deals.id"), nullable=True, index=True)
    referenced_pipeline_id = Column(BigInteger, ForeignKey("pipelines.id"), nullable=True, index=True)
    source_pipeline_id = Column(BigInteger, ForeignKey("pipelines.id"), nullable=True, index=True)
    pipeline_history = Column(JSON, nullable=True)
    
    # Financial
    commission_amount = Column(DECIMAL(12, 2), nullable=True)
    
    # Legacy/Pipedrive fields
    pipedrive_deal_id = Column(String(100), nullable=True)
    contact_id = Column(Integer, nullable=True)
    user_name = Column(String(255), nullable=True)  # Stores the person's full name
    won = Column(Boolean, nullable=True)  # Legacy field
    
    # Google Calendar integration
    google_calendar_event_id = Column(String(255), nullable=True)
    google_calendar_event_ids = Column(JSON, nullable=True)  # Multiple events support
    
    # Audit
    created_by = Column(Enum(CreatedBy), nullable=True, default=None)
    created_by_name = Column(String(255), nullable=True)

    # Flags
    final_thank_you_sent = Column(Boolean, nullable=True, default=False)
    contact_number_asked = Column(Boolean, nullable=True, default=False)
    event_date_asked = Column(Boolean, nullable=True, default=False)
    venue_asked = Column(Boolean, nullable=True, default=False)
    is_deleted = Column(SmallInteger, nullable=False, default=0)
    
    # Relationships
    conversation_summaries = relationship("InstagramConversationSummary", back_populates="deal")
    
    # Unique constraint to ensure one deal per username per brideside user
    __table_args__ = (
        UniqueConstraint('name', 'contacted_to', name='uq_deal_name_contacted_to'),
    )
    
    def __repr__(self):
        return f"<Deal(id={self.id}, name='{self.name}', status='{self.status}')>"