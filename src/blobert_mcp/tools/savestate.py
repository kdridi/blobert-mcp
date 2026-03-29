"""Save state MCP tools: save, load, list, and delete."""

from __future__ import annotations

import time
from io import BytesIO

from blobert_mcp.domain import registers
from blobert_mcp.domain.memory_diff import MAX_CHANGES, diff_memory
from blobert_mcp.domain.memory_map import (
    DEFAULT_DIFF_REGION_NAMES,
    resolve_regions,
)


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

    @mcp.tool()
    def gb_memory_diff(
        state_id_a: int,
        state_id_b: int,
        regions: list[str] | None = None,
    ) -> dict:
        """Compare memory between two save states and return changed bytes.

        Loads each state, dumps the requested memory regions, restores the
        original emulator state, and diffs the two dumps. Returns a list of
        ``(address, old_value, new_value)`` changes.

        The optional *regions* parameter accepts region names (e.g.
        ``["WRAM", "HRAM"]``). Prefix matching is supported: ``"WRAM"``
        matches both WRAM0 and WRAMX. Defaults to WRAM0 + WRAMX + HRAM.
        """
        if not session.rom_loaded:
            return {
                "error": "NO_ROM_LOADED",
                "message": "Load a ROM first with gb_load_rom.",
            }
        if state_id_a not in session.save_states:
            return {
                "error": "NOT_FOUND",
                "message": f"State {state_id_a} not found.",
            }
        if state_id_b not in session.save_states:
            return {
                "error": "NOT_FOUND",
                "message": f"State {state_id_b} not found.",
            }

        # Resolve regions
        region_names = list(regions) if regions else list(DEFAULT_DIFF_REGION_NAMES)
        try:
            resolved = resolve_regions(region_names)
        except ValueError as exc:
            return {"error": "INVALID_PARAMETER", "message": str(exc)}

        # Save current state so we can restore it after diffing
        tmp_buffer = BytesIO()
        session.pyboy.save_state(tmp_buffer)
        try:
            # Load state_a and dump memory for each region
            state_a = session.save_states[state_id_a]
            state_a["buffer"].seek(0)
            session.pyboy.load_state(state_a["buffer"])
            dumps_a = {}
            for region in resolved:
                raw = session.pyboy.memory[region.start : region.start + region.size]
                dumps_a[region.name] = bytes(raw)

            # Load state_b and dump memory for each region
            state_b = session.save_states[state_id_b]
            state_b["buffer"].seek(0)
            session.pyboy.load_state(state_b["buffer"])
            dumps_b = {}
            for region in resolved:
                raw = session.pyboy.memory[region.start : region.start + region.size]
                dumps_b[region.name] = bytes(raw)
        finally:
            # Restore original emulator state
            tmp_buffer.seek(0)
            session.pyboy.load_state(tmp_buffer)

        # Diff each region
        all_changes = []
        for region in resolved:
            changes = diff_memory(
                dumps_a[region.name], dumps_b[region.name], region.start
            )
            all_changes.extend(changes)

        total = len(all_changes)
        truncated = total > MAX_CHANGES
        if truncated:
            all_changes = all_changes[:MAX_CHANGES]

        formatted = [
            {
                "address": f"0x{c.address:04X}",
                "old": f"0x{c.old:02X}",
                "new": f"0x{c.new:02X}",
            }
            for c in all_changes
        ]

        result: dict = {
            "status": "ok",
            "state_id_a": state_id_a,
            "state_id_b": state_id_b,
            "regions_scanned": [r.name for r in resolved],
            "total": total,
            "changes": formatted,
        }
        if truncated:
            result["truncated"] = True
        return result
