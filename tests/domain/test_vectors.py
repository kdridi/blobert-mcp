"""Tests for domain/vectors.py — RST and interrupt vector definitions."""

from __future__ import annotations

import pytest

from blobert_mcp.domain.vectors import VECTORS, Vector, get_vectors


def test_vectors_count():
    assert len(VECTORS) == 14


def test_rst_vector_addresses():
    rst = [v for v in VECTORS if v.type == "rst"]
    assert [v.address for v in rst] == [
        0x00, 0x08, 0x10, 0x18, 0x20, 0x28, 0x30, 0x38,
    ]


def test_rst_vectors_count():
    rst = [v for v in VECTORS if v.type == "rst"]
    assert len(rst) == 8


def test_interrupt_vector_addresses():
    interrupts = [v for v in VECTORS if v.type == "interrupt"]
    assert [v.address for v in interrupts] == [0x40, 0x48, 0x50, 0x58, 0x60]


def test_interrupt_vector_labels():
    interrupts = [v for v in VECTORS if v.type == "interrupt"]
    assert [v.label for v in interrupts] == [
        "VBlank", "STAT", "Timer", "Serial", "Joypad",
    ]


def test_entry_point():
    entry = [v for v in VECTORS if v.type == "entry"]
    assert len(entry) == 1
    assert entry[0].address == 0x100
    assert entry[0].label == "Entry"


def test_get_vectors_returns_copy():
    v1 = get_vectors()
    v2 = get_vectors()
    assert v1 == v2
    assert v1 is not v2


def test_vectors_are_frozen():
    with pytest.raises(AttributeError):
        VECTORS[0].address = 0xFF  # type: ignore[misc]
