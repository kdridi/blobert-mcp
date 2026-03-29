"""TDD tests for KnowledgeBase SQLite layer — written before implementation."""

from __future__ import annotations

import json
import time

import pytest

from blobert_mcp.kb.database import KnowledgeBase

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_kb() -> KnowledgeBase:
    """Create an in-memory KnowledgeBase for testing."""
    return KnowledgeBase(":memory:")


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------


class TestKnowledgeBaseInit:
    def test_creates_tables(self):
        kb = _make_kb()
        cur = kb._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row[0] for row in cur.fetchall()]
        assert "annotations" in tables
        assert "functions" in tables
        assert "variables" in tables
        kb.close()

    def test_idempotent_init(self):
        kb = _make_kb()
        # Calling _create_tables again should not error
        kb._create_tables()
        kb.close()


# ---------------------------------------------------------------------------
# annotate
# ---------------------------------------------------------------------------


class TestAnnotate:
    def test_create_returns_id(self):
        kb = _make_kb()
        aid = kb.annotate(0x0100, label="entry")
        assert isinstance(aid, int)
        assert aid > 0
        kb.close()

    def test_create_with_all_fields(self):
        kb = _make_kb()
        aid = kb.annotate(
            0x0100, bank=1, label="vblank", type="code", comment="VBlank handler"
        )
        assert aid > 0
        kb.close()

    def test_create_minimal(self):
        kb = _make_kb()
        aid = kb.annotate(0x0100)
        assert aid > 0
        kb.close()

    def test_upsert_updates_existing(self):
        kb = _make_kb()
        kb.annotate(0x0100, label="old")
        kb.annotate(0x0100, label="new")
        # Should update, not create duplicate
        cur = kb._conn.execute("SELECT COUNT(*) FROM annotations WHERE address = 256")
        assert cur.fetchone()[0] == 1
        # Label should be updated
        cur = kb._conn.execute(
            "SELECT label FROM annotations WHERE address = 256 AND bank = -1"
        )
        assert cur.fetchone()[0] == "new"
        kb.close()

    def test_invalid_type_raises_valueerror(self):
        kb = _make_kb()
        with pytest.raises(ValueError, match="annotation type"):
            kb.annotate(0x0100, type="invalid")
        kb.close()

    def test_negative_address_raises_valueerror(self):
        kb = _make_kb()
        with pytest.raises(ValueError, match="address"):
            kb.annotate(-1, label="bad")
        kb.close()

    def test_bank_none_and_bank_0_are_separate(self):
        kb = _make_kb()
        kb.annotate(0x4000, label="no_bank")
        kb.annotate(0x4000, bank=0, label="bank_0")
        cur = kb._conn.execute("SELECT COUNT(*) FROM annotations WHERE address = 16384")
        assert cur.fetchone()[0] == 2
        kb.close()

    def test_updated_at_changes_on_upsert(self):
        kb = _make_kb()
        kb.annotate(0x0100, label="old")
        cur = kb._conn.execute(
            "SELECT updated_at FROM annotations WHERE address = 256 AND bank = -1"
        )
        first_ts = cur.fetchone()[0]
        time.sleep(0.05)
        kb.annotate(0x0100, label="new")
        cur = kb._conn.execute(
            "SELECT updated_at FROM annotations WHERE address = 256 AND bank = -1"
        )
        second_ts = cur.fetchone()[0]
        assert second_ts >= first_ts
        kb.close()


# ---------------------------------------------------------------------------
# define_function
# ---------------------------------------------------------------------------


class TestDefineFunction:
    def test_create_returns_id(self):
        kb = _make_kb()
        fid = kb.define_function(0x0150, name="main")
        assert isinstance(fid, int)
        assert fid > 0
        kb.close()

    def test_create_with_all_fields(self):
        kb = _make_kb()
        fid = kb.define_function(
            0x0150,
            end_address=0x0180,
            bank=1,
            name="vblank_handler",
            params=["a: u8", "b: u16"],
            description="Handles VBlank interrupt",
            returns="void",
        )
        assert fid > 0
        kb.close()

    def test_upsert_updates_existing(self):
        kb = _make_kb()
        kb.define_function(0x0150, name="old_name")
        kb.define_function(0x0150, name="new_name")
        cur = kb._conn.execute("SELECT COUNT(*) FROM functions WHERE address = 336")
        assert cur.fetchone()[0] == 1
        cur = kb._conn.execute(
            "SELECT name FROM functions WHERE address = 336 AND bank = -1"
        )
        assert cur.fetchone()[0] == "new_name"
        kb.close()

    def test_empty_name_raises_valueerror(self):
        kb = _make_kb()
        with pytest.raises(ValueError, match="name"):
            kb.define_function(0x0150, name="")
        kb.close()

    def test_params_stored_as_json(self):
        kb = _make_kb()
        params = ["a: u8", "b: u16"]
        kb.define_function(0x0150, name="func", params=params)
        cur = kb._conn.execute(
            "SELECT params FROM functions WHERE address = 336 AND bank = -1"
        )
        stored = cur.fetchone()[0]
        assert json.loads(stored) == params
        kb.close()

    def test_params_none_accepted(self):
        kb = _make_kb()
        fid = kb.define_function(0x0150, name="func")
        assert fid > 0
        cur = kb._conn.execute(
            "SELECT params FROM functions WHERE address = 336 AND bank = -1"
        )
        assert cur.fetchone()[0] is None
        kb.close()


# ---------------------------------------------------------------------------
# define_variable
# ---------------------------------------------------------------------------


class TestDefineVariable:
    def test_create_returns_id(self):
        kb = _make_kb()
        vid = kb.define_variable(0xC000, name="player_x", type="u8")
        assert isinstance(vid, int)
        assert vid > 0
        kb.close()

    def test_create_with_all_fields(self):
        kb = _make_kb()
        vid = kb.define_variable(
            0xC000, name="player_x", type="u8", description="Player X position"
        )
        assert vid > 0
        kb.close()

    def test_upsert_updates_existing(self):
        kb = _make_kb()
        kb.define_variable(0xC000, name="old_var", type="u8")
        kb.define_variable(0xC000, name="new_var", type="u16")
        cur = kb._conn.execute("SELECT COUNT(*) FROM variables WHERE address = 49152")
        assert cur.fetchone()[0] == 1
        cur = kb._conn.execute("SELECT name, type FROM variables WHERE address = 49152")
        row = cur.fetchone()
        assert row[0] == "new_var"
        assert row[1] == "u16"
        kb.close()

    def test_invalid_type_raises_valueerror(self):
        kb = _make_kb()
        with pytest.raises(ValueError, match="variable type"):
            kb.define_variable(0xC000, name="x", type="int32")
        kb.close()

    def test_empty_name_raises_valueerror(self):
        kb = _make_kb()
        with pytest.raises(ValueError, match="name"):
            kb.define_variable(0xC000, name="", type="u8")
        kb.close()

    def test_uniqueness_on_address(self):
        kb = _make_kb()
        kb.define_variable(0xC000, name="var1", type="u8")
        kb.define_variable(0xC000, name="var2", type="u16")
        cur = kb._conn.execute("SELECT COUNT(*) FROM variables WHERE address = 49152")
        assert cur.fetchone()[0] == 1
        kb.close()


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


class TestSearch:
    def test_search_by_label_exact(self):
        kb = _make_kb()
        kb.annotate(0x0100, label="vblank")
        results = kb.search("vblank")
        assert len(results) >= 1
        assert any(r["label"] == "vblank" for r in results)
        kb.close()

    def test_search_by_label_prefix(self):
        kb = _make_kb()
        kb.annotate(0x0100, label="vblank_handler")
        results = kb.search("vblank")
        assert len(results) >= 1
        kb.close()

    def test_search_by_label_substring(self):
        kb = _make_kb()
        kb.annotate(0x0100, label="handle_vblank")
        results = kb.search("vblank")
        assert len(results) >= 1
        kb.close()

    def test_search_by_comment(self):
        kb = _make_kb()
        kb.annotate(0x0100, label="entry", comment="Main entry point")
        results = kb.search("entry point")
        assert len(results) >= 1
        kb.close()

    def test_search_by_address_hex(self):
        kb = _make_kb()
        kb.annotate(0x0100, label="entry")
        results = kb.search("0x0100", filter="address")
        assert len(results) >= 1
        assert any(r["address"] == 0x0100 for r in results)
        kb.close()

    def test_search_by_type_filter(self):
        kb = _make_kb()
        kb.annotate(0x0100, label="entry", type="code")
        kb.annotate(0x0200, label="sprite", type="gfx")
        results = kb.search("code", filter="type")
        assert all(r["type"] == "code" for r in results)
        kb.close()

    def test_search_max_50_results(self):
        kb = _make_kb()
        for i in range(60):
            kb.annotate(i, label=f"item_{i}")
        results = kb.search("item")
        assert len(results) <= 50
        kb.close()

    def test_search_empty_query_returns_empty(self):
        kb = _make_kb()
        kb.annotate(0x0100, label="entry")
        results = kb.search("")
        assert results == []
        kb.close()

    def test_search_no_matches_returns_empty(self):
        kb = _make_kb()
        kb.annotate(0x0100, label="entry")
        results = kb.search("nonexistent_xyz")
        assert results == []
        kb.close()

    def test_search_across_tables(self):
        kb = _make_kb()
        kb.annotate(0x0100, label="main_entry")
        kb.define_function(0x0200, name="main_loop")
        kb.define_variable(0xC000, name="main_counter", type="u8")
        results = kb.search("main")
        assert len(results) == 3
        kb.close()

    def test_search_functions_by_name(self):
        kb = _make_kb()
        kb.define_function(0x0200, name="handle_input")
        results = kb.search("input")
        assert len(results) >= 1
        kb.close()

    def test_search_variables_by_name(self):
        kb = _make_kb()
        kb.define_variable(0xC000, name="scroll_x", type="u8")
        results = kb.search("scroll")
        assert len(results) >= 1
        kb.close()


# ---------------------------------------------------------------------------
# get_label
# ---------------------------------------------------------------------------


class TestGetLabel:
    def test_returns_label_for_annotated_address(self):
        kb = _make_kb()
        kb.annotate(0x0100, label="entry")
        assert kb.get_label(0x0100) == "entry"
        kb.close()

    def test_returns_none_for_unknown_address(self):
        kb = _make_kb()
        assert kb.get_label(0x9999) is None
        kb.close()

    def test_returns_label_with_bank(self):
        kb = _make_kb()
        kb.annotate(0x4000, bank=1, label="bank1_start")
        assert kb.get_label(0x4000, bank=1) == "bank1_start"
        kb.close()

    def test_returns_function_name_when_no_annotation_label(self):
        kb = _make_kb()
        kb.define_function(0x0200, name="my_func")
        assert kb.get_label(0x0200) == "my_func"
        kb.close()

    def test_annotation_label_preferred_over_function_name(self):
        kb = _make_kb()
        kb.annotate(0x0200, label="annotated_label")
        kb.define_function(0x0200, name="func_name")
        assert kb.get_label(0x0200) == "annotated_label"
        kb.close()

    def test_cache_hit_after_first_call(self):
        kb = _make_kb()
        kb.annotate(0x0100, label="entry")
        kb.get_label(0x0100)  # populate cache
        assert (0x0100, -1) in kb._label_cache
        kb.close()

    def test_cache_invalidated_after_annotate(self):
        kb = _make_kb()
        kb.annotate(0x0100, label="old")
        kb.get_label(0x0100)  # populate cache
        kb.annotate(0x0100, label="new")
        assert kb.get_label(0x0100) == "new"
        kb.close()


# ---------------------------------------------------------------------------
# annotation_count
# ---------------------------------------------------------------------------


class TestAnnotationCount:
    def test_returns_zero_initially(self):
        kb = _make_kb()
        assert kb.annotation_count() == 0
        kb.close()

    def test_returns_count_after_inserts(self):
        kb = _make_kb()
        kb.annotate(0x0100, label="a")
        kb.annotate(0x0200, label="b")
        assert kb.annotation_count() >= 2
        kb.close()

    def test_counts_all_tables(self):
        kb = _make_kb()
        kb.annotate(0x0100, label="a")
        kb.define_function(0x0200, name="f")
        kb.define_variable(0xC000, name="v", type="u8")
        assert kb.annotation_count() == 3
        kb.close()


# ---------------------------------------------------------------------------
# close
# ---------------------------------------------------------------------------


class TestClose:
    def test_close_closes_connection(self):
        kb = _make_kb()
        kb.close()
        # After close, operations should fail
        with pytest.raises(Exception):
            kb._conn.execute("SELECT 1")
