"""Integration tests for tools/io_registers.py — I/O register tool handlers."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from blobert_mcp.tools.io_registers import register_io_register_tools

# ---------------------------------------------------------------------------
# Fake infrastructure
# ---------------------------------------------------------------------------


class FakeMemory:
    """Provides pyboy.memory[...] interface backed by a 64KB address space."""

    def __init__(self) -> None:
        self._data = bytearray(0x10000)

    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, slice):
            return list(self._data[key])
        return self._data[key]

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mcp(session: FakeEmulatorSession) -> FastMCP:
    mcp = FastMCP("test")
    register_io_register_tools(mcp, session)
    return mcp


def _get_tool(mcp: FastMCP, name: str):
    tools = {t.name: t for t in mcp._tool_manager.list_tools()}
    assert name in tools, f"Tool '{name}' not registered. Available: {list(tools)}"
    return tools[name].fn


# ---------------------------------------------------------------------------
# gb_get_lcd_status
# ---------------------------------------------------------------------------


class TestGbGetLcdStatus:
    def test_no_rom(self) -> None:
        session = FakeEmulatorSession(with_rom=False)
        mcp = _make_mcp(session)
        result = _get_tool(mcp, "gb_get_lcd_status")()
        assert result["error"] == "NO_ROM_LOADED"

    def test_keys(self) -> None:
        session = FakeEmulatorSession(with_rom=True)
        mcp = _make_mcp(session)
        result = _get_tool(mcp, "gb_get_lcd_status")()
        expected = (
            "lcdc_raw",
            "stat_raw",
            "lcdc",
            "stat",
            "scy",
            "scx",
            "ly",
            "lyc",
            "wy",
            "wx",
        )
        for key in expected:
            assert key in result, f"Missing key: {key}"

    def test_reads_correct_addresses(self) -> None:
        session = FakeEmulatorSession(with_rom=True)
        mem = session.pyboy.memory
        mem.set_byte(0xFF40, 0x91)  # LCDC
        mem.set_byte(0xFF41, 0x45)  # STAT
        mem.set_byte(0xFF42, 10)  # SCY
        mem.set_byte(0xFF43, 20)  # SCX
        mem.set_byte(0xFF44, 144)  # LY
        mem.set_byte(0xFF45, 153)  # LYC
        mem.set_byte(0xFF4A, 0)  # WY
        mem.set_byte(0xFF4B, 7)  # WX
        mcp = _make_mcp(session)
        result = _get_tool(mcp, "gb_get_lcd_status")()
        assert result["lcdc_raw"] == 0x91
        assert result["stat_raw"] == 0x45
        assert result["scy"] == 10
        assert result["scx"] == 20
        assert result["ly"] == 144
        assert result["lyc"] == 153
        assert result["wy"] == 0
        assert result["wx"] == 7

    def test_lcdc_parsing_delegated(self) -> None:
        session = FakeEmulatorSession(with_rom=True)
        session.pyboy.memory.set_byte(0xFF40, 0x80)
        mcp = _make_mcp(session)
        result = _get_tool(mcp, "gb_get_lcd_status")()
        assert result["lcdc"]["lcd_enable"] is True

    def test_stat_mode_field(self) -> None:
        session = FakeEmulatorSession(with_rom=True)
        session.pyboy.memory.set_byte(0xFF41, 0x03)
        mcp = _make_mcp(session)
        result = _get_tool(mcp, "gb_get_lcd_status")()
        assert result["stat"]["mode"] == 3


# ---------------------------------------------------------------------------
# gb_get_timer_state
# ---------------------------------------------------------------------------


class TestGbGetTimerState:
    def test_no_rom(self) -> None:
        session = FakeEmulatorSession(with_rom=False)
        mcp = _make_mcp(session)
        result = _get_tool(mcp, "gb_get_timer_state")()
        assert result["error"] == "NO_ROM_LOADED"

    def test_keys(self) -> None:
        session = FakeEmulatorSession(with_rom=True)
        mcp = _make_mcp(session)
        result = _get_tool(mcp, "gb_get_timer_state")()
        for key in ("div", "tima", "tma", "tac_raw", "tac"):
            assert key in result, f"Missing key: {key}"

    def test_reads_correct_addresses(self) -> None:
        session = FakeEmulatorSession(with_rom=True)
        mem = session.pyboy.memory
        mem.set_byte(0xFF04, 0xAB)  # DIV
        mem.set_byte(0xFF05, 0x10)  # TIMA
        mem.set_byte(0xFF06, 0xFF)  # TMA
        mem.set_byte(0xFF07, 0x05)  # TAC
        mcp = _make_mcp(session)
        result = _get_tool(mcp, "gb_get_timer_state")()
        assert result["div"] == 0xAB
        assert result["tima"] == 0x10
        assert result["tma"] == 0xFF
        assert result["tac_raw"] == 0x05

    def test_tac_parsed(self) -> None:
        session = FakeEmulatorSession(with_rom=True)
        session.pyboy.memory.set_byte(0xFF07, 0x05)
        mcp = _make_mcp(session)
        result = _get_tool(mcp, "gb_get_timer_state")()
        assert result["tac"]["enabled"] is True
        assert result["tac"]["frequency_hz"] == 262144


# ---------------------------------------------------------------------------
# gb_get_audio_state
# ---------------------------------------------------------------------------


class TestGbGetAudioState:
    def test_no_rom(self) -> None:
        session = FakeEmulatorSession(with_rom=False)
        mcp = _make_mcp(session)
        result = _get_tool(mcp, "gb_get_audio_state")()
        assert result["error"] == "NO_ROM_LOADED"

    def test_all_channels_keys(self) -> None:
        session = FakeEmulatorSession(with_rom=True)
        mcp = _make_mcp(session)
        result = _get_tool(mcp, "gb_get_audio_state")()
        for key in ("channel1", "channel2", "channel3", "channel4", "master"):
            assert key in result, f"Missing key: {key}"

    def test_single_channel(self) -> None:
        session = FakeEmulatorSession(with_rom=True)
        mcp = _make_mcp(session)
        result = _get_tool(mcp, "gb_get_audio_state")(channel=1)
        assert "channel1" in result
        assert "master" in result
        assert "channel2" not in result
        assert "channel3" not in result
        assert "channel4" not in result

    def test_invalid_channel(self) -> None:
        session = FakeEmulatorSession(with_rom=True)
        mcp = _make_mcp(session)
        result = _get_tool(mcp, "gb_get_audio_state")(channel=5)
        assert result["error"] == "INVALID_PARAMETER"

    def test_invalid_channel_zero(self) -> None:
        session = FakeEmulatorSession(with_rom=True)
        mcp = _make_mcp(session)
        result = _get_tool(mcp, "gb_get_audio_state")(channel=0)
        assert result["error"] == "INVALID_PARAMETER"

    def test_channel_3_includes_wave_ram(self) -> None:
        session = FakeEmulatorSession(with_rom=True)
        # Plant wave RAM data
        for i in range(16):
            session.pyboy.memory.set_byte(0xFF30 + i, 0xAA)
        mcp = _make_mcp(session)
        result = _get_tool(mcp, "gb_get_audio_state")(channel=3)
        assert "wave_ram" in result["channel3"]
        assert result["channel3"]["wave_ram"] == "aa" * 16

    def test_reads_correct_nr_addresses(self) -> None:
        session = FakeEmulatorSession(with_rom=True)
        mem = session.pyboy.memory
        # Set NR52 audio enable
        mem.set_byte(0xFF26, 0x80)
        # Set NR10 with a recognizable value
        mem.set_byte(0xFF10, 0x12)
        mcp = _make_mcp(session)
        result = _get_tool(mcp, "gb_get_audio_state")()
        assert result["master"]["audio_enable"] is True
        assert result["channel1"]["sweep_pace"] == 1


# ---------------------------------------------------------------------------
# gb_get_serial_state
# ---------------------------------------------------------------------------


class TestGbGetSerialState:
    def test_no_rom(self) -> None:
        session = FakeEmulatorSession(with_rom=False)
        mcp = _make_mcp(session)
        result = _get_tool(mcp, "gb_get_serial_state")()
        assert result["error"] == "NO_ROM_LOADED"

    def test_keys(self) -> None:
        session = FakeEmulatorSession(with_rom=True)
        mcp = _make_mcp(session)
        result = _get_tool(mcp, "gb_get_serial_state")()
        for key in ("sb", "sc_raw", "sc"):
            assert key in result, f"Missing key: {key}"

    def test_reads_correct_addresses(self) -> None:
        session = FakeEmulatorSession(with_rom=True)
        mem = session.pyboy.memory
        mem.set_byte(0xFF01, 0x42)  # SB
        mem.set_byte(0xFF02, 0x81)  # SC
        mcp = _make_mcp(session)
        result = _get_tool(mcp, "gb_get_serial_state")()
        assert result["sb"] == 0x42
        assert result["sc_raw"] == 0x81

    def test_transfer_in_progress(self) -> None:
        session = FakeEmulatorSession(with_rom=True)
        session.pyboy.memory.set_byte(0xFF02, 0x81)
        mcp = _make_mcp(session)
        result = _get_tool(mcp, "gb_get_serial_state")()
        assert result["sc"]["transfer_in_progress"] is True
        assert result["sc"]["clock_source"] == "internal"
