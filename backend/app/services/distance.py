"""
Delivery distance & ETA estimation.

v1 uses a straight-line (haversine) estimate from the store's coordinates to the
buyer's pinned location, converted to minutes via a configurable average speed
plus a fixed prep time. The owner can always override the ETA manually.

The estimator is behind a small interface (``DistanceEstimator``) so a real
provider (e.g. Google Distance Matrix) can be dropped in later without touching
callers — swap the implementation returned by :func:`get_estimator`.
"""

from __future__ import annotations

import logging
import math
from decimal import Decimal
from typing import Protocol

from app.config import get_settings

logger = logging.getLogger(__name__)

EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance between two lat/lng points, in kilometres."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return EARTH_RADIUS_KM * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class DistanceEstimator(Protocol):
    """Pluggable distance/ETA strategy."""

    def estimate(
        self, origin: tuple[float, float], dest: tuple[float, float]
    ) -> tuple[Decimal, int]:
        """Return (distance_km, eta_minutes)."""
        ...


class HaversineEstimator:
    """Straight-line distance + constant-speed ETA (the v1 default)."""

    def __init__(self, speed_kmh: float, base_prep_minutes: int) -> None:
        self.speed_kmh = max(speed_kmh, 1.0)  # guard against div-by-zero
        self.base_prep_minutes = base_prep_minutes

    def estimate(
        self, origin: tuple[float, float], dest: tuple[float, float]
    ) -> tuple[Decimal, int]:
        km = haversine_km(origin[0], origin[1], dest[0], dest[1])
        travel_minutes = (km / self.speed_kmh) * 60.0
        eta = int(round(travel_minutes)) + self.base_prep_minutes
        return Decimal(f"{km:.2f}"), eta


def get_estimator() -> DistanceEstimator:
    """Return the configured estimator. Future: switch on a settings flag."""
    settings = get_settings()
    return HaversineEstimator(
        speed_kmh=settings.DELIVERY_SPEED_KMH,
        base_prep_minutes=settings.DELIVERY_BASE_PREP_MINUTES,
    )


def estimate_delivery(
    store_lat: float | Decimal | None,
    store_lng: float | Decimal | None,
    dest_lat: float | Decimal | None,
    dest_lng: float | Decimal | None,
) -> tuple[Decimal | None, int | None]:
    """
    Best-effort ETA. Returns (None, None) when either endpoint lacks coordinates
    — the order is still allowed; the owner sets the ETA manually. Never raises:
    a calc failure is logged and degrades to (None, None).
    """
    if None in (store_lat, store_lng, dest_lat, dest_lng):
        return None, None
    try:
        return get_estimator().estimate(
            (float(store_lat), float(store_lng)),  # type: ignore[arg-type]
            (float(dest_lat), float(dest_lng)),  # type: ignore[arg-type]
        )
    except Exception as exc:  # noqa: BLE001 - ETA is non-critical, degrade gracefully
        logger.warning("ETA estimation failed, degrading to manual: %s", exc)
        return None, None
