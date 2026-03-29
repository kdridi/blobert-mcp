# Planned Ticket Roadmap

Authoritative execution order for planned tickets. When activating the next ticket, pick the first uncompleted entry from this list.

When a ticket is moved out of `planned/` (to `ongoing/` or back to `backlog/`), update this file accordingly.

## Execution Order

| # | Ticket | Title | Size | Priority | Dependencies |
|---|--------|-------|------|----------|--------------|
| 4 | BLO-028 | Save state management tools | S | P1 | BLO-021 ✅ |
| 5 | BLO-030 | Memory diff between save states | S | P1 | BLO-021 ✅ |
| 6 | BLO-034 | Byte pattern search & string detection | M | P1 | BLO-013 ✅ |
| 7 | BLO-038 | KB struct and enum definitions | M | P1 | BLO-005 ✅ |
| 8 | BLO-040 | KB symbol import | M | P1 | BLO-005 ✅ |
| 9 | BLO-039 | KB export multi-format | M | P1 | BLO-005 ✅ |
| 10 | BLO-027 | Breakpoint system | M | P1 | BLO-021 ✅ |
| 11 | BLO-029 | Call stack reconstruction | M | P1 | BLO-021 ✅, BLO-015 ✅ |
| 12 | BLO-037 | Execution tracing & profiling | M | P1 | BLO-021 ✅ |
| 13 | BLO-031 | Input sequence playback & recording | M | P1 | BLO-021 ✅ |
| 14 | BLO-033 | VRAM, sprite, and tilemap inspection | L | P1 | BLO-022 ✅ |
| 15 | BLO-035 | Control flow graph builder | L | P1 | BLO-016 ✅ |
| 16 | BLO-036 | Cross-reference analysis | L | P1 | BLO-016 ✅, BLO-005 ✅ |
| 17 | BLO-053 | Watchpoint system | M | P2 | BLO-027 (#10) |
| 18 | BLO-056 | Symbol file auto-import | M | P2 | BLO-040 (#8) |
| 19 | BLO-043 | Visual diff & entropy analysis | S | P2 | BLO-022 ✅ |
| 20 | BLO-058 | Test ROM generator for CI | M | P2 | BLO-013 ✅ |

## Ordering Rationale

1. **Positions 1-5 (small P1):** Quick wins to build momentum — each is independently valuable with minimal complexity.
2. **Positions 6-9 (medium P1, search + KB):** Core search capability and KB data model completion. BLO-040 unblocks BLO-056 later.
3. **Positions 10-13 (medium P1, debugging + dynamic):** Interactive debugging loop and execution analysis. BLO-027 unblocks BLO-053 later.
4. **Positions 14-16 (large P1):** The hardest P1 features — visual inspection, CFG, and cross-references. Core decompilation pipeline.
5. **Positions 17-20 (P2):** Strategic P2 tickets — two extend P1 features completed earlier (#17, #18), one is a quick analysis win (#19), one strengthens CI (#20).
