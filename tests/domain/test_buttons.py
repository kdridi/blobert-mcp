"""TDD tests for button/action validation domain module.

Written before implementation (TDD).
"""

from __future__ import annotations

import pytest

from blobert_mcp.domain.buttons import (
    VALID_ACTIONS,
    VALID_BUTTONS,
    validate_action,
    validate_button,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants:
    def test_valid_buttons_set(self):
        assert VALID_BUTTONS == frozenset(
            {"a", "b", "start", "select", "up", "down", "left", "right"}
        )

    def test_valid_actions_set(self):
        assert VALID_ACTIONS == frozenset({"press", "release"})

    def test_valid_buttons_is_frozenset(self):
        assert isinstance(VALID_BUTTONS, frozenset)

    def test_valid_actions_is_frozenset(self):
        assert isinstance(VALID_ACTIONS, frozenset)


# ---------------------------------------------------------------------------
# validate_button
# ---------------------------------------------------------------------------


class TestValidateButton:
    @pytest.mark.parametrize(
        "button",
        ["a", "b", "start", "select", "up", "down", "left", "right"],
    )
    def test_valid_buttons_accepted(self, button: str):
        result = validate_button(button)
        assert result == button

    def test_returns_normalized_lowercase(self):
        assert validate_button("A") == "a"
        assert validate_button("Start") == "start"
        assert validate_button("UP") == "up"
        assert validate_button("SELECT") == "select"

    def test_invalid_button_raises_valueerror(self):
        with pytest.raises(ValueError, match="button"):
            validate_button("x")

    def test_unknown_name_raises_valueerror(self):
        with pytest.raises(ValueError, match="button"):
            validate_button("jump")

    def test_empty_string_raises_valueerror(self):
        with pytest.raises(ValueError):
            validate_button("")

    def test_error_message_includes_invalid_value(self):
        with pytest.raises(ValueError, match="invalid_btn"):
            validate_button("invalid_btn")

    def test_return_type_is_str(self):
        result = validate_button("a")
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# validate_action
# ---------------------------------------------------------------------------


class TestValidateAction:
    @pytest.mark.parametrize("action", ["press", "release"])
    def test_valid_actions_accepted(self, action: str):
        result = validate_action(action)
        assert result == action

    def test_returns_normalized_lowercase(self):
        assert validate_action("Press") == "press"
        assert validate_action("RELEASE") == "release"

    def test_invalid_action_raises_valueerror(self):
        with pytest.raises(ValueError, match="action"):
            validate_action("hold")

    def test_empty_string_raises_valueerror(self):
        with pytest.raises(ValueError):
            validate_action("")

    def test_error_message_includes_invalid_value(self):
        with pytest.raises(ValueError, match="toggle"):
            validate_action("toggle")

    def test_return_type_is_str(self):
        result = validate_action("press")
        assert isinstance(result, str)
