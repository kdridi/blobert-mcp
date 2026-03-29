"""Search MCP tools: byte pattern matching and string detection."""

from __future__ import annotations

from blobert_mcp.domain import search


def register_search_tools(mcp, session) -> None:  # noqa: ANN001
    """Register search tools with the FastMCP instance."""

    @mcp.tool()
    def find_byte_pattern(
        pattern: str,
        address: int = 0,
        length: int | None = None,
    ) -> dict:
        """Search for a byte pattern in ROM memory with wildcard support.

        Pattern syntax: hex bytes separated by spaces, '??' for wildcard.
        Example: 'CD ?? 40' matches any CALL to 0x40xx.
        Returns up to 100 matching addresses.
        """
        if not session.rom_loaded:
            return {
                "error": "NO_ROM_LOADED",
                "message": "Load a ROM first with gb_load_rom.",
            }

        start = address
        if length is not None:
            end = min(address + length, 0x10000)
        else:
            end = 0x8000  # Default: scan ROM area (32KB)

        data = bytes(session.pyboy.memory[start:end])

        try:
            offsets = search.match_byte_pattern(data, pattern, max_results=100)
        except ValueError as exc:
            return {"error": "INVALID_PARAMETER", "message": str(exc)}

        # Convert relative offsets back to absolute addresses
        matches = [f"0x{start + off:04X}" for off in offsets]

        return {
            "pattern": pattern,
            "matches": matches,
            "count": len(matches),
            "truncated": len(matches) == 100,
        }

    @mcp.tool()
    def find_strings(
        encoding: str = "ascii",
        min_length: int = 4,
    ) -> dict:
        """Find text strings in ROM memory.

        Scans the ROM area for runs of decodable text characters.
        Supports 'ascii' and 'gb_custom' encodings.
        Returns up to 200 results.
        """
        if not session.rom_loaded:
            return {
                "error": "NO_ROM_LOADED",
                "message": "Load a ROM first with gb_load_rom.",
            }

        data = bytes(session.pyboy.memory[0x0000:0x8000])

        try:
            results = search.find_text_strings(
                data,
                min_length=min_length,
                encoding=encoding,
                max_results=200,
            )
        except ValueError as exc:
            return {"error": "INVALID_PARAMETER", "message": str(exc)}

        return {
            "encoding": encoding,
            "min_length": min_length,
            "strings": [
                {"address": f"0x{addr:04X}", "text": text} for addr, text in results
            ],
            "count": len(results),
            "truncated": len(results) == 200,
        }
