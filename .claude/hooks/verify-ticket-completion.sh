#!/usr/bin/env bash
# verify-ticket-completion.sh — Claude Code Stop hook
#
# Runs at the end of every Claude turn. Checks git state for ticket
# completion problems:
#   1. Orphaned ticket files (old path not staged for deletion)
#   2. project_state.md modified but not staged
#   3. Unchecked acceptance criteria in completed tickets
#
# Advisory only — outputs a warning description, never blocks.

set -euo pipefail

TICKETS_DIR="tickets"
PROJECT_STATE=".claude/agent-memory/ticket-analyzer/project_state.md"

warnings=""

# --- Check 1: Recently staged completed tickets ---
# Look for tickets/completed/BLO-*.md in the staged changes
staged_completed=$(git diff --cached --name-only 2>/dev/null | grep "^${TICKETS_DIR}/completed/BLO-" || true)

for completed_file in $staged_completed; do
    ticket_id=$(basename "$completed_file" .md)

    # Check for orphaned file in backlog/
    backlog_file="${TICKETS_DIR}/backlog/${ticket_id}.md"
    if [ -f "$backlog_file" ]; then
        # File exists on disk — is its deletion staged?
        if ! git diff --cached --name-only 2>/dev/null | grep -q "^${backlog_file}$"; then
            warnings="${warnings}\n- ${backlog_file} still exists on disk but is not staged for deletion. Use: git rm ${backlog_file}"
        fi
    fi

    # Check for orphaned file in planned/
    planned_file="${TICKETS_DIR}/planned/${ticket_id}.md"
    if [ -f "$planned_file" ]; then
        if ! git diff --cached --name-only 2>/dev/null | grep -q "^${planned_file}$"; then
            warnings="${warnings}\n- ${planned_file} still exists on disk but is not staged for deletion. Use: git rm ${planned_file}"
        fi
    fi

    # Check for orphaned file in ongoing/
    ongoing_file="${TICKETS_DIR}/ongoing/${ticket_id}.md"
    if [ -f "$ongoing_file" ]; then
        if ! git diff --cached --name-only 2>/dev/null | grep -q "^${ongoing_file}$"; then
            warnings="${warnings}\n- ${ongoing_file} still exists on disk but is not staged for deletion. Use: git rm ${ongoing_file}"
        fi
    fi

    # Check for unchecked acceptance criteria
    if [ -f "$completed_file" ]; then
        unchecked=$(grep -c '^\- \[ \]' "$completed_file" 2>/dev/null || echo 0)
        if [ "$unchecked" -gt 0 ]; then
            warnings="${warnings}\n- ${ticket_id} has ${unchecked} unchecked acceptance criteria"
        fi
    fi
done

# --- Check 2: project_state.md modified but not staged ---
if git diff --name-only 2>/dev/null | grep -q "^${PROJECT_STATE}$"; then
    # Modified in working tree but not staged
    if ! git diff --cached --name-only 2>/dev/null | grep -q "^${PROJECT_STATE}$"; then
        warnings="${warnings}\n- ${PROJECT_STATE} is modified but not staged. It must be in the same commit as the ticket completion."
    fi
fi

# --- Check 3: Ticket files in wrong directory for their status ---
for f in ${TICKETS_DIR}/backlog/BLO-*.md; do
    [ -f "$f" ] || continue
    status=$(grep '^status:' "$f" 2>/dev/null | head -1 | awk '{print $2}')
    if [ "$status" != "backlog" ]; then
        warnings="${warnings}\n- $(basename "$f") has status '${status}' but is in backlog/"
    fi
done

for f in ${TICKETS_DIR}/planned/BLO-*.md; do
    [ -f "$f" ] || continue
    status=$(grep '^status:' "$f" 2>/dev/null | head -1 | awk '{print $2}')
    if [ "$status" != "planned" ]; then
        warnings="${warnings}\n- $(basename "$f") has status '${status}' but is in planned/"
    fi
done

for f in ${TICKETS_DIR}/ongoing/BLO-*.md; do
    [ -f "$f" ] || continue
    status=$(grep '^status:' "$f" 2>/dev/null | head -1 | awk '{print $2}')
    if [ "$status" != "ongoing" ]; then
        warnings="${warnings}\n- $(basename "$f") has status '${status}' but is in ongoing/"
    fi
done

# --- Output ---
if [ -n "$warnings" ]; then
    # Use printf to interpret \n sequences, then format as JSON
    message=$(printf "Ticket lifecycle warnings:%b" "$warnings")
    # Escape for JSON
    message=$(echo "$message" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read().strip()))')
    echo "{\"description\": ${message}}"
fi

exit 0
