---
name: Project ticket sizing calibration
description: Typical scope and size of completed and backlog tickets in blobert-mcp, for complexity calibration
type: project
---

Completed tickets as of 2026-03-28:
- BLO-001 (medium, infrastructure): 8 criteria, 6 files — Python project structure + MCP server skeleton
- BLO-006 (small, infrastructure): 4 criteria, 4 files — repository hygiene files (.gitignore, LICENSE, etc.)
- BLO-007 (small, docs): 4 criteria, 4 files — community health files (CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, CODEOWNERS)
- BLO-009 (infrastructure): CI/CD pipeline + pre-commit hooks + developer automation
- BLO-010 (infrastructure): CI action version bumps (Node 24)

Baseline for "small" docs ticket: 4 criteria, 4 files, single thematic concern (BLO-006 and BLO-007).

Backlog P0 tickets BLO-002 through BLO-005 are classified `medium` or `large` and each covers a coherent feature layer:
- BLO-002 (medium): 13 acceptance criteria, ~7 new files — ROM loading + static memory tools
- BLO-003 (large): 9 criteria, ~4 new files — full SM83 disassembler engine
- BLO-004 (large): 11 criteria, ~4 new files — dynamic execution/input/save states/screenshot
- BLO-005 (medium): 10 criteria, ~3 new files — SQLite knowledge base

**Why:** These tickets each represent a distinct, independently testable capability layer with tight internal cohesion. The project intentionally groups related tools into logical tickets rather than one-ticket-per-tool.

**How to apply:** When assessing split proposals, prefer splitting along architectural/layer boundaries (infrastructure vs. feature vs. test), not by individual tool. A "medium" ticket with 8 criteria all in the same module is normal for this project.
