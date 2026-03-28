"""Tests for domain/bank_info.py — MBC detection and bank count."""

from __future__ import annotations

from blobert_mcp.domain.bank_info import calculate_bank_count, detect_mbc_type


# --- detect_mbc_type ---


def test_detect_mbc_type_rom_only():
    result = detect_mbc_type(0x00)
    assert result["name"] == "ROM ONLY"
    assert result["mbc"] is None
    assert result["ram"] is False
    assert result["battery"] is False


def test_detect_mbc_type_mbc1():
    result = detect_mbc_type(0x01)
    assert result["name"] == "MBC1"
    assert result["mbc"] == "MBC1"
    assert result["ram"] is False


def test_detect_mbc_type_mbc1_ram_battery():
    result = detect_mbc_type(0x03)
    assert result["name"] == "MBC1+RAM+BATTERY"
    assert result["mbc"] == "MBC1"
    assert result["ram"] is True
    assert result["battery"] is True


def test_detect_mbc_type_mbc3_timer_battery():
    result = detect_mbc_type(0x0F)
    assert result["mbc"] == "MBC3"
    assert result["battery"] is True
    assert result.get("timer") is True


def test_detect_mbc_type_mbc3_ram_battery():
    result = detect_mbc_type(0x13)
    assert result["name"] == "MBC3+RAM+BATTERY"
    assert result["mbc"] == "MBC3"
    assert result["ram"] is True
    assert result["battery"] is True


def test_detect_mbc_type_mbc5():
    result = detect_mbc_type(0x19)
    assert result["name"] == "MBC5"
    assert result["mbc"] == "MBC5"
    assert result["ram"] is False


def test_detect_mbc_type_mbc5_rumble():
    result = detect_mbc_type(0x1C)
    assert result["mbc"] == "MBC5"
    assert result.get("rumble") is True


def test_detect_mbc_type_unknown():
    result = detect_mbc_type(0xFF)
    assert result["name"] == "UNKNOWN"
    assert result["mbc"] is None


def test_detect_mbc_type_returns_copy():
    r1 = detect_mbc_type(0x00)
    r1["name"] = "MUTATED"
    r2 = detect_mbc_type(0x00)
    assert r2["name"] == "ROM ONLY"


# --- calculate_bank_count ---


def test_calculate_bank_count_32k():
    assert calculate_bank_count(0) == 2


def test_calculate_bank_count_64k():
    assert calculate_bank_count(1) == 4


def test_calculate_bank_count_128k():
    assert calculate_bank_count(2) == 8


def test_calculate_bank_count_1mb():
    assert calculate_bank_count(5) == 64


def test_calculate_bank_count_8mb():
    assert calculate_bank_count(8) == 512
