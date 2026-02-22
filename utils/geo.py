from __future__ import annotations

import re
from functools import lru_cache
from typing import Any, Dict, Optional

import requests

from config import ENABLE_VENUE_CITY_LOOKUP, NOMINATIM_BASE_URL
from utils.logger import logger


_COUNTRY_STOPWORDS = {
    "india",
    "uae",
    "united arab emirates",
    "qatar",
    "oman",
    "bahrain",
    "saudi arabia",
    "ksa",
    "singapore",
}


def _clean_part(part: str) -> str:
    part = (part or "").strip()
    # Remove common Indian pincode patterns
    part = re.sub(r"\b\d{6}\b", "", part).strip()
    # Remove extra punctuation/spaces
    part = re.sub(r"\s{2,}", " ", part).strip(" -–,")
    return part.strip()


def heuristic_city_from_venue(venue: str) -> Optional[str]:
    """
    Best-effort heuristic for extracting a city-like token from a venue string.
    Used as a fallback when geocoding is unavailable.
    """
    if not venue or not isinstance(venue, str):
        return None

    parts = [_clean_part(p) for p in venue.split(",")]
    parts = [p for p in parts if p]
    if not parts:
        return None

    # Prefer the last meaningful part that's not just a country name.
    for part in reversed(parts):
        if part.lower() in _COUNTRY_STOPWORDS:
            continue
        # Avoid returning very short junk.
        if len(part) < 2:
            continue
        return part

    return None


def _pick_city_from_address(address: Dict[str, Any]) -> Optional[str]:
    # Nominatim returns different keys depending on the place type.
    for key in (
        "city",
        "town",
        "village",
        "municipality",
        "city_district",
        "state_district",
        "county",
        "region",
        "suburb",
        "hamlet",
    ):
        value = address.get(key)
        if isinstance(value, str):
            value = value.strip()
            if value:
                return value
    return None


@lru_cache(maxsize=512)
def resolve_city_from_venue(venue: str) -> Optional[str]:
    """
    Resolve the city name from a venue string.

    Strategy:
    - Try OpenStreetMap Nominatim (if enabled).
    - Fallback to a comma-based heuristic.
    """
    if not venue or not isinstance(venue, str):
        return None

    venue = venue.strip()
    if len(venue) < 3:
        return None

    if not ENABLE_VENUE_CITY_LOOKUP:
        return heuristic_city_from_venue(venue)

    try:
        url = f"{NOMINATIM_BASE_URL}/search"
        params = {
            "q": venue,
            "format": "jsonv2",
            "addressdetails": 1,
            "limit": 1,
        }
        headers = {
            # Nominatim requires a valid User-Agent
            "User-Agent": "TBS-Instagram-Bot/1.0 (venue-to-city enrichment)",
            "Accept": "application/json",
        }
        resp = requests.get(url, params=params, headers=headers, timeout=4)
        if resp.status_code != 200:
            logger.warning("Nominatim lookup failed (%s): %s", resp.status_code, resp.text[:300])
            return heuristic_city_from_venue(venue)

        data = resp.json()
        if not isinstance(data, list) or not data:
            return heuristic_city_from_venue(venue)

        first = data[0]
        if not isinstance(first, dict):
            return heuristic_city_from_venue(venue)

        address = first.get("address")
        if isinstance(address, dict):
            city = _pick_city_from_address(address)
            if city:
                return city

        # Sometimes Nominatim doesn't return addressdetails; fallback.
        return heuristic_city_from_venue(venue)
    except Exception as e:
        logger.warning("City resolution error for venue '%s': %s", venue[:120], e)
        return heuristic_city_from_venue(venue)

