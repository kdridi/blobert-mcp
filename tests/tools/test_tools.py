"""Integration tests for tools/session.py, tools/static.py, and tools/memory.py.

Uses FakeEmulatorSession (no PyBoy) for error-path tests and a
synthetic minimal ROM fixture for happy-path tests.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from mcp.server.fastmcp import FastMCP

from blobert_mcp.tools.memory import register_memory_tools
from blobert_mcp.tools.session import register_session_tools
from blobert_mcp.tools.static import register_static_tools

# ---------------------------------------------------------------------------
# Minimal synthetic ROM builder
# ---------------------------------------------------------------------------


def _make_rom(title: bytes = b"TESTGAME") -> bytes:
    """Build a minimal valid Game Boy ROM (0x8000 bytes).

    Places a valid header at 0x0100-0x014F and NOP instructions elsewhere.
    """
    rom = bytearray(0x8000)
    # Entry point NOP + JP (3 bytes) at 0x0100
    rom[0x0100] = 0x00  # NOP
    rom[0x0101] = 0xC3  # JP
    rom[0x0102] = 0x50
    rom[0x0103] = 0x01
    # Nintendo logo (48 bytes at 0x0104, filled with zeros is fine for our tests)
    # Title at 0x0134
    for i, b in enumerate(title[:16]):
        rom[0x0134 + i] = b
    # CGB flag at 0x0143
    rom[0x0143] = 0x00
    # SGB flag at 0x0146
    rom[0x0146] = 0x00
    # Cartridge type at 0x0147 (ROM ONLY)
    rom[0x0147] = 0x00
    # ROM size at 0x0148 (32KB = 0x00)
    rom[0x0148] = 0x00
    # RAM size at 0x0149
    rom[0x0149] = 0x00
    # Old licensee at 0x014B
    rom[0x014B] = 0x33
    # Header checksum at 0x014D
    checksum = 0
    for addr in range(0x0134, 0x014D):
        checksum = (checksum - rom[addr] - 1) & 0xFF
    rom[0x014D] = checksum
    # Global checksum at 0x014E-0x014F (not validated by hardware, set to 0)
    rom[0x014E] = 0x00
    rom[0x014F] = 0x00
    return bytes(rom)


# ---------------------------------------------------------------------------
# Fake infrastructure
# ---------------------------------------------------------------------------


class FakeRegisterFile:
    PC = 0x0100


class FakeMemory:
    """Provides pyboy.memory[...] interface backed by a full 64KB address space."""

    def __init__(self, data: bytes) -> None:
        self._data = bytearray(0x10000)
        self._data[: len(data)] = data

    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, slice):
            return list(self._data[key])
        if isinstance(key, tuple):
            # banked access: memory[bank, address] or memory[bank, slice]
            _, addr = key
            if isinstance(addr, slice):
                return list(self._data[addr])
            return self._data[addr]
        return self._data[key]


class FakePyBoy:
    frame_count = 42
    register_file = FakeRegisterFile()

    def __init__(self, rom_bytes: bytes) -> None:
        self.memory = FakeMemory(rom_bytes)

    def stop(self) -> None:
        pass


class FakeEmulatorSession:
    """In-memory mock of EmulatorSession (no real PyBoy)."""

    def __init__(
        self, *, rom_bytes: bytes | None = None, rom_path: str | None = None
    ) -> None:
        if rom_bytes is not None:
            self.pyboy: FakePyBoy | None = FakePyBoy(rom_bytes)
            self.rom_path: str | None = rom_path or "/fake/test.gb"
        else:
            self.pyboy = None
            self.rom_path = None
        self.save_states: dict[str, Any] = {}
        self.breakpoints: dict[str, Any] = {}
        self._rom_bytes = rom_bytes

    @property
    def rom_loaded(self) -> bool:
        return self.pyboy is not None

    def load_rom(self, path: str, *, headless: bool = True) -> None:
        p = Path(path)
        if not p.is_file():
            raise FileNotFoundError(f"ROM not found: {path}")
        rom_bytes = p.read_bytes()
        self.pyboy = FakePyBoy(rom_bytes)
        self.rom_path = str(p)
        self._rom_bytes = rom_bytes

    def shutdown(self) -> None:
        self.pyboy = None
        self.rom_path = None
        self._rom_bytes = None


# ---------------------------------------------------------------------------
# Helpers to build registered tools
# ---------------------------------------------------------------------------


def _make_mcp_with_session(session: FakeEmulatorSession) -> FastMCP:
    mcp = FastMCP("test")
    register_session_tools(mcp, session)
    register_static_tools(mcp, session)
    register_memory_tools(mcp, session)
    return mcp


def _get_tool(mcp: FastMCP, name: str):
    """Return the callable tool function by name."""
    tools = {t.name: t for t in mcp._tool_manager.list_tools()}
    assert name in tools, f"Tool '{name}' not registered. Available: {list(tools)}"
    return tools[name].fn


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def rom_file(tmp_path: Path) -> Path:
    """Write a synthetic minimal ROM to a temp file and return its path."""
    rom_bytes = _make_rom(title=b"TESTGAME")
    p = tmp_path / "test.gb"
    p.write_bytes(rom_bytes)
    return p


@pytest.fixture()
def session_no_rom() -> FakeEmulatorSession:
    return FakeEmulatorSession()


@pytest.fixture()
def session_with_rom(rom_file: Path) -> FakeEmulatorSession:
    rom_bytes = rom_file.read_bytes()
    return FakeEmulatorSession(rom_bytes=rom_bytes, rom_path=str(rom_file))


# ---------------------------------------------------------------------------
# gb_load_rom
# ---------------------------------------------------------------------------


class TestGbLoadRom:
    def test_file_not_found(self, session_no_rom: FakeEmulatorSession) -> None:
        mcp = _make_mcp_with_session(session_no_rom)
        tool = _get_tool(mcp, "gb_load_rom")
        result = tool(rom_path="/nonexistent/path.gb")
        assert result["error"] == "FILE_NOT_FOUND"
        assert "FILE_NOT_FOUND" in result["error"]

    def test_load_success(
        self, session_no_rom: FakeEmulatorSession, rom_file: Path
    ) -> None:
        mcp = _make_mcp_with_session(session_no_rom)
        tool = _get_tool(mcp, "gb_load_rom")
        result = tool(rom_path=str(rom_file))
        assert result["status"] == "ok"
        assert result["rom_loaded"] is True
        assert result["rom_title"] == "TESTGAME"
        assert result["rom_path"] == str(rom_file)

    def test_load_success_sets_session_state(
        self, session_no_rom: FakeEmulatorSession, rom_file: Path
    ) -> None:
        mcp = _make_mcp_with_session(session_no_rom)
        tool = _get_tool(mcp, "gb_load_rom")
        tool(rom_path=str(rom_file))
        assert session_no_rom.rom_loaded is True


# ---------------------------------------------------------------------------
# get_session_info
# ---------------------------------------------------------------------------


class TestGetSessionInfo:
    def test_no_rom(self, session_no_rom: FakeEmulatorSession) -> None:
        mcp = _make_mcp_with_session(session_no_rom)
        tool = _get_tool(mcp, "get_session_info")
        result = tool()
        assert result["rom_loaded"] is False
        assert result["rom_title"] is None
        assert result["frame_count"] == 0
        assert result["pc"] == 0
        assert result["annotation_count"] == 0
        assert result["save_state_count"] == 0

    def test_with_rom(self, session_with_rom: FakeEmulatorSession) -> None:
        mcp = _make_mcp_with_session(session_with_rom)
        tool = _get_tool(mcp, "get_session_info")
        result = tool()
        assert result["rom_loaded"] is True
        assert result["rom_title"] == "TESTGAME"
        assert result["frame_count"] == 42
        assert result["pc"] == 0x0100
        assert result["annotation_count"] == 0
        assert result["save_state_count"] == 0

    def test_save_state_count(self, session_with_rom: FakeEmulatorSession) -> None:
        session_with_rom.save_states = {"state1": b"...", "state2": b"..."}
        mcp = _make_mcp_with_session(session_with_rom)
        tool = _get_tool(mcp, "get_session_info")
        result = tool()
        assert result["save_state_count"] == 2


# ---------------------------------------------------------------------------
# gb_reset
# ---------------------------------------------------------------------------


class TestGbReset:
    def test_no_rom(self, session_no_rom: FakeEmulatorSession) -> None:
        mcp = _make_mcp_with_session(session_no_rom)
        tool = _get_tool(mcp, "gb_reset")
        result = tool()
        assert result["error"] == "NO_ROM_LOADED"

    def test_reset_with_rom(
        self, session_with_rom: FakeEmulatorSession, rom_file: Path
    ) -> None:
        mcp = _make_mcp_with_session(session_with_rom)
        tool = _get_tool(mcp, "gb_reset")
        result = tool()
        assert result["status"] == "ok"
        assert "reset" in result["message"].lower()

    def test_reset_rom_stays_loaded(
        self, session_with_rom: FakeEmulatorSession
    ) -> None:
        mcp = _make_mcp_with_session(session_with_rom)
        tool = _get_tool(mcp, "gb_reset")
        tool()
        assert session_with_rom.rom_loaded is True


# ---------------------------------------------------------------------------
# get_rom_header
# ---------------------------------------------------------------------------


class TestGetRomHeader:
    def test_no_rom(self, session_no_rom: FakeEmulatorSession) -> None:
        mcp = _make_mcp_with_session(session_no_rom)
        tool = _get_tool(mcp, "get_rom_header")
        result = tool()
        assert result["error"] == "NO_ROM_LOADED"

    def test_with_rom_keys(self, session_with_rom: FakeEmulatorSession) -> None:
        mcp = _make_mcp_with_session(session_with_rom)
        tool = _get_tool(mcp, "get_rom_header")
        result = tool()
        for key in (
            "title",
            "cgb_flag",
            "sgb_flag",
            "cartridge_type",
            "rom_size",
            "ram_size",
            "old_licensee",
            "header_checksum",
            "global_checksum",
        ):
            assert key in result, f"Missing key: {key}"

    def test_with_rom_title(self, session_with_rom: FakeEmulatorSession) -> None:
        mcp = _make_mcp_with_session(session_with_rom)
        tool = _get_tool(mcp, "get_rom_header")
        result = tool()
        assert result["title"] == "TESTGAME"

    def test_with_rom_cartridge_type(
        self, session_with_rom: FakeEmulatorSession
    ) -> None:
        mcp = _make_mcp_with_session(session_with_rom)
        tool = _get_tool(mcp, "get_rom_header")
        result = tool()
        assert result["cartridge_type"] == 0x00  # ROM ONLY


# ---------------------------------------------------------------------------
# get_memory_map
# ---------------------------------------------------------------------------


class TestGetMemoryMap:
    def test_no_rom_works(self, session_no_rom: FakeEmulatorSession) -> None:
        mcp = _make_mcp_with_session(session_no_rom)
        tool = _get_tool(mcp, "get_memory_map")
        result = tool()
        assert "regions" in result

    def test_has_12_regions(self, session_no_rom: FakeEmulatorSession) -> None:
        mcp = _make_mcp_with_session(session_no_rom)
        tool = _get_tool(mcp, "get_memory_map")
        result = tool()
        assert len(result["regions"]) == 12

    def test_region_keys(self, session_no_rom: FakeEmulatorSession) -> None:
        mcp = _make_mcp_with_session(session_no_rom)
        tool = _get_tool(mcp, "get_memory_map")
        result = tool()
        region = result["regions"][0]
        for key in ("name", "start", "end", "size", "access_type"):
            assert key in region, f"Missing key: {key}"

    def test_first_region_is_rom0(self, session_no_rom: FakeEmulatorSession) -> None:
        mcp = _make_mcp_with_session(session_no_rom)
        tool = _get_tool(mcp, "get_memory_map")
        result = tool()
        assert result["regions"][0]["name"] == "ROM0"
        assert result["regions"][0]["start"] == 0x0000
        assert result["regions"][0]["end"] == 0x3FFF


# ---------------------------------------------------------------------------
# read_rom_bytes
# ---------------------------------------------------------------------------


class TestReadRomBytes:
    def test_length_zero(self, session_with_rom: FakeEmulatorSession) -> None:
        mcp = _make_mcp_with_session(session_with_rom)
        tool = _get_tool(mcp, "read_rom_bytes")
        result = tool(address=0x0100, length=0)
        assert result["error"] == "INVALID_PARAMETER"

    def test_length_too_large(self, session_with_rom: FakeEmulatorSession) -> None:
        mcp = _make_mcp_with_session(session_with_rom)
        tool = _get_tool(mcp, "read_rom_bytes")
        result = tool(address=0x0100, length=5000)
        assert result["error"] == "INVALID_PARAMETER"

    def test_no_rom(self, session_no_rom: FakeEmulatorSession) -> None:
        mcp = _make_mcp_with_session(session_no_rom)
        tool = _get_tool(mcp, "read_rom_bytes")
        result = tool(address=0x0100, length=16)
        assert result["error"] == "NO_ROM_LOADED"

    def test_valid_read_keys(self, session_with_rom: FakeEmulatorSession) -> None:
        mcp = _make_mcp_with_session(session_with_rom)
        tool = _get_tool(mcp, "read_rom_bytes")
        result = tool(address=0x0100, length=16)
        for key in ("address", "bank", "length", "data"):
            assert key in result, f"Missing key: {key}"

    def test_valid_read_values(self, session_with_rom: FakeEmulatorSession) -> None:
        mcp = _make_mcp_with_session(session_with_rom)
        tool = _get_tool(mcp, "read_rom_bytes")
        result = tool(address=0x0100, length=16)
        assert result["address"] == 0x0100
        assert result["bank"] is None
        assert result["length"] == 16
        assert isinstance(result["data"], str)
        assert "00000100" in result["data"]

    def test_valid_read_default_length(
        self, session_with_rom: FakeEmulatorSession
    ) -> None:
        mcp = _make_mcp_with_session(session_with_rom)
        tool = _get_tool(mcp, "read_rom_bytes")
        result = tool(address=0x0000)
        assert result["length"] == 256

    def test_length_boundary_min(self, session_with_rom: FakeEmulatorSession) -> None:
        mcp = _make_mcp_with_session(session_with_rom)
        tool = _get_tool(mcp, "read_rom_bytes")
        result = tool(address=0x0100, length=1)
        assert result["length"] == 1

    def test_length_boundary_max(self, session_with_rom: FakeEmulatorSession) -> None:
        mcp = _make_mcp_with_session(session_with_rom)
        tool = _get_tool(mcp, "read_rom_bytes")
        result = tool(address=0x0000, length=4096)
        assert result["length"] == 4096


# ---------------------------------------------------------------------------
# get_vector_table
# ---------------------------------------------------------------------------


class TestGetVectorTable:
    def test_no_rom(self, session_no_rom: FakeEmulatorSession) -> None:
        mcp = _make_mcp_with_session(session_no_rom)
        tool = _get_tool(mcp, "get_vector_table")
        result = tool()
        assert result["error"] == "NO_ROM_LOADED"

    def test_has_14_vectors(self, session_with_rom: FakeEmulatorSession) -> None:
        mcp = _make_mcp_with_session(session_with_rom)
        tool = _get_tool(mcp, "get_vector_table")
        result = tool()
        assert "vectors" in result
        assert len(result["vectors"]) == 14

    def test_vector_keys(self, session_with_rom: FakeEmulatorSession) -> None:
        mcp = _make_mcp_with_session(session_with_rom)
        tool = _get_tool(mcp, "get_vector_table")
        result = tool()
        v = result["vectors"][0]
        for key in ("address", "label", "type", "first_bytes"):
            assert key in v, f"Missing key: {key}"

    def test_vector_types(self, session_with_rom: FakeEmulatorSession) -> None:
        mcp = _make_mcp_with_session(session_with_rom)
        tool = _get_tool(mcp, "get_vector_table")
        result = tool()
        types = {v["type"] for v in result["vectors"]}
        assert types == {"rst", "interrupt", "entry"}

    def test_entry_point_vector(self, session_with_rom: FakeEmulatorSession) -> None:
        mcp = _make_mcp_with_session(session_with_rom)
        tool = _get_tool(mcp, "get_vector_table")
        result = tool()
        entry = next(v for v in result["vectors"] if v["type"] == "entry")
        assert entry["address"] == 0x100
        assert entry["label"] == "Entry"

    def test_first_bytes_format(self, session_with_rom: FakeEmulatorSession) -> None:
        mcp = _make_mcp_with_session(session_with_rom)
        tool = _get_tool(mcp, "get_vector_table")
        result = tool()
        # first_bytes should be "XX XX" format (two hex bytes space-separated)
        for v in result["vectors"]:
            parts = v["first_bytes"].split()
            assert len(parts) == 2
            for p in parts:
                assert len(p) == 2
                int(p, 16)  # must be valid hex


# ---------------------------------------------------------------------------
# gb_read_memory
# ---------------------------------------------------------------------------


class TestGbReadMemory:
    def test_length_zero(self, session_with_rom: FakeEmulatorSession) -> None:
        mcp = _make_mcp_with_session(session_with_rom)
        tool = _get_tool(mcp, "gb_read_memory")
        result = tool(address=0x0100, length=0)
        assert result["error"] == "INVALID_PARAMETER"

    def test_length_too_large(self, session_with_rom: FakeEmulatorSession) -> None:
        mcp = _make_mcp_with_session(session_with_rom)
        tool = _get_tool(mcp, "gb_read_memory")
        result = tool(address=0x0100, length=5000)
        assert result["error"] == "INVALID_PARAMETER"

    def test_no_rom(self, session_no_rom: FakeEmulatorSession) -> None:
        mcp = _make_mcp_with_session(session_no_rom)
        tool = _get_tool(mcp, "gb_read_memory")
        result = tool(address=0x0100, length=16)
        assert result["error"] == "NO_ROM_LOADED"

    def test_valid_read_keys(self, session_with_rom: FakeEmulatorSession) -> None:
        mcp = _make_mcp_with_session(session_with_rom)
        tool = _get_tool(mcp, "gb_read_memory")
        result = tool(address=0x0100, length=16)
        for key in ("address", "length", "data"):
            assert key in result, f"Missing key: {key}"

    def test_valid_read_values(self, session_with_rom: FakeEmulatorSession) -> None:
        mcp = _make_mcp_with_session(session_with_rom)
        tool = _get_tool(mcp, "gb_read_memory")
        result = tool(address=0x0100, length=16)
        assert result["address"] == 0x0100
        assert result["length"] == 16
        assert isinstance(result["data"], str)
        assert "00000100" in result["data"]

    def test_default_length(self, session_with_rom: FakeEmulatorSession) -> None:
        mcp = _make_mcp_with_session(session_with_rom)
        tool = _get_tool(mcp, "gb_read_memory")
        result = tool(address=0x0000)
        assert result["length"] == 256

    def test_length_boundary_min(self, session_with_rom: FakeEmulatorSession) -> None:
        mcp = _make_mcp_with_session(session_with_rom)
        tool = _get_tool(mcp, "gb_read_memory")
        result = tool(address=0x0100, length=1)
        assert result["length"] == 1

    def test_length_boundary_max(self, session_with_rom: FakeEmulatorSession) -> None:
        mcp = _make_mcp_with_session(session_with_rom)
        tool = _get_tool(mcp, "gb_read_memory")
        result = tool(address=0x0000, length=4096)
        assert result["length"] == 4096


# ---------------------------------------------------------------------------
# gb_read_banked
# ---------------------------------------------------------------------------


class TestGbReadBanked:
    def test_length_zero(self, session_with_rom: FakeEmulatorSession) -> None:
        mcp = _make_mcp_with_session(session_with_rom)
        tool = _get_tool(mcp, "gb_read_banked")
        result = tool(bank=1, address=0x4000, length=0)
        assert result["error"] == "INVALID_PARAMETER"

    def test_length_too_large(self, session_with_rom: FakeEmulatorSession) -> None:
        mcp = _make_mcp_with_session(session_with_rom)
        tool = _get_tool(mcp, "gb_read_banked")
        result = tool(bank=1, address=0x4000, length=5000)
        assert result["error"] == "INVALID_PARAMETER"

    def test_no_rom(self, session_no_rom: FakeEmulatorSession) -> None:
        mcp = _make_mcp_with_session(session_no_rom)
        tool = _get_tool(mcp, "gb_read_banked")
        result = tool(bank=1, address=0x4000, length=16)
        assert result["error"] == "NO_ROM_LOADED"

    def test_valid_read_keys(self, session_with_rom: FakeEmulatorSession) -> None:
        mcp = _make_mcp_with_session(session_with_rom)
        tool = _get_tool(mcp, "gb_read_banked")
        result = tool(bank=0, address=0x0000, length=16)
        for key in ("bank", "address", "length", "data"):
            assert key in result, f"Missing key: {key}"

    def test_valid_read_values(self, session_with_rom: FakeEmulatorSession) -> None:
        mcp = _make_mcp_with_session(session_with_rom)
        tool = _get_tool(mcp, "gb_read_banked")
        result = tool(bank=0, address=0x0100, length=16)
        assert result["bank"] == 0
        assert result["address"] == 0x0100
        assert result["length"] == 16
        assert isinstance(result["data"], str)

    def test_default_length(self, session_with_rom: FakeEmulatorSession) -> None:
        mcp = _make_mcp_with_session(session_with_rom)
        tool = _get_tool(mcp, "gb_read_banked")
        result = tool(bank=0, address=0x0000)
        assert result["length"] == 256


# ---------------------------------------------------------------------------
# gb_get_bank_info
# ---------------------------------------------------------------------------


class TestGbGetBankInfo:
    def test_no_rom(self, session_no_rom: FakeEmulatorSession) -> None:
        mcp = _make_mcp_with_session(session_no_rom)
        tool = _get_tool(mcp, "gb_get_bank_info")
        result = tool()
        assert result["error"] == "NO_ROM_LOADED"

    def test_keys(self, session_with_rom: FakeEmulatorSession) -> None:
        mcp = _make_mcp_with_session(session_with_rom)
        tool = _get_tool(mcp, "gb_get_bank_info")
        result = tool()
        for key in (
            "mbc_type",
            "mbc_name",
            "total_banks",
            "current_rom_bank",
            "has_ram",
            "has_battery",
        ):
            assert key in result, f"Missing key: {key}"

    def test_total_banks(self, session_with_rom: FakeEmulatorSession) -> None:
        # ROM ONLY with size byte 0x00 → 2 << 0 = 2 banks
        mcp = _make_mcp_with_session(session_with_rom)
        tool = _get_tool(mcp, "gb_get_bank_info")
        result = tool()
        assert result["total_banks"] == 2

    def test_mbc_type_none_for_rom_only(
        self, session_with_rom: FakeEmulatorSession
    ) -> None:
        mcp = _make_mcp_with_session(session_with_rom)
        tool = _get_tool(mcp, "gb_get_bank_info")
        result = tool()
        assert result["mbc_type"] is None

    def test_has_no_ram_for_rom_only(
        self, session_with_rom: FakeEmulatorSession
    ) -> None:
        mcp = _make_mcp_with_session(session_with_rom)
        tool = _get_tool(mcp, "gb_get_bank_info")
        result = tool()
        assert result["has_ram"] is False

    def test_current_rom_bank(self, session_with_rom: FakeEmulatorSession) -> None:
        mcp = _make_mcp_with_session(session_with_rom)
        tool = _get_tool(mcp, "gb_get_bank_info")
        result = tool()
        assert result["current_rom_bank"] == 1


# ---------------------------------------------------------------------------
# gb_get_interrupt_status
# ---------------------------------------------------------------------------


class TestGbGetInterruptStatus:
    def test_no_rom(self, session_no_rom: FakeEmulatorSession) -> None:
        mcp = _make_mcp_with_session(session_no_rom)
        tool = _get_tool(mcp, "gb_get_interrupt_status")
        result = tool()
        assert result["error"] == "NO_ROM_LOADED"

    def test_keys(self, session_with_rom: FakeEmulatorSession) -> None:
        mcp = _make_mcp_with_session(session_with_rom)
        tool = _get_tool(mcp, "gb_get_interrupt_status")
        result = tool()
        for key in ("ie_raw", "if_raw", "interrupts"):
            assert key in result, f"Missing key: {key}"

    def test_all_zero_flags(self, session_with_rom: FakeEmulatorSession) -> None:
        # Test ROM has 0x00 at 0xFFFF (IE) and 0xFF0F (IF)
        mcp = _make_mcp_with_session(session_with_rom)
        tool = _get_tool(mcp, "gb_get_interrupt_status")
        result = tool()
        assert result["ie_raw"] == 0x00
        assert result["if_raw"] == 0x00
        for flag in result["interrupts"].values():
            assert flag["enabled"] is False
            assert flag["requested"] is False

    def test_interrupt_names(self, session_with_rom: FakeEmulatorSession) -> None:
        mcp = _make_mcp_with_session(session_with_rom)
        tool = _get_tool(mcp, "gb_get_interrupt_status")
        result = tool()
        assert set(result["interrupts"].keys()) == {
            "vblank",
            "stat",
            "timer",
            "serial",
            "joypad",
        }

    def test_flag_structure(self, session_with_rom: FakeEmulatorSession) -> None:
        mcp = _make_mcp_with_session(session_with_rom)
        tool = _get_tool(mcp, "gb_get_interrupt_status")
        result = tool()
        for name, flag in result["interrupts"].items():
            assert "enabled" in flag, f"Missing 'enabled' in {name}"
            assert "requested" in flag, f"Missing 'requested' in {name}"
