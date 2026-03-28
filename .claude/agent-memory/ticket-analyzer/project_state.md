---
name: Project state as of 2026-03-28 (updated)
description: Current state of the blobert-mcp project — completed tickets and source layout as of the BLO-012 completion pass
type: project
---

Completed tickets as of latest analysis: BLO-001 (MCP skeleton), BLO-006 (repo foundation), BLO-007 (community health docs), BLO-008 (GitHub templates + changelog), BLO-009 (CI/CD pipeline), BLO-010 (Node 24 CI bump), BLO-011 (architecture + TDD + testing-strategy docs), BLO-012 (domain layer TDD — 69 tests, all pass).

Source layout after BLO-012: `src/blobert_mcp/` now contains `__init__.py`, `emulator.py`, `server.py`, `domain/` (5 modules + `__init__.py`), and `utils/hexdump.py` + `utils/__init__.py`. No `tools/` subdirectory yet.

Backlog: BLO-003 (disassembler, large), BLO-004 (execution/save states, large), BLO-005 (SQLite knowledge base, medium), BLO-013 (session + static tools, medium), BLO-014 (memory tools, small). BLO-002 was rejected and decomposed into BLO-012/013/014.

**Why:** Knowing which tickets are done prevents re-analyzing completed work and gives accurate calibration on what's blocked vs. unblocked.

**How to apply:** BLO-013 depends on BLO-012 (completed). BLO-014 also depends only on BLO-012 (completed) — it is parallelizable with BLO-013 but the one-active-ticket rule means one must precede the other.
