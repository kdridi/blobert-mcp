"""Visual MCP tools: gb_screenshot."""

from __future__ import annotations

from io import BytesIO

from mcp.server.fastmcp.utilities.types import Image
from PIL import Image as PILImage


def register_visual_tools(mcp, session) -> None:
    """Register visual tools with the FastMCP instance."""

    @mcp.tool()
    def gb_screenshot(format: str = "png", scale: int = 1):
        """Capture the Game Boy screen as a base64-encoded image.

        Returns the screen buffer via MCP's image content type for multimodal
        display. Supports PNG and WebP formats, with optional integer scaling
        (nearest-neighbor interpolation preserves pixel art).
        """
        if not session.rom_loaded:
            return {
                "error": "NO_ROM_LOADED",
                "message": "Load a ROM first with gb_load_rom.",
            }
        fmt = format.lower()
        if fmt not in ("png", "webp"):
            return {
                "error": "INVALID_PARAMETER",
                "message": f"Invalid format: {format!r}. Use 'png' or 'webp'.",
            }
        if scale < 1:
            return {
                "error": "INVALID_PARAMETER",
                "message": f"Scale must be >= 1, got {scale}.",
            }

        image = session.pyboy.screen.image
        if scale > 1:
            image = image.resize(
                (image.width * scale, image.height * scale),
                PILImage.NEAREST,
            )

        buf = BytesIO()
        image.save(buf, format=fmt.upper())
        return Image(data=buf.getvalue(), format=fmt)
