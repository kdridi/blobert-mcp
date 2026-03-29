"""Input MCP tools: gb_press_button."""

from __future__ import annotations

from blobert_mcp.domain import buttons


def register_input_tools(mcp, session) -> None:
    """Register input tools with the FastMCP instance."""

    @mcp.tool()
    def gb_press_button(button: str, action: str = "press") -> dict:
        """Press or release a Game Boy button.

        Validates the button name and action via domain functions. Does NOT
        automatically advance a frame — the caller controls timing.

        Valid buttons: a, b, start, select, up, down, left, right.
        Valid actions: press, release.
        """
        if not session.rom_loaded:
            return {
                "error": "NO_ROM_LOADED",
                "message": "Load a ROM first with gb_load_rom.",
            }
        try:
            button = buttons.validate_button(button)
            action = buttons.validate_action(action)
        except ValueError as exc:
            return {"error": "INVALID_PARAMETER", "message": str(exc)}
        if action == "press":
            session.pyboy.button_press(button)
        else:
            session.pyboy.button_release(button)
        return {"status": "ok", "button": button, "action": action}
