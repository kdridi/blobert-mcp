"""Memory reading & hardware status MCP tools."""

from __future__ import annotations

from blobert_mcp.domain import bank_info, interrupts
from blobert_mcp.utils.hexdump import hexdump


def register_memory_tools(mcp, session) -> None:
    """Register memory reading and hardware status tools with the FastMCP instance."""

    @mcp.tool()
    def gb_read_memory(address: int, length: int = 256) -> dict:
        """Read bytes from any memory address and return as a hex dump.

        Reads from live emulator memory (RAM, VRAM, I/O, ROM). For banked regions
        the current bank is used. Use gb_read_banked for explicit bank selection.
        length must be between 1 and 4096. Returns error if no ROM loaded.
        """
        if not (1 <= length <= 4096):
            return {
                "error": "INVALID_PARAMETER",
                "message": "Length must be between 1 and 4096.",
            }
        if not session.rom_loaded:
            return {
                "error": "NO_ROM_LOADED",
                "message": "Load a ROM first with gb_load_rom.",
            }
        try:
            raw = bytes(session.pyboy.memory[address : address + length])
        except Exception:
            return {
                "error": "INVALID_ADDRESS",
                "message": f"Address 0x{address:04X} is out of range.",
            }
        return {
            "address": address,
            "length": len(raw),
            "data": hexdump(raw, start_offset=address),
        }

    @mcp.tool()
    def gb_read_banked(bank: int, address: int, length: int = 256) -> dict:
        """Read bytes from a specific memory bank and return as a hex dump.

        Uses pyboy.memory[bank, address] syntax for explicit bank selection.
        length must be between 1 and 4096. Returns error if no ROM loaded.
        """
        if not (1 <= length <= 4096):
            return {
                "error": "INVALID_PARAMETER",
                "message": "Length must be between 1 and 4096.",
            }
        if not session.rom_loaded:
            return {
                "error": "NO_ROM_LOADED",
                "message": "Load a ROM first with gb_load_rom.",
            }
        try:
            raw = bytes(session.pyboy.memory[bank, address : address + length])
        except Exception:
            return {
                "error": "INVALID_ADDRESS",
                "message": f"Address 0x{address:04X} bank {bank} is out of range.",
            }
        return {
            "bank": bank,
            "address": address,
            "length": len(raw),
            "data": hexdump(raw, start_offset=address),
        }

    @mcp.tool()
    def gb_get_bank_info() -> dict:
        """Return MBC type, total bank count, and current ROM bank.

        Reads cartridge type (0x0147) and ROM size (0x0148) from the header,
        delegates to domain/bank_info for interpretation. Returns error if no ROM loaded.
        """
        if not session.rom_loaded:
            return {
                "error": "NO_ROM_LOADED",
                "message": "Load a ROM first with gb_load_rom.",
            }
        cart_type_byte = session.pyboy.memory[0x0147]
        rom_size_byte = session.pyboy.memory[0x0148]
        info = bank_info.detect_mbc_type(cart_type_byte)
        total = bank_info.calculate_bank_count(rom_size_byte)
        return {
            "mbc_type": info["mbc"],
            "mbc_name": info["name"],
            "total_banks": total,
            "current_rom_bank": 1,
            "has_ram": info["ram"],
            "has_battery": info["battery"],
        }

    @mcp.tool()
    def gb_get_interrupt_status() -> dict:
        """Read IE (0xFFFF) and IF (0xFF0F) registers and interpret interrupt flags.

        Delegates to domain/interrupts for flag parsing. Returns structured JSON
        with individual flag states (vblank, stat, timer, serial, joypad).
        Returns error if no ROM loaded.
        """
        if not session.rom_loaded:
            return {
                "error": "NO_ROM_LOADED",
                "message": "Load a ROM first with gb_load_rom.",
            }
        ie_byte = session.pyboy.memory[0xFFFF]
        if_byte = session.pyboy.memory[0xFF0F]
        return interrupts.parse_interrupt_flags(ie_byte, if_byte)
