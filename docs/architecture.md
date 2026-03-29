# Architecture — blobert-mcp

## Overview

blobert-mcp uses **domain isolation** (simplified hexagonal architecture). Most tool logic is pure computation on bytes — ROM header parsing, MBC bank calculation, interrupt flag interpretation — that does not need PyBoy. Isolating this logic into a `domain/` layer makes it testable without an emulator, fast to iterate on via TDD, and reusable across tool groups.

---

## Layer Diagram

```
MCP Client (LLM)
    |
    v
tools/          Inbound adapter: validate input, read bytes, delegate, format output
    |
    v
domain/         Pure logic: zero project imports, stdlib + dataclasses only
    ^
    |
utils/          Shared formatting (hexdump, etc.)
    ^
    |
emulator.py     Outbound adapter: PyBoy + KB lifecycle
    |
    v
kb/             Persistence adapter: SQLite knowledge base
    |
    v
PyBoy           External dependency
```

---

## Dependency Rules

These are hard constraints. If a proposed change violates any of them, stop and restructure before proceeding.

1. **`domain/` imports nothing from the project.** Only Python stdlib and `dataclasses`. No PyBoy, no MCP, no emulator, no utils.
2. **`tools/` may import from `domain/`, `kb/`, and `emulator.py`.** Tools must not import from other `tools/` modules.
3. **`kb/` may import from `domain/`.** It wraps SQLite persistence and nothing else.
4. **`emulator.py` may import from `kb/`.** It manages PyBoy and KB lifecycle.
5. **`utils/` may import from `domain/` but not from `tools/` or `emulator.py`.**
6. **`server.py` is the composition root.** It imports `tools/` modules and registers them with FastMCP. It does not contain business logic.

---

## Layer Responsibilities

| Layer | Responsibility | Imports | Example |
|-------|---------------|---------|---------|
| `domain/` | Pure computation on bytes/ints | stdlib only | `parse_rom_header(data: bytes) -> RomHeader` |
| `tools/` | MCP tool handlers | domain, kb, emulator | `get_rom_header()` tool calling `rom_header.parse()` |
| `kb/` | SQLite knowledge base persistence | domain | `KnowledgeBase.annotate()` |
| `emulator.py` | PyBoy + KB lifecycle | PyBoy, kb | `EmulatorSession.load_rom()` |
| `utils/` | Shared formatting | domain (optionally) | `hexdump(data: bytes, offset: int) -> str` |
| `server.py` | Composition root, FastMCP setup | tools | registers all tool functions |

---

## Tool Implementation Pattern

Every MCP tool follows this 5-step recipe:

1. **Validate inputs** — check parameter types, ranges, limits (e.g., length <= 4096)
2. **Check preconditions** — is a ROM loaded? Is the address valid?
3. **Read raw bytes** — get data from `session.pyboy.memory[...]`
4. **Delegate to domain** — pass bytes to a pure function for parsing/computation
5. **Format and return** — use `utils/` for hexdump if needed, return dict

```python
# Example: tools/static.py
@mcp.tool()
def get_rom_header() -> dict:
    if not session.rom_loaded:
        return {"error": "NO_ROM_LOADED", "message": "Load a ROM first."}
    header_bytes = session.pyboy.memory[0x0100:0x0150]
    return rom_header.parse(header_bytes)
```

Domain functions are pure — they take bytes and return structured data:

```python
# Example: domain/rom_header.py
def parse(data: bytes) -> dict:
    return {"title": data[0x34:0x44].decode("ascii", errors="replace").rstrip("\x00"), ...}
```

---

## Source Layout

```
src/blobert_mcp/
├── __init__.py
├── server.py              # FastMCP instance + tool registration (composition root)
├── emulator.py            # EmulatorSession wrapping PyBoy
├── tools/                 # MCP tool handlers (thin wrappers)
│   ├── __init__.py
│   ├── session.py         # gb_load_rom, get_session_info, gb_reset
│   ├── static.py          # get_rom_header, get_memory_map, read_rom_bytes, get_vector_table
│   ├── memory.py          # gb_read_memory, gb_read_banked, gb_get_bank_info, gb_get_interrupt_status
│   └── kb.py              # kb_annotate, kb_define_function, kb_define_variable, kb_search
├── kb/                    # SQLite knowledge base (stateful persistence)
│   ├── __init__.py
│   └── database.py        # KnowledgeBase class, kb_path_for_rom()
├── domain/                # Pure business logic (no project imports)
│   ├── __init__.py
│   ├── rom_header.py      # ROM header field parsing (bytes -> structured data)
│   ├── memory_map.py      # Static Game Boy memory layout definitions
│   ├── bank_info.py       # MBC type detection, bank count calculation
│   ├── interrupts.py      # IE/IF flag interpretation
│   ├── vectors.py         # RST/interrupt vector table definitions
│   └── kb.py              # KB validation: type enums, address/name checks, search ranking
└── utils/
    ├── __init__.py
    └── hexdump.py         # Hex + ASCII formatting
```

---

## Error Handling

- **Domain layer** raises Python exceptions (e.g., `ValueError` for invalid data).
- **Tool layer** catches exceptions and returns error dicts:

```python
{"error": "NO_ROM_LOADED", "message": "Load a ROM first with gb_load_rom."}
{"error": "INVALID_ADDRESS", "message": "Address 0x10000 is out of range."}
{"error": "INVALID_BANK", "message": "Bank 256 exceeds ROM bank count."}
{"error": "INVALID_PARAMETER", "message": "Length must be between 1 and 4096."}
```

---

## Evolution

This architecture scales to all 68 tools. New tool groups add a file in `tools/` and optionally new domain modules. The dependency rules do not change.
