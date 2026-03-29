"""Integration tests for dynamic tools: execution, input, and savestate.

Uses FakeEmulatorSession (no PyBoy) for all tests.
"""

from __future__ import annotations

from typing import Any

import pytest
from mcp.server.fastmcp import FastMCP
from PIL import Image as PILImage

from blobert_mcp.domain.disasm.decoder import decode_instruction
from blobert_mcp.tools.execution import register_execution_tools
from blobert_mcp.tools.input import register_input_tools
from blobert_mcp.tools.savestate import register_savestate_tools
from blobert_mcp.tools.visual import register_visual_tools

# ---------------------------------------------------------------------------
# Fake infrastructure
# ---------------------------------------------------------------------------


class FakeRegisterFile:
    """Full SM83 register file with realistic boot values."""

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
    """Provides pyboy.memory[...] interface backed by a 64KB address space."""

    def __init__(self) -> None:
        self._data = bytearray(0x10000)
        # Place a NOP (0x00) at 0x0100 by default
        self._data[0x0100] = 0x00

    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, slice):
            return list(self._data[key])
        return self._data[key]

    def __setitem__(self, key: Any, value: Any) -> None:
        self._data[key] = value


class FakeScreen:
    """Provides pyboy.screen.image for screenshot tests."""

    def __init__(self) -> None:
        self.image = PILImage.new("RGBA", (160, 144), (255, 255, 255, 255))


class FakePyBoy:
    """Minimal PyBoy fake for dynamic tool tests."""

    def __init__(self) -> None:
        self.register_file = FakeRegisterFile()
        self.memory = FakeMemory()
        self.frame_count = 0
        self._hooks: dict[int, tuple] = {}
        self._instruction_map: dict[int, int] = {}
        self._last_button_press: str | None = None
        self._last_button_release: str | None = None
        self._saved_bytes: bytes | None = None
        self.screen = FakeScreen()

    def set_instruction_at(self, pc: int, opcode_bytes: bytes) -> None:
        """Plant instruction bytes at *pc* and register the pc->next_pc mapping."""
        for i, b in enumerate(opcode_bytes):
            self.memory[pc + i] = b
        instr = decode_instruction(opcode_bytes, pc)
        self._instruction_map[pc] = (pc + instr.size) & 0xFFFF

    def tick(self) -> bool:
        self.frame_count += 1
        pc = self.register_file.PC
        # Fire hooks at current PC — models "arrived at this address"
        if pc in self._hooks:
            callback, context = self._hooks[pc]
            callback(context)
            return True
        # Simulate instruction execution: advance PC if mapped
        if pc in self._instruction_map:
            self.register_file.PC = self._instruction_map[pc]
        return True

    def hook_register(self, address: int, callback, context: Any) -> None:
        self._hooks[address] = (callback, context)

    def hook_deregister(self, address: int) -> None:
        self._hooks.pop(address, None)

    def button_press(self, button: str) -> None:
        self._last_button_press = button

    def button_release(self, button: str) -> None:
        self._last_button_release = button

    def save_state(self, buffer) -> None:
        buffer.write(b"FAKESTATE")
        self._saved_bytes = b"FAKESTATE"

    def load_state(self, buffer) -> None:
        buffer.read()

    def stop(self) -> None:
        pass


class FakeEmulatorSession:
    """In-memory mock of EmulatorSession for dynamic tool tests."""

    def __init__(self, *, with_rom: bool = False) -> None:
        if with_rom:
            self.pyboy: FakePyBoy | None = FakePyBoy()
        else:
            self.pyboy = None
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
    register_execution_tools(mcp, session)
    register_input_tools(mcp, session)
    register_savestate_tools(mcp, session)
    register_visual_tools(mcp, session)
    return mcp


def _get_tool(mcp: FastMCP, name: str):
    tools = {t.name: t for t in mcp._tool_manager.list_tools()}
    assert name in tools, f"Tool '{name}' not registered. Available: {list(tools)}"
    return tools[name].fn


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def session_no_rom() -> FakeEmulatorSession:
    return FakeEmulatorSession()


@pytest.fixture()
def session_with_rom() -> FakeEmulatorSession:
    return FakeEmulatorSession(with_rom=True)


# ---------------------------------------------------------------------------
# TestGbStep
# ---------------------------------------------------------------------------


class TestGbStep:
    def test_no_rom(self, session_no_rom):
        mcp = _make_mcp(session_no_rom)
        result = _get_tool(mcp, "gb_step")()
        assert result["error"] == "NO_ROM_LOADED"

    def test_unknown_mode_invalid(self, session_with_rom):
        mcp = _make_mcp(session_with_rom)
        result = _get_tool(mcp, "gb_step")(mode="other")
        assert result["error"] == "INVALID_PARAMETER"

    def test_default_one_frame(self, session_with_rom):
        mcp = _make_mcp(session_with_rom)
        result = _get_tool(mcp, "gb_step")()
        assert result["status"] == "ok"
        assert result["frames_executed"] == 1
        assert session_with_rom.pyboy.frame_count == 1

    def test_multiple_frames(self, session_with_rom):
        mcp = _make_mcp(session_with_rom)
        _get_tool(mcp, "gb_step")(count=3)
        assert session_with_rom.pyboy.frame_count == 3

    def test_returns_pc(self, session_with_rom):
        mcp = _make_mcp(session_with_rom)
        result = _get_tool(mcp, "gb_step")()
        assert "pc" in result
        assert result["pc"] == 0x0100

    def test_returns_instruction(self, session_with_rom):
        mcp = _make_mcp(session_with_rom)
        result = _get_tool(mcp, "gb_step")()
        assert "instruction" in result
        instr = result["instruction"]
        assert "mnemonic" in instr
        assert "operands" in instr

    def test_returns_registers(self, session_with_rom):
        mcp = _make_mcp(session_with_rom)
        result = _get_tool(mcp, "gb_step")()
        assert "registers" in result
        regs = result["registers"]
        for key in ("A", "B", "C", "D", "E", "F", "H", "L", "SP", "PC", "flags"):
            assert key in regs


# ---------------------------------------------------------------------------
# TestGbRunUntil
# ---------------------------------------------------------------------------


class TestGbRunUntil:
    def test_no_rom(self, session_no_rom):
        mcp = _make_mcp(session_no_rom)
        result = _get_tool(mcp, "gb_run_until")(target_address=0x0100)
        assert result["error"] == "NO_ROM_LOADED"

    def test_hits_target(self, session_with_rom):
        # PC is already 0x0100 — hook fires on first tick
        mcp = _make_mcp(session_with_rom)
        result = _get_tool(mcp, "gb_run_until")(target_address=0x0100)
        assert result["status"] == "ok"
        assert result["frames_executed"] == 1

    def test_timeout(self, session_with_rom):
        mcp = _make_mcp(session_with_rom)
        result = _get_tool(mcp, "gb_run_until")(target_address=0xDEAD, timeout_frames=5)
        assert result["error"] == "TIMEOUT"
        assert session_with_rom.pyboy.frame_count == 5

    def test_returns_registers_on_hit(self, session_with_rom):
        mcp = _make_mcp(session_with_rom)
        result = _get_tool(mcp, "gb_run_until")(target_address=0x0100)
        assert "registers" in result
        assert "A" in result["registers"]

    def test_custom_timeout(self, session_with_rom):
        mcp = _make_mcp(session_with_rom)
        result = _get_tool(mcp, "gb_run_until")(
            target_address=0xFFFF, timeout_frames=10
        )
        assert result["error"] == "TIMEOUT"
        assert session_with_rom.pyboy.frame_count == 10


# ---------------------------------------------------------------------------
# TestGbGetRegisters
# ---------------------------------------------------------------------------


class TestGbGetRegisters:
    def test_no_rom(self, session_no_rom):
        mcp = _make_mcp(session_no_rom)
        result = _get_tool(mcp, "gb_get_registers")()
        assert result["error"] == "NO_ROM_LOADED"

    def test_returns_all_register_keys(self, session_with_rom):
        mcp = _make_mcp(session_with_rom)
        result = _get_tool(mcp, "gb_get_registers")()
        expected_keys = (
            "A",
            "B",
            "C",
            "D",
            "E",
            "F",
            "H",
            "L",
            "AF",
            "BC",
            "DE",
            "HL",
            "SP",
            "PC",
        )
        for key in expected_keys:
            assert key in result

    def test_flags_are_booleans(self, session_with_rom):
        mcp = _make_mcp(session_with_rom)
        result = _get_tool(mcp, "gb_get_registers")()
        flags = result["flags"]
        for flag in ("Z", "N", "H", "C"):
            assert isinstance(flags[flag], bool)

    def test_hex_formatting(self, session_with_rom):
        mcp = _make_mcp(session_with_rom)
        result = _get_tool(mcp, "gb_get_registers")()
        assert result["A"].startswith("0x")
        assert result["PC"].startswith("0x")


# ---------------------------------------------------------------------------
# TestGbPressButton
# ---------------------------------------------------------------------------


class TestGbPressButton:
    def test_no_rom(self, session_no_rom):
        mcp = _make_mcp(session_no_rom)
        result = _get_tool(mcp, "gb_press_button")(button="a")
        assert result["error"] == "NO_ROM_LOADED"

    def test_press_valid_button(self, session_with_rom):
        mcp = _make_mcp(session_with_rom)
        result = _get_tool(mcp, "gb_press_button")(button="a", action="press")
        assert result["status"] == "ok"
        assert result["button"] == "a"
        assert result["action"] == "press"
        assert session_with_rom.pyboy._last_button_press == "a"

    def test_release_valid_button(self, session_with_rom):
        mcp = _make_mcp(session_with_rom)
        result = _get_tool(mcp, "gb_press_button")(button="b", action="release")
        assert result["status"] == "ok"
        assert session_with_rom.pyboy._last_button_release == "b"

    def test_invalid_button(self, session_with_rom):
        mcp = _make_mcp(session_with_rom)
        result = _get_tool(mcp, "gb_press_button")(button="jump")
        assert result["error"] == "INVALID_PARAMETER"

    def test_invalid_action(self, session_with_rom):
        mcp = _make_mcp(session_with_rom)
        result = _get_tool(mcp, "gb_press_button")(button="a", action="hold")
        assert result["error"] == "INVALID_PARAMETER"

    def test_case_insensitive_button(self, session_with_rom):
        mcp = _make_mcp(session_with_rom)
        result = _get_tool(mcp, "gb_press_button")(button="A", action="press")
        assert result["status"] == "ok"
        assert result["button"] == "a"

    def test_default_action_is_press(self, session_with_rom):
        mcp = _make_mcp(session_with_rom)
        result = _get_tool(mcp, "gb_press_button")(button="start")
        assert result["action"] == "press"
        assert session_with_rom.pyboy._last_button_press == "start"


# ---------------------------------------------------------------------------
# TestGbSaveState
# ---------------------------------------------------------------------------


class TestGbSaveState:
    def test_no_rom(self, session_no_rom):
        mcp = _make_mcp(session_no_rom)
        result = _get_tool(mcp, "gb_save_state")()
        assert result["error"] == "NO_ROM_LOADED"

    def test_returns_state_id(self, session_with_rom):
        mcp = _make_mcp(session_with_rom)
        result = _get_tool(mcp, "gb_save_state")()
        assert result["status"] == "ok"
        assert isinstance(result["state_id"], int)

    def test_increments_id(self, session_with_rom):
        mcp = _make_mcp(session_with_rom)
        tool = _get_tool(mcp, "gb_save_state")
        r1 = tool()
        r2 = tool()
        assert r2["state_id"] == r1["state_id"] + 1

    def test_stores_in_session(self, session_with_rom):
        mcp = _make_mcp(session_with_rom)
        result = _get_tool(mcp, "gb_save_state")()
        state_id = result["state_id"]
        assert state_id in session_with_rom.save_states

    def test_stores_timestamp(self, session_with_rom):
        mcp = _make_mcp(session_with_rom)
        result = _get_tool(mcp, "gb_save_state")()
        state_id = result["state_id"]
        entry = session_with_rom.save_states[state_id]
        assert "timestamp" in entry
        assert isinstance(entry["timestamp"], float)

    def test_with_name(self, session_with_rom):
        mcp = _make_mcp(session_with_rom)
        result = _get_tool(mcp, "gb_save_state")(name="before_boss")
        assert result["name"] == "before_boss"
        state_id = result["state_id"]
        assert session_with_rom.save_states[state_id]["name"] == "before_boss"


# ---------------------------------------------------------------------------
# TestGbLoadState
# ---------------------------------------------------------------------------


class TestGbLoadState:
    def test_no_rom(self, session_no_rom):
        mcp = _make_mcp(session_no_rom)
        result = _get_tool(mcp, "gb_load_state")(state_id=1)
        assert result["error"] == "NO_ROM_LOADED"

    def test_not_found(self, session_with_rom):
        mcp = _make_mcp(session_with_rom)
        result = _get_tool(mcp, "gb_load_state")(state_id=999)
        assert result["error"] == "NOT_FOUND"

    def test_load_valid_state(self, session_with_rom):
        mcp = _make_mcp(session_with_rom)
        save_result = _get_tool(mcp, "gb_save_state")()
        state_id = save_result["state_id"]
        load_result = _get_tool(mcp, "gb_load_state")(state_id=state_id)
        assert load_result["status"] == "ok"
        assert load_result["state_id"] == state_id

    def test_returns_registers_after_load(self, session_with_rom):
        mcp = _make_mcp(session_with_rom)
        save_result = _get_tool(mcp, "gb_save_state")()
        load_result = _get_tool(mcp, "gb_load_state")(state_id=save_result["state_id"])
        assert "registers" in load_result
        assert "A" in load_result["registers"]

    def test_returns_name(self, session_with_rom):
        mcp = _make_mcp(session_with_rom)
        save_result = _get_tool(mcp, "gb_save_state")(name="checkpoint")
        load_result = _get_tool(mcp, "gb_load_state")(state_id=save_result["state_id"])
        assert load_result["name"] == "checkpoint"


# ---------------------------------------------------------------------------
# TestGbListStates
# ---------------------------------------------------------------------------


class TestGbListStates:
    def test_no_rom(self, session_no_rom):
        mcp = _make_mcp(session_no_rom)
        result = _get_tool(mcp, "gb_list_states")()
        assert result["error"] == "NO_ROM_LOADED"

    def test_empty(self, session_with_rom):
        mcp = _make_mcp(session_with_rom)
        result = _get_tool(mcp, "gb_list_states")()
        assert result["status"] == "ok"
        assert result["states"] == []

    def test_lists_metadata(self, session_with_rom):
        mcp = _make_mcp(session_with_rom)
        save = _get_tool(mcp, "gb_save_state")
        save(name="first")
        save(name="second")
        result = _get_tool(mcp, "gb_list_states")()
        assert result["status"] == "ok"
        assert len(result["states"]) == 2
        for entry in result["states"]:
            for key in ("state_id", "name", "frame_count", "pc", "timestamp"):
                assert key in entry

    def test_excludes_buffer(self, session_with_rom):
        mcp = _make_mcp(session_with_rom)
        _get_tool(mcp, "gb_save_state")()
        result = _get_tool(mcp, "gb_list_states")()
        for entry in result["states"]:
            assert "buffer" not in entry


# ---------------------------------------------------------------------------
# TestGbDeleteState
# ---------------------------------------------------------------------------


class TestGbDeleteState:
    def test_no_rom(self, session_no_rom):
        mcp = _make_mcp(session_no_rom)
        result = _get_tool(mcp, "gb_delete_state")(state_id=1)
        assert result["error"] == "NO_ROM_LOADED"

    def test_not_found(self, session_with_rom):
        mcp = _make_mcp(session_with_rom)
        result = _get_tool(mcp, "gb_delete_state")(state_id=999)
        assert result["error"] == "NOT_FOUND"

    def test_deletes_state(self, session_with_rom):
        mcp = _make_mcp(session_with_rom)
        save_result = _get_tool(mcp, "gb_save_state")()
        state_id = save_result["state_id"]
        _get_tool(mcp, "gb_delete_state")(state_id=state_id)
        assert state_id not in session_with_rom.save_states

    def test_returns_ok(self, session_with_rom):
        mcp = _make_mcp(session_with_rom)
        save_result = _get_tool(mcp, "gb_save_state")()
        state_id = save_result["state_id"]
        result = _get_tool(mcp, "gb_delete_state")(state_id=state_id)
        assert result["status"] == "ok"
        assert result["state_id"] == state_id


# ---------------------------------------------------------------------------
# TestGbStepInstruction
# ---------------------------------------------------------------------------


class TestGbStepInstruction:
    def test_no_rom(self, session_no_rom):
        mcp = _make_mcp(session_no_rom)
        result = _get_tool(mcp, "gb_step")(mode="instruction")
        assert result["error"] == "NO_ROM_LOADED"

    def test_single_nop(self, session_with_rom):
        """NOP (0x00) is 1 byte — PC should advance from 0x0100 to 0x0101."""
        session_with_rom.pyboy.set_instruction_at(0x0100, b"\x00")
        mcp = _make_mcp(session_with_rom)
        result = _get_tool(mcp, "gb_step")(mode="instruction")
        assert result["status"] == "ok"
        assert result["instructions_executed"] == 1
        assert result["pc"] == 0x0101

    def test_two_byte_instruction(self, session_with_rom):
        """LD A,0x42 (0x3E 0x42) is 2 bytes — PC advances to 0x0102."""
        session_with_rom.pyboy.set_instruction_at(0x0100, b"\x3e\x42")
        mcp = _make_mcp(session_with_rom)
        result = _get_tool(mcp, "gb_step")(mode="instruction")
        assert result["status"] == "ok"
        assert result["pc"] == 0x0102

    def test_three_byte_instruction(self, session_with_rom):
        """JP 0x1234 (0xC3 0x34 0x12) is 3 bytes — size=3, timeout path."""
        session_with_rom.pyboy.set_instruction_at(0x0100, b"\xc3\x34\x12")
        mcp = _make_mcp(session_with_rom)
        result = _get_tool(mcp, "gb_step")(mode="instruction")
        assert result["status"] == "ok"
        assert result["instructions_executed"] == 1

    def test_cb_prefixed(self, session_with_rom):
        """BIT 0,B (0xCB 0x40) is 2 bytes — PC advances to 0x0102."""
        session_with_rom.pyboy.set_instruction_at(0x0100, b"\xcb\x40")
        mcp = _make_mcp(session_with_rom)
        result = _get_tool(mcp, "gb_step")(mode="instruction")
        assert result["status"] == "ok"
        assert result["pc"] == 0x0102

    def test_multiple_steps(self, session_with_rom):
        """Two NOPs — count=2 should step both, PC at 0x0102."""
        session_with_rom.pyboy.set_instruction_at(0x0100, b"\x00")
        session_with_rom.pyboy.set_instruction_at(0x0101, b"\x00")
        mcp = _make_mcp(session_with_rom)
        result = _get_tool(mcp, "gb_step")(count=2, mode="instruction")
        assert result["status"] == "ok"
        assert result["instructions_executed"] == 2
        assert result["pc"] == 0x0102

    def test_returns_instruction_and_registers(self, session_with_rom):
        """Response includes decoded instruction at new PC and full registers."""
        session_with_rom.pyboy.set_instruction_at(0x0100, b"\x00")
        session_with_rom.pyboy.set_instruction_at(0x0101, b"\x3e\x42")
        mcp = _make_mcp(session_with_rom)
        result = _get_tool(mcp, "gb_step")(mode="instruction")
        assert result["instruction"]["mnemonic"] == "LD"
        assert "registers" in result
        for key in ("A", "B", "C", "D", "E", "F", "H", "L", "SP", "PC", "flags"):
            assert key in result["registers"]


# ---------------------------------------------------------------------------
# TestGbScreenshot
# ---------------------------------------------------------------------------


class TestGbScreenshot:
    def test_no_rom(self, session_no_rom):
        mcp = _make_mcp(session_no_rom)
        result = _get_tool(mcp, "gb_screenshot")()
        assert result["error"] == "NO_ROM_LOADED"

    def test_default_png(self, session_with_rom):
        from mcp.server.fastmcp.utilities.types import Image as MCPImage

        mcp = _make_mcp(session_with_rom)
        result = _get_tool(mcp, "gb_screenshot")()
        assert isinstance(result, MCPImage)
        assert result._mime_type == "image/png"
        # PNG magic bytes
        assert result.data[:4] == b"\x89PNG"

    def test_webp_format(self, session_with_rom):
        from mcp.server.fastmcp.utilities.types import Image as MCPImage

        mcp = _make_mcp(session_with_rom)
        result = _get_tool(mcp, "gb_screenshot")(format="webp")
        assert isinstance(result, MCPImage)
        assert result._mime_type == "image/webp"

    def test_invalid_format(self, session_with_rom):
        mcp = _make_mcp(session_with_rom)
        result = _get_tool(mcp, "gb_screenshot")(format="bmp")
        assert result["error"] == "INVALID_PARAMETER"

    def test_scale_2(self, session_with_rom):
        from io import BytesIO

        from mcp.server.fastmcp.utilities.types import Image as MCPImage

        mcp = _make_mcp(session_with_rom)
        result = _get_tool(mcp, "gb_screenshot")(scale=2)
        assert isinstance(result, MCPImage)
        img = PILImage.open(BytesIO(result.data))
        assert img.size == (320, 288)

    def test_invalid_scale(self, session_with_rom):
        mcp = _make_mcp(session_with_rom)
        result = _get_tool(mcp, "gb_screenshot")(scale=0)
        assert result["error"] == "INVALID_PARAMETER"


# ---------------------------------------------------------------------------
# TestGbSetRegister
# ---------------------------------------------------------------------------


class TestGbSetRegister:
    def test_no_rom(self, session_no_rom):
        mcp = _make_mcp(session_no_rom)
        result = _get_tool(mcp, "gb_set_register")(register="A", value=0x42)
        assert result["error"] == "NO_ROM_LOADED"

    def test_set_a_register(self, session_with_rom):
        mcp = _make_mcp(session_with_rom)
        result = _get_tool(mcp, "gb_set_register")(register="A", value=0x42)
        assert result["status"] == "ok"
        assert session_with_rom.pyboy.register_file.A == 0x42

    def test_set_sp_register(self, session_with_rom):
        mcp = _make_mcp(session_with_rom)
        result = _get_tool(mcp, "gb_set_register")(register="SP", value=0x1234)
        assert result["status"] == "ok"
        assert session_with_rom.pyboy.register_file.SP == 0x1234

    def test_set_pc_register(self, session_with_rom):
        mcp = _make_mcp(session_with_rom)
        result = _get_tool(mcp, "gb_set_register")(register="PC", value=0x0150)
        assert result["status"] == "ok"
        assert session_with_rom.pyboy.register_file.PC == 0x0150

    def test_returns_confirmation(self, session_with_rom):
        mcp = _make_mcp(session_with_rom)
        result = _get_tool(mcp, "gb_set_register")(register="A", value=0x42)
        assert result["status"] == "ok"
        assert result["register"] == "A"
        assert result["value"] == "0x42"

    def test_case_insensitive(self, session_with_rom):
        mcp = _make_mcp(session_with_rom)
        result = _get_tool(mcp, "gb_set_register")(register="a", value=0x42)
        assert result["status"] == "ok"
        assert result["register"] == "A"

    def test_invalid_register_name(self, session_with_rom):
        mcp = _make_mcp(session_with_rom)
        result = _get_tool(mcp, "gb_set_register")(register="X", value=0x42)
        assert result["error"] == "INVALID_PARAMETER"

    def test_composite_register_rejected(self, session_with_rom):
        mcp = _make_mcp(session_with_rom)
        result = _get_tool(mcp, "gb_set_register")(register="AF", value=0x1234)
        assert result["error"] == "INVALID_PARAMETER"

    def test_8bit_value_out_of_range(self, session_with_rom):
        mcp = _make_mcp(session_with_rom)
        result = _get_tool(mcp, "gb_set_register")(register="A", value=0x100)
        assert result["error"] == "INVALID_PARAMETER"

    def test_negative_value(self, session_with_rom):
        mcp = _make_mcp(session_with_rom)
        result = _get_tool(mcp, "gb_set_register")(register="A", value=-1)
        assert result["error"] == "INVALID_PARAMETER"

    def test_16bit_value_out_of_range(self, session_with_rom):
        mcp = _make_mcp(session_with_rom)
        result = _get_tool(mcp, "gb_set_register")(register="SP", value=0x10000)
        assert result["error"] == "INVALID_PARAMETER"

    def test_f_register_masked(self, session_with_rom):
        mcp = _make_mcp(session_with_rom)
        result = _get_tool(mcp, "gb_set_register")(register="F", value=0xFF)
        assert result["status"] == "ok"
        assert session_with_rom.pyboy.register_file.F == 0xF0
        assert result["value"] == "0xF0"

    def test_16bit_value_formatted_as_hex(self, session_with_rom):
        mcp = _make_mcp(session_with_rom)
        result = _get_tool(mcp, "gb_set_register")(register="SP", value=0x1234)
        assert result["value"] == "0x1234"
