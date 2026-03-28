"""RST and interrupt vector definitions for Game Boy."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Vector:
    """A CPU vector: reset, interrupt, or entry point."""

    address: int
    label: str
    type: str


VECTORS: list[Vector] = [
    Vector(0x00, "RST 00", "rst"),
    Vector(0x08, "RST 08", "rst"),
    Vector(0x10, "RST 10", "rst"),
    Vector(0x18, "RST 18", "rst"),
    Vector(0x20, "RST 20", "rst"),
    Vector(0x28, "RST 28", "rst"),
    Vector(0x30, "RST 30", "rst"),
    Vector(0x38, "RST 38", "rst"),
    Vector(0x40, "VBlank", "interrupt"),
    Vector(0x48, "STAT", "interrupt"),
    Vector(0x50, "Timer", "interrupt"),
    Vector(0x58, "Serial", "interrupt"),
    Vector(0x60, "Joypad", "interrupt"),
    Vector(0x100, "Entry", "entry"),
]


def get_vectors() -> list[Vector]:
    """Return all Game Boy vectors."""
    return list(VECTORS)
