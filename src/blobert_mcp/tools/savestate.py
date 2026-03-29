"""Save state MCP tools: save, load, list, and delete."""

from __future__ import annotations

import time
from io import BytesIO

from blobert_mcp.domain import registers


def register_savestate_tools(mcp, session) -> None:
    """Register save state tools with the FastMCP instance."""

    @mcp.tool()
    def gb_save_state(name: str | None = None) -> dict:
        """Save the current emulator state to memory.

        States are stored in-memory (lost on server restart). Each save gets
        an auto-incrementing integer ID. Supports an optional human-readable
        name. Returns the state_id and metadata.
        """
        if not session.rom_loaded:
            return {
                "error": "NO_ROM_LOADED",
                "message": "Load a ROM first with gb_load_rom.",
            }
        buffer = BytesIO()
        session.pyboy.save_state(buffer)
        state_id = session.next_state_id
        session.next_state_id += 1
        rf = session.pyboy.register_file
        session.save_states[state_id] = {
            "buffer": buffer,
            "name": name,
            "frame_count": session.pyboy.frame_count,
            "pc": rf.PC,
            "timestamp": time.time(),
        }
        return {
            "status": "ok",
            "state_id": state_id,
            "name": name,
            "frame_count": session.pyboy.frame_count,
            "pc": rf.PC,
        }

    @mcp.tool()
    def gb_load_state(state_id: int) -> dict:
        """Restore a previously saved emulator state.

        Returns registers as they are after restoration. Returns
        {"error": "NOT_FOUND", ...} if the state_id does not exist.
        """
        if not session.rom_loaded:
            return {
                "error": "NO_ROM_LOADED",
                "message": "Load a ROM first with gb_load_rom.",
            }
        if state_id not in session.save_states:
            return {
                "error": "NOT_FOUND",
                "message": f"State {state_id} not found.",
            }
        state = session.save_states[state_id]
        state["buffer"].seek(0)
        session.pyboy.load_state(state["buffer"])
        rf = session.pyboy.register_file
        return {
            "status": "ok",
            "state_id": state_id,
            "name": state.get("name"),
            "registers": registers.format_registers(
                rf.A, rf.B, rf.C, rf.D, rf.E, rf.F, rf.H, rf.L, rf.SP, rf.PC
            ),
        }

    @mcp.tool()
    def gb_list_states() -> dict:
        """List all saved emulator states with metadata.

        Returns state_id, name, frame_count, pc, and timestamp for each
        saved state. Does not include the raw state buffer.
        """
        if not session.rom_loaded:
            return {
                "error": "NO_ROM_LOADED",
                "message": "Load a ROM first with gb_load_rom.",
            }
        states = [
            {
                "state_id": sid,
                "name": s["name"],
                "frame_count": s["frame_count"],
                "pc": s["pc"],
                "timestamp": s["timestamp"],
            }
            for sid, s in session.save_states.items()
        ]
        return {"status": "ok", "states": states}

    @mcp.tool()
    def gb_delete_state(state_id: int) -> dict:
        """Delete a previously saved emulator state.

        Returns {"error": "NOT_FOUND", ...} if the state_id does not exist.
        """
        if not session.rom_loaded:
            return {
                "error": "NO_ROM_LOADED",
                "message": "Load a ROM first with gb_load_rom.",
            }
        if state_id not in session.save_states:
            return {
                "error": "NOT_FOUND",
                "message": f"State {state_id} not found.",
            }
        session.save_states.pop(state_id)
        return {"status": "ok", "state_id": state_id}
