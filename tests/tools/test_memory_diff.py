"""Integration tests for gb_memory_diff tool.

Uses enhanced fakes where save/load actually snapshot/restore memory.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from blobert_mcp.tools.savestate import register_savestate_tools

# ---------------------------------------------------------------------------
# Fake infrastructure (enhanced for memory diff)
# ---------------------------------------------------------------------------


class FakeRegisterFile:
    def __init__(self) -> None:
        self.A = 0x01
        self.B = 0x00
        self.C = 0x13
        self.D = 0x00
        self.E = 0xD8
        self.F = 0xB0
        self.H = 0x01
        self.L = 0x4D
        self.SP = 0xFFFE
        self.PC = 0x0100


class FakeMemory:
    """64KB memory that supports snapshot/restore for save state testing."""

    def __init__(self) -> None:
        self._data = bytearray(0x10000)

    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, slice):
            return list(self._data[key])
        return self._data[key]

    def __setitem__(self, key: Any, value: Any) -> None:
        self._data[key] = value

    def snapshot(self) -> bytes:
        return bytes(self._data)

    def restore(self, data: bytes) -> None:
        self._data[:] = data


class FakePyBoy:
    """FakePyBoy that captures/restores full memory on save/load."""

    def __init__(self) -> None:
        self.register_file = FakeRegisterFile()
        self.memory = FakeMemory()
        self.frame_count = 0

    def save_state(self, buffer) -> None:  # noqa: ANN001
        data = self.memory.snapshot()
        buffer.write(data)

    def load_state(self, buffer) -> None:  # noqa: ANN001
        data = buffer.read()
        self.memory.restore(data)

    def stop(self) -> None:
        pass


class FakeEmulatorSession:
    def __init__(self, *, with_rom: bool = False) -> None:
        self.pyboy: FakePyBoy | None = FakePyBoy() if with_rom else None
        self.save_states: dict[int, dict] = {}
        self.next_state_id: int = 1

    @property
    def rom_loaded(self) -> bool:
        return self.pyboy is not None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mcp(session: FakeEmulatorSession) -> FastMCP:
    mcp = FastMCP("test")
    register_savestate_tools(mcp, session)
    return mcp


def _get_tool(mcp: FastMCP, name: str):  # noqa: ANN201
    tools = {t.name: t for t in mcp._tool_manager.list_tools()}
    assert name in tools, f"Tool {name!r} not registered"
    return tools[name].fn


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGbMemoryDiff:
    def test_no_rom(self):
        session = FakeEmulatorSession()
        mcp = _make_mcp(session)
        result = _get_tool(mcp, "gb_memory_diff")(state_id_a=1, state_id_b=2)
        assert result["error"] == "NO_ROM_LOADED"

    def test_state_a_not_found(self):
        session = FakeEmulatorSession(with_rom=True)
        mcp = _make_mcp(session)
        _get_tool(mcp, "gb_save_state")()
        result = _get_tool(mcp, "gb_memory_diff")(state_id_a=999, state_id_b=1)
        assert result["error"] == "NOT_FOUND"
        assert "999" in result["message"]

    def test_state_b_not_found(self):
        session = FakeEmulatorSession(with_rom=True)
        mcp = _make_mcp(session)
        _get_tool(mcp, "gb_save_state")()
        result = _get_tool(mcp, "gb_memory_diff")(state_id_a=1, state_id_b=999)
        assert result["error"] == "NOT_FOUND"
        assert "999" in result["message"]

    def test_identical_states_no_changes(self):
        session = FakeEmulatorSession(with_rom=True)
        mcp = _make_mcp(session)
        save = _get_tool(mcp, "gb_save_state")
        s1 = save()
        s2 = save()
        result = _get_tool(mcp, "gb_memory_diff")(
            state_id_a=s1["state_id"], state_id_b=s2["state_id"]
        )
        assert result["status"] == "ok"
        assert result["changes"] == []
        assert result["total"] == 0

    def test_detects_changes(self):
        session = FakeEmulatorSession(with_rom=True)
        mcp = _make_mcp(session)
        save = _get_tool(mcp, "gb_save_state")
        s1 = save()
        session.pyboy.memory[0xC000] = 0x42
        session.pyboy.memory[0xC001] = 0xFF
        s2 = save()
        result = _get_tool(mcp, "gb_memory_diff")(
            state_id_a=s1["state_id"], state_id_b=s2["state_id"]
        )
        assert result["status"] == "ok"
        assert result["total"] == 2
        changes = result["changes"]
        assert len(changes) == 2
        assert changes[0]["address"] == "0xC000"
        assert changes[0]["old"] == "0x00"
        assert changes[0]["new"] == "0x42"

    def test_region_filtering(self):
        session = FakeEmulatorSession(with_rom=True)
        mcp = _make_mcp(session)
        save = _get_tool(mcp, "gb_save_state")
        s1 = save()
        session.pyboy.memory[0xC000] = 0x42  # WRAM0
        session.pyboy.memory[0xFF80] = 0xAA  # HRAM
        s2 = save()
        result = _get_tool(mcp, "gb_memory_diff")(
            state_id_a=s1["state_id"],
            state_id_b=s2["state_id"],
            regions=["HRAM"],
        )
        assert result["total"] == 1
        assert result["changes"][0]["address"] == "0xFF80"

    def test_prefix_region_wram(self):
        session = FakeEmulatorSession(with_rom=True)
        mcp = _make_mcp(session)
        save = _get_tool(mcp, "gb_save_state")
        s1 = save()
        session.pyboy.memory[0xC000] = 0x42  # WRAM0
        session.pyboy.memory[0xD000] = 0x43  # WRAMX
        session.pyboy.memory[0xFF80] = 0xAA  # HRAM — not in "WRAM" prefix
        s2 = save()
        result = _get_tool(mcp, "gb_memory_diff")(
            state_id_a=s1["state_id"],
            state_id_b=s2["state_id"],
            regions=["WRAM"],
        )
        assert result["total"] == 2
        addrs = [c["address"] for c in result["changes"]]
        assert "0xC000" in addrs
        assert "0xD000" in addrs

    def test_invalid_region_name(self):
        session = FakeEmulatorSession(with_rom=True)
        mcp = _make_mcp(session)
        save = _get_tool(mcp, "gb_save_state")
        s1 = save()
        s2 = save()
        result = _get_tool(mcp, "gb_memory_diff")(
            state_id_a=s1["state_id"],
            state_id_b=s2["state_id"],
            regions=["NONEXISTENT"],
        )
        assert result["error"] == "INVALID_PARAMETER"

    def test_truncation(self):
        session = FakeEmulatorSession(with_rom=True)
        mcp = _make_mcp(session)
        save = _get_tool(mcp, "gb_save_state")
        s1 = save()
        for i in range(600):
            session.pyboy.memory[0xC000 + i] = 0xFF
        s2 = save()
        result = _get_tool(mcp, "gb_memory_diff")(
            state_id_a=s1["state_id"], state_id_b=s2["state_id"]
        )
        assert result["truncated"] is True
        assert result["total"] == 600
        assert len(result["changes"]) == 512

    def test_no_truncation_when_under_limit(self):
        session = FakeEmulatorSession(with_rom=True)
        mcp = _make_mcp(session)
        save = _get_tool(mcp, "gb_save_state")
        s1 = save()
        session.pyboy.memory[0xC000] = 0x42
        s2 = save()
        result = _get_tool(mcp, "gb_memory_diff")(
            state_id_a=s1["state_id"], state_id_b=s2["state_id"]
        )
        assert result.get("truncated", False) is False

    def test_original_state_restored(self):
        session = FakeEmulatorSession(with_rom=True)
        mcp = _make_mcp(session)
        save = _get_tool(mcp, "gb_save_state")
        # Save state with known value
        session.pyboy.memory[0xC000] = 0xAB
        save()
        # Save state with different value
        session.pyboy.memory[0xC000] = 0xCD
        save()
        # Set memory to a distinct value before diff
        session.pyboy.memory[0xC000] = 0xEF
        _get_tool(mcp, "gb_memory_diff")(state_id_a=1, state_id_b=2)
        # Original state (0xEF) should be restored
        assert session.pyboy.memory[0xC000] == 0xEF

    def test_default_regions_exclude_vram(self):
        session = FakeEmulatorSession(with_rom=True)
        mcp = _make_mcp(session)
        save = _get_tool(mcp, "gb_save_state")
        s1 = save()
        session.pyboy.memory[0x8000] = 0xFF  # VRAM
        session.pyboy.memory[0xC000] = 0x42  # WRAM0
        s2 = save()
        result = _get_tool(mcp, "gb_memory_diff")(
            state_id_a=s1["state_id"], state_id_b=s2["state_id"]
        )
        assert result["total"] == 1
        assert result["changes"][0]["address"] == "0xC000"

    def test_returns_regions_scanned(self):
        session = FakeEmulatorSession(with_rom=True)
        mcp = _make_mcp(session)
        save = _get_tool(mcp, "gb_save_state")
        s1 = save()
        s2 = save()
        result = _get_tool(mcp, "gb_memory_diff")(
            state_id_a=s1["state_id"], state_id_b=s2["state_id"]
        )
        assert "regions_scanned" in result
        names = result["regions_scanned"]
        assert "WRAM0" in names
        assert "WRAMX" in names
        assert "HRAM" in names
