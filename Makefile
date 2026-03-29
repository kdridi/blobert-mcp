.DEFAULT_GOAL := help

.PHONY: help setup test lint format check verify-ticket clean run

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

setup: ## Install dependencies and pre-commit hooks
	uv sync
	uv run pre-commit install

test: ## Run tests with pytest
	uv run pytest

lint: ## Run ruff linter
	uv run ruff check .

format: ## Format code with ruff
	uv run ruff format .

check: ## Run lint + format check + tests + ticket integrity
	uv run ruff check .
	uv run ruff format --check .
	uv run pytest
	@$(MAKE) --no-print-directory verify-ticket

verify-ticket: ## Verify ticket lifecycle integrity
	@echo "Checking ticket integrity..."
	@for f in tickets/completed/BLO-*.md; do \
		[ -f "$$f" ] || continue; \
		id=$$(basename "$$f" .md); \
		if [ -f "tickets/backlog/$$id.md" ]; then \
			echo "ERROR: $$id exists in both backlog/ and completed/"; \
			exit 1; \
		fi; \
		if [ -f "tickets/planned/$$id.md" ]; then \
			echo "ERROR: $$id exists in both planned/ and completed/"; \
			exit 1; \
		fi; \
		if [ -f "tickets/ongoing/$$id.md" ]; then \
			echo "ERROR: $$id exists in both ongoing/ and completed/"; \
			exit 1; \
		fi; \
	done
	@count=$$(ls tickets/ongoing/BLO-*.md 2>/dev/null | wc -l | tr -d ' '); \
	if [ "$$count" -gt 1 ]; then \
		echo "ERROR: $$count tickets in ongoing/ (max 1)"; \
		exit 1; \
	fi
	@for f in tickets/completed/BLO-*.md; do \
		[ -f "$$f" ] || continue; \
		unchecked=$$(grep -c '^- \[ \]' "$$f" 2>/dev/null; true); \
		if [ "$$unchecked" -gt 0 ]; then \
			echo "WARNING: $$(basename $$f) has $$unchecked unchecked criteria"; \
		fi; \
	done
	@echo "Ticket integrity OK"

clean: ## Remove build artifacts and caches
	rm -rf dist/ build/ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache

run: ## Run the MCP server
	uv run blobert-mcp
