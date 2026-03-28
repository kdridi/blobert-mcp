# Testing Strategy — blobert-mcp

## Philosophy

Domain logic is tested first via TDD with synthetic byte sequences. Tool handlers are tested via integration tests. Smoke tests ensure the package loads. The test pyramid: domain (many, fast) > tools (fewer, may need fixtures) > smoke (minimal, always pass).

---

## Test Categories

| Category | Location | Dependencies | Speed | When to write |
|----------|----------|-------------|-------|---------------|
| Domain unit tests | `tests/domain/` | None (pure Python) | < 1ms each | **Before** implementation (TDD) |
| Utility tests | `tests/utils/` | None | < 1ms each | **Before** implementation (TDD) |
| Tool integration tests | `tests/tools/` | PyBoy + test ROM or mock | Varies | After domain + tool code |
| Smoke tests | `tests/test_smoke.py` | Package import only | < 100ms total | Per ticket, as needed |

---

## TDD Workflow for Domain Modules

This sequence is mandatory for every new domain module:

1. **Create the test file first** (e.g., `tests/domain/test_rom_header.py`)
2. **Write test cases** with known byte inputs and expected structured outputs
3. **Run the test** — it fails (module does not exist yet)
4. **Create the domain module** (e.g., `src/blobert_mcp/domain/rom_header.py`)
5. **Implement until tests pass**
6. **Refactor** if needed — tests must stay green

The test is written BEFORE the code. This is not optional.

---

## Fixture Strategy

In order of preference:

### 1. Synthetic byte sequences (preferred for domain tests)

Construct `bytes` literals directly in the test. Self-documenting, zero dependencies, run anywhere.

```python
# Example: test_rom_header.py
TETRIS_HEADER = (
    b"\x00" * 0x34                   # 0x0100-0x0133: entry point + logo
    + b"TETRIS\x00\x00\x00\x00\x00"  # 0x0134-0x013E: title
    + b"\x00\x00\x00\x00\x00"        # 0x013F-0x0143: manufacturer + CGB
    + b"\x00\x00"                     # 0x0144-0x0145: licensee
    + b"\x00"                         # 0x0146: SGB flag
    + b"\x00"                         # 0x0147: cartridge type (ROM ONLY)
    + b"\x00"                         # 0x0148: ROM size (32KB)
    + b"\x00"                         # 0x0149: RAM size (none)
    + b"\x01"                         # 0x014A: destination (non-Japanese)
    + b"\x01"                         # 0x014B: old licensee (Nintendo)
    + b"\x00"                         # 0x014C: ROM version
    + b"\x00"                         # 0x014D: header checksum
    + b"\x00\x00"                     # 0x014E-0x014F: global checksum
)

def test_parse_header_title():
    result = rom_header.parse(TETRIS_HEADER)
    assert result["title"] == "TETRIS"
```

### 2. Minimal test ROM (for integration tests needing PyBoy)

A ~32KB `.gb` file with a valid header and minimal code (tight loop at 0x100). Can be generated programmatically or stored in `tests/fixtures/`. Must not be a copyrighted ROM.

### 3. Mock emulator (fallback for tool tests)

A `FakeEmulatorSession` that returns predetermined bytes for given addresses. Use when testing tool logic without real emulation.

**Never use copyrighted ROM files in tests. All test data must be synthetic or generated.**

---

## Naming Conventions

- **Test files**: `test_<module_name>.py`
- **Test functions**: `test_<what>_<scenario>` (e.g., `test_parse_header_tetris_rom`, `test_mbc_type_detection_mbc5`)
- **Test directories mirror source**: `tests/domain/` tests `src/blobert_mcp/domain/`, `tests/utils/` tests `src/blobert_mcp/utils/`

---

## Test Layout

```
tests/
├── __init__.py
├── test_smoke.py              # Package import + server instance checks
├── domain/                    # Domain unit tests (TDD, no dependencies)
│   ├── __init__.py
│   ├── test_rom_header.py
│   ├── test_memory_map.py
│   ├── test_bank_info.py
│   ├── test_interrupts.py
│   └── test_vectors.py
├── utils/                     # Utility tests
│   ├── __init__.py
│   └── test_hexdump.py
└── tools/                     # Integration tests
    ├── __init__.py
    └── test_session.py
```

---

## Running Tests

- **All tests**: `make test` or `uv run pytest`
- **Domain tests only** (during TDD): `uv run pytest tests/domain/`
- **Stop at first failure**: `uv run pytest -x`
- **Single module**: `uv run pytest tests/domain/test_rom_header.py`
