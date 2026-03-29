"""TDD tests for domain/search.py — byte pattern search and string detection."""

from __future__ import annotations

import pytest

from blobert_mcp.domain.search import (
    GB_CUSTOM_ENCODING,
    find_text_strings,
    match_byte_pattern,
)

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


# ---------------------------------------------------------------------------
# GB_CUSTOM_ENCODING
# ---------------------------------------------------------------------------


class TestGBCustomEncoding:
    """Tests for the default Game Boy character encoding table."""

    def test_encoding_is_dict(self):
        assert isinstance(GB_CUSTOM_ENCODING, dict)

    def test_uppercase_a(self):
        assert GB_CUSTOM_ENCODING[0x80] == "A"

    def test_uppercase_z(self):
        assert GB_CUSTOM_ENCODING[0x99] == "Z"

    def test_lowercase_a(self):
        assert GB_CUSTOM_ENCODING[0xA0] == "a"

    def test_lowercase_z(self):
        assert GB_CUSTOM_ENCODING[0xB9] == "z"

    def test_digit_0(self):
        assert GB_CUSTOM_ENCODING[0xBA] == "0"

    def test_digit_9(self):
        assert GB_CUSTOM_ENCODING[0xC3] == "9"

    def test_space(self):
        assert GB_CUSTOM_ENCODING[0x7F] == " "

    def test_has_punctuation(self):
        # At least some common punctuation is mapped
        values = set(GB_CUSTOM_ENCODING.values())
        assert "!" in values
        assert "." in values


# ---------------------------------------------------------------------------
# find_text_strings
# ---------------------------------------------------------------------------


class TestFindTextStrings:
    """Tests for text string detection in ROM data."""

    # --- ASCII happy paths ---

    def test_ascii_finds_string(self):
        data = b"\x00HELLO\x00"
        result = find_text_strings(data, min_length=4, encoding="ascii")
        assert result == [(1, "HELLO")]

    def test_ascii_multiple_strings(self):
        data = b"\x00HELLO\x00WORLD\x00"
        result = find_text_strings(data, min_length=4, encoding="ascii")
        assert result == [(1, "HELLO"), (7, "WORLD")]

    def test_ascii_min_length_filters(self):
        data = b"\x00AB\x00"
        result = find_text_strings(data, min_length=4, encoding="ascii")
        assert result == []

    def test_ascii_min_length_includes(self):
        data = b"\x00ABCD\x00"
        result = find_text_strings(data, min_length=4, encoding="ascii")
        assert result == [(1, "ABCD")]

    def test_ascii_printable_range(self):
        # Space (0x20) through tilde (0x7E) are printable ASCII
        data = bytes([0x20, 0x41, 0x7E, 0x42])
        result = find_text_strings(data, min_length=4, encoding="ascii")
        assert len(result) == 1
        assert result[0] == (0, " A~B")

    def test_ascii_non_printable_terminates(self):
        data = b"ABCD\x00EFGH"
        result = find_text_strings(data, min_length=4, encoding="ascii")
        assert result == [(0, "ABCD"), (5, "EFGH")]

    # --- GB custom happy paths ---

    def test_gb_custom_uppercase(self):
        data = bytes([0x80, 0x81, 0x82, 0x83])
        result = find_text_strings(data, min_length=4, encoding="gb_custom")
        assert result == [(0, "ABCD")]

    def test_gb_custom_lowercase(self):
        data = bytes([0xA0, 0xA1, 0xA2, 0xA3])
        result = find_text_strings(data, min_length=4, encoding="gb_custom")
        assert result == [(0, "abcd")]

    def test_gb_custom_digits(self):
        data = bytes([0xBA, 0xBB, 0xBC, 0xBD])
        result = find_text_strings(data, min_length=4, encoding="gb_custom")
        assert result == [(0, "0123")]

    def test_gb_custom_with_space(self):
        data = bytes([0x80, 0x81, 0x7F, 0x82, 0x83])
        result = find_text_strings(data, min_length=4, encoding="gb_custom")
        assert result == [(0, "AB CD")]

    def test_gb_custom_unknown_byte_terminates(self):
        data = bytes([0x80, 0x81, 0x82, 0x83, 0x00, 0xA0, 0xA1, 0xA2, 0xA3])
        result = find_text_strings(data, min_length=4, encoding="gb_custom")
        assert result == [(0, "ABCD"), (5, "abcd")]

    # --- Limits ---

    def test_max_results_caps(self):
        # Create data with many short strings
        segment = b"\x00ABCD"
        data = segment * 250
        result = find_text_strings(
            data, min_length=4, encoding="ascii", max_results=200
        )
        assert len(result) == 200

    def test_max_results_custom(self):
        segment = b"\x00ABCD"
        data = segment * 10
        result = find_text_strings(data, min_length=4, encoding="ascii", max_results=3)
        assert len(result) == 3

    # --- Edge cases ---

    def test_empty_data_returns_empty(self):
        assert find_text_strings(b"", encoding="ascii") == []

    def test_no_strings_found(self):
        data = bytes([0x00, 0x01, 0x02, 0x03])
        assert find_text_strings(data, encoding="ascii") == []

    def test_string_at_offset_zero(self):
        data = b"HELLO\x00"
        result = find_text_strings(data, min_length=4, encoding="ascii")
        assert result[0][0] == 0

    def test_string_at_end_of_data(self):
        data = b"\x00HELLO"
        result = find_text_strings(data, min_length=4, encoding="ascii")
        assert result == [(1, "HELLO")]

    def test_min_length_one(self):
        data = b"\x00A\x00"
        result = find_text_strings(data, min_length=1, encoding="ascii")
        assert result == [(1, "A")]

    # --- Validation ---

    def test_unsupported_encoding_raises(self):
        with pytest.raises(ValueError, match="[Uu]nsupported"):
            find_text_strings(b"\x00", encoding="utf-16")

    def test_min_length_zero_raises(self):
        with pytest.raises(ValueError, match="min_length"):
            find_text_strings(b"\x00", min_length=0)

    def test_min_length_negative_raises(self):
        with pytest.raises(ValueError, match="min_length"):
            find_text_strings(b"\x00", min_length=-1)
