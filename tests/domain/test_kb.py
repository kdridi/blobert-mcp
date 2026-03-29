"""TDD tests for knowledge base domain validation — written before implementation."""

from __future__ import annotations

import pytest

from blobert_mcp.domain.kb import (
    ANNOTATION_TYPES,
    VARIABLE_TYPES,
    rank_search_results,
    validate_address,
    validate_annotation_type,
    validate_name,
    validate_variable_type,
)

# ---------------------------------------------------------------------------
# validate_annotation_type
# ---------------------------------------------------------------------------


class TestValidateAnnotationType:
    @pytest.mark.parametrize("t", ["code", "data", "gfx", "audio", "text"])
    def test_valid_types_accepted(self, t: str):
        validate_annotation_type(t)  # should not raise

    def test_invalid_type_raises_valueerror(self):
        with pytest.raises(ValueError, match="annotation type"):
            validate_annotation_type("invalid")

    def test_none_accepted(self):
        validate_annotation_type(None)  # type is optional

    def test_constants_match_valid_types(self):
        assert ANNOTATION_TYPES == frozenset({"code", "data", "gfx", "audio", "text"})


# ---------------------------------------------------------------------------
# validate_variable_type
# ---------------------------------------------------------------------------


class TestValidateVariableType:
    @pytest.mark.parametrize("t", ["u8", "u16", "bool", "enum"])
    def test_valid_types_accepted(self, t: str):
        validate_variable_type(t)  # should not raise

    def test_invalid_type_raises_valueerror(self):
        with pytest.raises(ValueError, match="variable type"):
            validate_variable_type("int32")

    def test_constants_match_valid_types(self):
        assert VARIABLE_TYPES == frozenset({"u8", "u16", "bool", "enum"})


# ---------------------------------------------------------------------------
# validate_address
# ---------------------------------------------------------------------------


class TestValidateAddress:
    def test_zero_accepted(self):
        validate_address(0)

    def test_max_accepted(self):
        validate_address(0xFFFF)

    def test_mid_range_accepted(self):
        validate_address(0x4000)

    def test_negative_raises_valueerror(self):
        with pytest.raises(ValueError, match="address"):
            validate_address(-1)

    def test_above_max_raises_valueerror(self):
        with pytest.raises(ValueError, match="address"):
            validate_address(0x10000)


# ---------------------------------------------------------------------------
# validate_name
# ---------------------------------------------------------------------------


class TestValidateName:
    def test_non_empty_accepted(self):
        validate_name("main")

    def test_empty_raises_valueerror(self):
        with pytest.raises(ValueError, match="name"):
            validate_name("")

    def test_whitespace_only_raises_valueerror(self):
        with pytest.raises(ValueError, match="name"):
            validate_name("   ")

    def test_custom_field_name_in_error(self):
        with pytest.raises(ValueError, match="label"):
            validate_name("", field="label")


# ---------------------------------------------------------------------------
# rank_search_results
# ---------------------------------------------------------------------------


class TestRankSearchResults:
    def test_exact_match_ranked_first(self):
        results = [
            {"label": "vblank_handler", "rank": 0},
            {"label": "vblank", "rank": 0},
            {"label": "handle_vblank", "rank": 0},
        ]
        ranked = rank_search_results(results, "vblank")
        assert ranked[0]["label"] == "vblank"

    def test_prefix_ranked_above_substring(self):
        results = [
            {"label": "handle_main", "rank": 0},
            {"label": "main_loop", "rank": 0},
        ]
        ranked = rank_search_results(results, "main")
        assert ranked[0]["label"] == "main_loop"

    def test_no_matches_returns_empty(self):
        assert rank_search_results([], "query") == []

    def test_caps_at_50(self):
        results = [{"label": f"item_{i}", "rank": 0} for i in range(100)]
        ranked = rank_search_results(results, "item")
        assert len(ranked) == 50

    def test_case_insensitive_ranking(self):
        results = [
            {"label": "Main", "rank": 0},
            {"label": "MAIN_LOOP", "rank": 0},
        ]
        ranked = rank_search_results(results, "main")
        # "Main" is exact (case-insensitive), should be first
        assert ranked[0]["label"] == "Main"

    def test_results_without_label_key_use_name(self):
        results = [
            {"name": "do_stuff", "rank": 0},
            {"name": "stuff_handler", "rank": 0},
        ]
        ranked = rank_search_results(results, "stuff")
        # "stuff_handler" has prefix match, "do_stuff" has substring
        assert ranked[0]["name"] == "stuff_handler"
