"""Static reading MCP tools: ROM header, memory map, raw bytes, vector table."""

from __future__ import annotations

from blobert_mcp.domain import memory_map, rom_header, vectors
from blobert_mcp.utils.hexdump import hexdump


def register_static_tools(mcp, session) -> None:
    """Register static reading tools with the FastMCP instance."""

    @mcp.tool()
    def get_rom_header() -> dict:
        """Parse and return the ROM header (0x0100-0x014F).

        Delegates to domain/rom_header.parse(). Returns error if no ROM loaded.
        """
        if not session.rom_loaded:
            return {
                "error": "NO_ROM_LOADED",
                "message": "Load a ROM first with gb_load_rom.",
            }
        header_bytes = bytes(session.pyboy.memory[0x0100:0x0150])
        return rom_header.parse(header_bytes)

    @mcp.tool()
    def get_memory_map() -> dict:
        """Return the static Game Boy memory map.

        Works without a loaded ROM (static data).
        """
        return {
            "regions": [
                {
                    "name": r.name,
                    "start": r.start,
                    "end": r.end,
                    "size": r.size,
                    "access_type": r.access_type,
                }
                for r in memory_map.get_regions()
            ]
        }

    @mcp.tool()
    def read_rom_bytes(
        address: int, length: int = 256, bank: int | None = None
    ) -> dict:
        """Read bytes from ROM at the given address and format as a hex dump.

        length must be between 1 and 4096. Use bank for banked ROM reads.
        Returns error if no ROM loaded or parameters are invalid.
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
            if bank is None:
                raw = bytes(session.pyboy.memory[address : address + length])
            else:
                raw = bytes(session.pyboy.memory[bank, address : address + length])
        except Exception:
            return {
                "error": "INVALID_ADDRESS",
                "message": f"Address 0x{address:04X} is out of range.",
            }
        return {
            "address": address,
            "bank": bank,
            "length": len(raw),
            "data": hexdump(raw, start_offset=address),
        }

    @mcp.tool()
    def get_vector_table() -> dict:
        """Return RST vectors, interrupt vectors, and entry point with first bytes.

        Returns error if no ROM loaded.
        """
        if not session.rom_loaded:
            return {
                "error": "NO_ROM_LOADED",
                "message": "Load a ROM first with gb_load_rom.",
            }
        result = []
        for v in vectors.get_vectors():
            first_bytes = bytes(session.pyboy.memory[v.address : v.address + 2])
            result.append(
                {
                    "address": v.address,
                    "label": v.label,
                    "type": v.type,
                    "first_bytes": " ".join(f"{b:02X}" for b in first_bytes),
                }
            )
        return {"vectors": result}
