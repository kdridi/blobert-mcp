---
name: Project state as of 2026-03-29
description: Current state of the blobert-mcp project — completed tickets and source layout as of 2026-03-29
type: project
---

Completed tickets as of 2026-03-29: BLO-001, BLO-005 (SQLite KB), BLO-006, BLO-007, BLO-008, BLO-009, BLO-010, BLO-011, BLO-012 (domain TDD — 69 tests), BLO-013 (session + static tools — 7 tools, 31 tests), BLO-014 (memory tools), BLO-015 (disassembler domain), BLO-016, BLO-018 (lint/CI fixes), BLO-019 (design decision log).

Rejected tickets: BLO-002 (decomposed into BLO-012/013/014), BLO-004 (decomposed into BLO-020/021/022).

Backlog: BLO-003 (disassembler tools — now may be covered), BLO-020 (domain layer for dynamic tools — TDD), BLO-021 (core dynamic tools), BLO-022 (instruction stepping + screenshot), BLO-023 (unknown — new as of 2026-03-29).

Source layout after BLO-013: `src/blobert_mcp/domain/` has 6 modules (rom_header, memory_map, bank_info, interrupts, vectors, kb). `src/blobert_mcp/tools/` has session.py, static.py, memory.py, kb.py. No `domain/registers.py` or `domain/buttons.py` yet — those are created by BLO-020.

**Why:** Knowing the completed state avoids re-analyzing finished work and gives accurate unblocked-ticket view.

**How to apply:** BLO-020 depends on BLO-013 (completed) — it is ready to activate. BLO-021 depends on BLO-020; BLO-022 depends on BLO-021. The sequence is ordered and clear.
