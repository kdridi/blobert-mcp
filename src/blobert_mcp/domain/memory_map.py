"""Static Game Boy memory layout definitions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MemoryRegion:
    """A contiguous region of the Game Boy address space."""

    name: str
    start: int
    end: int
    size: int
    access_type: str


REGIONS: list[MemoryRegion] = [
    MemoryRegion("ROM0", 0x0000, 0x3FFF, 0x4000, "R"),
    MemoryRegion("ROMX", 0x4000, 0x7FFF, 0x4000, "R/banked"),
    MemoryRegion("VRAM", 0x8000, 0x9FFF, 0x2000, "RW"),
    MemoryRegion("SRAM", 0xA000, 0xBFFF, 0x2000, "RW/banked"),
    MemoryRegion("WRAM0", 0xC000, 0xCFFF, 0x1000, "RW"),
    MemoryRegion("WRAMX", 0xD000, 0xDFFF, 0x1000, "RW/banked"),
    MemoryRegion("Echo", 0xE000, 0xFDFF, 0x1E00, "R"),
    MemoryRegion("OAM", 0xFE00, 0xFE9F, 0x00A0, "RW"),
    MemoryRegion("Unusable", 0xFEA0, 0xFEFF, 0x0060, "-"),
    MemoryRegion("I/O", 0xFF00, 0xFF7F, 0x0080, "RW"),
    MemoryRegion("HRAM", 0xFF80, 0xFFFE, 0x007F, "RW"),
    MemoryRegion("IE", 0xFFFF, 0xFFFF, 0x0001, "RW"),
]


DEFAULT_DIFF_REGION_NAMES: tuple[str, ...] = ("WRAM0", "WRAMX", "HRAM")


def get_regions() -> list[MemoryRegion]:
    """Return all Game Boy memory regions."""
    return list(REGIONS)


def resolve_regions(names: list[str]) -> list[MemoryRegion]:
    """Resolve region name strings to MemoryRegion objects.

    Supports exact match (case-insensitive) and prefix match.
    If a name exactly matches a region, only that region is returned.
    If no exact match, all regions whose name starts with the input are returned.
    Raises ValueError for unknown names or empty list.
    Results are deduplicated and sorted by start address.
    """
    if not names:
        msg = "Region names list must not be empty"
        raise ValueError(msg)
    seen: set[str] = set()
    matched: list[MemoryRegion] = []
    for name in names:
        upper = name.strip().upper()
        exact = [r for r in REGIONS if r.name.upper() == upper]
        if exact:
            for r in exact:
                if r.name not in seen:
                    seen.add(r.name)
                    matched.append(r)
            continue
        prefix = [r for r in REGIONS if r.name.upper().startswith(upper)]
        if prefix:
            for r in prefix:
                if r.name not in seen:
                    seen.add(r.name)
                    matched.append(r)
            continue
        msg = f"Unknown region name: {name!r}"
        raise ValueError(msg)
    return sorted(matched, key=lambda r: r.start)
