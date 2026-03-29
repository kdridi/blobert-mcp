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
