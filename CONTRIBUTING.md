# Contributing to blobert-mcp

Thank you for your interest in contributing to blobert-mcp! This document
covers how to set up the project for development and the conventions we follow.

## Prerequisites

- **Python 3.10+**
- **[uv](https://docs.astral.sh/uv/)** — Python package manager
- **git**

## Development Setup

```bash
git clone https://github.com/kdridi/blobert-mcp.git
cd blobert-mcp
make setup
```

`make setup` runs `uv sync` (installs all dependencies including dev tools)
and `uv run pre-commit install` (sets up commit hooks).

### Pre-commit Hooks

Pre-commit hooks run automatically on every commit:

- Trailing whitespace removal
- End-of-file fixer
- YAML and TOML syntax validation
- [Ruff](https://docs.astral.sh/ruff/) linting with auto-fix
- Ruff formatting

### Useful Make Targets

| Target         | Description                      |
| -------------- | -------------------------------- |
| `make setup`   | Install deps and pre-commit hooks |
| `make check`   | Lint + format check + tests      |
| `make test`    | Run tests with pytest            |
| `make lint`    | Run ruff linter                  |
| `make format`  | Format code with ruff            |
| `make clean`   | Remove build artifacts and caches |

## Ticket Workflow

This project follows a strict ticket-based workflow:

> **No code changes without an active ticket.**

Every code change — even a one-line fix — requires a ticket in `tickets/`.
Tickets move through: `backlog/` &rarr; `ongoing/` &rarr; `completed/`.
Only one ticket may be in `ongoing/` at a time.

See [CLAUDE.md](CLAUDE.md) for the full ticket system documentation, including
the ticket template, lifecycle, and sub-agent roles.

## Commit Messages

All commits must reference their ticket ID:

```
BLO-XXX: Short description of the change
```

One ticket may span multiple commits.

## Code Style

- **Python 3.10+** — do not use features from newer Python versions
- Enforced by [Ruff](https://docs.astral.sh/ruff/) with:
  - Line length: 88
  - Rules: E, F, W, I, UP
  - Target version: `py310`
- Pre-commit hooks auto-fix style issues on commit — no manual formatting needed

## Pull Request Process

1. Pick a ticket from `tickets/backlog/` (or create one)
2. Verify `tickets/ongoing/` is empty, then move your ticket there
3. Create a branch and implement the changes
4. Ensure `make check` passes
5. Open a PR with a title starting with the ticket ID (e.g., `BLO-007: Add health files`)
6. [@kdridi](https://github.com/kdridi) is assigned as the default reviewer
   via [CODEOWNERS](CODEOWNERS)

## ROM Files

ROM files (`.gb`, `.gbc`, `.sgb`) must be **legally obtained** by each
developer. ROM files are never committed to the repository — they are excluded
by `.gitignore`. Do not include ROM data in PRs, issues, or documentation.

## Code of Conduct

This project follows the [Contributor Covenant v2.1](CODE_OF_CONDUCT.md).

## Security

To report a vulnerability, see [SECURITY.md](SECURITY.md).
