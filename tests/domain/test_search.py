"""TDD tests for domain/search.py — byte pattern search and string detection."""

from __future__ import annotations

import pytest

from blobert_mcp.domain.search import match_byte_pattern

# ---------------------------------------------------------------------------
# match_byte_pattern
# ---------------------------------------------------------------------------


class TestMatchBytePattern:
    """Tests for hex byte pattern matching with wildcard support."""

    # --- Happy paths ---

    def test_single_exact_byte(self):
        assert match_byte_pattern(b"\xcd", "CD") == [0]

    def test_multi_byte_exact_match(self):
        data = b"\x00\xcd\x00\x40\x00"
        assert match_byte_pattern(data, "CD 00 40") == [1]

    def test_wildcard_matches_any_byte(self):
        data = b"\xcd\xff\x40"
        assert match_byte_pattern(data, "CD ?? 40") == [0]

    def test_all_wildcards(self):
        data = b"\xaa\xbb\xcc"
        # "?? ??" matches at positions 0 and 1
        assert match_byte_pattern(data, "?? ??") == [0, 1]

    def test_pattern_at_start(self):
        data = b"\xff\x00\x00\x00"
        assert match_byte_pattern(data, "FF") == [0]

    def test_pattern_at_end(self):
        data = b"\x00\x00\x00\xff"
        assert match_byte_pattern(data, "FF") == [3]

    def test_case_insensitive_pattern(self):
        data = b"\xab\xcd"
        assert match_byte_pattern(data, "ab cd") == [0]

    # --- Multiple matches ---

    def test_multiple_matches(self):
        data = b"\xcd\x00\xcd\x00\xcd"
        assert match_byte_pattern(data, "CD") == [0, 2, 4]

    def test_overlapping_matches(self):
        data = b"\xaa\xaa\xaa"
        assert match_byte_pattern(data, "AA AA") == [0, 1]

    # --- Not found ---

    def test_not_found(self):
        data = b"\x00\x00\x00"
        assert match_byte_pattern(data, "FF") == []

    # --- Range limiting ---

    def test_start_skips_early_bytes(self):
        data = b"\xff\x00\xff"
        assert match_byte_pattern(data, "FF", start=1) == [2]

    def test_end_stops_search(self):
        data = b"\xff\x00\xff"
        assert match_byte_pattern(data, "FF", end=2) == [0]

    def test_start_and_end(self):
        data = b"\xff\x00\xff\x00\xff"
        assert match_byte_pattern(data, "FF", start=1, end=4) == [2]

    def test_end_none_searches_to_end(self):
        data = b"\x00\x00\xff"
        assert match_byte_pattern(data, "FF", end=None) == [2]

    def test_start_equals_end_returns_empty(self):
        data = b"\xff\xff"
        assert match_byte_pattern(data, "FF", start=1, end=1) == []

    def test_start_beyond_data_returns_empty(self):
        data = b"\xff"
        assert match_byte_pattern(data, "FF", start=10) == []

    # --- Max results ---

    def test_max_results_caps_output(self):
        data = bytes([0xFF] * 150)
        results = match_byte_pattern(data, "FF", max_results=100)
        assert len(results) == 100

    def test_max_results_custom(self):
        data = bytes([0xFF] * 10)
        results = match_byte_pattern(data, "FF", max_results=5)
        assert len(results) == 5

    # --- Edge cases ---

    def test_empty_data_returns_empty(self):
        assert match_byte_pattern(b"", "FF") == []

    def test_pattern_longer_than_data(self):
        assert match_byte_pattern(b"\xff", "FF FF FF FF") == []

    # --- Validation errors ---

    def test_empty_pattern_raises(self):
        with pytest.raises(ValueError, match="[Ee]mpty"):
            match_byte_pattern(b"\x00", "")

    def test_whitespace_only_pattern_raises(self):
        with pytest.raises(ValueError, match="[Ee]mpty"):
            match_byte_pattern(b"\x00", "   ")

    def test_invalid_hex_raises(self):
        with pytest.raises(ValueError, match="[Ii]nvalid"):
            match_byte_pattern(b"\x00", "GG")

    def test_odd_length_token_raises(self):
        with pytest.raises(ValueError, match="[Ii]nvalid"):
            match_byte_pattern(b"\x00", "F")

    def test_negative_start_raises(self):
        with pytest.raises(ValueError, match="[Nn]egative"):
            match_byte_pattern(b"\x00", "FF", start=-1)
