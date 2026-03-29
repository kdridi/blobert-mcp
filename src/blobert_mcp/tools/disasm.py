"""Disassembly MCP tools.

gb_disassemble_range, gb_disassemble_function, gb_disassemble_at_pc.
"""

from __future__ import annotations

from blobert_mcp.domain.disasm.decoder import Instruction
from blobert_mcp.domain.disasm.disassembler import (
    disassemble_at_pc,
    disassemble_function,
    disassemble_range,
)


def _fmt(instr: Instruction, *, current: bool = False) -> dict:
    """Format an Instruction as a tool output dict."""
    d = {
        "address": f"0x{instr.address:04X}",
        "bytes": " ".join(f"{b:02X}" for b in instr.raw_bytes),
        "mnemonic": instr.mnemonic,
        "operands": instr.operands,
        "size": instr.size,
    }
    if current:
        d["current"] = True
    return d


def register_disasm_tools(mcp, session) -> None:
    """Register disassembly tools with the FastMCP instance."""

    def _reader():
        return lambda addr, n: bytes(session.pyboy.memory[addr : addr + n])

    @mcp.tool()
    def gb_disassemble_range(
        address: int,
        length: int | None = None,
        end_address: int | None = None,
    ) -> dict:
        """Disassemble SM83 instructions starting at *address*.

        Decodes forward until *length* bytes are consumed, *end_address* is reached,
        or the 256-instruction safety cap is hit. At least one of *length* or
        *end_address* must be provided. Returns error if no ROM loaded.
        """
        if length is None and end_address is None:
            return {
                "error": "INVALID_PARAMETER",
                "message": "Provide at least one of 'length' or 'end_address'.",
            }
        if not session.rom_loaded:
            return {
                "error": "NO_ROM_LOADED",
                "message": "Load a ROM first with gb_load_rom.",
            }
        instrs = disassemble_range(
            _reader(), address, length=length, end_address=end_address
        )
        return {
            "address": f"0x{address:04X}",
            "count": len(instrs),
            "instructions": [_fmt(i) for i in instrs],
        }

    @mcp.tool()
    def gb_disassemble_function(entry_point: int) -> dict:
        """Trace a function from *entry_point* to its terminal instruction.

        Stops at unconditional RET (0xC9), RETI (0xD9), or JP nn (0xC3) that jumps
        outside the traced range. Safety cap: 1024 instructions. Returns error if no
        ROM loaded.
        """
        if not session.rom_loaded:
            return {
                "error": "NO_ROM_LOADED",
                "message": "Load a ROM first with gb_load_rom.",
            }
        result = disassemble_function(_reader(), entry_point)
        instrs = result["instructions"]
        return {
            "entry_point": f"0x{entry_point:04X}",
            "size_bytes": result["size_bytes"],
            "count": len(instrs),
            "instructions": [_fmt(i) for i in instrs],
        }

    @mcp.tool()
    def gb_disassemble_at_pc(before: int = 5, after: int = 20) -> dict:
        """Show instructions around the current program counter.

        Uses a backward-scan heuristic to find *before* instructions preceding PC,
        then decodes *after* instructions following it. The instruction at PC is
        marked with "current": true. Returns error if no ROM loaded.
        """
        if not session.rom_loaded:
            return {
                "error": "NO_ROM_LOADED",
                "message": "Load a ROM first with gb_load_rom.",
            }
        pc = session.pyboy.register_file.PC
        instrs = disassemble_at_pc(_reader(), pc, before=before, after=after)
        return {
            "pc": f"0x{pc:04X}",
            "instructions": [_fmt(i, current=(i.address == pc)) for i in instrs],
        }
