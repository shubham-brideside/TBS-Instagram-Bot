from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime, func, ForeignKey
from models import Base
from models import TimestampMixin

class CourseRelatedUser(Base, TimestampMixin):
    __tablename__ = "course_related_users"
    id = Column(BigInteger, primary_key=True, autoincrement=True, index=True)
    instagram_username = Column(String(255), unique=True, index=True, nullable=False)
    brideside_vendor_id = Column(BigInteger, ForeignKey("brideside_vendors.id", ondelete="CASCADE"), nullable=False, index=True)
