"""Knowledge base MCP tools: annotate, define_function, define_variable, search,
get_function_info, stats, define_struct, apply_struct, define_enum."""

from __future__ import annotations

from blobert_mcp.domain.bank_info import calculate_bank_count
from blobert_mcp.domain.kb import (
    calculate_coverage_pct,
    decode_struct_fields,
    validate_address,
)


def register_kb_tools(mcp, session) -> None:
    """Register knowledge base tools with the FastMCP instance."""

    @mcp.tool()
    def kb_annotate(
        address: int,
        bank: int | None = None,
        label: str | None = None,
        type: str | None = None,
        comment: str | None = None,
    ) -> dict:
        """Annotate a ROM address with a label, type, and/or comment.

        UPSERT: updates the existing annotation if address+bank already exists.
        Type must be one of: code, data, gfx, audio, text.
        """
        if not session.rom_loaded:
            return {
                "error": "NO_ROM_LOADED",
                "message": "Load a ROM first with gb_load_rom.",
            }
        try:
            annotation_id = session.kb.annotate(
                address, bank=bank, label=label, type=type, comment=comment
            )
        except ValueError as e:
            return {"error": "INVALID_PARAMETER", "message": str(e)}
        return {"annotation_id": annotation_id}

    @mcp.tool()
    def kb_define_function(
        address: int,
        name: str,
        end_address: int | None = None,
        bank: int | None = None,
        params: list | None = None,
        description: str | None = None,
        returns: str | None = None,
    ) -> dict:
        """Define a function at the given address.

        Stores the function's name, parameter list (JSON), description, and
        return info. UPSERT on address+bank.
        """
        if not session.rom_loaded:
            return {
                "error": "NO_ROM_LOADED",
                "message": "Load a ROM first with gb_load_rom.",
            }
        try:
            function_id = session.kb.define_function(
                address,
                end_address=end_address,
                bank=bank,
                name=name,
                params=params,
                description=description,
                returns=returns,
            )
        except ValueError as e:
            return {"error": "INVALID_PARAMETER", "message": str(e)}
        return {"function_id": function_id}

    @mcp.tool()
    def kb_define_variable(
        address: int,
        name: str,
        type: str,
        description: str | None = None,
    ) -> dict:
        """Name a RAM variable at the given address.

        Type must be one of: u8, u16, bool, enum. UPSERT on address.
        """
        if not session.rom_loaded:
            return {
                "error": "NO_ROM_LOADED",
                "message": "Load a ROM first with gb_load_rom.",
            }
        try:
            variable_id = session.kb.define_variable(
                address, name=name, type=type, description=description
            )
        except ValueError as e:
            return {"error": "INVALID_PARAMETER", "message": str(e)}
        return {"variable_id": variable_id}

    @mcp.tool()
    def kb_search(
        query: str,
        filter: str | None = None,
    ) -> dict:
        """Search the knowledge base.

        Searches across annotations, functions, and variables.
        Optional filter: label, comment, address, type.
        Returns max 50 results sorted by relevance.
        """
        if not session.rom_loaded:
            return {
                "error": "NO_ROM_LOADED",
                "message": "Load a ROM first with gb_load_rom.",
            }
        results = session.kb.search(query, filter=filter)
        return {"count": len(results), "results": results}

    @mcp.tool()
    def kb_get_function_info(name_or_address: str) -> dict:
        """Retrieve all information about a function by name or address.

        Accepts a function name (string match) or address (integer or hex
        string like "0x0150"). Returns function definition, local variables,
        cross-references, and comments.
        """
        if not session.rom_loaded:
            return {
                "error": "NO_ROM_LOADED",
                "message": "Load a ROM first with gb_load_rom.",
            }
        result = session.kb.get_function_info(name_or_address)
        if result is None:
            return {
                "error": "NOT_FOUND",
                "message": f"No function found for: {name_or_address}",
            }
        return result

    @mcp.tool()
    def kb_stats() -> dict:
        """Statistics on decompilation progress.

        Returns total ROM addresses, annotated count (ROM-only), function
        count, variable count, and coverage percentage. Non-ROM annotations
        (address >= 0x8000) are excluded from the annotated count and
        coverage calculation.
        """
        if not session.rom_loaded:
            return {
                "error": "NO_ROM_LOADED",
                "message": "Load a ROM first with gb_load_rom.",
            }
        rom_size_byte = session.pyboy.memory[0x0148]
        bank_count = calculate_bank_count(rom_size_byte)
        total_addresses = bank_count * 0x4000

        annotated = session.kb.rom_annotation_count()
        functions_named = session.kb.function_count()
        variables_named = session.kb.variable_count()
        coverage_pct = calculate_coverage_pct(annotated, total_addresses)

        return {
            "total_addresses": total_addresses,
            "annotated": annotated,
            "functions_named": functions_named,
            "variables_named": variables_named,
            "coverage_pct": coverage_pct,
        }

    @mcp.tool()
    def kb_define_struct(
        name: str,
        fields: list[dict],
        comment: str | None = None,
    ) -> dict:
        """Define a data structure with typed fields.

        Each field dict must have: name, offset, type, size.
        Optional: comment. Valid types: u8, u16, s8, s16, bool, bytes.
        Struct names must be unique — duplicates are rejected.
        """
        if not session.rom_loaded:
            return {
                "error": "NO_ROM_LOADED",
                "message": "Load a ROM first with gb_load_rom.",
            }
        try:
            struct_id = session.kb.define_struct(name, fields, comment=comment)
        except ValueError as e:
            return {"error": "INVALID_PARAMETER", "message": str(e)}
        return {"struct_id": struct_id}

    @mcp.tool()
    def kb_apply_struct(
        struct_name: str,
        address: int,
        count: int | None = None,
    ) -> dict:
        """Apply a struct definition to a memory region.

        Reads live memory at the given address and decodes fields
        according to the struct layout. If count is provided, decodes
        that many consecutive struct instances (array of structs).
        """
        if not session.rom_loaded:
            return {
                "error": "NO_ROM_LOADED",
                "message": "Load a ROM first with gb_load_rom.",
            }
        try:
            validate_address(address)
            if count is not None and count < 1:
                raise ValueError("count must be >= 1.")
        except ValueError as e:
            return {"error": "INVALID_PARAMETER", "message": str(e)}

        struct_def = session.kb.get_struct(struct_name)
        if struct_def is None:
            return {
                "error": "NOT_FOUND",
                "message": f"No struct found with name: {struct_name}",
            }

        n = count if count is not None else 1
        total_size = struct_def["total_size"]
        entries = []
        for i in range(n):
            base = address + i * total_size
            data = bytes(session.pyboy.memory[base : base + total_size])
            decoded = decode_struct_fields(struct_def["fields"], data)
            entries.append(
                {
                    "address": f"0x{base:04X}",
                    "index": i,
                    "fields": decoded,
                }
            )

        return {
            "struct_name": struct_name,
            "address": f"0x{address:04X}",
            "count": n,
            "entries": entries,
        }

    @mcp.tool()
    def kb_define_enum(
        name: str,
        values: dict[str, int],
        comment: str | None = None,
    ) -> dict:
        """Define a named enumeration with name-to-value mappings.

        Enum names must be unique. All numeric values must be unique
        within the enum. Names must be non-empty.
        """
        if not session.rom_loaded:
            return {
                "error": "NO_ROM_LOADED",
                "message": "Load a ROM first with gb_load_rom.",
            }
        try:
            enum_id = session.kb.define_enum(name, values, comment=comment)
        except ValueError as e:
            return {"error": "INVALID_PARAMETER", "message": str(e)}
        return {"enum_id": enum_id}
