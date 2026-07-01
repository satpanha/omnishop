"""
Order fulfillment state machine.

Pure, side-effect-free validation of order status transitions. The DB-touching
effects (restock on cancel/expire, ETA on dispatch, notifications) live in
``app.services.orders`` — this module only answers "is this transition legal?".

    awaiting_payment → paid → preparing → dispatched → delivered
    side exits: cancelled, payment_expired
"""

from __future__ import annotations

ORDER_TRANSITIONS: dict[str, set[str]] = {
    # 'preparing' is an optional intermediate; the owner may also dispatch a paid
    # order directly so the actionable alert is a single tap.
    "awaiting_payment": {"paid", "cancelled", "payment_expired"},
    "paid": {"preparing", "dispatched", "cancelled"},
    "preparing": {"dispatched", "cancelled"},
    "dispatched": {"delivered"},
    "delivered": set(),
    "cancelled": set(),
    "payment_expired": set(),
}

TERMINAL_STATES: frozenset[str] = frozenset(
    {"delivered", "cancelled", "payment_expired"}
)

# Transitions that should return stock to inventory.
RESTOCK_ON: frozenset[str] = frozenset({"cancelled", "payment_expired"})


class InvalidTransition(ValueError):
    """Raised when an illegal order status transition is attempted."""


def can_transition(current: str, target: str) -> bool:
    """True if moving from ``current`` to ``target`` is allowed."""
    return target in ORDER_TRANSITIONS.get(current, set())


def assert_transition(current: str, target: str) -> None:
    """Raise :class:`InvalidTransition` if the transition is not allowed."""
    if not can_transition(current, target):
        raise InvalidTransition(
            f"Cannot move order from '{current}' to '{target}'"
        )


def is_terminal(status: str) -> bool:
    return status in TERMINAL_STATES
