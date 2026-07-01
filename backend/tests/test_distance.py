"""Unit tests for delivery distance/ETA estimation."""

from decimal import Decimal

from app.services.distance import estimate_delivery, haversine_km


def test_haversine_known_distance():
    # Phnom Penh (~11.5564, 104.9282) to a point ~3-4 km away.
    km = haversine_km(11.5564, 104.9282, 11.5700, 104.9000)
    assert 2.5 < km < 4.5


def test_haversine_zero():
    assert haversine_km(11.5, 104.9, 11.5, 104.9) == 0.0


def test_estimate_delivery_returns_none_without_coords():
    assert estimate_delivery(None, None, 11.5, 104.9) == (None, None)
    assert estimate_delivery(11.5, 104.9, None, None) == (None, None)


def test_estimate_delivery_includes_prep_time():
    dist, eta = estimate_delivery(11.5564, 104.9282, 11.5700, 104.9000)
    assert isinstance(dist, Decimal)
    assert dist > 0
    # ETA = travel minutes + base prep (15 default), so always > prep floor.
    assert eta is not None and eta >= 15
