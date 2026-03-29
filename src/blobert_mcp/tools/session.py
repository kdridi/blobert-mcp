"""Session management MCP tools: load ROM, query state, reset."""

from __future__ import annotations

from blobert_mcp.domain import rom_header


def register_session_tools(mcp, session) -> None:
    """Register session tools with the FastMCP instance."""

    @mcp.tool()
    def gb_load_rom(rom_path: str, headless: bool = True) -> dict:
        """Load a Game Boy ROM file into the emulator.

        Returns status, the parsed ROM title, and the resolved path.
        Supports headless mode (default: true).
        """
        try:
            session.load_rom(rom_path, headless=headless)
        except FileNotFoundError:
            return {
                "error": "FILE_NOT_FOUND",
                "message": f"ROM file not found: {rom_path}",
            }
        header = rom_header.parse(bytes(session.pyboy.memory[0x0100:0x0150]))
        return {
            "status": "ok",
            "rom_loaded": True,
            "rom_title": header["title"],
            "rom_path": session.rom_path,
        }

    @mcp.tool()
    def get_session_info() -> dict:
        """Return current emulator session state.

        Works whether or not a ROM is loaded.
        """
        if session.rom_loaded:
            header = rom_header.parse(bytes(session.pyboy.memory[0x0100:0x0150]))
            rom_title = header["title"]
            frame_count = session.pyboy.frame_count
            pc = session.pyboy.register_file.PC
        else:
            rom_title = None
            frame_count = 0
            pc = 0
        return {
            "rom_loaded": session.rom_loaded,
            "rom_title": rom_title,
            "frame_count": frame_count,
            "pc": pc,
            "annotation_count": session.kb.annotation_count() if session.kb else 0,
            "save_state_count": len(session.save_states),
        }

    @mcp.tool()
    def gb_reset() -> dict:
        """Reset the emulator to initial state (reloads the current ROM).

        Returns error if no ROM is loaded.
        """
        if not session.rom_loaded:
            return {
                "error": "NO_ROM_LOADED",
                "message": "Load a ROM first with gb_load_rom.",
            }
        session.load_rom(session.rom_path)
        return {"status": "ok", "message": "Emulator reset."}
