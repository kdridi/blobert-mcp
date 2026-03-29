"""Integration tests for gb_write_memory tool."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from blobert_mcp.tools.memory import register_memory_tools

# ---------------------------------------------------------------------------
# Fake infrastructure
# ---------------------------------------------------------------------------


class FakeMemory:
    def __init__(self) -> None:
        self._data = bytearray(0x10000)

    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, slice):
            return list(self._data[key])
        return self._data[key]

    def __setitem__(self, key: Any, value: Any) -> None:
        self._data[key] = value

    def set_byte(self, addr: int, value: int) -> None:
        self._data[addr] = value


class FakePyBoy:
    def __init__(self) -> None:
        self.memory = FakeMemory()


class FakeEmulatorSession:
    def __init__(self, *, with_rom: bool = False) -> None:
        self.pyboy: FakePyBoy | None = FakePyBoy() if with_rom else None

    @property
    def rom_loaded(self) -> bool:
        return self.pyboy is not None


def _make_mcp(session: FakeEmulatorSession) -> FastMCP:
    mcp = FastMCP("test")
    register_memory_tools(mcp, session)
    return mcp


def _get_tool(mcp: FastMCP, name: str):
    tools = {t.name: t for t in mcp._tool_manager.list_tools()}
    assert name in tools, f"Tool '{name}' not registered. Available: {list(tools)}"
    return tools[name].fn


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGbWriteMemory:
    def test_no_rom(self) -> None:
        session = FakeEmulatorSession(with_rom=False)
        mcp = _make_mcp(session)
        result = _get_tool(mcp, "gb_write_memory")(address=0xC000, data="42")
        assert result["error"] == "NO_ROM_LOADED"

    def test_write_single_byte_to_ram(self) -> None:
        session = FakeEmulatorSession(with_rom=True)
        mcp = _make_mcp(session)
        result = _get_tool(mcp, "gb_write_memory")(address=0xC000, data="42")
        assert "error" not in result
        assert session.pyboy.memory[0xC000] == 0x42

    def test_write_multiple_bytes(self) -> None:
        session = FakeEmulatorSession(with_rom=True)
        mcp = _make_mcp(session)
        result = _get_tool(mcp, "gb_write_memory")(address=0xC000, data="FF0042")
        assert "error" not in result
        assert session.pyboy.memory[0xC000] == 0xFF
        assert session.pyboy.memory[0xC001] == 0x00
        assert session.pyboy.memory[0xC002] == 0x42

    def test_returns_confirmation(self) -> None:
        session = FakeEmulatorSession(with_rom=True)
        mcp = _make_mcp(session)
        result = _get_tool(mcp, "gb_write_memory")(address=0xC000, data="AABB")
        assert result["status"] == "ok"
        assert result["address"] == "0xC000"
        assert result["bytes_written"] == 2

    def test_invalid_address_rom_region(self) -> None:
        session = FakeEmulatorSession(with_rom=True)
        mcp = _make_mcp(session)
        result = _get_tool(mcp, "gb_write_memory")(address=0x0000, data="42")
        assert result["error"] == "INVALID_ADDRESS"

    def test_invalid_address_io_region(self) -> None:
        session = FakeEmulatorSession(with_rom=True)
        mcp = _make_mcp(session)
        result = _get_tool(mcp, "gb_write_memory")(address=0xFF00, data="42")
        assert result["error"] == "INVALID_ADDRESS"

    def test_invalid_hex_odd_length(self) -> None:
        session = FakeEmulatorSession(with_rom=True)
        mcp = _make_mcp(session)
        result = _get_tool(mcp, "gb_write_memory")(address=0xC000, data="FFF")
        assert result["error"] == "INVALID_DATA"

    def test_invalid_hex_bad_chars(self) -> None:
        session = FakeEmulatorSession(with_rom=True)
        mcp = _make_mcp(session)
        result = _get_tool(mcp, "gb_write_memory")(address=0xC000, data="ZZZZ")
        assert result["error"] == "INVALID_DATA"

    def test_empty_hex_string(self) -> None:
        session = FakeEmulatorSession(with_rom=True)
        mcp = _make_mcp(session)
        result = _get_tool(mcp, "gb_write_memory")(address=0xC000, data="")
        assert result["error"] == "INVALID_DATA"

    def test_write_to_hram(self) -> None:
        session = FakeEmulatorSession(with_rom=True)
        mcp = _make_mcp(session)
        result = _get_tool(mcp, "gb_write_memory")(address=0xFF80, data="AB")
        assert "error" not in result
        assert session.pyboy.memory[0xFF80] == 0xAB

    def test_write_to_vram(self) -> None:
        session = FakeEmulatorSession(with_rom=True)
        mcp = _make_mcp(session)
        result = _get_tool(mcp, "gb_write_memory")(address=0x8000, data="AB")
        assert "error" not in result
        assert session.pyboy.memory[0x8000] == 0xAB

    def test_write_to_oam(self) -> None:
        session = FakeEmulatorSession(with_rom=True)
        mcp = _make_mcp(session)
        result = _get_tool(mcp, "gb_write_memory")(address=0xFE00, data="AB")
        assert "error" not in result
        assert session.pyboy.memory[0xFE00] == 0xAB

    def test_data_spanning_beyond_writable_range(self) -> None:
        session = FakeEmulatorSession(with_rom=True)
        mcp = _make_mcp(session)
        result = _get_tool(mcp, "gb_write_memory")(address=0xDFF0, data="00" * 32)
        assert result["error"] == "INVALID_ADDRESS"
