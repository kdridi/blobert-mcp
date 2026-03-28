"""SM83 instruction decoder."""

from __future__ import annotations

from dataclasses import dataclass, field

from blobert_mcp.domain.disasm.opcodes import BASE_OPCODES, CB_OPCODES


@dataclass
class Instruction:
    """A single decoded SM83 instruction."""

    address: int
    raw_bytes: bytes
    mnemonic: str
    operands: list[str]
    size: int


def decode_instruction(data: bytes, address: int) -> Instruction:
    """Decode one SM83 instruction from *data* at *address*.

    *data* must contain at least as many bytes as the instruction size.
    For CB-prefixed instructions *data* must be at least 2 bytes.
    """
    opcode = data[0]

    # CB-prefix dispatch: 0xCB + next byte selects CB opcode.
    if opcode == 0xCB:
        cb_opcode = data[1]
        entry = CB_OPCODES[cb_opcode]
        # All CB operand_types are register/bit-number literals — pass through.
        return Instruction(
            address=address,
            raw_bytes=bytes(data[0:2]),
            mnemonic=entry.mnemonic,
            operands=list(entry.operand_types),
            size=2,
        )

    entry = BASE_OPCODES[opcode]

    # Undefined opcode: decode as raw data byte.
    if entry.mnemonic == "DB":
        return Instruction(
            address=address,
            raw_bytes=bytes(data[0:1]),
            mnemonic="DB",
            operands=[f"0x{opcode:02X}"],
            size=1,
        )

    operands: list[str] = []
    cursor = 1  # byte index into *data*, after the opcode byte

    for token in entry.operand_types:
        if token == "d8":
            v = data[cursor]
            operands.append(f"0x{v:02X}")
            cursor += 1
        elif token in ("d16", "a16"):
            v = data[cursor] | (data[cursor + 1] << 8)
            operands.append(f"0x{v:04X}")
            cursor += 2
        elif token == "(a16)":
            v = data[cursor] | (data[cursor + 1] << 8)
            operands.append(f"(0x{v:04X})")
            cursor += 2
        elif token == "r8":
            # Relative jump: resolve signed offset to absolute address.
            raw = data[cursor]
            offset = raw if raw < 128 else raw - 256
            target = (address + 2 + offset) & 0xFFFF
            operands.append(f"0x{target:04X}")
            cursor += 1
        elif token == "r8s":
            # Signed immediate for SP arithmetic (ADD SP,r8s).
            raw = data[cursor]
            n = raw if raw < 128 else raw - 256
            operands.append(f"+{n}" if n >= 0 else str(n))
            cursor += 1
        elif token == "SP+r8s":
            # Signed immediate for LD HL,SP+r8s.
            raw = data[cursor]
            n = raw if raw < 128 else raw - 256
            operands.append(f"SP+{n}" if n >= 0 else f"SP{n}")
            cursor += 1
        elif token == "(a8)":
            v = data[cursor]
            operands.append(f"(0xFF{v:02X})")
            cursor += 1
        elif token == "(C)":
            operands.append("(C)")
        else:
            # Register name, condition code, RST target, or other literal.
            operands.append(token)

    return Instruction(
        address=address,
        raw_bytes=bytes(data[0:entry.size]),
        mnemonic=entry.mnemonic,
        operands=operands,
        size=entry.size,
    )
