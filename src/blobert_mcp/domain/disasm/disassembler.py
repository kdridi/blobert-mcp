"""SM83 disassembly algorithms — pure functions, no project imports beyond decoder."""

from __future__ import annotations

from typing import Callable

from blobert_mcp.domain.disasm.decoder import Instruction, decode_instruction

_MEMORY_READER = Callable[[int, int], bytes]

_TERMINALS = frozenset({0xC9, 0xD9})  # RET, RETI
_JP_NN = 0xC3


def disassemble_range(
    memory_reader: _MEMORY_READER,
    address: int,
    length: int | None = None,
    end_address: int | None = None,
    bank: int | None = None,
) -> list[Instruction]:
    """Decode instructions from *address* until *length* bytes consumed, *end_address*
    reached, or the 256-instruction safety cap is hit.

    At least one of *length* or *end_address* must be provided.
    """
    if length is None and end_address is None:
        raise ValueError("At least one of 'length' or 'end_address' must be provided.")

    instructions: list[Instruction] = []
    start = address
    current = address

    while len(instructions) < 256:
        if length is not None and (current - start) >= length:
            break
        if end_address is not None and current >= end_address:
            break
        instr = decode_instruction(memory_reader(current, 3), current)
        instructions.append(instr)
        current += instr.size

    return instructions


def disassemble_function(
    memory_reader: _MEMORY_READER,
    entry_point: int,
    bank: int | None = None,
) -> dict:
    """Trace a function from *entry_point*, stopping at terminal instructions.

    Terminal conditions:
    - RET (0xC9) or RETI (0xD9): unconditional return
    - JP nn (0xC3) that jumps outside the traced range [entry_point, current_address]

    Safety cap: 1024 instructions. Returns {"instructions": list[Instruction], "size_bytes": int}.
    """
    instructions: list[Instruction] = []
    current = entry_point

    while len(instructions) < 1024:
        instr = decode_instruction(memory_reader(current, 3), current)
        instructions.append(instr)
        opcode = instr.raw_bytes[0]

        if opcode in _TERMINALS:
            break

        if opcode == _JP_NN:
            target = int(instr.operands[0], 16)
            if target < entry_point or target > current:
                break

        current += instr.size

    size_bytes = sum(i.size for i in instructions)
    return {"instructions": instructions, "size_bytes": size_bytes}


def disassemble_at_pc(
    memory_reader: _MEMORY_READER,
    pc: int,
    before: int = 5,
    after: int = 20,
) -> list[Instruction]:
    """Return instructions around *pc*.

    Tries to find *before* instructions before *pc* using a backward-scan heuristic:
    scan starting points from max(0, pc - before*3) to pc-1; prefer the closest start
    that decodes a sequence aligning exactly on *pc*. Falls back to pc - before if no
    alignment is found.

    Then decodes *after* instructions following *pc*.
    """
    pre_instructions = _scan_before(memory_reader, pc, before)

    # Decode pc instruction + after instructions
    post_instructions: list[Instruction] = []
    current = pc
    for _ in range(after + 1):  # +1 to include pc itself
        instr = decode_instruction(memory_reader(current, 3), current)
        post_instructions.append(instr)
        current += instr.size

    return pre_instructions + post_instructions


def _scan_before(
    memory_reader: _MEMORY_READER,
    pc: int,
    before: int,
) -> list[Instruction]:
    """Find up to *before* instructions immediately preceding *pc*."""
    if before == 0 or pc == 0:
        return []

    scan_start = max(0, pc - before * 3)
    best_pre: list[Instruction] | None = None

    for start in range(scan_start, pc):
        instrs: list[Instruction] = []
        addr = start
        while addr < pc:
            instr = decode_instruction(memory_reader(addr, 3), addr)
            instrs.append(instr)
            addr += instr.size
        if addr == pc:  # aligned — last valid alignment wins (closest to pc)
            best_pre = instrs[-before:] if len(instrs) >= before else instrs

    if best_pre is not None:
        return best_pre

    # Fallback: start from pc - before, decode whatever aligns
    fallback: list[Instruction] = []
    addr = max(0, pc - before)
    while addr < pc:
        instr = decode_instruction(memory_reader(addr, 3), addr)
        fallback.append(instr)
        addr += instr.size
    return fallback
