"""Tests for domain/disasm/opcodes.py — SM83 opcode table completeness."""

from __future__ import annotations

from blobert_mcp.domain.disasm.opcodes import BASE_OPCODES, CB_OPCODES, OpcodeEntry

# --- Completeness ---


def test_base_opcodes_complete():
    assert len(BASE_OPCODES) == 256


def test_cb_opcodes_complete():
    assert len(CB_OPCODES) == 256


def test_base_opcodes_keys_range():
    assert set(BASE_OPCODES.keys()) == set(range(256))


def test_cb_opcodes_keys_range():
    assert set(CB_OPCODES.keys()) == set(range(256))


def test_cb_opcodes_all_size_2():
    for opcode, entry in CB_OPCODES.items():
        assert entry.size == 2, f"CB 0x{opcode:02X} has size {entry.size}, expected 2"


def test_base_opcodes_all_sizes_valid():
    for opcode, entry in BASE_OPCODES.items():
        assert entry.size in (1, 2, 3), (
            f"BASE 0x{opcode:02X} has invalid size {entry.size}"
        )


# --- OpcodeEntry is a NamedTuple ---


def test_opcode_entry_fields():
    e = OpcodeEntry("NOP", (), 1)
    assert e.mnemonic == "NOP"
    assert e.operand_types == ()
    assert e.size == 1


# --- Base opcode spot-checks per category ---


def test_nop():
    e = BASE_OPCODES[0x00]
    assert e.mnemonic == "NOP"
    assert e.operand_types == ()
    assert e.size == 1


def test_ld_bc_d16():
    e = BASE_OPCODES[0x01]
    assert e.mnemonic == "LD"
    assert e.operand_types == ("BC", "d16")
    assert e.size == 3


def test_ld_a_d8():
    e = BASE_OPCODES[0x3E]
    assert e.mnemonic == "LD"
    assert e.operand_types == ("A", "d8")
    assert e.size == 2


def test_ld_b_b():
    e = BASE_OPCODES[0x40]
    assert e.mnemonic == "LD"
    assert e.operand_types == ("B", "B")
    assert e.size == 1


def test_halt():
    e = BASE_OPCODES[0x76]
    assert e.mnemonic == "HALT"
    assert e.operand_types == ()
    assert e.size == 1


def test_jr_unconditional():
    e = BASE_OPCODES[0x18]
    assert e.mnemonic == "JR"
    assert e.operand_types == ("r8",)
    assert e.size == 2


def test_jr_nz():
    e = BASE_OPCODES[0x20]
    assert e.mnemonic == "JR"
    assert e.operand_types == ("NZ", "r8")
    assert e.size == 2


def test_jr_z():
    e = BASE_OPCODES[0x28]
    assert e.mnemonic == "JR"
    assert e.operand_types == ("Z", "r8")
    assert e.size == 2


def test_jr_nc():
    e = BASE_OPCODES[0x30]
    assert e.mnemonic == "JR"
    assert e.operand_types == ("NC", "r8")
    assert e.size == 2


def test_jr_c():
    e = BASE_OPCODES[0x38]
    assert e.mnemonic == "JR"
    assert e.operand_types == ("C", "r8")
    assert e.size == 2


def test_jp_a16():
    e = BASE_OPCODES[0xC3]
    assert e.mnemonic == "JP"
    assert e.operand_types == ("a16",)
    assert e.size == 3


def test_call_a16():
    e = BASE_OPCODES[0xCD]
    assert e.mnemonic == "CALL"
    assert e.operand_types == ("a16",)
    assert e.size == 3


def test_ret():
    e = BASE_OPCODES[0xC9]
    assert e.mnemonic == "RET"
    assert e.operand_types == ()
    assert e.size == 1


def test_cb_prefix_entry():
    e = BASE_OPCODES[0xCB]
    assert e.mnemonic == "PREFIX"
    assert e.size == 1


def test_undefined_opcode_d3():
    e = BASE_OPCODES[0xD3]
    assert e.mnemonic == "DB"
    assert e.size == 1


def test_undefined_opcode_fd():
    e = BASE_OPCODES[0xFD]
    assert e.mnemonic == "DB"
    assert e.size == 1


def test_add_sp_r8s():
    e = BASE_OPCODES[0xE8]
    assert e.mnemonic == "ADD"
    assert e.operand_types == ("SP", "r8s")
    assert e.size == 2


def test_ld_hl_sp_r8s():
    e = BASE_OPCODES[0xF8]
    assert e.mnemonic == "LD"
    assert e.operand_types == ("HL", "SP+r8s")
    assert e.size == 2


def test_ldh_write():
    e = BASE_OPCODES[0xE0]
    assert e.mnemonic == "LDH"
    assert e.operand_types == ("(a8)", "A")
    assert e.size == 2


def test_ldh_read():
    e = BASE_OPCODES[0xF0]
    assert e.mnemonic == "LDH"
    assert e.operand_types == ("A", "(a8)")
    assert e.size == 2


def test_ld_indirect_c_a():
    e = BASE_OPCODES[0xE2]
    assert e.mnemonic == "LD"
    assert e.operand_types == ("(C)", "A")
    assert e.size == 1


def test_ld_a_indirect_c():
    e = BASE_OPCODES[0xF2]
    assert e.mnemonic == "LD"
    assert e.operand_types == ("A", "(C)")
    assert e.size == 1


def test_ld_a16_sp():
    e = BASE_OPCODES[0x08]
    assert e.mnemonic == "LD"
    assert e.operand_types == ("(a16)", "SP")
    assert e.size == 3


def test_ld_indirect_a16_a():
    e = BASE_OPCODES[0xEA]
    assert e.mnemonic == "LD"
    assert e.operand_types == ("(a16)", "A")
    assert e.size == 3


def test_ld_a_indirect_a16():
    e = BASE_OPCODES[0xFA]
    assert e.mnemonic == "LD"
    assert e.operand_types == ("A", "(a16)")
    assert e.size == 3


def test_stop():
    e = BASE_OPCODES[0x10]
    assert e.mnemonic == "STOP"
    assert e.operand_types == ()
    assert e.size == 2


def test_add_a_b():
    e = BASE_OPCODES[0x80]
    assert e.mnemonic == "ADD"
    assert e.operand_types == ("A", "B")
    assert e.size == 1


def test_sub_b():
    e = BASE_OPCODES[0x90]
    assert e.mnemonic == "SUB"
    assert e.operand_types == ("B",)
    assert e.size == 1


def test_and_b():
    e = BASE_OPCODES[0xA0]
    assert e.mnemonic == "AND"
    assert e.operand_types == ("B",)
    assert e.size == 1


def test_xor_a():
    e = BASE_OPCODES[0xAF]
    assert e.mnemonic == "XOR"
    assert e.operand_types == ("A",)
    assert e.size == 1


def test_or_b():
    e = BASE_OPCODES[0xB0]
    assert e.mnemonic == "OR"
    assert e.operand_types == ("B",)
    assert e.size == 1


def test_cp_b():
    e = BASE_OPCODES[0xB8]
    assert e.mnemonic == "CP"
    assert e.operand_types == ("B",)
    assert e.size == 1


# --- CB opcode spot-checks ---


def test_cb_rlc_b():
    e = CB_OPCODES[0x00]
    assert e.mnemonic == "RLC"
    assert e.operand_types == ("B",)
    assert e.size == 2


def test_cb_rlc_a():
    e = CB_OPCODES[0x07]
    assert e.mnemonic == "RLC"
    assert e.operand_types == ("A",)
    assert e.size == 2


def test_cb_swap_a():
    e = CB_OPCODES[0x37]
    assert e.mnemonic == "SWAP"
    assert e.operand_types == ("A",)
    assert e.size == 2


def test_cb_bit_0_b():
    e = CB_OPCODES[0x40]
    assert e.mnemonic == "BIT"
    assert e.operand_types == ("0", "B")
    assert e.size == 2


def test_cb_bit_7_a():
    e = CB_OPCODES[0x7F]
    assert e.mnemonic == "BIT"
    assert e.operand_types == ("7", "A")
    assert e.size == 2


def test_cb_res_0_b():
    e = CB_OPCODES[0x80]
    assert e.mnemonic == "RES"
    assert e.operand_types == ("0", "B")
    assert e.size == 2


def test_cb_set_0_b():
    e = CB_OPCODES[0xC0]
    assert e.mnemonic == "SET"
    assert e.operand_types == ("0", "B")
    assert e.size == 2


def test_cb_set_7_a():
    e = CB_OPCODES[0xFF]
    assert e.mnemonic == "SET"
    assert e.operand_types == ("7", "A")
    assert e.size == 2
