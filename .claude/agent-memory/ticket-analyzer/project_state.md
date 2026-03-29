---
name: Project state as of 2026-03-29
description: Current state of the blobert-mcp project — completed tickets and source layout as of 2026-03-29
type: project
---

Completed tickets as of 2026-03-29: BLO-001, BLO-005 (SQLite KB), BLO-006, BLO-007, BLO-008, BLO-009, BLO-010, BLO-011, BLO-012 (domain TDD — 69 tests), BLO-013 (session + static tools — 7 tools, 31 tests), BLO-014 (memory tools), BLO-015 (disassembler domain), BLO-016, BLO-018 (lint/CI fixes), BLO-019 (design decision log), BLO-020 (domain layer: registers.py + buttons.py, TDD), BLO-021 (core dynamic tools: 6 tools across execution/input/savestate modules, 34 new tests, 447 total), BLO-022 (instruction stepping + screenshot: mode="instruction" in gb_step, gb_screenshot tool, 459 total tests), BLO-023 (datetime backfill), BLO-024 (ticket completion automation: CLAUDE.md checklist, Stop hook, verify-ticket Makefile target).

Rejected tickets: BLO-002 (decomposed into BLO-012/013/014), BLO-004 (decomposed into BLO-020/021/022).

Planned: BLO-017 (label enrichment, ready to activate).

Backlog: (empty — new tier for idea tickets).

Source layout after BLO-022: `src/blobert_mcp/domain/` has registers.py, buttons.py, disasm/, rom_header, memory_map, bank_info, interrupts, vectors, kb. `src/blobert_mcp/tools/` has session.py, static.py, memory.py, kb.py, disasm.py, execution.py, input.py, savestate.py, visual.py.

**Why:** Knowing the completed state avoids re-analyzing finished work and gives accurate unblocked-ticket view.

BLO-025 (completed): Added `tickets/planned/` tier to lifecycle. backlog = ideas, planned = refined and ready.

BLO-017 (completed): Disassembly label enrichment from knowledge base.

BLO-073 (completed): Scheduled 20 tickets from backlog to planned/ with roadmap.md. All 16 P1 tickets + 4 strategic P2 tickets (BLO-053, BLO-056, BLO-043, BLO-058). Execution order documented in `tickets/planned/roadmap.md`. CLAUDE.md updated with roadmap convention.

BLO-032 (completed): LCD and hardware register tools — 4 MCP tools (gb_get_lcd_status, gb_get_timer_state, gb_get_audio_state, gb_get_serial_state) backed by domain/io_registers.py. 58 domain tests + 20 tool tests. 553 total tests.

BLO-026 (completed): Memory and register write tools — gb_write_memory + gb_set_register. Domain: registers.py (4 validation functions, 3 constants), memory.py (new — WRITABLE_RANGES, validate_write_address, parse_hex_string). 670 total tests.

BLO-041 (completed): KB function info & statistics — kb_get_function_info + kb_stats tools. Domain: ROM_ADDRESS_LIMIT constant, calculate_coverage_pct(). KB: get_function_info(), rom_annotation_count(), function_count(), variable_count(). Coverage only counts ROM annotations (address < 0x8000). 704 total tests.

BLO-028 (completed): Save state management tools — gb_list_states + gb_delete_state, timestamp added to gb_save_state. 9 new tests. 713 total tests.

Planned tickets (in execution order): BLO-030, BLO-034, BLO-038, BLO-040, BLO-039, BLO-027, BLO-029, BLO-037, BLO-031, BLO-033, BLO-035, BLO-036, BLO-053, BLO-056, BLO-043, BLO-058.

Remaining backlog (27 tickets): BLO-042, BLO-044, BLO-045, BLO-046, BLO-047, BLO-048, BLO-049, BLO-050, BLO-051, BLO-052, BLO-054, BLO-055, BLO-057, BLO-059, BLO-060, BLO-061, BLO-062, BLO-063, BLO-064, BLO-065, BLO-066, BLO-067, BLO-068, BLO-069, BLO-070, BLO-071, BLO-072.

**How to apply:** All P0 tools are complete. Next ticket to activate: BLO-030 (Memory diff between save states). Consult `tickets/planned/roadmap.md` for the full sequence. Ticket lifecycle: backlog → planned → ongoing → completed/rejected.
