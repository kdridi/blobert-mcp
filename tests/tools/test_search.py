"""Integration tests for find_byte_pattern and find_strings MCP tools."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from blobert_mcp.tools.search import register_search_tools

# ---------------------------------------------------------------------------
# Fake infrastructure
# ---------------------------------------------------------------------------


class FakeMemory:
    """Flat 64KB memory backed by a bytearray."""

    def __init__(self, data: bytes) -> None:
        self._data = bytearray(0x10000)
        self._data[: len(data)] = data

    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, slice):
            return list(self._data[key])
        return self._data[key]


class FakePyBoy:
    def __init__(self, rom_bytes: bytes) -> None:
        self.memory = FakeMemory(rom_bytes)


class FakeEmulatorSession:
    def __init__(self, *, rom_bytes: bytes | None = None) -> None:
        if rom_bytes is not None:
            self.pyboy: FakePyBoy | None = FakePyBoy(rom_bytes)
        else:
            self.pyboy = None

    @property
    def rom_loaded(self) -> bool:
        return self.pyboy is not None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mcp(session: FakeEmulatorSession) -> FastMCP:
    mcp = FastMCP("test")
    register_search_tools(mcp, session)
    return mcp


def _get_tool(mcp: FastMCP, name: str):  # noqa: ANN201
    tools = {t.name: t for t in mcp._tool_manager.list_tools()}
    assert name in tools, f"Tool {name!r} not registered"
    return tools[name].fn


# ---------------------------------------------------------------------------
# find_byte_pattern tool tests
# ---------------------------------------------------------------------------


class TestFindBytePatternTool:
    def test_no_rom_returns_error(self):
        session = FakeEmulatorSession()
        mcp = _make_mcp(session)
        result = _get_tool(mcp, "find_byte_pattern")(pattern="CD")
        assert result["error"] == "NO_ROM_LOADED"

    def test_empty_pattern_returns_error(self):
        session = FakeEmulatorSession(rom_bytes=b"\x00" * 16)
        mcp = _make_mcp(session)
        result = _get_tool(mcp, "find_byte_pattern")(pattern="")
        assert result["error"] == "INVALID_PARAMETER"

    def test_invalid_pattern_returns_error(self):
        session = FakeEmulatorSession(rom_bytes=b"\x00" * 16)
        mcp = _make_mcp(session)
        result = _get_tool(mcp, "find_byte_pattern")(pattern="GG")
        assert result["error"] == "INVALID_PARAMETER"

    def test_happy_path(self):
        rom = bytearray(0x100)
        rom[0x10] = 0xCD
        rom[0x11] = 0x00
        rom[0x12] = 0x40
        session = FakeEmulatorSession(rom_bytes=bytes(rom))
        mcp = _make_mcp(session)
        result = _get_tool(mcp, "find_byte_pattern")(pattern="CD 00 40")
        assert "matches" in result
        assert "0x0010" in result["matches"]
        assert result["count"] >= 1

    def test_address_and_length(self):
        rom = bytearray(0x100)
        rom[0x00] = 0xFF
        rom[0x50] = 0xFF
        session = FakeEmulatorSession(rom_bytes=bytes(rom))
        mcp = _make_mcp(session)
        result = _get_tool(mcp, "find_byte_pattern")(
            pattern="FF", address=0x40, length=0x20
        )
        assert "0x0050" in result["matches"]
        assert "0x0000" not in result["matches"]

    def test_address_defaults_to_zero(self):
        rom = bytearray(0x10)
        rom[0] = 0xAA
        session = FakeEmulatorSession(rom_bytes=bytes(rom))
        mcp = _make_mcp(session)
        result = _get_tool(mcp, "find_byte_pattern")(pattern="AA")
        assert "0x0000" in result["matches"]

    def test_response_has_expected_keys(self):
        session = FakeEmulatorSession(rom_bytes=b"\x00" * 16)
        mcp = _make_mcp(session)
        result = _get_tool(mcp, "find_byte_pattern")(pattern="FF")
        assert "pattern" in result
        assert "matches" in result
        assert "count" in result
        assert "truncated" in result

    def test_truncation_flag(self):
        rom = bytes([0xFF] * 0x200)
        session = FakeEmulatorSession(rom_bytes=rom)
        mcp = _make_mcp(session)
        result = _get_tool(mcp, "find_byte_pattern")(pattern="FF")
        assert result["truncated"] is True
        assert result["count"] == 100


# ---------------------------------------------------------------------------
# find_strings tool tests
# ---------------------------------------------------------------------------


class TestFindStringsTool:
    def test_no_rom_returns_error(self):
        session = FakeEmulatorSession()
        mcp = _make_mcp(session)
        result = _get_tool(mcp, "find_strings")(encoding="ascii")
        assert result["error"] == "NO_ROM_LOADED"

    def test_invalid_encoding_returns_error(self):
        session = FakeEmulatorSession(rom_bytes=b"\x00" * 16)
        mcp = _make_mcp(session)
        result = _get_tool(mcp, "find_strings")(encoding="utf-16")
        assert result["error"] == "INVALID_PARAMETER"

    def test_invalid_min_length_returns_error(self):
        session = FakeEmulatorSession(rom_bytes=b"\x00" * 16)
        mcp = _make_mcp(session)
        result = _get_tool(mcp, "find_strings")(min_length=0)
        assert result["error"] == "INVALID_PARAMETER"

    def test_happy_path_ascii(self):
        rom = bytearray(0x100)
        rom[0x10:0x15] = b"HELLO"
        session = FakeEmulatorSession(rom_bytes=bytes(rom))
        mcp = _make_mcp(session)
        result = _get_tool(mcp, "find_strings")(encoding="ascii")
        assert "strings" in result
        texts = [s["text"] for s in result["strings"]]
        assert "HELLO" in texts

    def test_happy_path_gb_custom(self):
        rom = bytearray(0x100)
        rom[0x10:0x14] = bytes([0x80, 0x81, 0x82, 0x83])  # ABCD
        session = FakeEmulatorSession(rom_bytes=bytes(rom))
        mcp = _make_mcp(session)
        result = _get_tool(mcp, "find_strings")(encoding="gb_custom")
        texts = [s["text"] for s in result["strings"]]
        assert "ABCD" in texts

    def test_default_encoding_is_ascii(self):
        rom = bytearray(0x100)
        rom[0x10:0x15] = b"HELLO"
        session = FakeEmulatorSession(rom_bytes=bytes(rom))
        mcp = _make_mcp(session)
        result = _get_tool(mcp, "find_strings")()
        assert result["encoding"] == "ascii"
        texts = [s["text"] for s in result["strings"]]
        assert "HELLO" in texts

    def test_default_min_length_is_4(self):
        session = FakeEmulatorSession(rom_bytes=b"\x00" * 16)
        mcp = _make_mcp(session)
        result = _get_tool(mcp, "find_strings")()
        assert result["min_length"] == 4

    def test_response_has_expected_keys(self):
        session = FakeEmulatorSession(rom_bytes=b"\x00" * 16)
        mcp = _make_mcp(session)
        result = _get_tool(mcp, "find_strings")()
        assert "encoding" in result
        assert "min_length" in result
        assert "strings" in result
        assert "count" in result
        assert "truncated" in result

    def test_string_entry_format(self):
        rom = bytearray(0x100)
        rom[0x10:0x15] = b"HELLO"
        session = FakeEmulatorSession(rom_bytes=bytes(rom))
        mcp = _make_mcp(session)
        result = _get_tool(mcp, "find_strings")(encoding="ascii")
        entry = result["strings"][0]
        assert "address" in entry
        assert "text" in entry
        assert entry["address"].startswith("0x")

    def test_truncation_flag(self):
        # Build data with many strings
        segment = bytearray(b"\x00ABCDE")
        rom = bytearray(segment * 250)
        session = FakeEmulatorSession(rom_bytes=bytes(rom))
        mcp = _make_mcp(session)
        result = _get_tool(mcp, "find_strings")(encoding="ascii", min_length=4)
        assert result["truncated"] is True
        assert result["count"] == 200
