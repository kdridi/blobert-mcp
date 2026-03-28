"""Tests for domain/disasm/decoder.py — SM83 instruction decoder."""

from __future__ import annotations

from blobert_mcp.domain.disasm.decoder import Instruction, decode_instruction

# --- Basic structure ---


def test_decode_nop():
    instr = decode_instruction(b"\x00", 0x100)
    assert instr.address == 0x100
    assert instr.raw_bytes == b"\x00"
    assert instr.mnemonic == "NOP"
    assert instr.operands == []
    assert instr.size == 1


def test_decode_address_preserved():
    instr = decode_instruction(b"\x00", 0xABCD)
    assert instr.address == 0xABCD


def test_decode_raw_bytes_single():
    instr = decode_instruction(b"\x00", 0)
    assert instr.raw_bytes == b"\x00"


def test_decode_raw_bytes_triple():
    instr = decode_instruction(b"\x01\x34\x12", 0)
    assert instr.raw_bytes == b"\x01\x34\x12"


def test_instruction_is_dataclass():
    instr = decode_instruction(b"\x00", 0)
    assert isinstance(instr, Instruction)


# --- Immediate operands ---


def test_decode_ld_bc_d16():
    instr = decode_instruction(b"\x01\x34\x12", 0x100)
    assert instr.mnemonic == "LD"
    assert instr.operands == ["BC", "0x1234"]
    assert instr.size == 3


def test_decode_ld_a_d8():
    instr = decode_instruction(b"\x3E\x42", 0x100)
    assert instr.mnemonic == "LD"
    assert instr.operands == ["A", "0x42"]
    assert instr.size == 2


def test_decode_d8_zero_padded():
    instr = decode_instruction(b"\x3E\x05", 0)
    assert instr.operands[-1] == "0x05"


def test_decode_d16_little_endian():
    # LD DE,d16 with bytes 0xCD 0xAB → word = 0xABCD
    instr = decode_instruction(b"\x11\xCD\xAB", 0)
    assert instr.operands == ["DE", "0xABCD"]


def test_decode_d16_all_zeros():
    instr = decode_instruction(b"\x01\x00\x00", 0)
    assert instr.operands == ["BC", "0x0000"]


# --- Register-literal operands ---


def test_decode_ld_b_b():
    instr = decode_instruction(b"\x40", 0)
    assert instr.mnemonic == "LD"
    assert instr.operands == ["B", "B"]
    assert instr.size == 1


def test_decode_halt():
    instr = decode_instruction(b"\x76", 0)
    assert instr.mnemonic == "HALT"
    assert instr.operands == []
    assert instr.size == 1


def test_decode_ret():
    instr = decode_instruction(b"\xC9", 0)
    assert instr.mnemonic == "RET"
    assert instr.operands == []
    assert instr.size == 1


def test_decode_xor_a():
    instr = decode_instruction(b"\xAF", 0)
    assert instr.mnemonic == "XOR"
    assert instr.operands == ["A"]
    assert instr.size == 1


# --- Relative jumps (r8 → absolute address) ---


def test_decode_jr_forward():
    # JR +5 from 0x100: (0x100 + 2 + 5) = 0x107
    instr = decode_instruction(b"\x18\x05", 0x100)
    assert instr.mnemonic == "JR"
    assert instr.operands == ["0x0107"]
    assert instr.size == 2


def test_decode_jr_negative_offset():
    # JR -2 (0xFE as signed = -2) from 0x100: (0x100 + 2 - 2) = 0x100
    instr = decode_instruction(b"\x18\xFE", 0x100)
    assert instr.operands == ["0x0100"]


def test_decode_jr_self_loop():
    # JR -2 (0xFE) from 0x0000: (0 + 2 - 2) = 0x0000
    instr = decode_instruction(b"\x18\xFE", 0x0000)
    assert instr.operands == ["0x0000"]


def test_decode_jr_nz():
    # JR NZ,+16 from 0x100: (0x100 + 2 + 0x10) = 0x112
    instr = decode_instruction(b"\x20\x10", 0x100)
    assert instr.mnemonic == "JR"
    assert instr.operands == ["NZ", "0x0112"]


def test_decode_jr_z():
    instr = decode_instruction(b"\x28\x00", 0x100)
    assert instr.operands == ["Z", "0x0102"]


def test_decode_jr_16bit_wrap():
    # JR +127 (0x7F) from 0xFF80: (0xFF80 + 2 + 127) & 0xFFFF = 0x0001
    instr = decode_instruction(b"\x18\x7F", 0xFF80)
    assert instr.operands == ["0x0001"]


def test_decode_jr_negative_wrap():
    # JR -128 (0x80) from 0x0001: (0x0001 + 2 - 128) & 0xFFFF = 0xFF83
    instr = decode_instruction(b"\x18\x80", 0x0001)
    assert instr.operands == ["0xFF83"]


# --- Signed immediate (r8s — plain signed number for SP arithmetic) ---


def test_decode_add_sp_r8s_positive():
    instr = decode_instruction(b"\xE8\x05", 0x100)
    assert instr.mnemonic == "ADD"
    assert instr.operands == ["SP", "+5"]
    assert instr.size == 2


def test_decode_add_sp_r8s_negative():
    # 0xFE = -2 as signed byte
    instr = decode_instruction(b"\xE8\xFE", 0x100)
    assert instr.operands == ["SP", "-2"]


def test_decode_add_sp_r8s_zero():
    instr = decode_instruction(b"\xE8\x00", 0x100)
    assert instr.operands == ["SP", "+0"]


def test_decode_ld_hl_sp_r8s_positive():
    instr = decode_instruction(b"\xF8\x03", 0x100)
    assert instr.mnemonic == "LD"
    assert instr.operands == ["HL", "SP+3"]
    assert instr.size == 2


def test_decode_ld_hl_sp_r8s_negative():
    # 0xFF = -1
    instr = decode_instruction(b"\xF8\xFF", 0x100)
    assert instr.operands == ["HL", "SP-1"]


# --- High-page address operands (a8) ---


def test_decode_ldh_write():
    # LDH (a8),A with a8=0xFF: address = 0xFFFF
    instr = decode_instruction(b"\xE0\xFF", 0x100)
    assert instr.mnemonic == "LDH"
    assert instr.operands == ["(0xFFFF)", "A"]
    assert instr.size == 2


def test_decode_ldh_read():
    # LDH A,(a8) with a8=0x40: address = 0xFF40
    instr = decode_instruction(b"\xF0\x40", 0x100)
    assert instr.mnemonic == "LDH"
    assert instr.operands == ["A", "(0xFF40)"]
    assert instr.size == 2


def test_decode_ldh_zero():
    instr = decode_instruction(b"\xE0\x00", 0)
    assert instr.operands == ["(0xFF00)", "A"]


# --- Indirect address operands (a16) ---


def test_decode_ld_indirect_a16_a():
    # LD (a16),A with address 0xC000
    instr = decode_instruction(b"\xEA\x00\xC0", 0x100)
    assert instr.mnemonic == "LD"
    assert instr.operands == ["(0xC000)", "A"]
    assert instr.size == 3


def test_decode_ld_a_indirect_a16():
    instr = decode_instruction(b"\xFA\x50\xFF", 0)
    assert instr.operands == ["A", "(0xFF50)"]


# --- CB prefix dispatch ---


def test_decode_cb_rlc_b():
    instr = decode_instruction(b"\xCB\x00", 0x100)
    assert instr.mnemonic == "RLC"
    assert instr.operands == ["B"]
    assert instr.size == 2
    assert instr.raw_bytes == b"\xCB\x00"


def test_decode_cb_bit_7_a():
    instr = decode_instruction(b"\xCB\x7F", 0x100)
    assert instr.mnemonic == "BIT"
    assert instr.operands == ["7", "A"]
    assert instr.size == 2


def test_decode_cb_res_0_b():
    instr = decode_instruction(b"\xCB\x80", 0x100)
    assert instr.mnemonic == "RES"
    assert instr.operands == ["0", "B"]
    assert instr.size == 2


def test_decode_cb_set_7_a():
    instr = decode_instruction(b"\xCB\xFF", 0x100)
    assert instr.mnemonic == "SET"
    assert instr.operands == ["7", "A"]
    assert instr.size == 2


def test_decode_cb_raw_bytes_only_two():
    # Extra byte must not be consumed
    instr = decode_instruction(b"\xCB\x00\xFF", 0)
    assert instr.raw_bytes == b"\xCB\x00"
    assert instr.size == 2


def test_decode_cb_swap_hl():
    instr = decode_instruction(b"\xCB\x36", 0)
    assert instr.mnemonic == "SWAP"
    assert instr.operands == ["(HL)"]


# --- Undefined opcodes ---


def test_decode_undefined_d3():
    instr = decode_instruction(b"\xD3", 0x100)
    assert instr.mnemonic == "DB"
    assert instr.operands == ["0xD3"]
    assert instr.size == 1
    assert instr.raw_bytes == b"\xD3"


def test_decode_undefined_dd():
    instr = decode_instruction(b"\xDD", 0x100)
    assert instr.mnemonic == "DB"
    assert instr.operands == ["0xDD"]


def test_decode_undefined_fd():
    instr = decode_instruction(b"\xFD", 0)
    assert instr.mnemonic == "DB"
    assert instr.operands == ["0xFD"]


# --- STOP ---


def test_decode_stop():
    instr = decode_instruction(b"\x10\x00", 0)
    assert instr.mnemonic == "STOP"
    assert instr.operands == []
    assert instr.size == 2
    assert instr.raw_bytes == b"\x10\x00"
