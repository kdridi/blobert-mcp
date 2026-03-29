"""TDD tests for SM83 disassembly algorithms — written before implementation."""

from __future__ import annotations

import pytest

from blobert_mcp.domain.disasm.disassembler import (
    disassemble_at_pc,
    disassemble_function,
    disassemble_range,
)


def _reader(data: bytes):
    """Build a memory_reader from a flat bytes object."""

    def read(address: int, length: int) -> bytes:
        # Pad with 0x00 (NOP) if reading beyond the data
        result = bytearray(length)
        for i in range(length):
            idx = address + i
            result[i] = data[idx] if idx < len(data) else 0x00
        return bytes(result)

    return read


# ---------------------------------------------------------------------------
# disassemble_range
# ---------------------------------------------------------------------------


class TestDisassembleRange:
    def test_three_nops_by_length(self):
        reader = _reader(b"\x00\x00\x00")
        instrs = disassemble_range(reader, 0x0000, length=3)
        assert len(instrs) == 3
        assert all(i.mnemonic == "NOP" for i in instrs)
        assert instrs[0].address == 0x0000
        assert instrs[1].address == 0x0001
        assert instrs[2].address == 0x0002

    def test_end_address_stops_before_next_instruction(self):
        # NOP NOP LD B,0xFF — stop before the LD
        reader = _reader(b"\x00\x00\x06\xff")
        instrs = disassemble_range(reader, 0x0100, end_address=0x0102)
        assert len(instrs) == 2
        assert all(i.mnemonic == "NOP" for i in instrs)

    def test_256_instruction_cap(self):
        reader = _reader(b"\x00" * 512)
        instrs = disassemble_range(reader, 0x0000, length=512)
        assert len(instrs) == 256

    def test_requires_length_or_end_address(self):
        reader = _reader(b"\x00")
        with pytest.raises(ValueError):
            disassemble_range(reader, 0x0000)

    def test_length_and_end_address_both_provided(self):
        # Both provided: stops at whichever comes first
        reader = _reader(b"\x00\x00\x00")
        # length=1 hits before end_address=0x0003
        instrs = disassemble_range(reader, 0x0000, length=1, end_address=0x0003)
        assert len(instrs) == 1

    def test_multibyte_instruction_length_consumed_correctly(self):
        # LD BC, 0x1234 = 0x01 0x34 0x12 (3 bytes)
        reader = _reader(b"\x01\x34\x12\x00")
        instrs = disassemble_range(reader, 0x0000, length=3)
        assert len(instrs) == 1
        assert instrs[0].mnemonic == "LD"
        assert instrs[0].size == 3

    def test_address_field_correct_for_each_instruction(self):
        # LD B,0xFF (2 bytes) at 0x0000, then NOP at 0x0002
        reader = _reader(b"\x06\xff\x00")
        instrs = disassemble_range(reader, 0x0000, length=3)
        assert instrs[0].address == 0x0000
        assert instrs[1].address == 0x0002


# ---------------------------------------------------------------------------
# disassemble_function
# ---------------------------------------------------------------------------


class TestDisassembleFunction:
    def test_stops_at_ret(self):
        # NOP, RET
        reader = _reader(b"\x00\xc9")
        result = disassemble_function(reader, 0x0000)
        assert len(result["instructions"]) == 2
        assert result["instructions"][-1].mnemonic == "RET"
        assert result["instructions"][-1].raw_bytes == b"\xc9"
        assert result["size_bytes"] == 2

    def test_stops_at_reti(self):
        # NOP, RETI
        reader = _reader(b"\x00\xd9")
        result = disassemble_function(reader, 0x0000)
        assert len(result["instructions"]) == 2
        assert result["instructions"][-1].mnemonic == "RETI"
        assert result["size_bytes"] == 2

    def test_stops_at_unconditional_jp_outside_range(self):
        # JP 0x0200 — jumps well outside entry_point=0x0000
        reader = _reader(b"\xc3\x00\x02")
        result = disassemble_function(reader, 0x0000)
        assert len(result["instructions"]) == 1
        assert result["instructions"][0].mnemonic == "JP"
        assert result["size_bytes"] == 3

    def test_unconditional_jp_inside_range_does_not_stop(self):
        # JP back to entry_point (0x0000) — a loop; hits 1024-instruction cap
        reader = _reader(b"\xc3\x00\x00")
        result = disassemble_function(reader, 0x0000)
        assert len(result["instructions"]) == 1024

    def test_conditional_ret_does_not_stop(self):
        # RET NZ (0xC0), NOP, RET — conditional RET must NOT stop tracing
        reader = _reader(b"\xc0\x00\xc9")
        result = disassemble_function(reader, 0x0000)
        assert len(result["instructions"]) == 3
        assert result["instructions"][0].raw_bytes == b"\xc0"
        assert result["instructions"][-1].mnemonic == "RET"

    def test_1024_instruction_cap(self):
        reader = _reader(b"\x00" * 2048)
        result = disassemble_function(reader, 0x0000)
        assert len(result["instructions"]) == 1024

    def test_size_bytes_reflects_total_decoded_bytes(self):
        # LD BC,0x1234 (3 bytes) + RET (1 byte) = 4
        reader = _reader(b"\x01\x34\x12\xc9")
        result = disassemble_function(reader, 0x0000)
        assert result["size_bytes"] == 4

    def test_returns_dict_with_required_keys(self):
        reader = _reader(b"\xc9")
        result = disassemble_function(reader, 0x0000)
        assert "instructions" in result
        assert "size_bytes" in result


# ---------------------------------------------------------------------------
# disassemble_at_pc
# ---------------------------------------------------------------------------


class TestDisassembleAtPc:
    def test_basic_pc_instruction_included(self):
        # NOP at 0x0000, then NOP at 0x0001 (this is pc)
        reader = _reader(b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00")
        instrs = disassemble_at_pc(reader, pc=0x0002, before=2, after=0)
        # Should include the pc instruction
        addresses = [i.address for i in instrs]
        assert 0x0002 in addresses

    def test_after_instructions_decoded_from_pc(self):
        reader = _reader(b"\x00" * 30)
        instrs = disassemble_at_pc(reader, pc=0x0000, before=0, after=5)
        assert len(instrs) == 6  # pc instruction + 5 after

    def test_before_with_aligned_multibyte(self):
        # CALL 0x1000 (3 bytes: 0xCD 0x00 0x10) at 0x0000, then NOP at 0x0003 (pc)
        reader = _reader(b"\xcd\x00\x10" + b"\x00" * 10)
        instrs = disassemble_at_pc(reader, pc=0x0003, before=1, after=0)
        addresses = [i.address for i in instrs]
        assert 0x0000 in addresses  # pre-pc instruction found by backward scan
        assert 0x0003 in addresses  # pc instruction

    def test_fallback_when_no_alignment(self):
        # Use a pc where backward scan won't find clean alignment
        # Just verify we still get some instructions including the pc
        reader = _reader(b"\x00" * 20)
        instrs = disassemble_at_pc(reader, pc=0x0005, before=3, after=0)
        addresses = [i.address for i in instrs]
        assert 0x0005 in addresses

    def test_pc_at_address_zero_before_clamped(self):
        # pc=0x0000 with before=5 — scan start would go negative, must clamp to 0
        reader = _reader(b"\x00" * 10)
        instrs = disassemble_at_pc(reader, pc=0x0000, before=5, after=2)
        addresses = [i.address for i in instrs]
        assert 0x0000 in addresses

    def test_combined_before_pc_and_after(self):
        # All NOPs: 5 before, pc at 0x0005, 3 after
        reader = _reader(b"\x00" * 20)
        instrs = disassemble_at_pc(reader, pc=0x0005, before=5, after=3)
        # pc instruction is at 0x0005, 3 after = 0x0006, 0x0007, 0x0008
        addresses = [i.address for i in instrs]
        assert 0x0005 in addresses
        assert 0x0006 in addresses
        assert 0x0007 in addresses
        assert 0x0008 in addresses
