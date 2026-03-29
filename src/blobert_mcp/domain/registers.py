"""CPU register formatting for the Game Boy SM83 processor.

No project imports; stdlib only.
"""

from __future__ import annotations


def format_registers(
    a: int,
    b: int,
    c: int,
    d: int,
    e: int,
    f: int,
    h: int,
    l: int,  # noqa: E741
    sp: int,
    pc: int,
) -> dict:
    """Return a spec-compliant dict of all SM83 CPU registers.

    8-bit registers are formatted as "0xAB"; 16-bit as "0xABCD".
    Composite registers are computed from their component halves.
    Flags are extracted from the upper nibble of F as booleans.
    """
    return {
        "A": f"0x{a:02X}",
        "B": f"0x{b:02X}",
        "C": f"0x{c:02X}",
        "D": f"0x{d:02X}",
        "E": f"0x{e:02X}",
        "F": f"0x{f:02X}",
        "H": f"0x{h:02X}",
        "L": f"0x{l:02X}",
        "AF": f"0x{(a << 8) | f:04X}",
        "BC": f"0x{(b << 8) | c:04X}",
        "DE": f"0x{(d << 8) | e:04X}",
        "HL": f"0x{(h << 8) | l:04X}",
        "SP": f"0x{sp:04X}",
        "PC": f"0x{pc:04X}",
        "flags": {
            "Z": bool(f & 0x80),
            "N": bool(f & 0x40),
            "H": bool(f & 0x20),
            "C": bool(f & 0x10),
        },
    }
