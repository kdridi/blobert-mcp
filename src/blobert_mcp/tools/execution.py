"""Execution control MCP tools: gb_step, gb_run_until, gb_get_registers."""

from __future__ import annotations

from blobert_mcp.domain import registers
from blobert_mcp.domain.disasm.decoder import decode_instruction


def register_execution_tools(mcp, session) -> None:
    """Register execution tools with the FastMCP instance."""

    @mcp.tool()
    def gb_step(count: int = 1, mode: str = "frame") -> dict:
        """Advance emulation by *count* steps and return CPU state.

        Modes:
        - "frame": advance *count* frames (fast, default).
        - "instruction": advance *count* individual CPU instructions via
          hook-based stepping (slower, precise).

        Returns current PC, decoded instruction at the new PC, and full
        register state.
        """
        if mode not in ("frame", "instruction"):
            return {
                "error": "INVALID_PARAMETER",
                "message": f"Invalid mode: {mode!r}. Use 'frame' or 'instruction'.",
            }
        if not session.rom_loaded:
            return {
                "error": "NO_ROM_LOADED",
                "message": "Load a ROM first with gb_load_rom.",
            }

        if mode == "frame":
            for _ in range(count):
                session.pyboy.tick()
            rf = session.pyboy.register_file
            pc = rf.PC
            raw = bytes(session.pyboy.memory[pc : pc + 3])
            instr = decode_instruction(raw, pc)
            return {
                "status": "ok",
                "frames_executed": count,
                "pc": pc,
                "instruction": {
                    "mnemonic": instr.mnemonic,
                    "operands": instr.operands,
                },
                "registers": registers.format_registers(
                    rf.A, rf.B, rf.C, rf.D, rf.E, rf.F, rf.H, rf.L, rf.SP, rf.PC
                ),
            }

        # mode == "instruction"
        for _ in range(count):
            pc = session.pyboy.register_file.PC
            raw = bytes(session.pyboy.memory[pc : pc + 3])
            instr = decode_instruction(raw, pc)
            next_pc = (pc + instr.size) & 0xFFFF

            hit = [False]

            def _on_step(context: list) -> None:
                context[0] = True

            session.pyboy.hook_register(next_pc, _on_step, hit)
            frames = 0
            while not hit[0] and frames < 10:
                session.pyboy.tick()
                frames += 1
            session.pyboy.hook_deregister(next_pc)

        rf = session.pyboy.register_file
        pc = rf.PC
        raw = bytes(session.pyboy.memory[pc : pc + 3])
        next_instr = decode_instruction(raw, pc)
        return {
            "status": "ok",
            "instructions_executed": count,
            "pc": pc,
            "instruction": {
                "mnemonic": next_instr.mnemonic,
                "operands": next_instr.operands,
            },
            "registers": registers.format_registers(
                rf.A, rf.B, rf.C, rf.D, rf.E, rf.F, rf.H, rf.L, rf.SP, rf.PC
            ),
        }

    @mcp.tool()
    def gb_run_until(target_address: int, timeout_frames: int = 600) -> dict:
        """Execute until *target_address* is hit or *timeout_frames* exceeded.

        Registers a hook at the target address and ticks until the hook fires
        or the frame budget runs out. Returns registers at the breakpoint or
        {"error": "TIMEOUT", ...} if the target was not reached.
        """
        if not session.rom_loaded:
            return {
                "error": "NO_ROM_LOADED",
                "message": "Load a ROM first with gb_load_rom.",
            }
        hit = [False]

        def _on_hit(context: list) -> None:
            context[0] = True

        session.pyboy.hook_register(target_address, _on_hit, hit)
        frames = 0
        while not hit[0] and frames < timeout_frames:
            session.pyboy.tick()
            frames += 1
        if not hit[0]:
            return {
                "error": "TIMEOUT",
                "message": (
                    f"Target 0x{target_address:04X} not reached within "
                    f"{timeout_frames} frames."
                ),
            }
        rf = session.pyboy.register_file
        return {
            "status": "ok",
            "target_address": f"0x{target_address:04X}",
            "frames_executed": frames,
            "registers": registers.format_registers(
                rf.A, rf.B, rf.C, rf.D, rf.E, rf.F, rf.H, rf.L, rf.SP, rf.PC
            ),
        }

    @mcp.tool()
    def gb_get_registers() -> dict:
        """Read all CPU registers and return them in spec format.

        Returns the full SM83 register set including composite registers
        (AF, BC, DE, HL) and individual flag bits.
        """
        if not session.rom_loaded:
            return {
                "error": "NO_ROM_LOADED",
                "message": "Load a ROM first with gb_load_rom.",
            }
        rf = session.pyboy.register_file
        return registers.format_registers(
            rf.A, rf.B, rf.C, rf.D, rf.E, rf.F, rf.H, rf.L, rf.SP, rf.PC
        )
