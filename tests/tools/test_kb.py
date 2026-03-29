"""Integration tests for KB MCP tools."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from blobert_mcp.kb.database import KnowledgeBase
from blobert_mcp.tools.kb import register_kb_tools

# ---------------------------------------------------------------------------
# Fake infrastructure
# ---------------------------------------------------------------------------


class FakeMemory:
    def __init__(self, rom_size_byte: int = 0) -> None:
        self._data = bytearray(0x10000)
        self._data[0x0148] = rom_size_byte

    def __getitem__(self, key):
        return self._data[key]


class FakePyBoy:
    def __init__(self, rom_size_byte: int = 0) -> None:
        self.memory = FakeMemory(rom_size_byte)


class FakeEmulatorSession:
    def __init__(self, *, with_kb: bool = False, rom_size_byte: int = 0) -> None:
        if with_kb:
            self.pyboy: FakePyBoy | None = FakePyBoy(rom_size_byte)
            self.kb: KnowledgeBase | None = KnowledgeBase(":memory:")
        else:
            self.pyboy = None
            self.kb = None

    @property
    def rom_loaded(self) -> bool:
        return self.pyboy is not None


def _make_mcp(session: FakeEmulatorSession) -> FastMCP:
    mcp = FastMCP("test")
    register_kb_tools(mcp, session)
    return mcp


def _get_tool(mcp: FastMCP, name: str):
    tools = {t.name: t for t in mcp._tool_manager.list_tools()}
    assert name in tools, f"Tool '{name}' not registered. Available: {list(tools)}"
    return tools[name].fn


# ---------------------------------------------------------------------------
# kb_annotate
# ---------------------------------------------------------------------------


class TestKbAnnotate:
    def test_no_rom_returns_error(self):
        session = FakeEmulatorSession()
        tool = _get_tool(_make_mcp(session), "kb_annotate")
        result = tool(address=0x0100)
        assert result["error"] == "NO_ROM_LOADED"

    def test_happy_path_returns_annotation_id(self):
        session = FakeEmulatorSession(with_kb=True)
        tool = _get_tool(_make_mcp(session), "kb_annotate")
        result = tool(address=0x0100, label="entry", type="code")
        assert "error" not in result
        assert "annotation_id" in result
        assert isinstance(result["annotation_id"], int)

    def test_invalid_type_returns_error(self):
        session = FakeEmulatorSession(with_kb=True)
        tool = _get_tool(_make_mcp(session), "kb_annotate")
        result = tool(address=0x0100, type="invalid")
        assert result["error"] == "INVALID_PARAMETER"

    def test_upsert_returns_id(self):
        session = FakeEmulatorSession(with_kb=True)
        tool = _get_tool(_make_mcp(session), "kb_annotate")
        tool(address=0x0100, label="old")
        result = tool(address=0x0100, label="new")
        assert "annotation_id" in result

    def test_with_bank(self):
        session = FakeEmulatorSession(with_kb=True)
        tool = _get_tool(_make_mcp(session), "kb_annotate")
        result = tool(address=0x4000, bank=1, label="bank1")
        assert "annotation_id" in result


# ---------------------------------------------------------------------------
# kb_define_function
# ---------------------------------------------------------------------------


class TestKbDefineFunction:
    def test_no_rom_returns_error(self):
        session = FakeEmulatorSession()
        tool = _get_tool(_make_mcp(session), "kb_define_function")
        result = tool(address=0x0100, name="main")
        assert result["error"] == "NO_ROM_LOADED"

    def test_happy_path_returns_function_id(self):
        session = FakeEmulatorSession(with_kb=True)
        tool = _get_tool(_make_mcp(session), "kb_define_function")
        result = tool(address=0x0150, name="main")
        assert "error" not in result
        assert "function_id" in result

    def test_empty_name_returns_error(self):
        session = FakeEmulatorSession(with_kb=True)
        tool = _get_tool(_make_mcp(session), "kb_define_function")
        result = tool(address=0x0150, name="")
        assert result["error"] == "INVALID_PARAMETER"

    def test_with_params(self):
        session = FakeEmulatorSession(with_kb=True)
        tool = _get_tool(_make_mcp(session), "kb_define_function")
        result = tool(
            address=0x0150,
            name="handler",
            params=["a: u8", "b: u16"],
            description="Handler function",
            returns="void",
        )
        assert "function_id" in result


# ---------------------------------------------------------------------------
# kb_define_variable
# ---------------------------------------------------------------------------


class TestKbDefineVariable:
    def test_no_rom_returns_error(self):
        session = FakeEmulatorSession()
        tool = _get_tool(_make_mcp(session), "kb_define_variable")
        result = tool(address=0xC000, name="x", type="u8")
        assert result["error"] == "NO_ROM_LOADED"

    def test_happy_path_returns_variable_id(self):
        session = FakeEmulatorSession(with_kb=True)
        tool = _get_tool(_make_mcp(session), "kb_define_variable")
        result = tool(address=0xC000, name="player_x", type="u8")
        assert "error" not in result
        assert "variable_id" in result

    def test_invalid_type_returns_error(self):
        session = FakeEmulatorSession(with_kb=True)
        tool = _get_tool(_make_mcp(session), "kb_define_variable")
        result = tool(address=0xC000, name="x", type="int32")
        assert result["error"] == "INVALID_PARAMETER"

    def test_empty_name_returns_error(self):
        session = FakeEmulatorSession(with_kb=True)
        tool = _get_tool(_make_mcp(session), "kb_define_variable")
        result = tool(address=0xC000, name="", type="u8")
        assert result["error"] == "INVALID_PARAMETER"


# ---------------------------------------------------------------------------
# kb_search
# ---------------------------------------------------------------------------


class TestKbSearch:
    def test_no_rom_returns_error(self):
        session = FakeEmulatorSession()
        tool = _get_tool(_make_mcp(session), "kb_search")
        result = tool(query="test")
        assert result["error"] == "NO_ROM_LOADED"

    def test_finds_annotation(self):
        session = FakeEmulatorSession(with_kb=True)
        session.kb.annotate(0x0100, label="vblank_handler")
        tool = _get_tool(_make_mcp(session), "kb_search")
        result = tool(query="vblank")
        assert "error" not in result
        assert len(result["results"]) >= 1

    def test_with_filter(self):
        session = FakeEmulatorSession(with_kb=True)
        session.kb.annotate(0x0100, label="entry", type="code")
        tool = _get_tool(_make_mcp(session), "kb_search")
        result = tool(query="code", filter="type")
        assert len(result["results"]) >= 1

    def test_empty_query(self):
        session = FakeEmulatorSession(with_kb=True)
        tool = _get_tool(_make_mcp(session), "kb_search")
        result = tool(query="")
        assert result["results"] == []

    def test_returns_count(self):
        session = FakeEmulatorSession(with_kb=True)
        session.kb.annotate(0x0100, label="entry")
        session.kb.annotate(0x0200, label="main_entry")
        tool = _get_tool(_make_mcp(session), "kb_search")
        result = tool(query="entry")
        assert result["count"] == len(result["results"])


# ---------------------------------------------------------------------------
# kb_get_function_info
# ---------------------------------------------------------------------------


class TestKbGetFunctionInfo:
    def test_no_rom_returns_error(self):
        session = FakeEmulatorSession()
        tool = _get_tool(_make_mcp(session), "kb_get_function_info")
        result = tool(name_or_address="main")
        assert result["error"] == "NO_ROM_LOADED"

    def test_lookup_by_name(self):
        session = FakeEmulatorSession(with_kb=True)
        session.kb.define_function(0x0150, name="main")
        tool = _get_tool(_make_mcp(session), "kb_get_function_info")
        result = tool(name_or_address="main")
        assert "error" not in result
        assert result["function"]["name"] == "main"

    def test_lookup_by_hex_address(self):
        session = FakeEmulatorSession(with_kb=True)
        session.kb.define_function(0x0150, name="main")
        tool = _get_tool(_make_mcp(session), "kb_get_function_info")
        result = tool(name_or_address="0x0150")
        assert result["function"]["name"] == "main"

    def test_lookup_by_decimal_address(self):
        session = FakeEmulatorSession(with_kb=True)
        session.kb.define_function(0x0150, name="main")
        tool = _get_tool(_make_mcp(session), "kb_get_function_info")
        result = tool(name_or_address="336")
        assert result["function"]["name"] == "main"

    def test_not_found_returns_error(self):
        session = FakeEmulatorSession(with_kb=True)
        tool = _get_tool(_make_mcp(session), "kb_get_function_info")
        result = tool(name_or_address="nonexistent")
        assert result["error"] == "NOT_FOUND"


# ---------------------------------------------------------------------------
# kb_stats
# ---------------------------------------------------------------------------


class TestKbStats:
    def test_no_rom_returns_error(self):
        session = FakeEmulatorSession()
        tool = _get_tool(_make_mcp(session), "kb_stats")
        result = tool()
        assert result["error"] == "NO_ROM_LOADED"

    def test_returns_all_fields(self):
        session = FakeEmulatorSession(with_kb=True)
        tool = _get_tool(_make_mcp(session), "kb_stats")
        result = tool()
        expected_keys = {
            "total_addresses",
            "annotated",
            "functions_named",
            "variables_named",
            "coverage_pct",
        }
        assert set(result.keys()) == expected_keys

    def test_coverage_calculation(self):
        session = FakeEmulatorSession(with_kb=True)  # rom_size_byte=0 → 2 banks
        session.kb.annotate(0x0100, label="a")
        session.kb.annotate(0x0200, label="b")
        tool = _get_tool(_make_mcp(session), "kb_stats")
        result = tool()
        # 2 banks * 0x4000 = 32768 total addresses
        assert result["total_addresses"] == 32768
        assert result["annotated"] == 2
        assert result["coverage_pct"] == 2 / 32768 * 100

    def test_non_rom_excluded(self):
        session = FakeEmulatorSession(with_kb=True)
        session.kb.annotate(0x0100, label="rom")
        session.kb.annotate(0xC000, label="wram")
        tool = _get_tool(_make_mcp(session), "kb_stats")
        result = tool()
        assert result["annotated"] == 1  # only ROM annotation counted

    def test_total_addresses_from_header(self):
        # rom_size_byte=1 → 4 banks → 4 * 0x4000 = 65536
        session = FakeEmulatorSession(with_kb=True, rom_size_byte=1)
        tool = _get_tool(_make_mcp(session), "kb_stats")
        result = tool()
        assert result["total_addresses"] == 65536


# ---------------------------------------------------------------------------
# kb_define_struct
# ---------------------------------------------------------------------------

_SPRITE_FIELDS = [
    {"name": "y", "offset": 0, "type": "u8", "size": 1},
    {"name": "x", "offset": 1, "type": "u8", "size": 1},
    {"name": "tile", "offset": 2, "type": "u8", "size": 1},
    {"name": "flags", "offset": 3, "type": "u8", "size": 1},
]


class TestKbDefineStruct:
    def test_no_rom_returns_error(self):
        session = FakeEmulatorSession()
        tool = _get_tool(_make_mcp(session), "kb_define_struct")
        result = tool(name="Sprite", fields=_SPRITE_FIELDS)
        assert result["error"] == "NO_ROM_LOADED"

    def test_happy_path_returns_struct_id(self):
        session = FakeEmulatorSession(with_kb=True)
        tool = _get_tool(_make_mcp(session), "kb_define_struct")
        result = tool(name="Sprite", fields=_SPRITE_FIELDS)
        assert "error" not in result
        assert "struct_id" in result
        assert isinstance(result["struct_id"], int)

    def test_duplicate_name_returns_error(self):
        session = FakeEmulatorSession(with_kb=True)
        tool = _get_tool(_make_mcp(session), "kb_define_struct")
        tool(name="Sprite", fields=_SPRITE_FIELDS)
        result = tool(name="Sprite", fields=_SPRITE_FIELDS)
        assert result["error"] == "INVALID_PARAMETER"

    def test_invalid_field_type_returns_error(self):
        session = FakeEmulatorSession(with_kb=True)
        tool = _get_tool(_make_mcp(session), "kb_define_struct")
        bad = [{"name": "x", "offset": 0, "type": "int32", "size": 4}]
        result = tool(name="Bad", fields=bad)
        assert result["error"] == "INVALID_PARAMETER"

    def test_overlapping_fields_returns_error(self):
        session = FakeEmulatorSession(with_kb=True)
        tool = _get_tool(_make_mcp(session), "kb_define_struct")
        bad = [
            {"name": "a", "offset": 0, "type": "u16", "size": 2},
            {"name": "b", "offset": 1, "type": "u8", "size": 1},
        ]
        result = tool(name="Bad", fields=bad)
        assert result["error"] == "INVALID_PARAMETER"

    def test_empty_name_returns_error(self):
        session = FakeEmulatorSession(with_kb=True)
        tool = _get_tool(_make_mcp(session), "kb_define_struct")
        result = tool(name="", fields=_SPRITE_FIELDS)
        assert result["error"] == "INVALID_PARAMETER"

    def test_with_comment(self):
        session = FakeEmulatorSession(with_kb=True)
        tool = _get_tool(_make_mcp(session), "kb_define_struct")
        result = tool(name="Sprite", fields=_SPRITE_FIELDS, comment="OAM entry")
        assert "struct_id" in result


# ---------------------------------------------------------------------------
# kb_apply_struct
# ---------------------------------------------------------------------------


class TestKbApplyStruct:
    def test_no_rom_returns_error(self):
        session = FakeEmulatorSession()
        tool = _get_tool(_make_mcp(session), "kb_apply_struct")
        result = tool(struct_name="Sprite", address=0xFE00)
        assert result["error"] == "NO_ROM_LOADED"

    def test_happy_path_single(self):
        session = FakeEmulatorSession(with_kb=True)
        session.kb.define_struct("Sprite", _SPRITE_FIELDS)
        # Write test bytes into fake memory at OAM area
        session.pyboy.memory._data[0xFE00] = 0x10  # y
        session.pyboy.memory._data[0xFE01] = 0x20  # x
        session.pyboy.memory._data[0xFE02] = 0x05  # tile
        session.pyboy.memory._data[0xFE03] = 0x80  # flags
        tool = _get_tool(_make_mcp(session), "kb_apply_struct")
        result = tool(struct_name="Sprite", address=0xFE00)
        assert "error" not in result
        assert result["count"] == 1
        entry = result["entries"][0]
        assert entry["index"] == 0
        fields = {f["name"]: f["value"] for f in entry["fields"]}
        assert fields["y"] == 0x10
        assert fields["x"] == 0x20
        assert fields["tile"] == 0x05
        assert fields["flags"] == 0x80

    def test_happy_path_with_count(self):
        session = FakeEmulatorSession(with_kb=True)
        session.kb.define_struct("Sprite", _SPRITE_FIELDS)
        # Two sprites at consecutive addresses
        for i, b in enumerate([0x10, 0x20, 0x05, 0x80]):
            session.pyboy.memory._data[0xFE00 + i] = b
        for i, b in enumerate([0x30, 0x40, 0x0A, 0x00]):
            session.pyboy.memory._data[0xFE04 + i] = b
        tool = _get_tool(_make_mcp(session), "kb_apply_struct")
        result = tool(struct_name="Sprite", address=0xFE00, count=2)
        assert result["count"] == 2
        assert len(result["entries"]) == 2
        e0_fields = {f["name"]: f["value"] for f in result["entries"][0]["fields"]}
        e1_fields = {f["name"]: f["value"] for f in result["entries"][1]["fields"]}
        assert e0_fields["y"] == 0x10
        assert e1_fields["y"] == 0x30

    def test_unknown_struct_returns_error(self):
        session = FakeEmulatorSession(with_kb=True)
        tool = _get_tool(_make_mcp(session), "kb_apply_struct")
        result = tool(struct_name="Nonexistent", address=0xFE00)
        assert result["error"] == "NOT_FOUND"

    def test_u16_little_endian(self):
        session = FakeEmulatorSession(with_kb=True)
        fields = [{"name": "addr", "offset": 0, "type": "u16", "size": 2}]
        session.kb.define_struct("Ptr", fields)
        session.pyboy.memory._data[0x0100] = 0x34
        session.pyboy.memory._data[0x0101] = 0x12
        tool = _get_tool(_make_mcp(session), "kb_apply_struct")
        result = tool(struct_name="Ptr", address=0x0100)
        decoded = result["entries"][0]["fields"][0]
        assert decoded["value"] == 0x1234

    def test_invalid_address_returns_error(self):
        session = FakeEmulatorSession(with_kb=True)
        tool = _get_tool(_make_mcp(session), "kb_apply_struct")
        result = tool(struct_name="Sprite", address=0x10000)
        assert result["error"] == "INVALID_PARAMETER"

    def test_count_zero_returns_error(self):
        session = FakeEmulatorSession(with_kb=True)
        session.kb.define_struct("Sprite", _SPRITE_FIELDS)
        tool = _get_tool(_make_mcp(session), "kb_apply_struct")
        result = tool(struct_name="Sprite", address=0xFE00, count=0)
        assert result["error"] == "INVALID_PARAMETER"

    def test_count_negative_returns_error(self):
        session = FakeEmulatorSession(with_kb=True)
        session.kb.define_struct("Sprite", _SPRITE_FIELDS)
        tool = _get_tool(_make_mcp(session), "kb_apply_struct")
        result = tool(struct_name="Sprite", address=0xFE00, count=-1)
        assert result["error"] == "INVALID_PARAMETER"


# ---------------------------------------------------------------------------
# kb_define_enum
# ---------------------------------------------------------------------------


class TestKbDefineEnum:
    def test_no_rom_returns_error(self):
        session = FakeEmulatorSession()
        tool = _get_tool(_make_mcp(session), "kb_define_enum")
        result = tool(name="Direction", values={"UP": 0})
        assert result["error"] == "NO_ROM_LOADED"

    def test_happy_path_returns_enum_id(self):
        session = FakeEmulatorSession(with_kb=True)
        tool = _get_tool(_make_mcp(session), "kb_define_enum")
        values = {"UP": 0, "DOWN": 1, "LEFT": 2, "RIGHT": 3}
        result = tool(name="Direction", values=values)
        assert "error" not in result
        assert "enum_id" in result
        assert isinstance(result["enum_id"], int)

    def test_duplicate_name_returns_error(self):
        session = FakeEmulatorSession(with_kb=True)
        tool = _get_tool(_make_mcp(session), "kb_define_enum")
        tool(name="Direction", values={"UP": 0})
        result = tool(name="Direction", values={"DOWN": 1})
        assert result["error"] == "INVALID_PARAMETER"

    def test_empty_values_returns_error(self):
        session = FakeEmulatorSession(with_kb=True)
        tool = _get_tool(_make_mcp(session), "kb_define_enum")
        result = tool(name="Empty", values={})
        assert result["error"] == "INVALID_PARAMETER"

    def test_duplicate_numeric_values_returns_error(self):
        session = FakeEmulatorSession(with_kb=True)
        tool = _get_tool(_make_mcp(session), "kb_define_enum")
        result = tool(name="Bad", values={"A": 0, "B": 0})
        assert result["error"] == "INVALID_PARAMETER"

    def test_empty_name_returns_error(self):
        session = FakeEmulatorSession(with_kb=True)
        tool = _get_tool(_make_mcp(session), "kb_define_enum")
        result = tool(name="", values={"UP": 0})
        assert result["error"] == "INVALID_PARAMETER"

    def test_with_comment(self):
        session = FakeEmulatorSession(with_kb=True)
        tool = _get_tool(_make_mcp(session), "kb_define_enum")
        result = tool(name="Direction", values={"UP": 0}, comment="D-pad")
        assert "enum_id" in result


# ---------------------------------------------------------------------------
# kb_import_symbols
# ---------------------------------------------------------------------------


class TestKbImportSymbols:
    def test_no_rom_returns_error(self):
        session = FakeEmulatorSession()
        tool = _get_tool(_make_mcp(session), "kb_import_symbols")
        result = tool(file_path="/nonexistent.sym")
        assert result["error"] == "NO_ROM_LOADED"

    def test_file_not_found_returns_error(self, tmp_path):
        session = FakeEmulatorSession(with_kb=True)
        tool = _get_tool(_make_mcp(session), "kb_import_symbols")
        result = tool(file_path=str(tmp_path / "missing.sym"))
        assert result["error"] == "FILE_NOT_FOUND"

    def test_invalid_format_returns_error(self, tmp_path):
        sym_file = tmp_path / "test.sym"
        sym_file.write_text("00:0100 main\n")
        session = FakeEmulatorSession(with_kb=True)
        tool = _get_tool(_make_mcp(session), "kb_import_symbols")
        result = tool(file_path=str(sym_file), format="invalid")
        assert result["error"] == "INVALID_PARAMETER"

    def test_happy_path_sym_format(self, tmp_path):
        sym_file = tmp_path / "test.sym"
        sym_file.write_text("00:0100 main\n00:0150 init\n")
        session = FakeEmulatorSession(with_kb=True)
        tool = _get_tool(_make_mcp(session), "kb_import_symbols")
        result = tool(file_path=str(sym_file), format="sym")
        assert result["imported"] == 2
        assert result["skipped"] == 0
        assert result["errors"] == 0

    def test_happy_path_auto_format(self, tmp_path):
        sym_file = tmp_path / "test.sym"
        sym_file.write_text("00:0100 main\n00:0150 init\n")
        session = FakeEmulatorSession(with_kb=True)
        tool = _get_tool(_make_mcp(session), "kb_import_symbols")
        result = tool(file_path=str(sym_file))
        assert result["imported"] == 2

    def test_pokered_format(self, tmp_path):
        sym_file = tmp_path / "test.sym"
        sym_file.write_text("00:0100 VBlank.handler\n00:0150 Timer.tick\n")
        session = FakeEmulatorSession(with_kb=True)
        tool = _get_tool(_make_mcp(session), "kb_import_symbols")
        result = tool(file_path=str(sym_file), format="pokered")
        assert result["imported"] == 2

    def test_returns_imported_skipped_errors(self, tmp_path):
        sym_file = tmp_path / "test.sym"
        sym_file.write_text("00:0100 main\nbad line\n00:0150 init\n")
        session = FakeEmulatorSession(with_kb=True)
        tool = _get_tool(_make_mcp(session), "kb_import_symbols")
        result = tool(file_path=str(sym_file), format="sym")
        assert result["imported"] == 2
        assert result["skipped"] == 0
        assert result["errors"] == 1

    def test_duplicates_skipped(self, tmp_path):
        sym_file = tmp_path / "test.sym"
        sym_file.write_text("00:0100 main\n00:0150 init\n")
        session = FakeEmulatorSession(with_kb=True)
        # Pre-populate an annotation
        session.kb.annotate(0x0100, bank=0, label="existing")
        tool = _get_tool(_make_mcp(session), "kb_import_symbols")
        result = tool(file_path=str(sym_file), format="sym")
        assert result["imported"] == 1
        assert result["skipped"] == 1
