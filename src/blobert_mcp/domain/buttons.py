"""Game Boy button and action validation.

No project imports; stdlib only.
"""

from __future__ import annotations

VALID_BUTTONS: frozenset[str] = frozenset(
    {"a", "b", "start", "select", "up", "down", "left", "right"}
)
VALID_ACTIONS: frozenset[str] = frozenset({"press", "release"})


def validate_button(name: str) -> str:
    """Return the normalized lowercase button name, or raise ValueError."""
    normalized = name.lower()
    if normalized not in VALID_BUTTONS:
        valid = sorted(VALID_BUTTONS)
        msg = f"Invalid button: {name!r}. Must be one of {valid}."
        raise ValueError(msg)
    return normalized


def validate_action(action: str) -> str:
    """Return the normalized lowercase action name, or raise ValueError."""
    normalized = action.lower()
    if normalized not in VALID_ACTIONS:
        valid = sorted(VALID_ACTIONS)
        msg = f"Invalid action: {action!r}. Must be one of {valid}."
        raise ValueError(msg)
    return normalized
