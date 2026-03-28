"""Tests for domain/memory_map.py — static Game Boy memory layout."""

from __future__ import annotations

import pytest

from blobert_mcp.domain.memory_map import REGIONS, get_regions


def test_regions_count():
    assert len(REGIONS) == 12


def test_regions_cover_full_address_space():
    assert REGIONS[0].start == 0x0000
    assert REGIONS[-1].end == 0xFFFF


def test_region_sizes_match_bounds():
    for region in REGIONS:
        assert region.end - region.start + 1 == region.size, (
            f"{region.name}: end - start + 1 != size"
        )


def test_rom0_region():
    rom0 = REGIONS[0]
    assert rom0.name == "ROM0"
    assert rom0.start == 0x0000
    assert rom0.end == 0x3FFF
    assert rom0.size == 0x4000
    assert rom0.access_type == "R"


def test_romx_region():
    romx = REGIONS[1]
    assert romx.name == "ROMX"
    assert romx.start == 0x4000
    assert romx.end == 0x7FFF
    assert romx.access_type == "R/banked"


def test_vram_region():
    vram = REGIONS[2]
    assert vram.name == "VRAM"
    assert vram.start == 0x8000
    assert vram.end == 0x9FFF
    assert vram.size == 0x2000


def test_sram_region():
    sram = REGIONS[3]
    assert sram.name == "SRAM"
    assert sram.start == 0xA000
    assert sram.end == 0xBFFF
    assert sram.access_type == "RW/banked"


def test_ie_register_single_byte():
    ie = REGIONS[-1]
    assert ie.name == "IE"
    assert ie.start == 0xFFFF
    assert ie.end == 0xFFFF
    assert ie.size == 1


def test_unusable_region_access_type():
    unusable = [r for r in REGIONS if r.name == "Unusable"][0]
    assert unusable.access_type == "-"


def test_get_regions_returns_copy():
    r1 = get_regions()
    r2 = get_regions()
    assert r1 == r2
    assert r1 is not r2


def test_regions_are_frozen():
    with pytest.raises(AttributeError):
        REGIONS[0].name = "MODIFIED"  # type: ignore[misc]
