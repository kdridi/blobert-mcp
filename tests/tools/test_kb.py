"""Integration tests for KB MCP tools."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from blobert_mcp.kb.database import KnowledgeBase
from blobert_mcp.tools.kb import register_kb_tools

# ---------------------------------------------------------------------------
# Fake infrastructure
# ---------------------------------------------------------------------------


class FakeEmulatorSession:
    def __init__(self, *, with_kb: bool = False) -> None:
        if with_kb:
            self.pyboy = object()  # truthy
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
