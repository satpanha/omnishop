"""Unit tests for the order fulfillment state machine (pure, no DB)."""

import pytest

from app.services import order_state
from app.services.order_state import InvalidTransition


@pytest.mark.parametrize(
    "current,target,allowed",
    [
        ("awaiting_payment", "paid", True),
        ("awaiting_payment", "cancelled", True),
        ("awaiting_payment", "payment_expired", True),
        ("awaiting_payment", "delivered", False),  # illegal jump
        ("paid", "dispatched", True),  # one-tap dispatch
        ("paid", "preparing", True),
        ("preparing", "dispatched", True),
        ("dispatched", "delivered", True),
        ("delivered", "paid", False),  # terminal
        ("cancelled", "paid", False),  # terminal
    ],
)
def test_can_transition(current, target, allowed):
    assert order_state.can_transition(current, target) is allowed


def test_assert_transition_raises_on_illegal():
    with pytest.raises(InvalidTransition):
        order_state.assert_transition("delivered", "paid")


def test_terminal_states():
    assert order_state.is_terminal("delivered")
    assert order_state.is_terminal("cancelled")
    assert order_state.is_terminal("payment_expired")
    assert not order_state.is_terminal("awaiting_payment")


def test_restock_on_set():
    assert "cancelled" in order_state.RESTOCK_ON
    assert "payment_expired" in order_state.RESTOCK_ON
    assert "delivered" not in order_state.RESTOCK_ON
