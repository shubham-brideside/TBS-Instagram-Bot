"""CRM mirror routing cursor (e.g. DIRECT lane presales round-robin)."""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class OrganizationRoundRobinRoutingState(Base):
    __tablename__ = "organization_round_robin_routing_state"

    organization_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("organizations.id"), primary_key=True
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    autodivert_mirror_last_pipeline_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("pipelines.id"), nullable=True
    )
    direct_mirror_last_pipeline_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("pipelines.id"), nullable=True
    )
