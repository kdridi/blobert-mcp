"""SQLite-backed KnowledgeBase for per-ROM annotations, functions, and variables."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from blobert_mcp.domain.kb import (
    rank_search_results,
    validate_address,
    validate_annotation_type,
    validate_name,
    validate_variable_type,
)

_SENTINEL_BANK = -1  # NULL bank mapped to -1 for UNIQUE constraint correctness


class KnowledgeBase:
    """Per-ROM knowledge base backed by SQLite.

    All bank parameters map ``None`` → ``-1`` internally so that
    ``UNIQUE(address, bank)`` constraints work correctly (SQLite treats
    ``NULL != NULL``).
    """

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._label_cache: dict[tuple[int, int], str | None] = {}
        self._create_tables()

    def _create_tables(self) -> None:
        self._conn.executescript(
            """\
            CREATE TABLE IF NOT EXISTS annotations (
                id INTEGER PRIMARY KEY,
                address INTEGER NOT NULL,
                bank INTEGER NOT NULL DEFAULT -1,
                label TEXT,
                type TEXT CHECK(type IN ('code','data','gfx','audio','text')),
                comment TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(address, bank)
            );

            CREATE TABLE IF NOT EXISTS functions (
                id INTEGER PRIMARY KEY,
                address INTEGER NOT NULL,
                end_address INTEGER,
                bank INTEGER NOT NULL DEFAULT -1,
                name TEXT NOT NULL,
                params TEXT,
                description TEXT,
                returns TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(address, bank)
            );

            CREATE TABLE IF NOT EXISTS variables (
                id INTEGER PRIMARY KEY,
                address INTEGER NOT NULL,
                name TEXT NOT NULL,
                type TEXT CHECK(type IN ('u8','u16','bool','enum')),
                description TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(address)
            );

            CREATE INDEX IF NOT EXISTS idx_annotations_address
                ON annotations(address, bank);
            CREATE INDEX IF NOT EXISTS idx_functions_address
                ON functions(address, bank);
            CREATE INDEX IF NOT EXISTS idx_variables_address
                ON variables(address);
            """
        )

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def _bank(self, bank: int | None) -> int:
        return bank if bank is not None else _SENTINEL_BANK

    def annotate(
        self,
        address: int,
        *,
        bank: int | None = None,
        label: str | None = None,
        type: str | None = None,
        comment: str | None = None,
    ) -> int:
        """Create or update an annotation. Returns the annotation id."""
        validate_address(address)
        validate_annotation_type(type)
        b = self._bank(bank)
        cur = self._conn.execute(
            """\
            INSERT INTO annotations (address, bank, label, type, comment)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(address, bank) DO UPDATE SET
                label = COALESCE(excluded.label, annotations.label),
                type = COALESCE(excluded.type, annotations.type),
                comment = COALESCE(excluded.comment, annotations.comment),
                updated_at = CURRENT_TIMESTAMP
            """,
            (address, b, label, type, comment),
        )
        self._conn.commit()
        # Invalidate cache for this address+bank
        self._label_cache.pop((address, b), None)
        return cur.lastrowid  # type: ignore[return-value]

    def define_function(
        self,
        address: int,
        *,
        end_address: int | None = None,
        bank: int | None = None,
        name: str,
        params: list | None = None,
        description: str | None = None,
        returns: str | None = None,
    ) -> int:
        """Create or update a function definition. Returns the function id."""
        validate_address(address)
        validate_name(name)
        b = self._bank(bank)
        params_json = json.dumps(params) if params is not None else None
        cur = self._conn.execute(
            """\
            INSERT INTO functions
                (address, end_address, bank, name, params, description, returns)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(address, bank) DO UPDATE SET
                end_address = COALESCE(excluded.end_address, functions.end_address),
                name = excluded.name,
                params = COALESCE(excluded.params, functions.params),
                description = COALESCE(excluded.description, functions.description),
                returns = COALESCE(excluded.returns, functions.returns)
            """,
            (address, end_address, b, name, params_json, description, returns),
        )
        self._conn.commit()
        self._label_cache.pop((address, b), None)
        return cur.lastrowid  # type: ignore[return-value]

    def define_variable(
        self,
        address: int,
        *,
        name: str,
        type: str,
        description: str | None = None,
    ) -> int:
        """Create or update a variable definition. Returns the variable id."""
        validate_address(address)
        validate_name(name)
        validate_variable_type(type)
        cur = self._conn.execute(
            """\
            INSERT INTO variables (address, name, type, description)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(address) DO UPDATE SET
                name = excluded.name,
                type = excluded.type,
                description = COALESCE(excluded.description, variables.description)
            """,
            (address, name, type, description),
        )
        self._conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(self, query: str, *, filter: str | None = None) -> list[dict]:
        """Search the KB. Returns max 50 results sorted by relevance."""
        if not query or not query.strip():
            return []

        if filter == "address":
            return self._search_by_address(query)
        if filter == "type":
            return self._search_by_type(query)

        # Default: search across labels, names, comments
        pattern = f"%{query}%"
        results: list[dict] = []

        # Annotations
        cur = self._conn.execute(
            "SELECT id, address, bank, label, type, comment "
            "FROM annotations WHERE label LIKE ? OR comment LIKE ?",
            (pattern, pattern),
        )
        for row in cur.fetchall():
            results.append(self._annotation_row_to_dict(row))

        # Functions
        cur = self._conn.execute(
            "SELECT id, address, bank, name, description "
            "FROM functions WHERE name LIKE ? OR description LIKE ?",
            (pattern, pattern),
        )
        for row in cur.fetchall():
            results.append(self._function_row_to_dict(row))

        # Variables
        cur = self._conn.execute(
            "SELECT id, address, name, type, description "
            "FROM variables WHERE name LIKE ? OR description LIKE ?",
            (pattern, pattern),
        )
        for row in cur.fetchall():
            results.append(self._variable_row_to_dict(row))

        return rank_search_results(results, query)

    def _search_by_address(self, query: str) -> list[dict]:
        try:
            addr = int(query, 0)
        except ValueError:
            return []
        results: list[dict] = []
        cur = self._conn.execute(
            "SELECT id, address, bank, label, type, comment "
            "FROM annotations WHERE address = ?",
            (addr,),
        )
        for row in cur.fetchall():
            results.append(self._annotation_row_to_dict(row))
        cur = self._conn.execute(
            "SELECT id, address, bank, name, description "
            "FROM functions WHERE address = ?",
            (addr,),
        )
        for row in cur.fetchall():
            results.append(self._function_row_to_dict(row))
        cur = self._conn.execute(
            "SELECT id, address, name, type, description "
            "FROM variables WHERE address = ?",
            (addr,),
        )
        for row in cur.fetchall():
            results.append(self._variable_row_to_dict(row))
        return results[:50]

    def _search_by_type(self, query: str) -> list[dict]:
        results: list[dict] = []
        cur = self._conn.execute(
            "SELECT id, address, bank, label, type, comment "
            "FROM annotations WHERE type = ?",
            (query,),
        )
        for row in cur.fetchall():
            results.append(self._annotation_row_to_dict(row))
        return results[:50]

    # ------------------------------------------------------------------
    # Row → dict helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _annotation_row_to_dict(row: tuple) -> dict:
        bank = row[2] if row[2] != _SENTINEL_BANK else None
        return {
            "id": row[0],
            "address": row[1],
            "bank": bank,
            "label": row[3],
            "type": row[4],
            "comment": row[5],
            "source": "annotation",
        }

    @staticmethod
    def _function_row_to_dict(row: tuple) -> dict:
        bank = row[2] if row[2] != _SENTINEL_BANK else None
        return {
            "id": row[0],
            "address": row[1],
            "bank": bank,
            "name": row[3],
            "description": row[4],
            "source": "function",
        }

    @staticmethod
    def _variable_row_to_dict(row: tuple) -> dict:
        return {
            "id": row[0],
            "address": row[1],
            "name": row[2],
            "type": row[3],
            "description": row[4],
            "source": "variable",
        }

    # ------------------------------------------------------------------
    # Label lookup (hot path)
    # ------------------------------------------------------------------

    def get_label(self, address: int, bank: int | None = None) -> str | None:
        """Fast label lookup with caching. Returns annotation label or function name."""
        b = self._bank(bank)
        key = (address, b)
        if key in self._label_cache:
            return self._label_cache[key]

        # Try annotation label first
        cur = self._conn.execute(
            "SELECT label FROM annotations"
            " WHERE address = ? AND bank = ? AND label IS NOT NULL",
            (address, b),
        )
        row = cur.fetchone()
        if row:
            self._label_cache[key] = row[0]
            return row[0]

        # Fall back to function name
        cur = self._conn.execute(
            "SELECT name FROM functions WHERE address = ? AND bank = ?",
            (address, b),
        )
        row = cur.fetchone()
        label = row[0] if row else None
        self._label_cache[key] = label
        return label

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def annotation_count(self) -> int:
        """Total number of entries across all three tables."""
        cur = self._conn.execute(
            "SELECT "
            "(SELECT COUNT(*) FROM annotations) + "
            "(SELECT COUNT(*) FROM functions) + "
            "(SELECT COUNT(*) FROM variables)"
        )
        return cur.fetchone()[0]

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()


def kb_path_for_rom(rom_path: str) -> Path:
    """Derive KB database path from ROM path: ``~/.blobert-mcp/<stem>.db``."""
    stem = Path(rom_path).stem
    kb_dir = Path.home() / ".blobert-mcp"
    kb_dir.mkdir(parents=True, exist_ok=True)
    return kb_dir / f"{stem}.db"
