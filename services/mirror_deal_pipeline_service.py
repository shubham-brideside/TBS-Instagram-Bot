"""
Round-robin pipeline assignment for mirror deals (e.g. hub org 117).

Writes the cursor to:
- organizations.mirror_round_robin_last_pipeline_id (bot-local)
- organization_round_robin_routing_state.direct_mirror_last_pipeline_id (CRM / TBS presales DIRECT lane)
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from config import (
    HUB_MIRROR_ORGANIZATION_ID,
    MIRROR_PIPELINE_ORDER_BY_ORG,
    MIRROR_PIPELINE_OWNER_ROLE_NAME,
    MIRROR_PRESALES_DEAL_LANE,
    MIRROR_PRESALES_ROLE_ID,
)
from database.connection import SessionLocal
from models.organization import Organization
from models.organization_round_robin_routing_state import OrganizationRoundRobinRoutingState
from models.pipeline import Pipeline
from models.role import Role
from models.user import User
from models.timestamp_mixin import now_ist
from utils.logger import logger


def _fetch_mirror_direct_lane_default_pipeline_ids(organization_id: int) -> list[int]:
    """
    Ordered distinct ``users.tbs_default_pipeline_id`` for TBS presales DIRECT lane:
    ``is_tbs_user``, ``roles.name`` = MIRROR_PIPELINE_OWNER_ROLE_NAME, optional ``role_id`` match,
    ``tbs_presales_deal_lane``, default pipeline in hub org (not deleted).
    """
    session = SessionLocal()
    try:
        filters = [
            User.is_tbs_user.is_(True),
            User.active.is_(True),
            User.tbs_default_pipeline_id.isnot(None),
            User.tbs_presales_deal_lane.isnot(None),
            func.upper(User.tbs_presales_deal_lane) == MIRROR_PRESALES_DEAL_LANE,
            Role.name == MIRROR_PIPELINE_OWNER_ROLE_NAME,
            Pipeline.organization_id == organization_id,
            Pipeline.is_deleted.is_(False),
        ]
        if MIRROR_PRESALES_ROLE_ID is not None:
            filters.append(User.role_id == MIRROR_PRESALES_ROLE_ID)

        rows = (
            session.query(User.tbs_default_pipeline_id)
            .join(Role, Role.id == User.role_id)
            .join(Pipeline, Pipeline.id == User.tbs_default_pipeline_id)
            .filter(*filters)
            .order_by(User.id.asc())
            .all()
        )
        out: list[int] = []
        seen: set[int] = set()
        for r in rows:
            pid = int(r[0])
            if pid not in seen:
                seen.add(pid)
                out.append(pid)
        return out
    except Exception as e:
        logger.error("Mirror RR: failed to list default pipelines for org %s: %s", organization_id, e)
        return []
    finally:
        session.close()


def _ordered_pipelines_for_mirror_org(organization_id: int) -> list[int]:
    eligible = _fetch_mirror_direct_lane_default_pipeline_ids(organization_id)
    eligible_set = set(eligible)
    explicit = MIRROR_PIPELINE_ORDER_BY_ORG.get(organization_id)
    if explicit:
        ordered_explicit = [pid for pid in explicit if pid in eligible_set]
        skipped = [pid for pid in explicit if pid not in eligible_set]
        if skipped:
            logger.warning(
                "Mirror RR: env pipeline order skipped ids not in DIRECT presales default-pipeline list: %s",
                skipped,
            )
        if ordered_explicit:
            return ordered_explicit
        logger.warning(
            "Mirror RR: TBS_MIRROR_PIPELINE_ORDER_%s matched no eligible pipelines; "
            "using default %s+DIRECT order (%s)",
            organization_id,
            MIRROR_PIPELINE_OWNER_ROLE_NAME,
            eligible,
        )
    return eligible


def _resolve_last_used_mirror_pipeline(
    session,
    mirror_org_id: int,
    routing_state: Optional[OrganizationRoundRobinRoutingState],
    org: Organization,
    ordered: list[int],
) -> Optional[int]:
    """
    Pipeline id of the last mirror assignment, for advancing round-robin.

    Prefer ``organization_round_robin_routing_state.direct_mirror_last_pipeline_id`` (last
    created mirror deal pipeline) when it lies in the current DIRECT presales default-pipeline
    order; otherwise infer from the latest hub mirror deal, then ``organizations.mirror_round_robin_last_pipeline_id``.
    """
    from models.deal import Deal

    ordered_set = set(ordered)
    if routing_state is not None and routing_state.direct_mirror_last_pipeline_id is not None:
        cand = int(routing_state.direct_mirror_last_pipeline_id)
        if cand in ordered_set:
            return cand
        logger.info(
            "Mirror RR: direct_mirror_last_pipeline_id=%s not in current eligible order %s; "
            "inferring last assignment from deals or org cursor",
            cand,
            ordered,
        )

    row = (
        session.query(Deal.pipeline_id)
        .filter(
            Deal.organization_id == mirror_org_id,
            Deal.referenced_deal_id.isnot(None),
        )
        .order_by(Deal.id.desc())
        .limit(1)
        .first()
    )
    if row and row[0] is not None:
        cand = int(row[0])
        if cand in ordered_set:
            return cand

    if org.mirror_round_robin_last_pipeline_id is not None:
        cand = int(org.mirror_round_robin_last_pipeline_id)
        if cand in ordered_set:
            return cand

    return None


def get_mirror_hub_pipeline_owner_user_id(pipeline_id: int) -> Optional[int]:
    """
    Deal owner for hub mirror: ``users.id`` whose ``tbs_default_pipeline_id`` is this pipeline,
    with ``is_tbs_user``, TBS_PRESALES role, and DIRECT presales lane (and optional role_id).
    """
    session = SessionLocal()
    try:
        filters = [
            User.tbs_default_pipeline_id == pipeline_id,
            User.is_tbs_user.is_(True),
            User.active.is_(True),
            Role.name == MIRROR_PIPELINE_OWNER_ROLE_NAME,
            User.tbs_presales_deal_lane.isnot(None),
            func.upper(User.tbs_presales_deal_lane) == MIRROR_PRESALES_DEAL_LANE,
        ]
        if MIRROR_PRESALES_ROLE_ID is not None:
            filters.append(User.role_id == MIRROR_PRESALES_ROLE_ID)
        row = (
            session.query(User.id)
            .join(Role, Role.id == User.role_id)
            .filter(*filters)
            .order_by(User.id.asc())
            .first()
        )
        if not row:
            return None
        return int(row[0])
    except Exception as e:
        logger.error("Mirror RR: failed to resolve presales owner for pipeline %s: %s", pipeline_id, e)
        return None
    finally:
        session.close()


def _next_in_cycle(ordered: list[int], last_used: Optional[int]) -> int:
    if not ordered:
        raise ValueError("ordered pipeline list is empty")
    if last_used is None or last_used not in ordered:
        return ordered[0]
    i = ordered.index(last_used)
    return ordered[(i + 1) % len(ordered)]


def resolve_mirror_deal_pipeline_id(mirror_org_id: int) -> Optional[int]:
    """
    Pick next pipeline for a new mirror deal under mirror_org_id.

    Computes the next pipeline from ``ordered`` = distinct ``users.tbs_default_pipeline_id`` for
    TBS users (``is_tbs_user``), role ``MIRROR_PIPELINE_OWNER_ROLE_NAME``, lane
    ``MIRROR_PRESALES_DEAL_LANE``, optional ``MIRROR_PRESALES_ROLE_ID``, default pipeline in this org.

    ``last_used`` prefers ``direct_mirror_last_pipeline_id`` when it appears in ``ordered``;
    otherwise latest mirror deal / org cursor (see ``_resolve_last_used_mirror_pipeline``).

    Persists the chosen pipeline id to ``direct_mirror_last_pipeline_id`` and
    ``organizations.mirror_round_robin_last_pipeline_id`` plus ``routing_state.updated_at``.
    """
    if mirror_org_id != HUB_MIRROR_ORGANIZATION_ID:
        logger.error(
            "Mirror RR: org %s is not supported (hub mirror round-robin is org %s only)",
            mirror_org_id,
            HUB_MIRROR_ORGANIZATION_ID,
        )
        return None

    ordered = _ordered_pipelines_for_mirror_org(mirror_org_id)
    if not ordered:
        logger.warning(
            "Mirror RR: no default pipelines for org %s (TBS users: is_tbs_user, role %s, lane %s, "
            "tbs_default_pipeline_id in org; optional role_id %s; or TBS_MIRROR_PIPELINE_ORDER_%s)",
            mirror_org_id,
            MIRROR_PIPELINE_OWNER_ROLE_NAME,
            MIRROR_PRESALES_DEAL_LANE,
            MIRROR_PRESALES_ROLE_ID,
            mirror_org_id,
        )
        return None

    session = SessionLocal()
    try:
        org = (
            session.query(Organization)
            .filter(Organization.id == mirror_org_id)
            .with_for_update()
            .first()
        )
        if not org:
            logger.error("Mirror RR: organization %s not found", mirror_org_id)
            session.rollback()
            return None

        routing_state = (
            session.query(OrganizationRoundRobinRoutingState)
            .filter(OrganizationRoundRobinRoutingState.organization_id == mirror_org_id)
            .with_for_update()
            .first()
        )
        if routing_state is None:
            routing_state = OrganizationRoundRobinRoutingState(
                organization_id=mirror_org_id,
                updated_at=now_ist(),
                direct_mirror_last_pipeline_id=None,
                autodivert_mirror_last_pipeline_id=None,
            )
            session.add(routing_state)
            try:
                session.flush()
            except IntegrityError:
                session.rollback()
                session.close()
                return resolve_mirror_deal_pipeline_id(mirror_org_id)

        last_used = _resolve_last_used_mirror_pipeline(
            session, mirror_org_id, routing_state, org, ordered
        )

        next_id = _next_in_cycle(ordered, last_used)

        org.mirror_round_robin_last_pipeline_id = next_id
        routing_state.direct_mirror_last_pipeline_id = next_id
        routing_state.updated_at = now_ist()

        session.commit()

        logger.info(
            "Mirror RR: org=%s assigned pipeline_id=%s order=%s previous_cursor=%s; "
            "persisted organization_round_robin_routing_state.direct_mirror_last_pipeline_id "
            "and organizations.mirror_round_robin_last_pipeline_id",
            mirror_org_id,
            next_id,
            ordered,
            last_used,
        )
        return next_id
    except Exception as e:
        logger.error("Mirror RR: error for org %s: %s", mirror_org_id, e)
        session.rollback()
        return None
    finally:
        session.close()
