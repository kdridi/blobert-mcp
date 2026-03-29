---
name: Project state as of 2026-03-29
description: Current state of the blobert-mcp project — completed tickets and source layout as of 2026-03-29
type: project
---

Completed tickets as of 2026-03-29: BLO-001, BLO-005 (SQLite KB), BLO-006, BLO-007, BLO-008, BLO-009, BLO-010, BLO-011, BLO-012 (domain TDD — 69 tests), BLO-013 (session + static tools — 7 tools, 31 tests), BLO-014 (memory tools), BLO-015 (disassembler domain), BLO-016, BLO-018 (lint/CI fixes), BLO-019 (design decision log), BLO-020 (domain layer: registers.py + buttons.py, TDD), BLO-021 (core dynamic tools: 6 tools across execution/input/savestate modules, 34 new tests, 447 total), BLO-022 (instruction stepping + screenshot: mode="instruction" in gb_step, gb_screenshot tool, 459 total tests), BLO-023 (datetime backfill), BLO-024 (ticket completion automation: CLAUDE.md checklist, Stop hook, verify-ticket Makefile target).

Rejected tickets: BLO-002 (decomposed into BLO-012/013/014), BLO-004 (decomposed into BLO-020/021/022).

Backlog: BLO-017.

Source layout after BLO-022: `src/blobert_mcp/domain/` has registers.py, buttons.py, disasm/, rom_header, memory_map, bank_info, interrupts, vectors, kb. `src/blobert_mcp/tools/` has session.py, static.py, memory.py, kb.py, disasm.py, execution.py, input.py, savestate.py, visual.py.

**Why:** Knowing the completed state avoids re-analyzing finished work and gives accurate unblocked-ticket view.

**How to apply:** All P0 tools from BLO-004 are now complete. BLO-017 is the only remaining backlog item.
