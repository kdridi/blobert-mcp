# Design Decisions — blobert-mcp

This file records significant architectural and design decisions.
Each entry has a stable `D-XXX` identifier for cross-referencing from
tickets, code comments, and other docs.

Format: **Context** (why we faced a choice), **Decision** (what we chose),
**Why** (rationale and rejected alternatives).

---

## Index

| ID | Date | Decision | Ticket |
|----|------|----------|--------|
| D-001 | 2026-03-28 | Abandon autoresearch | — |
| D-002 | 2026-03-28 | Use a real emulator | — |
| D-003 | 2026-03-28 | Choose PyBoy | — |
| D-004 | 2026-03-28 | MCP server architecture | — |
| D-005 | 2026-03-28 | LLM for semantics only | — |
| D-006 | 2026-03-28 | Domain isolation (hexagonal) | BLO-011 |
| D-007 | 2026-03-28 | TDD mandatory for domain | BLO-011 |
| D-008 | 2026-03-28 | Decompose large tickets by layer | BLO-002 |
| D-009 | 2026-03-28 | Disasm modules under domain/ | BLO-003 |
| D-010 | 2026-03-29 | SQLite for knowledge base | BLO-005 |
| D-011 | 2026-03-29 | KB in kb/ layer, not domain/ | BLO-005 |
| D-012 | 2026-03-29 | NULL bank → -1 sentinel | BLO-005 |
| D-013 | 2026-03-29 | Dict cache for get_label() | BLO-005 |
| D-014 | 2026-03-29 | Pre-commit hooks mandatory | BLO-018 |
| D-015 | 2026-03-29 | Single-file decision log | BLO-019 |
| D-016 | 2026-03-29 | Datetime format for tickets | BLO-004 |
| D-017 | 2026-03-29 | Instruction stepping via hook + timeout | BLO-022 |
| D-018 | 2026-03-29 | Screenshot returns FastMCP Image | BLO-022 |
| D-019 | 2026-03-29 | Hook API — keep existing 3-arg form | BLO-022 |
| D-020 | 2026-03-29 | Default GB custom encoding table | BLO-034 |

---

### D-001: Abandon autoresearch
**Date:** 2026-03-28 | **Ticket:** — (journal.md Phase 1-2)

**Context:** Initial approach used LLM-generated metrics to
evaluate LLM-generated decompilation output.

**Decision:** Abandon autoresearch for this project.

**Why:** Circular metric — LLM judges LLM. The system optimized the
scoring tool, not the actual decompilation quality.

---

### D-002: Use a real emulator
**Date:** 2026-03-28 | **Ticket:** — (journal.md Phase 3)

**Context:** Needed to execute Game Boy ROMs for dynamic analysis.
Considered having the LLM simulate execution.

**Decision:** Use a real emulator for execution.

**Why:** The LLM cannot maintain coherent CPU state across thousands
of instructions. Cognitive erosion, carry flag errors,
non-determinism. "It tells a story about execution; it does not
execute."

---

### D-003: Choose PyBoy
**Date:** 2026-03-28 | **Ticket:** — (journal.md Phase 5)

**Context:** Multiple Game Boy emulators exist. Need one
controllable from Python with headless mode.

**Decision:** PyBoy.

**Why:** Native Python, rich API, headless mode, parallelizable.
Alternatives rejected: BGB (Windows-only, no Python API),
Gambatte (C++, no scripting), mGBA (C, limited Python bindings).

---

### D-004: MCP server architecture
**Date:** 2026-03-28 | **Ticket:** — (journal.md Phase 5)

**Context:** The LLM needs to drive the emulator interactively,
requesting specific data (disassembly, memory reads, execution)
as its analysis progresses.

**Decision:** MCP (Model Context Protocol) server exposing tools.

**Why:** The LLM drives the emulator conversationally via tool
calls. MCP provides a standard protocol, tool discovery, and
structured I/O. The LLM decides what to examine; the server
provides the data.

---

### D-005: LLM for semantics only
**Date:** 2026-03-28 | **Ticket:** — (journal.md Phase 5)

**Context:** Need to divide responsibilities between LLM and
deterministic code.

**Decision:** LLM handles semantic interpretation only. Everything
else (traces, graphs, I/O, scoring) is pure Python.

**Why:** LLMs excel at pattern recognition and naming. They fail at
precise state tracking. Give the LLM pre-digested data and ask it
to interpret meaning.

---

### D-006: Domain isolation (hexagonal architecture)
**Date:** 2026-03-28 | **Ticket:** BLO-011

**Context:** Tool logic mixes pure computation (header parsing,
opcode decoding) with emulator I/O, making testing slow and
brittle.

**Decision:** Simplified hexagonal architecture. `domain/` imports
nothing from the project (stdlib + dataclasses only). `tools/` are
thin wrappers: validate → read bytes → delegate to domain → format.

**Why:** Enables TDD with synthetic byte sequences — no emulator
needed for testing ~80% of logic. See `docs/architecture.md` for
full dependency rules.

---

### D-007: TDD mandatory for domain modules
**Date:** 2026-03-28 | **Ticket:** BLO-011

**Context:** Domain modules are pure functions on bytes. They are
the most testable layer but also the most correctness-critical
(wrong opcode decoding = wrong analysis).

**Decision:** TDD is mandatory for `domain/` modules: write test
file first, run it (fails), implement, run again (passes).

**Why:** Pure functions on synthetic bytes are trivial to TDD. The
test doubles as a specification. See `docs/testing-strategy.md`.

---

### D-008: Decompose large tickets by architectural layer
**Date:** 2026-03-28 | **Ticket:** BLO-002

**Context:** BLO-002 bundled 13 acceptance criteria across 3
architectural layers (domain, tools, session) and 11 tools. Too
large for a single implementation session.

**Decision:** Decompose into layer-aligned tickets: BLO-012 (domain
layer), BLO-013 (tools + session), BLO-014 (integration). Each
ticket owns one layer and can be TDD'd independently.

**Why:** Layer-aligned decomposition matches the dependency
direction (`domain/` first, then `tools/`) and enables incremental
TDD. Rejected: per-tool decomposition (too many tiny tickets with
cross-cutting concerns).

---

### D-009: Disassembler modules under domain/
**Date:** 2026-03-28 | **Ticket:** BLO-003

**Context:** BLO-003 proposed `src/blobert_mcp/disasm/` as a
top-level package. But the disassembler is pure computation on
bytes — it has no I/O, no emulator dependency.

**Decision:** Place disassembler under `domain/disasm/` (opcodes,
decoder, disassembler).

**Why:** Module paths must reflect architecture. Pure logic belongs
in `domain/`. This was one of the reasons BLO-003 was rejected
and decomposed into BLO-015 + BLO-016 + BLO-017.

---

### D-010: SQLite for knowledge base
**Date:** 2026-03-29 | **Ticket:** BLO-005

**Context:** The KB needs persistent per-ROM storage for
annotations, functions, and variables with relational queries and
UPSERT semantics.

**Decision:** SQLite via stdlib `sqlite3`. Per-ROM DB file at
`~/.blobert-mcp/<rom_stem>.db`.

**Why:** In stdlib (no dependency), relational queries, UNIQUE
constraints, single portable file per ROM. Alternatives: JSON
files (no queries), TinyDB (extra dependency), PostgreSQL
(overkill for per-ROM storage).

---

### D-011: KB in kb/ layer, not domain/
**Date:** 2026-03-29 | **Ticket:** BLO-005

**Context:** The KnowledgeBase class uses `sqlite3` for persistent
I/O. `domain/` requires pure functions with no side effects.

**Decision:** Create `src/blobert_mcp/kb/` as a new sibling of
`domain/`, `tools/`, `utils/`. Pure validation logic (type enums,
address checks, search ranking) goes in `domain/kb.py`.

**Why:** The KB is a stateful I/O adapter (like PyBoy). It doesn't
belong in `domain/` (impure) or `tools/` (not an MCP handler).
Dependency direction: `tools/kb.py` → `kb/database.py` →
`domain/kb.py` → stdlib.

---

### D-012: NULL bank → -1 sentinel
**Date:** 2026-03-29 | **Ticket:** BLO-005

**Context:** The annotations and functions tables use
`UNIQUE(address, bank)`. When `bank` is NULL (no bank specified),
SQLite treats `NULL != NULL`, so two rows with `(0x100, NULL)`
would NOT conflict — breaking UPSERT semantics.

**Decision:** Store bank as `INTEGER NOT NULL DEFAULT -1`. Map
Python `None` → `-1` at the KnowledgeBase boundary.

**Why:** Makes UNIQUE constraints work correctly without complex
SQL workarounds (COALESCE expressions, partial indices). The
sentinel is internal — the API still accepts `None`.

---

### D-013: Dict cache for get_label()
**Date:** 2026-03-29 | **Ticket:** BLO-005

**Context:** `get_label(address, bank)` is called for every
instruction during disassembly — a hot path.

**Decision:** Simple `dict[tuple[int, int], str | None]` cache on
the `KnowledgeBase` instance. Invalidate specific key on
`annotate()` / `define_function()`. Entire cache dropped when KB
instance is replaced (ROM change).

**Why:** `functools.lru_cache` cannot invalidate per-key. A dict is
simpler, correct, and sufficient. No TTL needed — the KB is the
single source of truth.

---

### D-014: Pre-commit hooks mandatory
**Date:** 2026-03-29 | **Ticket:** BLO-018

**Context:** BLO-014 through BLO-016 introduced lint violations
that were not caught locally because the pre-commit hook was never
installed. CI was red for 5 commits.

**Decision:** `make setup` installs pre-commit hooks. `make check`
(ruff lint + format + tests) must pass before every commit.
Documented in CLAUDE.md.

**Why:** CI should never be the first place lint errors are
discovered. The pre-commit hook catches them at commit time.

---

### D-015: Single-file decision log over individual ADRs
**Date:** 2026-03-29 | **Ticket:** BLO-019

**Context:** Needed a system to track design decisions. Options:
individual ADR files (Nygard/MADR), embedded in architecture.md,
in tickets, in journal.md, or a single dedicated file.

**Decision:** Single `docs/decisions.md` with index table and flat
`D-XXX` entries. Lightweight format: Context / Decision / Why.

**Why:** The primary consumer is an AI that reads project files at
session start. One file = one read for full decision context.
Individual ADR files require globbing 20+ files. MADR's 7-10
sections are too heavy for this project's decision velocity.
The project will have ~30-50 decisions total — a single file
remains scannable at that scale.

---

### D-016: Datetime format for tickets
**Date:** 2026-03-29 | **Ticket:** BLO-004

**Context:** Multiple tickets are created on the same day. The
`YYYY-MM-DD` format in frontmatter (`created`, `updated`) and
log entries does not allow temporal sorting within a single day.

**Decision:** Change ticket date format to `YYYY-MM-DD HH:MM:SS`
in both frontmatter fields and log entries. Existing tickets
retain date-only format (no fabricated timestamps). New tickets
use the full datetime going forward.

**Why:** Enables temporal ordering of tickets and events within
the same day. The AI creates tickets rapidly — sometimes several
per session — and the date-only format loses sequencing
information. Not backfilling existing tickets avoids fabricating
data we don't have.

---

### D-017: Instruction stepping via hook at PC+size with frame timeout
**Date:** 2026-03-29 | **Ticket:** BLO-022

**Context:** `gb_step(mode="instruction")` needs to advance
exactly one CPU instruction. PyBoy's `tick()` runs a full frame
(~70K cycles). Need a mechanism to stop after one instruction.

**Decision:** Decode instruction at PC to get `size`, register a
hook at `(PC + size) & 0xFFFF`, tick until hook fires or 10-frame
timeout. Deregister hook after each step to prevent stale hooks
from blocking subsequent steps.

**Why:** Hook-based stepping reuses the same pattern as
`gb_run_until`. The 10-frame timeout handles jumps/calls where
PC+size is never reached (the instruction executed, but PC jumped
elsewhere). After timeout, return current state normally — not an
error. Rejected: detecting jump targets to hook at the destination
(adds complexity, fragile for indirect jumps like `JP HL`).

---

### D-018: Screenshot returns FastMCP Image object
**Date:** 2026-03-29 | **Ticket:** BLO-022

**Context:** `gb_screenshot` must return image data via MCP's
multimodal content type. Options: return a raw dict with
`{"type": "image", ...}`, or use FastMCP's `Image` helper class.

**Decision:** Return `Image(data=bytes, format=str)` from
`mcp.server.fastmcp.utilities.types`. FastMCP's
`_convert_to_content()` auto-converts it to `ImageContent`.

**Why:** Cleaner than manual base64 encoding + dict construction.
The `Image` class handles MIME type derivation and base64 encoding
internally. Note: the return type annotation is omitted (not
`-> dict | Image`) because Pydantic cannot generate a schema for
the `Image` class, causing registration to fail.

---

### D-019: Hook API — keep existing 3-arg form
**Date:** 2026-03-29 | **Ticket:** BLO-022

**Context:** Real PyBoy uses `hook_register(bank, addr, callback,
context)` (4 args). The existing codebase uses
`hook_register(addr, callback, context)` (3 args). Fixing this
would require updating `gb_run_until` and all test fakes.

**Decision:** Keep the 3-arg form for now. Both instruction
stepping and `gb_run_until` use the same convention.

**Why:** Scope discipline — BLO-022 is about instruction stepping
and screenshot, not hook API fixes. A follow-up ticket can align
the hook API with real PyBoy if needed when testing against real
hardware.

---

### D-020: Default GB custom encoding table
**Date:** 2026-03-29 | **Ticket:** BLO-034

**Context:** `find_strings` supports a `gb_custom` encoding for
Game Boy text detection. There is no universal GB character
encoding — each game may define its own table.

**Decision:** Provide a common default mapping in
`domain/search.py`: uppercase (0x80-0x99), lowercase (0xA0-0xB9),
digits (0xBA-0xC3), space (0x7F), and common punctuation
(0xE0-0xE5). Document that game-specific tables may differ.

**Why:** A default table enables useful text detection out of the
box for many games without requiring per-game configuration.
The chosen ranges cover the most common subset seen across
popular Game Boy titles. Rejected: no default (too restrictive —
gb_custom would be useless without a table), per-game tables
(scope creep — can be added later as KB extension).
