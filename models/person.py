from sqlalchemy import Column, BigInteger, Integer, String, Date, Enum, Boolean
from sqlalchemy.orm import mapped_column, Mapped
from models import Base
from models import TimestampMixin
from typing import Optional
from datetime import date
import enum


class PersonSource(enum.Enum):
    INSTAGRAM = "INSTAGRAM"
    WHATSAPP = "WHATSAPP"
    TBS_WEBSITE = "TBS_WEBSITE"
    REFERRAL = "REFERRAL"
    OTHER = "OTHER"


class PersonSubSource(enum.Enum):
    INSTAGRAM = "INSTAGRAM"
    WHATSAPP = "WHATSAPP"
    LANDING_PAGE = "LANDING_PAGE"
    EMAIL = "EMAIL"


class PersonLabel(enum.Enum):
    BRIDAL_MAKEUP = "BRIDAL_MAKEUP"
    PARTY_MAKEUP = "PARTY_MAKEUP"
    ENGAGEMENT = "ENGAGEMENT"
    RECEPTION = "RECEPTION"
    OTHER = "OTHER"


class Person(Base, TimestampMixin):
    __tablename__ = "persons"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Instagram related fields
    instagram_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    insta: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Contact information
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    phone_num: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Personal information
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Lead information
    lead_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    person_source: Mapped[Optional[PersonSource]] = mapped_column(Enum(PersonSource), nullable=True)
    sub_source: Mapped[Optional[PersonSubSource]] = mapped_column(Enum(PersonSubSource), nullable=True)
    label: Mapped[Optional[PersonLabel]] = mapped_column(Enum(PersonLabel), nullable=True)
    
    # Relationships
    organization_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)
    owner_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)
    category_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)
    
    # Legacy fields (kept for backward compatibility)
    category: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_date: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    event_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    manager: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    organization: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    venue: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    wedding_date: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source_organization: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    wedding_city: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Soft delete flag
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default='0')

