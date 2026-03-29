"""TDD tests for KnowledgeBase SQLite layer — written before implementation."""

from __future__ import annotations

import json
import time

import pytest

from blobert_mcp.domain.kb_import import ParsedSymbol
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
# get_function_info
# ---------------------------------------------------------------------------


class TestGetFunctionInfo:
    def test_lookup_by_name(self):
        kb = _make_kb()
        kb.define_function(0x0150, name="main", description="Entry point")
        result = kb.get_function_info("main")
        assert result is not None
        assert result["function"]["name"] == "main"
        assert result["function"]["address"] == 0x0150
        assert result["function"]["description"] == "Entry point"
        kb.close()

    def test_lookup_by_address(self):
        kb = _make_kb()
        kb.define_function(0x0150, name="main")
        result = kb.get_function_info(0x0150)
        assert result is not None
        assert result["function"]["name"] == "main"
        kb.close()

    def test_not_found_returns_none(self):
        kb = _make_kb()
        assert kb.get_function_info("nonexistent") is None
        assert kb.get_function_info(0x9999) is None
        kb.close()

    def test_includes_annotations_in_range(self):
        kb = _make_kb()
        kb.define_function(0x0100, end_address=0x0120, name="handler")
        kb.annotate(0x0110, label="mid_handler", comment="Middle of handler")
        result = kb.get_function_info("handler")
        assert len(result["annotations"]) == 1
        assert result["annotations"][0]["address"] == 0x0110
        kb.close()

    def test_excludes_annotations_outside_range(self):
        kb = _make_kb()
        kb.define_function(0x0100, end_address=0x0120, name="handler")
        kb.annotate(0x0200, label="elsewhere")
        result = kb.get_function_info("handler")
        assert len(result["annotations"]) == 0
        kb.close()

    def test_includes_variables_in_range(self):
        kb = _make_kb()
        kb.define_function(0x0100, end_address=0x0120, name="handler")
        kb.define_variable(0x0110, name="local_var", type="u8")
        result = kb.get_function_info("handler")
        assert len(result["variables"]) == 1
        assert result["variables"][0]["name"] == "local_var"
        kb.close()

    def test_no_end_address_returns_empty_lists(self):
        kb = _make_kb()
        kb.define_function(0x0150, name="stub")
        result = kb.get_function_info("stub")
        assert result["annotations"] == []
        assert result["variables"] == []
        kb.close()

    def test_cross_references_placeholder(self):
        kb = _make_kb()
        kb.define_function(0x0150, name="func")
        result = kb.get_function_info("func")
        assert result["cross_references"] == []
        kb.close()

    def test_params_deserialized(self):
        kb = _make_kb()
        params = ["a: u8", "b: u16"]
        kb.define_function(0x0150, name="func", params=params)
        result = kb.get_function_info("func")
        assert result["function"]["params"] == params
        kb.close()

    def test_lookup_with_bank(self):
        kb = _make_kb()
        kb.define_function(0x4000, bank=1, name="bank1_func")
        result = kb.get_function_info(0x4000)
        assert result is not None
        assert result["function"]["bank"] == 1
        kb.close()


# ---------------------------------------------------------------------------
# rom_annotation_count
# ---------------------------------------------------------------------------


class TestRomAnnotationCount:
    def test_zero_initially(self):
        kb = _make_kb()
        assert kb.rom_annotation_count() == 0
        kb.close()

    def test_counts_rom_annotations(self):
        kb = _make_kb()
        kb.annotate(0x0100, label="a")
        kb.annotate(0x4000, label="b")
        assert kb.rom_annotation_count() == 2
        kb.close()

    def test_excludes_non_rom(self):
        kb = _make_kb()
        kb.annotate(0x8000, label="vram")
        assert kb.rom_annotation_count() == 0
        kb.close()

    def test_excludes_ram(self):
        kb = _make_kb()
        kb.annotate(0xC000, label="wram")
        assert kb.rom_annotation_count() == 0
        kb.close()

    def test_mixed_rom_and_non_rom(self):
        kb = _make_kb()
        kb.annotate(0x0100, label="rom1")
        kb.annotate(0x0200, label="rom2")
        kb.annotate(0x4000, label="rom3")
        kb.annotate(0x8000, label="vram")
        kb.annotate(0xC000, label="wram")
        assert kb.rom_annotation_count() == 3
        kb.close()


# ---------------------------------------------------------------------------
# function_count
# ---------------------------------------------------------------------------


class TestFunctionCount:
    def test_zero_initially(self):
        kb = _make_kb()
        assert kb.function_count() == 0
        kb.close()

    def test_counts_all(self):
        kb = _make_kb()
        kb.define_function(0x0100, name="f1")
        kb.define_function(0x0200, name="f2")
        kb.define_function(0x0300, name="f3")
        assert kb.function_count() == 3
        kb.close()


# ---------------------------------------------------------------------------
# variable_count
# ---------------------------------------------------------------------------


class TestVariableCount:
    def test_zero_initially(self):
        kb = _make_kb()
        assert kb.variable_count() == 0
        kb.close()

    def test_counts_all(self):
        kb = _make_kb()
        kb.define_variable(0xC000, name="v1", type="u8")
        kb.define_variable(0xC001, name="v2", type="u16")
        assert kb.variable_count() == 2
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


# ---------------------------------------------------------------------------
# struct/enum tables created
# ---------------------------------------------------------------------------


class TestCreateTablesStructEnum:
    def test_struct_tables_exist(self):
        kb = _make_kb()
        cur = kb._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row[0] for row in cur.fetchall()]
        assert "structs" in tables
        assert "struct_fields" in tables
        kb.close()

    def test_enum_tables_exist(self):
        kb = _make_kb()
        cur = kb._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row[0] for row in cur.fetchall()]
        assert "enums" in tables
        assert "enum_values" in tables
        kb.close()


# ---------------------------------------------------------------------------
# define_struct
# ---------------------------------------------------------------------------

_SPRITE_FIELDS = [
    {"name": "y", "offset": 0, "type": "u8", "size": 1},
    {"name": "x", "offset": 1, "type": "u8", "size": 1},
    {"name": "tile", "offset": 2, "type": "u8", "size": 1},
    {"name": "flags", "offset": 3, "type": "u8", "size": 1},
]


class TestDefineStruct:
    def test_create_returns_id(self):
        kb = _make_kb()
        sid = kb.define_struct("Sprite", _SPRITE_FIELDS)
        assert isinstance(sid, int)
        assert sid > 0
        kb.close()

    def test_total_size_computed(self):
        kb = _make_kb()
        kb.define_struct("Sprite", _SPRITE_FIELDS)
        cur = kb._conn.execute(
            "SELECT total_size FROM structs WHERE name = ?", ("Sprite",)
        )
        assert cur.fetchone()[0] == 4
        kb.close()

    def test_with_comment(self):
        kb = _make_kb()
        kb.define_struct("Sprite", _SPRITE_FIELDS, comment="OAM entry")
        cur = kb._conn.execute(
            "SELECT comment FROM structs WHERE name = ?", ("Sprite",)
        )
        assert cur.fetchone()[0] == "OAM entry"
        kb.close()

    def test_fields_stored_correctly(self):
        kb = _make_kb()
        kb.define_struct("Sprite", _SPRITE_FIELDS)
        cur = kb._conn.execute(
            "SELECT name, offset, type, size FROM struct_fields "
            "WHERE struct_id = (SELECT id FROM structs WHERE name = 'Sprite') "
            "ORDER BY offset"
        )
        rows = cur.fetchall()
        assert len(rows) == 4
        assert rows[0] == ("y", 0, "u8", 1)
        assert rows[1] == ("x", 1, "u8", 1)
        assert rows[2] == ("tile", 2, "u8", 1)
        assert rows[3] == ("flags", 3, "u8", 1)
        kb.close()

    def test_duplicate_name_raises_valueerror(self):
        kb = _make_kb()
        kb.define_struct("Sprite", _SPRITE_FIELDS)
        with pytest.raises(ValueError, match="already exists"):
            kb.define_struct("Sprite", _SPRITE_FIELDS)
        kb.close()

    def test_empty_name_raises_valueerror(self):
        kb = _make_kb()
        with pytest.raises(ValueError, match="name"):
            kb.define_struct("", _SPRITE_FIELDS)
        kb.close()

    def test_invalid_field_type_raises_valueerror(self):
        kb = _make_kb()
        bad_fields = [{"name": "x", "offset": 0, "type": "int32", "size": 4}]
        with pytest.raises(ValueError, match="struct field type"):
            kb.define_struct("Bad", bad_fields)
        kb.close()

    def test_overlapping_fields_raises_valueerror(self):
        kb = _make_kb()
        bad_fields = [
            {"name": "a", "offset": 0, "type": "u16", "size": 2},
            {"name": "b", "offset": 1, "type": "u8", "size": 1},
        ]
        with pytest.raises(ValueError, match="overlap"):
            kb.define_struct("Bad", bad_fields)
        kb.close()


# ---------------------------------------------------------------------------
# define_enum
# ---------------------------------------------------------------------------

_DIRECTION_VALUES = {"UP": 0, "DOWN": 1, "LEFT": 2, "RIGHT": 3}


class TestDefineEnum:
    def test_create_returns_id(self):
        kb = _make_kb()
        eid = kb.define_enum("Direction", _DIRECTION_VALUES)
        assert isinstance(eid, int)
        assert eid > 0
        kb.close()

    def test_values_stored_correctly(self):
        kb = _make_kb()
        kb.define_enum("Direction", _DIRECTION_VALUES)
        cur = kb._conn.execute(
            "SELECT name, value FROM enum_values "
            "WHERE enum_id = (SELECT id FROM enums WHERE name = 'Direction') "
            "ORDER BY value"
        )
        rows = cur.fetchall()
        assert len(rows) == 4
        assert ("UP", 0) in rows
        assert ("DOWN", 1) in rows
        assert ("LEFT", 2) in rows
        assert ("RIGHT", 3) in rows
        kb.close()

    def test_with_comment(self):
        kb = _make_kb()
        kb.define_enum("Direction", _DIRECTION_VALUES, comment="D-pad")
        cur = kb._conn.execute(
            "SELECT comment FROM enums WHERE name = ?", ("Direction",)
        )
        assert cur.fetchone()[0] == "D-pad"
        kb.close()

    def test_duplicate_name_raises_valueerror(self):
        kb = _make_kb()
        kb.define_enum("Direction", _DIRECTION_VALUES)
        with pytest.raises(ValueError, match="already exists"):
            kb.define_enum("Direction", _DIRECTION_VALUES)
        kb.close()

    def test_empty_name_raises_valueerror(self):
        kb = _make_kb()
        with pytest.raises(ValueError, match="name"):
            kb.define_enum("", _DIRECTION_VALUES)
        kb.close()

    def test_empty_values_raises_valueerror(self):
        kb = _make_kb()
        with pytest.raises(ValueError, match="empty"):
            kb.define_enum("Empty", {})
        kb.close()

    def test_duplicate_numeric_values_raises_valueerror(self):
        kb = _make_kb()
        with pytest.raises(ValueError, match="(?i)duplicate"):
            kb.define_enum("Bad", {"A": 0, "B": 0})
        kb.close()


# ---------------------------------------------------------------------------
# get_struct
# ---------------------------------------------------------------------------


class TestGetStruct:
    def test_returns_struct_with_fields(self):
        kb = _make_kb()
        kb.define_struct("Sprite", _SPRITE_FIELDS, comment="OAM")
        result = kb.get_struct("Sprite")
        assert result is not None
        assert result["name"] == "Sprite"
        assert result["total_size"] == 4
        assert result["comment"] == "OAM"
        assert len(result["fields"]) == 4
        assert result["fields"][0]["name"] == "y"
        assert result["fields"][0]["offset"] == 0
        kb.close()

    def test_returns_none_for_unknown(self):
        kb = _make_kb()
        assert kb.get_struct("Nonexistent") is None
        kb.close()


# ---------------------------------------------------------------------------
# get_enum
# ---------------------------------------------------------------------------


class TestGetEnum:
    def test_returns_enum_with_values(self):
        kb = _make_kb()
        kb.define_enum("Direction", _DIRECTION_VALUES, comment="D-pad")
        result = kb.get_enum("Direction")
        assert result is not None
        assert result["name"] == "Direction"
        assert result["comment"] == "D-pad"
        assert result["values"] == _DIRECTION_VALUES
        kb.close()

    def test_returns_none_for_unknown(self):
        kb = _make_kb()
        assert kb.get_enum("Nonexistent") is None
        kb.close()


# ---------------------------------------------------------------------------
# import_symbols
# ---------------------------------------------------------------------------


class TestImportSymbols:
    def test_code_symbol_creates_annotation_and_function(self):
        kb = _make_kb()
        symbols = [ParsedSymbol(0x0100, 0, "main", "code")]
        result = kb.import_symbols(symbols)
        assert result["imported"] == 1
        assert kb.get_label(0x0100, bank=0) == "main"
        info = kb.get_function_info("main")
        assert info is not None
        assert info["function"]["name"] == "main"
        kb.close()

    def test_data_symbol_creates_annotation_only(self):
        kb = _make_kb()
        symbols = [ParsedSymbol(0xC000, None, "wram_var", "data")]
        result = kb.import_symbols(symbols)
        assert result["imported"] == 1
        assert kb.get_label(0xC000) == "wram_var"
        # No function should be created for data symbols
        info = kb.get_function_info("wram_var")
        assert info is None
        kb.close()

    def test_skips_duplicate_label(self):
        kb = _make_kb()
        kb.annotate(0x0100, bank=0, label="existing")
        symbols = [ParsedSymbol(0x0100, 0, "new_label", "code")]
        result = kb.import_symbols(symbols)
        assert result["skipped"] == 1
        assert result["imported"] == 0
        # Original label preserved
        assert kb.get_label(0x0100, bank=0) == "existing"
        kb.close()

    def test_returns_imported_and_skipped_counts(self):
        kb = _make_kb()
        kb.annotate(0x0100, bank=0, label="existing")
        symbols = [
            ParsedSymbol(0x0100, 0, "dup", "code"),
            ParsedSymbol(0x0150, 0, "new_func", "code"),
            ParsedSymbol(0xC000, None, "wram_var", "data"),
        ]
        result = kb.import_symbols(symbols)
        assert result["imported"] == 2
        assert result["skipped"] == 1
        kb.close()

    def test_empty_list_returns_zeros(self):
        kb = _make_kb()
        result = kb.import_symbols([])
        assert result == {"imported": 0, "skipped": 0}
        kb.close()

    def test_multiple_symbols_mixed(self):
        kb = _make_kb()
        symbols = [
            ParsedSymbol(0x0100, 0, "entry", "code"),
            ParsedSymbol(0x0150, 0, "init", "code"),
            ParsedSymbol(0xC000, None, "counter", "data"),
            ParsedSymbol(0xFF80, None, "hram_tmp", "data"),
        ]
        result = kb.import_symbols(symbols)
        assert result["imported"] == 4
        assert result["skipped"] == 0
        assert kb.get_label(0x0100, bank=0) == "entry"
        assert kb.get_label(0xC000) == "counter"
        kb.close()

    def test_bank_preserved(self):
        kb = _make_kb()
        symbols = [
            ParsedSymbol(0x4000, 1, "bank1_start", "code"),
            ParsedSymbol(0x4000, 2, "bank2_start", "code"),
        ]
        result = kb.import_symbols(symbols)
        assert result["imported"] == 2
        assert kb.get_label(0x4000, bank=1) == "bank1_start"
        assert kb.get_label(0x4000, bank=2) == "bank2_start"
        kb.close()
