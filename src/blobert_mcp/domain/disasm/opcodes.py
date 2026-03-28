"""SM83 opcode tables for base and CB-prefixed instructions."""

from __future__ import annotations

from typing import NamedTuple


class OpcodeEntry(NamedTuple):
    """Single SM83 opcode descriptor."""

    mnemonic: str
    operand_types: tuple[str, ...]
    size: int


# Operand type token conventions:
#   "d8"      — 1 unsigned byte immediate
#   "d16"     — 2-byte little-endian unsigned immediate
#   "a16"     — 2-byte little-endian address immediate
#   "(a16)"   — 2-byte little-endian indirect address
#   "r8"      — 1-byte signed relative-jump offset (resolved to absolute by decoder)
#   "r8s"     — 1-byte signed immediate for SP arithmetic (formatted as +N/-N)
#   "SP+r8s"  — 1-byte signed immediate formatted as SP+N/SP-N
#   "(a8)"    — 1-byte high-page address (0xFF00 | byte)
#   "(C)"     — literal indirect via C register
#   All other tokens are register/condition-code literals passed through verbatim.

BASE_OPCODES: dict[int, OpcodeEntry] = {
    # --- Row 0x00 ---
    0x00: OpcodeEntry("NOP",  (),                1),
    0x01: OpcodeEntry("LD",   ("BC", "d16"),     3),
    0x02: OpcodeEntry("LD",   ("(BC)", "A"),     1),
    0x03: OpcodeEntry("INC",  ("BC",),           1),
    0x04: OpcodeEntry("INC",  ("B",),            1),
    0x05: OpcodeEntry("DEC",  ("B",),            1),
    0x06: OpcodeEntry("LD",   ("B", "d8"),       2),
    0x07: OpcodeEntry("RLCA", (),                1),
    0x08: OpcodeEntry("LD",   ("(a16)", "SP"),   3),
    0x09: OpcodeEntry("ADD",  ("HL", "BC"),      1),
    0x0A: OpcodeEntry("LD",   ("A", "(BC)"),     1),
    0x0B: OpcodeEntry("DEC",  ("BC",),           1),
    0x0C: OpcodeEntry("INC",  ("C",),            1),
    0x0D: OpcodeEntry("DEC",  ("C",),            1),
    0x0E: OpcodeEntry("LD",   ("C", "d8"),       2),
    0x0F: OpcodeEntry("RRCA", (),                1),
    # --- Row 0x10 ---
    0x10: OpcodeEntry("STOP", (),                2),
    0x11: OpcodeEntry("LD",   ("DE", "d16"),     3),
    0x12: OpcodeEntry("LD",   ("(DE)", "A"),     1),
    0x13: OpcodeEntry("INC",  ("DE",),           1),
    0x14: OpcodeEntry("INC",  ("D",),            1),
    0x15: OpcodeEntry("DEC",  ("D",),            1),
    0x16: OpcodeEntry("LD",   ("D", "d8"),       2),
    0x17: OpcodeEntry("RLA",  (),                1),
    0x18: OpcodeEntry("JR",   ("r8",),           2),
    0x19: OpcodeEntry("ADD",  ("HL", "DE"),      1),
    0x1A: OpcodeEntry("LD",   ("A", "(DE)"),     1),
    0x1B: OpcodeEntry("DEC",  ("DE",),           1),
    0x1C: OpcodeEntry("INC",  ("E",),            1),
    0x1D: OpcodeEntry("DEC",  ("E",),            1),
    0x1E: OpcodeEntry("LD",   ("E", "d8"),       2),
    0x1F: OpcodeEntry("RRA",  (),                1),
    # --- Row 0x20 ---
    0x20: OpcodeEntry("JR",   ("NZ", "r8"),      2),
    0x21: OpcodeEntry("LD",   ("HL", "d16"),     3),
    0x22: OpcodeEntry("LD",   ("(HL+)", "A"),    1),
    0x23: OpcodeEntry("INC",  ("HL",),           1),
    0x24: OpcodeEntry("INC",  ("H",),            1),
    0x25: OpcodeEntry("DEC",  ("H",),            1),
    0x26: OpcodeEntry("LD",   ("H", "d8"),       2),
    0x27: OpcodeEntry("DAA",  (),                1),
    0x28: OpcodeEntry("JR",   ("Z", "r8"),       2),
    0x29: OpcodeEntry("ADD",  ("HL", "HL"),      1),
    0x2A: OpcodeEntry("LD",   ("A", "(HL+)"),    1),
    0x2B: OpcodeEntry("DEC",  ("HL",),           1),
    0x2C: OpcodeEntry("INC",  ("L",),            1),
    0x2D: OpcodeEntry("DEC",  ("L",),            1),
    0x2E: OpcodeEntry("LD",   ("L", "d8"),       2),
    0x2F: OpcodeEntry("CPL",  (),                1),
    # --- Row 0x30 ---
    0x30: OpcodeEntry("JR",   ("NC", "r8"),      2),
    0x31: OpcodeEntry("LD",   ("SP", "d16"),     3),
    0x32: OpcodeEntry("LD",   ("(HL-)", "A"),    1),
    0x33: OpcodeEntry("INC",  ("SP",),           1),
    0x34: OpcodeEntry("INC",  ("(HL)",),         1),
    0x35: OpcodeEntry("DEC",  ("(HL)",),         1),
    0x36: OpcodeEntry("LD",   ("(HL)", "d8"),    2),
    0x37: OpcodeEntry("SCF",  (),                1),
    0x38: OpcodeEntry("JR",   ("C", "r8"),       2),
    0x39: OpcodeEntry("ADD",  ("HL", "SP"),      1),
    0x3A: OpcodeEntry("LD",   ("A", "(HL-)"),    1),
    0x3B: OpcodeEntry("DEC",  ("SP",),           1),
    0x3C: OpcodeEntry("INC",  ("A",),            1),
    0x3D: OpcodeEntry("DEC",  ("A",),            1),
    0x3E: OpcodeEntry("LD",   ("A", "d8"),       2),
    0x3F: OpcodeEntry("CCF",  (),                1),
    # --- Row 0x40: LD r,r (0x76 = HALT) ---
    0x40: OpcodeEntry("LD",   ("B", "B"),        1),
    0x41: OpcodeEntry("LD",   ("B", "C"),        1),
    0x42: OpcodeEntry("LD",   ("B", "D"),        1),
    0x43: OpcodeEntry("LD",   ("B", "E"),        1),
    0x44: OpcodeEntry("LD",   ("B", "H"),        1),
    0x45: OpcodeEntry("LD",   ("B", "L"),        1),
    0x46: OpcodeEntry("LD",   ("B", "(HL)"),     1),
    0x47: OpcodeEntry("LD",   ("B", "A"),        1),
    0x48: OpcodeEntry("LD",   ("C", "B"),        1),
    0x49: OpcodeEntry("LD",   ("C", "C"),        1),
    0x4A: OpcodeEntry("LD",   ("C", "D"),        1),
    0x4B: OpcodeEntry("LD",   ("C", "E"),        1),
    0x4C: OpcodeEntry("LD",   ("C", "H"),        1),
    0x4D: OpcodeEntry("LD",   ("C", "L"),        1),
    0x4E: OpcodeEntry("LD",   ("C", "(HL)"),     1),
    0x4F: OpcodeEntry("LD",   ("C", "A"),        1),
    # --- Row 0x50 ---
    0x50: OpcodeEntry("LD",   ("D", "B"),        1),
    0x51: OpcodeEntry("LD",   ("D", "C"),        1),
    0x52: OpcodeEntry("LD",   ("D", "D"),        1),
    0x53: OpcodeEntry("LD",   ("D", "E"),        1),
    0x54: OpcodeEntry("LD",   ("D", "H"),        1),
    0x55: OpcodeEntry("LD",   ("D", "L"),        1),
    0x56: OpcodeEntry("LD",   ("D", "(HL)"),     1),
    0x57: OpcodeEntry("LD",   ("D", "A"),        1),
    0x58: OpcodeEntry("LD",   ("E", "B"),        1),
    0x59: OpcodeEntry("LD",   ("E", "C"),        1),
    0x5A: OpcodeEntry("LD",   ("E", "D"),        1),
    0x5B: OpcodeEntry("LD",   ("E", "E"),        1),
    0x5C: OpcodeEntry("LD",   ("E", "H"),        1),
    0x5D: OpcodeEntry("LD",   ("E", "L"),        1),
    0x5E: OpcodeEntry("LD",   ("E", "(HL)"),     1),
    0x5F: OpcodeEntry("LD",   ("E", "A"),        1),
    # --- Row 0x60 ---
    0x60: OpcodeEntry("LD",   ("H", "B"),        1),
    0x61: OpcodeEntry("LD",   ("H", "C"),        1),
    0x62: OpcodeEntry("LD",   ("H", "D"),        1),
    0x63: OpcodeEntry("LD",   ("H", "E"),        1),
    0x64: OpcodeEntry("LD",   ("H", "H"),        1),
    0x65: OpcodeEntry("LD",   ("H", "L"),        1),
    0x66: OpcodeEntry("LD",   ("H", "(HL)"),     1),
    0x67: OpcodeEntry("LD",   ("H", "A"),        1),
    0x68: OpcodeEntry("LD",   ("L", "B"),        1),
    0x69: OpcodeEntry("LD",   ("L", "C"),        1),
    0x6A: OpcodeEntry("LD",   ("L", "D"),        1),
    0x6B: OpcodeEntry("LD",   ("L", "E"),        1),
    0x6C: OpcodeEntry("LD",   ("L", "H"),        1),
    0x6D: OpcodeEntry("LD",   ("L", "L"),        1),
    0x6E: OpcodeEntry("LD",   ("L", "(HL)"),     1),
    0x6F: OpcodeEntry("LD",   ("L", "A"),        1),
    # --- Row 0x70 ---
    0x70: OpcodeEntry("LD",   ("(HL)", "B"),     1),
    0x71: OpcodeEntry("LD",   ("(HL)", "C"),     1),
    0x72: OpcodeEntry("LD",   ("(HL)", "D"),     1),
    0x73: OpcodeEntry("LD",   ("(HL)", "E"),     1),
    0x74: OpcodeEntry("LD",   ("(HL)", "H"),     1),
    0x75: OpcodeEntry("LD",   ("(HL)", "L"),     1),
    0x76: OpcodeEntry("HALT", (),                1),
    0x77: OpcodeEntry("LD",   ("(HL)", "A"),     1),
    0x78: OpcodeEntry("LD",   ("A", "B"),        1),
    0x79: OpcodeEntry("LD",   ("A", "C"),        1),
    0x7A: OpcodeEntry("LD",   ("A", "D"),        1),
    0x7B: OpcodeEntry("LD",   ("A", "E"),        1),
    0x7C: OpcodeEntry("LD",   ("A", "H"),        1),
    0x7D: OpcodeEntry("LD",   ("A", "L"),        1),
    0x7E: OpcodeEntry("LD",   ("A", "(HL)"),     1),
    0x7F: OpcodeEntry("LD",   ("A", "A"),        1),
    # --- Row 0x80: ADD/ADC ---
    0x80: OpcodeEntry("ADD",  ("A", "B"),        1),
    0x81: OpcodeEntry("ADD",  ("A", "C"),        1),
    0x82: OpcodeEntry("ADD",  ("A", "D"),        1),
    0x83: OpcodeEntry("ADD",  ("A", "E"),        1),
    0x84: OpcodeEntry("ADD",  ("A", "H"),        1),
    0x85: OpcodeEntry("ADD",  ("A", "L"),        1),
    0x86: OpcodeEntry("ADD",  ("A", "(HL)"),     1),
    0x87: OpcodeEntry("ADD",  ("A", "A"),        1),
    0x88: OpcodeEntry("ADC",  ("A", "B"),        1),
    0x89: OpcodeEntry("ADC",  ("A", "C"),        1),
    0x8A: OpcodeEntry("ADC",  ("A", "D"),        1),
    0x8B: OpcodeEntry("ADC",  ("A", "E"),        1),
    0x8C: OpcodeEntry("ADC",  ("A", "H"),        1),
    0x8D: OpcodeEntry("ADC",  ("A", "L"),        1),
    0x8E: OpcodeEntry("ADC",  ("A", "(HL)"),     1),
    0x8F: OpcodeEntry("ADC",  ("A", "A"),        1),
    # --- Row 0x90: SUB/SBC ---
    0x90: OpcodeEntry("SUB",  ("B",),            1),
    0x91: OpcodeEntry("SUB",  ("C",),            1),
    0x92: OpcodeEntry("SUB",  ("D",),            1),
    0x93: OpcodeEntry("SUB",  ("E",),            1),
    0x94: OpcodeEntry("SUB",  ("H",),            1),
    0x95: OpcodeEntry("SUB",  ("L",),            1),
    0x96: OpcodeEntry("SUB",  ("(HL)",),         1),
    0x97: OpcodeEntry("SUB",  ("A",),            1),
    0x98: OpcodeEntry("SBC",  ("A", "B"),        1),
    0x99: OpcodeEntry("SBC",  ("A", "C"),        1),
    0x9A: OpcodeEntry("SBC",  ("A", "D"),        1),
    0x9B: OpcodeEntry("SBC",  ("A", "E"),        1),
    0x9C: OpcodeEntry("SBC",  ("A", "H"),        1),
    0x9D: OpcodeEntry("SBC",  ("A", "L"),        1),
    0x9E: OpcodeEntry("SBC",  ("A", "(HL)"),     1),
    0x9F: OpcodeEntry("SBC",  ("A", "A"),        1),
    # --- Row 0xA0: AND/XOR ---
    0xA0: OpcodeEntry("AND",  ("B",),            1),
    0xA1: OpcodeEntry("AND",  ("C",),            1),
    0xA2: OpcodeEntry("AND",  ("D",),            1),
    0xA3: OpcodeEntry("AND",  ("E",),            1),
    0xA4: OpcodeEntry("AND",  ("H",),            1),
    0xA5: OpcodeEntry("AND",  ("L",),            1),
    0xA6: OpcodeEntry("AND",  ("(HL)",),         1),
    0xA7: OpcodeEntry("AND",  ("A",),            1),
    0xA8: OpcodeEntry("XOR",  ("B",),            1),
    0xA9: OpcodeEntry("XOR",  ("C",),            1),
    0xAA: OpcodeEntry("XOR",  ("D",),            1),
    0xAB: OpcodeEntry("XOR",  ("E",),            1),
    0xAC: OpcodeEntry("XOR",  ("H",),            1),
    0xAD: OpcodeEntry("XOR",  ("L",),            1),
    0xAE: OpcodeEntry("XOR",  ("(HL)",),         1),
    0xAF: OpcodeEntry("XOR",  ("A",),            1),
    # --- Row 0xB0: OR/CP ---
    0xB0: OpcodeEntry("OR",   ("B",),            1),
    0xB1: OpcodeEntry("OR",   ("C",),            1),
    0xB2: OpcodeEntry("OR",   ("D",),            1),
    0xB3: OpcodeEntry("OR",   ("E",),            1),
    0xB4: OpcodeEntry("OR",   ("H",),            1),
    0xB5: OpcodeEntry("OR",   ("L",),            1),
    0xB6: OpcodeEntry("OR",   ("(HL)",),         1),
    0xB7: OpcodeEntry("OR",   ("A",),            1),
    0xB8: OpcodeEntry("CP",   ("B",),            1),
    0xB9: OpcodeEntry("CP",   ("C",),            1),
    0xBA: OpcodeEntry("CP",   ("D",),            1),
    0xBB: OpcodeEntry("CP",   ("E",),            1),
    0xBC: OpcodeEntry("CP",   ("H",),            1),
    0xBD: OpcodeEntry("CP",   ("L",),            1),
    0xBE: OpcodeEntry("CP",   ("(HL)",),         1),
    0xBF: OpcodeEntry("CP",   ("A",),            1),
    # --- Row 0xC0 ---
    0xC0: OpcodeEntry("RET",  ("NZ",),           1),
    0xC1: OpcodeEntry("POP",  ("BC",),           1),
    0xC2: OpcodeEntry("JP",   ("NZ", "a16"),     3),
    0xC3: OpcodeEntry("JP",   ("a16",),          3),
    0xC4: OpcodeEntry("CALL", ("NZ", "a16"),     3),
    0xC5: OpcodeEntry("PUSH", ("BC",),           1),
    0xC6: OpcodeEntry("ADD",  ("A", "d8"),       2),
    0xC7: OpcodeEntry("RST",  ("0x00",),         1),
    0xC8: OpcodeEntry("RET",  ("Z",),            1),
    0xC9: OpcodeEntry("RET",  (),                1),
    0xCA: OpcodeEntry("JP",   ("Z", "a16"),      3),
    0xCB: OpcodeEntry("PREFIX", (),              1),
    0xCC: OpcodeEntry("CALL", ("Z", "a16"),      3),
    0xCD: OpcodeEntry("CALL", ("a16",),          3),
    0xCE: OpcodeEntry("ADC",  ("A", "d8"),       2),
    0xCF: OpcodeEntry("RST",  ("0x08",),         1),
    # --- Row 0xD0 ---
    0xD0: OpcodeEntry("RET",  ("NC",),           1),
    0xD1: OpcodeEntry("POP",  ("DE",),           1),
    0xD2: OpcodeEntry("JP",   ("NC", "a16"),     3),
    0xD3: OpcodeEntry("DB",   (),                1),
    0xD4: OpcodeEntry("CALL", ("NC", "a16"),     3),
    0xD5: OpcodeEntry("PUSH", ("DE",),           1),
    0xD6: OpcodeEntry("SUB",  ("d8",),           2),
    0xD7: OpcodeEntry("RST",  ("0x10",),         1),
    0xD8: OpcodeEntry("RET",  ("C",),            1),
    0xD9: OpcodeEntry("RETI", (),                1),
    0xDA: OpcodeEntry("JP",   ("C", "a16"),      3),
    0xDB: OpcodeEntry("DB",   (),                1),
    0xDC: OpcodeEntry("CALL", ("C", "a16"),      3),
    0xDD: OpcodeEntry("DB",   (),                1),
    0xDE: OpcodeEntry("SBC",  ("A", "d8"),       2),
    0xDF: OpcodeEntry("RST",  ("0x18",),         1),
    # --- Row 0xE0 ---
    0xE0: OpcodeEntry("LDH",  ("(a8)", "A"),     2),
    0xE1: OpcodeEntry("POP",  ("HL",),           1),
    0xE2: OpcodeEntry("LD",   ("(C)", "A"),      1),
    0xE3: OpcodeEntry("DB",   (),                1),
    0xE4: OpcodeEntry("DB",   (),                1),
    0xE5: OpcodeEntry("PUSH", ("HL",),           1),
    0xE6: OpcodeEntry("AND",  ("d8",),           2),
    0xE7: OpcodeEntry("RST",  ("0x20",),         1),
    0xE8: OpcodeEntry("ADD",  ("SP", "r8s"),     2),
    0xE9: OpcodeEntry("JP",   ("HL",),           1),
    0xEA: OpcodeEntry("LD",   ("(a16)", "A"),    3),
    0xEB: OpcodeEntry("DB",   (),                1),
    0xEC: OpcodeEntry("DB",   (),                1),
    0xED: OpcodeEntry("DB",   (),                1),
    0xEE: OpcodeEntry("XOR",  ("d8",),           2),
    0xEF: OpcodeEntry("RST",  ("0x28",),         1),
    # --- Row 0xF0 ---
    0xF0: OpcodeEntry("LDH",  ("A", "(a8)"),     2),
    0xF1: OpcodeEntry("POP",  ("AF",),           1),
    0xF2: OpcodeEntry("LD",   ("A", "(C)"),      1),
    0xF3: OpcodeEntry("DI",   (),                1),
    0xF4: OpcodeEntry("DB",   (),                1),
    0xF5: OpcodeEntry("PUSH", ("AF",),           1),
    0xF6: OpcodeEntry("OR",   ("d8",),           2),
    0xF7: OpcodeEntry("RST",  ("0x30",),         1),
    0xF8: OpcodeEntry("LD",   ("HL", "SP+r8s"),  2),
    0xF9: OpcodeEntry("LD",   ("SP", "HL"),      1),
    0xFA: OpcodeEntry("LD",   ("A", "(a16)"),    3),
    0xFB: OpcodeEntry("EI",   (),                1),
    0xFC: OpcodeEntry("DB",   (),                1),
    0xFD: OpcodeEntry("DB",   (),                1),
    0xFE: OpcodeEntry("CP",   ("d8",),           2),
    0xFF: OpcodeEntry("RST",  ("0x38",),         1),
}

# CB opcode register encoding (bits 2-0)
_CB_REGS: tuple[str, ...] = ("B", "C", "D", "E", "H", "L", "(HL)", "A")

# CB rotate/shift operations (opcodes 0x00-0x3F), 8 ops × 8 regs
_CB_ROT_OPS: tuple[str, ...] = (
    "RLC", "RRC", "RL", "RR", "SLA", "SRA", "SWAP", "SRL",
)


def _build_cb_table() -> dict[int, OpcodeEntry]:
    """Generate all 256 CB-prefixed opcode entries."""
    table: dict[int, OpcodeEntry] = {}

    # 0x00-0x3F: rotate/shift ops
    for op_idx, mnemonic in enumerate(_CB_ROT_OPS):
        for reg_idx, reg in enumerate(_CB_REGS):
            opcode = op_idx * 8 + reg_idx
            table[opcode] = OpcodeEntry(mnemonic, (reg,), 2)

    # 0x40-0xFF: BIT, RES, SET — each covers 8 bit-values × 8 regs = 64 opcodes
    for grp_idx, mnemonic in enumerate(("BIT", "RES", "SET")):
        base = 0x40 + grp_idx * 0x40
        for bit in range(8):
            for reg_idx, reg in enumerate(_CB_REGS):
                opcode = base + bit * 8 + reg_idx
                table[opcode] = OpcodeEntry(mnemonic, (str(bit), reg), 2)

    return table


CB_OPCODES: dict[int, OpcodeEntry] = _build_cb_table()
