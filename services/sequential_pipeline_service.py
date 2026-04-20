"""
Sequential pipeline selection for new Instagram deals (one pipeline per new deal, in order).

Aligns with CRM round-robin ordering (pipeline id ascending) when using DB discovery.
Persists the cursor on organizations.round_robin_last_pipeline_id with SELECT ... FOR UPDATE.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from config import (
    SEQUENTIAL_PIPELINE_ORDER_BY_ORG,
    SEQUENTIAL_PIPELINE_ORG_IDS,
    SEQUENTIAL_PIPELINE_PAIRS,
    SEQUENTIAL_PIPELINE_VENDOR_IDS,
)
from database.connection import SessionLocal
from models.organization import Organization
from models.pipeline import Pipeline
from utils.logger import logger


def _sequential_rotation_applies(organization_id: Optional[int], brideside_vendor_id: int) -> bool:
    if organization_id is None:
        return False
    if SEQUENTIAL_PIPELINE_PAIRS:
        return (organization_id, brideside_vendor_id) in SEQUENTIAL_PIPELINE_PAIRS
    if organization_id not in SEQUENTIAL_PIPELINE_ORG_IDS:
        return False
    if not SEQUENTIAL_PIPELINE_VENDOR_IDS:
        return True
    return brideside_vendor_id in SEQUENTIAL_PIPELINE_VENDOR_IDS


def _fetch_pipeline_ids_ordered_by_id(organization_id: int) -> list[int]:
    session = SessionLocal()
    try:
        rows = (
            session.query(Pipeline.id)
            .filter(
                Pipeline.organization_id == organization_id,
                Pipeline.is_deleted.is_(False),
            )
            .order_by(Pipeline.id.asc())
            .all()
        )
        return [int(r[0]) for r in rows]
    except Exception as e:
        logger.error("Sequential pipeline: failed to list pipelines for org %s: %s", organization_id, e)
        return []
    finally:
        session.close()


def _ordered_pipelines_for_org(organization_id: int) -> list[int]:
    explicit = SEQUENTIAL_PIPELINE_ORDER_BY_ORG.get(organization_id)
    if explicit:
        return list(explicit)
    return _fetch_pipeline_ids_ordered_by_id(organization_id)


def _next_in_cycle(ordered: list[int], last_used: Optional[int]) -> int:
    if not ordered:
        raise ValueError("ordered pipeline list is empty")
    if last_used is None or last_used not in ordered:
        return ordered[0]
    i = ordered.index(last_used)
    return ordered[(i + 1) % len(ordered)]


def resolve_pipeline_id_for_new_instagram_deal(
    organization_id: Optional[int],
    brideside_vendor_id: int,
    default_pipeline_id: Optional[int],
) -> Optional[int]:
    """
    When configured, assign the next pipeline in rotation for this org (and optional vendor filter).
    Reads/writes organizations.round_robin_last_pipeline_id under a row lock.
    Otherwise returns default_pipeline_id unchanged.
    """
    if not _sequential_rotation_applies(organization_id, brideside_vendor_id):
        return default_pipeline_id
    assert organization_id is not None

    ordered = _ordered_pipelines_for_org(organization_id)
    if not ordered:
        logger.warning(
            "Sequential pipeline: no pipelines for org %s (set TBS_SEQUENTIAL_PIPELINE_ORDER_%s or DB pipelines); using default pipeline %s",
            organization_id,
            organization_id,
            default_pipeline_id,
        )
        return default_pipeline_id

    session: Session = SessionLocal()
    try:
        org = (
            session.query(Organization)
            .filter(Organization.id == organization_id)
            .with_for_update()
            .first()
        )
        if not org:
            logger.error("Sequential pipeline: organization %s not found; using default pipeline %s", organization_id, default_pipeline_id)
            session.rollback()
            return default_pipeline_id

        last_raw = org.round_robin_last_pipeline_id
        last_used: Optional[int] = int(last_raw) if last_raw is not None else None

        next_id = _next_in_cycle(ordered, last_used)
        org.round_robin_last_pipeline_id = next_id
        session.commit()

        logger.info(
            "Sequential pipeline rotation: org=%s vendor=%s assigned pipeline_id=%s (order=%s, round_robin_last_pipeline_id was=%s)",
            organization_id,
            brideside_vendor_id,
            next_id,
            ordered,
            last_used,
        )
        return next_id
    except Exception as e:
        logger.error("Sequential pipeline: error updating round_robin_last_pipeline_id: %s; using default pipeline %s", e, default_pipeline_id)
        session.rollback()
        return default_pipeline_id
    finally:
        session.close()
