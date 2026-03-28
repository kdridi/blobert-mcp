"""Interrupt flag interpretation for Game Boy IE/IF registers."""

from __future__ import annotations

_INTERRUPT_NAMES: list[str] = ["vblank", "stat", "timer", "serial", "joypad"]


def parse_interrupt_flags(ie_byte: int, if_byte: int) -> dict:
    """Parse IE and IF register bytes into individual interrupt states."""
    interrupts = {}
    for bit, name in enumerate(_INTERRUPT_NAMES):
        interrupts[name] = {
            "enabled": bool(ie_byte & (1 << bit)),
            "requested": bool(if_byte & (1 << bit)),
        }
    return {
        "ie_raw": ie_byte,
        "if_raw": if_byte,
        "interrupts": interrupts,
    }
