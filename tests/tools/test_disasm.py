"""Integration tests for disassembly MCP tools."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from blobert_mcp.tools.disasm import register_disasm_tools

# ---------------------------------------------------------------------------
# Fake infrastructure (mirrors test_tools.py pattern)
# ---------------------------------------------------------------------------


class FakeRegisterFile:
    PC = 0x0100


class FakeMemory:
    def __init__(self, data: bytes) -> None:
        self._data = bytearray(0x10000)
        self._data[: len(data)] = data

    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, slice):
            return list(self._data[key])
        if isinstance(key, tuple):
            _, addr = key
            if isinstance(addr, slice):
                return list(self._data[addr])
            return self._data[addr]
        return self._data[key]


class FakePyBoy:
    register_file = FakeRegisterFile()

    def __init__(self, data: bytes = b"") -> None:
        self.memory = FakeMemory(data)


class FakeEmulatorSession:
    def __init__(self, *, rom_bytes: bytes | None = None) -> None:
        if rom_bytes is not None:
            self.pyboy: FakePyBoy | None = FakePyBoy(rom_bytes)
        else:
            self.pyboy = None

    @property
    def rom_loaded(self) -> bool:
        return self.pyboy is not None


def _make_mcp(session: FakeEmulatorSession) -> FastMCP:
    mcp = FastMCP("test")
    register_disasm_tools(mcp, session)
    return mcp


def _get_tool(mcp: FastMCP, name: str):
    tools = {t.name: t for t in mcp._tool_manager.list_tools()}
    assert name in tools, f"Tool '{name}' not registered. Available: {list(tools)}"
    return tools[name].fn


# ---------------------------------------------------------------------------
# gb_disassemble_range
# ---------------------------------------------------------------------------


class TestGbDisassembleRange:
    def test_no_rom_returns_error(self):
        session = FakeEmulatorSession()
        tool = _get_tool(_make_mcp(session), "gb_disassemble_range")
        result = tool(address=0x0100, length=10)
        assert result["error"] == "NO_ROM_LOADED"

    def test_no_length_or_end_address_returns_error(self):
        session = FakeEmulatorSession(rom_bytes=b"\x00" * 0x8000)
        tool = _get_tool(_make_mcp(session), "gb_disassemble_range")
        result = tool(address=0x0100)
        assert result["error"] == "INVALID_PARAMETER"

    def test_happy_path_with_length(self):
        # Three NOPs at 0x0000
        rom = bytearray(0x8000)
        session = FakeEmulatorSession(rom_bytes=bytes(rom))
        tool = _get_tool(_make_mcp(session), "gb_disassemble_range")
        result = tool(address=0x0000, length=3)
        assert "error" not in result
        assert result["count"] == 3
        assert len(result["instructions"]) == 3
        assert result["address"] == "0x0000"

    def test_happy_path_with_end_address(self):
        rom = bytearray(0x8000)
        session = FakeEmulatorSession(rom_bytes=bytes(rom))
        tool = _get_tool(_make_mcp(session), "gb_disassemble_range")
        result = tool(address=0x0000, end_address=0x0003)
        assert "error" not in result
        assert result["count"] == 3

    def test_instruction_dict_format(self):
        # NOP at 0x0000
        rom = bytearray(0x8000)
        session = FakeEmulatorSession(rom_bytes=bytes(rom))
        tool = _get_tool(_make_mcp(session), "gb_disassemble_range")
        result = tool(address=0x0000, length=1)
        instr = result["instructions"][0]
        assert instr["address"] == "0x0000"
        assert instr["bytes"] == "00"
        assert instr["mnemonic"] == "NOP"
        assert instr["operands"] == []
        assert instr["size"] == 1

    def test_multibyte_instruction_formatted_correctly(self):
        # LD BC,0x1234 = 0x01 0x34 0x12
        rom = bytearray(0x8000)
        rom[0x0000] = 0x01
        rom[0x0001] = 0x34
        rom[0x0002] = 0x12
        session = FakeEmulatorSession(rom_bytes=bytes(rom))
        tool = _get_tool(_make_mcp(session), "gb_disassemble_range")
        result = tool(address=0x0000, length=3)
        instr = result["instructions"][0]
        assert instr["bytes"] == "01 34 12"
        assert instr["mnemonic"] == "LD"
        assert instr["size"] == 3


# ---------------------------------------------------------------------------
# gb_disassemble_function
# ---------------------------------------------------------------------------


class TestGbDisassembleFunction:
    def test_no_rom_returns_error(self):
        session = FakeEmulatorSession()
        tool = _get_tool(_make_mcp(session), "gb_disassemble_function")
        result = tool(entry_point=0x0100)
        assert result["error"] == "NO_ROM_LOADED"

    def test_happy_path_stops_at_ret(self):
        # NOP (0x00), RET (0xC9) at 0x0000
        rom = bytearray(0x8000)
        rom[0x0000] = 0x00  # NOP
        rom[0x0001] = 0xC9  # RET
        session = FakeEmulatorSession(rom_bytes=bytes(rom))
        tool = _get_tool(_make_mcp(session), "gb_disassemble_function")
        result = tool(entry_point=0x0000)
        assert "error" not in result
        assert result["count"] == 2
        assert result["size_bytes"] == 2
        assert result["entry_point"] == "0x0000"
        assert result["instructions"][-1]["mnemonic"] == "RET"

    def test_returns_required_keys(self):
        rom = bytearray(0x8000)
        rom[0x0000] = 0xC9  # RET immediately
        session = FakeEmulatorSession(rom_bytes=bytes(rom))
        tool = _get_tool(_make_mcp(session), "gb_disassemble_function")
        result = tool(entry_point=0x0000)
        assert "entry_point" in result
        assert "instructions" in result
        assert "size_bytes" in result
        assert "count" in result


# ---------------------------------------------------------------------------
# gb_disassemble_at_pc
# ---------------------------------------------------------------------------


class TestGbDisassembleAtPc:
    def test_no_rom_returns_error(self):
        session = FakeEmulatorSession()
        tool = _get_tool(_make_mcp(session), "gb_disassemble_at_pc")
        result = tool()
        assert result["error"] == "NO_ROM_LOADED"

    def test_happy_path_includes_current_marker(self):
        # FakeRegisterFile.PC = 0x0100
        rom = bytearray(0x8000)
        session = FakeEmulatorSession(rom_bytes=bytes(rom))
        tool = _get_tool(_make_mcp(session), "gb_disassemble_at_pc")
        result = tool(before=2, after=2)
        assert "error" not in result
        assert result["pc"] == "0x0100"
        current_instrs = [i for i in result["instructions"] if i.get("current")]
        assert len(current_instrs) == 1
        assert current_instrs[0]["address"] == "0x0100"

    def test_non_current_instructions_lack_current_key(self):
        rom = bytearray(0x8000)
        session = FakeEmulatorSession(rom_bytes=bytes(rom))
        tool = _get_tool(_make_mcp(session), "gb_disassemble_at_pc")
        result = tool(before=1, after=1)
        non_current = [i for i in result["instructions"] if i["address"] != "0x0100"]
        assert all("current" not in i for i in non_current)

    def test_returns_pc_key(self):
        rom = bytearray(0x8000)
        session = FakeEmulatorSession(rom_bytes=bytes(rom))
        tool = _get_tool(_make_mcp(session), "gb_disassemble_at_pc")
        result = tool()
        assert "pc" in result
        assert "instructions" in result
