"""Tests for domain/interrupts.py — IE/IF flag parsing."""

from __future__ import annotations

from blobert_mcp.domain.interrupts import parse_interrupt_flags


def test_parse_all_disabled():
    result = parse_interrupt_flags(0x00, 0x00)
    for name in ("vblank", "stat", "timer", "serial", "joypad"):
        assert result["interrupts"][name]["enabled"] is False
        assert result["interrupts"][name]["requested"] is False


def test_parse_all_enabled_none_requested():
    result = parse_interrupt_flags(0x1F, 0x00)
    for name in ("vblank", "stat", "timer", "serial", "joypad"):
        assert result["interrupts"][name]["enabled"] is True
        assert result["interrupts"][name]["requested"] is False


def test_parse_none_enabled_all_requested():
    result = parse_interrupt_flags(0x00, 0x1F)
    for name in ("vblank", "stat", "timer", "serial", "joypad"):
        assert result["interrupts"][name]["enabled"] is False
        assert result["interrupts"][name]["requested"] is True


def test_parse_vblank_only_enabled():
    result = parse_interrupt_flags(0x01, 0x00)
    assert result["interrupts"]["vblank"]["enabled"] is True
    assert result["interrupts"]["stat"]["enabled"] is False
    assert result["interrupts"]["timer"]["enabled"] is False
    assert result["interrupts"]["serial"]["enabled"] is False
    assert result["interrupts"]["joypad"]["enabled"] is False


def test_parse_timer_requested():
    result = parse_interrupt_flags(0x00, 0x04)
    assert result["interrupts"]["timer"]["requested"] is True
    assert result["interrupts"]["vblank"]["requested"] is False


def test_parse_mixed_flags():
    # IE=0x15 -> vblank(1), stat(0), timer(1), serial(0), joypad(1)
    # IF=0x0A -> vblank(0), stat(1), timer(0), serial(1), joypad(0)
    result = parse_interrupt_flags(0x15, 0x0A)
    assert result["interrupts"]["vblank"] == {
        "enabled": True, "requested": False,
    }
    assert result["interrupts"]["stat"] == {
        "enabled": False, "requested": True,
    }
    assert result["interrupts"]["timer"] == {
        "enabled": True, "requested": False,
    }
    assert result["interrupts"]["serial"] == {
        "enabled": False, "requested": True,
    }
    assert result["interrupts"]["joypad"] == {
        "enabled": True, "requested": False,
    }


def test_parse_raw_values_preserved():
    result = parse_interrupt_flags(0xAB, 0xCD)
    assert result["ie_raw"] == 0xAB
    assert result["if_raw"] == 0xCD


def test_parse_single_bit_joypad():
    result = parse_interrupt_flags(0x10, 0x10)
    assert result["interrupts"]["joypad"]["enabled"] is True
    assert result["interrupts"]["joypad"]["requested"] is True
    assert result["interrupts"]["vblank"]["enabled"] is False
