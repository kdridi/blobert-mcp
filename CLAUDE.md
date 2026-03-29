# blobert-mcp — Project Instructions

An MCP server for LLM-assisted Game Boy ROM decompilation. See [README.md](README.md) for project overview.

---

## Golden Rule

**No code changes without an active ticket.**

- A **code change** is any modification to files outside `tickets/` and `docs/`.
- An **active ticket** is a ticket file present in `tickets/ongoing/` with `status: ongoing`.
- If no active ticket exists, **refuse the change** and offer to create a ticket first.
- Maximum **one ticket in `tickets/ongoing/` at a time** — this enforces focus and prevents scope creep.
- Even one-line fixes require a ticket. The discipline is the point.

---

## Ticket System

### Directory Layout

```
tickets/
├── TEMPLATE.md        # Canonical ticket template — copy this for new tickets
├── backlog/           # Ticket ideas — rough drafts, not yet refined
├── planned/           # Refined tickets — fully specified, ready to activate
├── ongoing/           # The one active ticket (max 1)
├── completed/         # Successfully finished tickets
└── rejected/          # Cancelled or invalid tickets
```

### Ticket Format

All tickets follow the template in `tickets/TEMPLATE.md`. Key fields:

| Field | Description |
|---|---|
| `id` | `BLO-XXX` — zero-padded 3-digit number |
| `title` | Concise description |
| `status` | `backlog` \| `planned` \| `ongoing` \| `completed` \| `rejected` |
| `priority` | `P0` \| `P1` \| `P2` (matches `docs/mcp-spec.md` convention) |
| `type` | `feature` \| `bugfix` \| `refactor` \| `docs` \| `research` \| `infrastructure` |
| `dependencies` | List of ticket IDs that must be completed first |
| `assignee` | `human` \| `ai` \| `unassigned` |
| `estimated_complexity` | `small` \| `medium` \| `large` |
| `created` / `updated` | Datetime in `YYYY-MM-DD HH:MM:SS` format (enables temporal sorting) |

### ID Assignment

To assign a new ticket ID:
1. Scan all files across `tickets/backlog/`, `tickets/planned/`, `tickets/ongoing/`, `tickets/completed/`, `tickets/rejected/`
2. Find the highest `BLO-XXX` number
3. Increment by 1, zero-pad to 3 digits

### Ticket Lifecycle

```
backlog → planned → ongoing → completed
                             → rejected
```

**1. Create** — Generate ticket from template, save to `tickets/backlog/BLO-XXX.md`. Backlog tickets are ideas — they may have rough acceptance criteria and incomplete technical approaches.

**2. Plan** — When a ticket is refined and ready for implementation:
  - Ensure all frontmatter fields are complete, acceptance criteria are concrete, and technical approach is specified
  - Use `git mv tickets/backlog/BLO-XXX.md tickets/planned/BLO-XXX.md` — always `git mv`, never delete+recreate
  - Update frontmatter: `status: planned`, `updated: <now>`
  - Add log entry: `- <now>: Ticket planned.`

**3. Activate** — Before moving to `ongoing/`:
  - Verify `tickets/ongoing/` is empty (no other active ticket)
  - Verify all dependencies are in `tickets/completed/`
  - Use `git mv tickets/planned/BLO-XXX.md tickets/ongoing/BLO-XXX.md` — always `git mv`, never delete+recreate
  - Update frontmatter: `status: ongoing`, `updated: <now>`
  - Add log entry: `- <now>: Ticket activated.`

**4. Work** — While the ticket is active:
  - All code changes must fall within the ticket's scope
  - Append significant events to the Log section
  - Track every created/modified file in the Files Modified section
  - Every commit message must start with the ticket ID: `BLO-XXX: <description>`

**5. Complete** — When all acceptance criteria are met, execute these steps in order:
  1. Verify every `- [ ]` in Acceptance Criteria is now `- [x]`. If any remain unchecked, stop.
  2. Ensure the `## Files Modified` section lists every file created or changed.
  3. Add log entry: `- <now>: Ticket completed.`
  4. Update frontmatter: `status: completed`, `updated: <now>`
  5. Use `git mv tickets/ongoing/BLO-XXX.md tickets/completed/BLO-XXX.md` — always `git mv`, never delete+recreate. This stages both the deletion and creation in one step.
  6. Update `.claude/agent-memory/ticket-analyzer/project_state.md` if applicable, then `git add` it.
  7. Stage all other modified files (`git add` the specific files).
  8. Commit everything in a **single commit**. The old ticket path, the new ticket path, project_state.md, and any remaining changes must all be in this one commit. Never split ticket cleanup into a separate commit.

**6. Reject** — If the ticket is cancelled or invalid:
  - Document the reason in the Log section
  - Update frontmatter: `status: rejected`, `updated: <now>`
  - Use `git mv tickets/ongoing/BLO-XXX.md tickets/rejected/BLO-XXX.md` (or from `backlog/` or `planned/`) — always `git mv`, never delete+recreate
  - Check if other tickets depend on this one and flag them for review

---

## Sub-Agents

### Ticketing AI

**Purpose:** Analyze project state and generate well-formed tickets.

**Trigger:** User says "create tickets", "what tickets do we need", "analyze the backlog", or similar.

**Behavior:**
1. Read `docs/mcp-spec.md`, `docs/journal.md`, and all existing tickets
2. Identify gaps between the spec and current implementation
3. Generate tickets using `tickets/TEMPLATE.md` format
4. Place them in `tickets/backlog/`
5. Assign priorities consistent with `docs/mcp-spec.md` P0/P1/P2 classification
6. Group related tools into logical tickets (don't create one ticket per tool)

**Constraints:** Only creates files in `tickets/backlog/`. Never modifies code.

### Project Organization AI

**Purpose:** Maintain project structure, move tickets, enforce conventions.

**Trigger:** User says "organize tickets", "move ticket BLO-XXX to completed", "clean up", or similar.

**Behavior:**
1. Validate ticket format (all frontmatter fields present, ID consistency, file in correct directory for its status)
2. Move tickets between directories as requested
3. Update the `status` and `updated` fields in frontmatter when moving
4. Verify no orphaned dependencies (tickets depending on rejected tickets)

**Constraints:** Only modifies files in `tickets/`. Never modifies code.

### Project Management AI

**Purpose:** Strategic oversight — roadmap analysis, priority recommendations, progress tracking.

**Trigger:** User says "project status", "what should we work on next", "roadmap", "sprint planning", or similar.

**Behavior:**
1. Read all tickets across all status directories
2. Assess progress: completed count, ongoing work, backlog size, P0 coverage
3. Identify blockers: unresolved dependencies, missing prerequisites
4. Recommend the next ticket to work on based on priority + dependency ordering
5. Generate summary reports
6. May suggest new tickets (delegates creation to Ticketing AI)

**Constraints:** Read-only analysis. Does not modify any files directly.

---

## Workflow Examples

### Working on a Ticket

```
1. User: "Let's work on BLO-003"
2. AI reads tickets/planned/BLO-003.md (or tickets/backlog/ if not yet planned)
3. AI verifies tickets/ongoing/ is empty
4. AI verifies BLO-003 dependencies are all in tickets/completed/
5. AI moves BLO-003.md to tickets/ongoing/ and updates status → ongoing
6. AI confirms the objective and acceptance criteria with the user
7. AI implements the work
8. AI updates BLO-003.md: checks criteria, fills Files Modified, adds Log entries
9. AI moves BLO-003.md to tickets/completed/ and updates status → completed
```

### Creating Tickets from the Spec

```
1. User: "Create tickets for the P0 tools"
2. AI (Ticketing role) reads docs/mcp-spec.md
3. AI identifies all P0 tools and groups them logically
4. AI creates BLO-001.md through BLO-00N.md in tickets/backlog/
5. AI reports what was created
```

### Quick Fix Request

```
1. User: "Just fix this import error"
2. AI: "I need a ticket for this. Let me create one."
3. AI creates a minimal ticket in tickets/backlog/ (or directly in tickets/planned/ if fully specified)
4. AI activates it (moves to ongoing/)
5. AI makes the fix
6. AI completes the ticket (moves to completed/)
```

---

## Conventions

### Commits
- Every commit message starts with the ticket ID: `BLO-XXX: <short description>`
- One ticket may span multiple commits

### File Scope Rules
| Path | Rule |
|---|---|
| `tickets/` | Managed by the ticketing system |
| `docs/` | Can be updated as part of any ticket |
| `src/` | Only modified under an active ticket |
| `tests/` | Only modified under an active ticket |
| Root config files | Only modified under an active ticket |
| `CLAUDE.md` | Only modified under explicit user instruction |
| `README.md` | Updated when significant milestones are reached |
| `.claude/agent-memory/ticket-analyzer/project_state.md` | Stage with the ticket completion commit if modified — never as a standalone commit |

### Code
- Python 3.10+
- Use `uv` for package management
- Follow existing documentation style (see `docs/` for reference)

### Linting & Pre-commit
- The repo uses **ruff** for linting and formatting (`pyproject.toml` → `[tool.ruff]`).
- A **pre-commit hook** is configured in `.pre-commit-config.yaml` (ruff lint + format, trailing whitespace, etc.).
- After cloning, run `make setup` to install the hook (runs `uv run pre-commit install`).
- **Before committing, always run `make check`** (lint + format check + tests) to catch issues locally.
- CI runs the same ruff checks — if the pre-commit hook is installed, CI lint failures are prevented.

---

## Architecture

See `docs/architecture.md` for the full architecture documentation.

### Key Rules (enforced on every code change)

1. **Domain isolation**: `domain/` imports nothing from the project. Pure functions, stdlib + dataclasses only.
2. **Dependency direction**: `tools/` -> `domain/` -> nothing. Never the reverse.
3. **Thin tools**: Tool handlers validate, read bytes, delegate to domain, format output. No business logic in tools.
4. **Error convention**: Tools return `{"error": "CODE", "message": "..."}` on failure. Domain functions raise exceptions.

### Design Decisions

See `docs/decisions.md` for the full decision log.

- Significant design choices get a `D-XXX` entry in `docs/decisions.md`.
- A "significant" choice is one where alternatives were considered or the rationale is non-obvious.
- When making a decision during ticket work, append it to `docs/decisions.md` and reference the `D-XXX` ID in the ticket's `## Decisions` section.
- Do not record routine implementation choices (variable names, loop vs comprehension, etc.).

### Testing

See `docs/testing-strategy.md` for the full testing strategy.

- **Domain modules use TDD**: Write tests first, then implementation. This is not optional.
- **Test data is synthetic**: Never use copyrighted ROMs in tests. Use byte literals.
- **Mirror layout**: `tests/domain/` tests `src/blobert_mcp/domain/`, `tests/tools/` tests `src/blobert_mcp/tools/`.
