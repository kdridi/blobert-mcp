"""TDD tests for knowledge base domain validation — written before implementation."""

from __future__ import annotations

import pytest

from blobert_mcp.domain.kb import (
    ANNOTATION_TYPES,
    ROM_ADDRESS_LIMIT,
    STRUCT_FIELD_TYPES,
    VARIABLE_TYPES,
    calculate_coverage_pct,
    calculate_struct_total_size,
    decode_struct_fields,
    rank_search_results,
    validate_address,
    validate_annotation_type,
    validate_enum_values,
    validate_name,
    validate_struct_field_type,
    validate_struct_fields,
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


# ---------------------------------------------------------------------------
# ROM_ADDRESS_LIMIT
# ---------------------------------------------------------------------------


class TestRomAddressLimit:
    def test_constant_value(self):
        assert ROM_ADDRESS_LIMIT == 0x8000


# ---------------------------------------------------------------------------
# calculate_coverage_pct
# ---------------------------------------------------------------------------


class TestCalculateCoveragePct:
    def test_zero_total_returns_zero(self):
        assert calculate_coverage_pct(10, 0) == 0.0

    def test_full_coverage(self):
        assert calculate_coverage_pct(100, 100) == 100.0

    def test_partial_coverage(self):
        assert calculate_coverage_pct(50, 200) == 25.0

    def test_returns_float(self):
        result = calculate_coverage_pct(1, 2)
        assert isinstance(result, float)


# ---------------------------------------------------------------------------
# STRUCT_FIELD_TYPES
# ---------------------------------------------------------------------------


class TestStructFieldTypes:
    def test_constant_value(self):
        assert STRUCT_FIELD_TYPES == frozenset(
            {"u8", "u16", "s8", "s16", "bool", "bytes"}
        )


# ---------------------------------------------------------------------------
# validate_struct_field_type
# ---------------------------------------------------------------------------


class TestValidateStructFieldType:
    @pytest.mark.parametrize("t", ["u8", "u16", "s8", "s16", "bool", "bytes"])
    def test_valid_types_accepted(self, t: str):
        validate_struct_field_type(t)  # should not raise

    def test_invalid_type_raises_valueerror(self):
        with pytest.raises(ValueError, match="struct field type"):
            validate_struct_field_type("int32")


# ---------------------------------------------------------------------------
# validate_struct_fields
# ---------------------------------------------------------------------------


class TestValidateStructFields:
    def test_valid_fields_accepted(self):
        fields = [
            {"name": "y", "offset": 0, "type": "u8", "size": 1},
            {"name": "x", "offset": 1, "type": "u8", "size": 1},
        ]
        validate_struct_fields(fields)  # should not raise

    def test_empty_list_raises_valueerror(self):
        with pytest.raises(ValueError, match="empty"):
            validate_struct_fields([])

    def test_missing_name_raises_valueerror(self):
        with pytest.raises(ValueError, match="name"):
            validate_struct_fields([{"offset": 0, "type": "u8", "size": 1}])

    def test_empty_name_raises_valueerror(self):
        with pytest.raises(ValueError, match="name"):
            validate_struct_fields([{"name": "", "offset": 0, "type": "u8", "size": 1}])

    def test_missing_offset_raises_valueerror(self):
        with pytest.raises(ValueError, match="offset"):
            validate_struct_fields([{"name": "y", "type": "u8", "size": 1}])

    def test_negative_offset_raises_valueerror(self):
        with pytest.raises(ValueError, match="offset"):
            validate_struct_fields(
                [{"name": "y", "offset": -1, "type": "u8", "size": 1}]
            )

    def test_missing_size_raises_valueerror(self):
        with pytest.raises(ValueError, match="size"):
            validate_struct_fields([{"name": "y", "offset": 0, "type": "u8"}])

    def test_zero_size_raises_valueerror(self):
        with pytest.raises(ValueError, match="size"):
            validate_struct_fields(
                [{"name": "y", "offset": 0, "type": "u8", "size": 0}]
            )

    def test_negative_size_raises_valueerror(self):
        with pytest.raises(ValueError, match="size"):
            validate_struct_fields(
                [{"name": "y", "offset": 0, "type": "u8", "size": -1}]
            )

    def test_missing_type_raises_valueerror(self):
        with pytest.raises(ValueError, match="type"):
            validate_struct_fields([{"name": "y", "offset": 0, "size": 1}])

    def test_invalid_type_raises_valueerror(self):
        with pytest.raises(ValueError, match="struct field type"):
            validate_struct_fields(
                [{"name": "y", "offset": 0, "type": "int32", "size": 4}]
            )

    def test_overlapping_fields_raises_valueerror(self):
        fields = [
            {"name": "a", "offset": 0, "type": "u16", "size": 2},
            {"name": "b", "offset": 1, "type": "u8", "size": 1},
        ]
        with pytest.raises(ValueError, match="overlap"):
            validate_struct_fields(fields)

    def test_adjacent_fields_accepted(self):
        fields = [
            {"name": "a", "offset": 0, "type": "u16", "size": 2},
            {"name": "b", "offset": 2, "type": "u8", "size": 1},
        ]
        validate_struct_fields(fields)  # should not raise

    def test_same_offset_raises_valueerror(self):
        fields = [
            {"name": "a", "offset": 0, "type": "u8", "size": 1},
            {"name": "b", "offset": 0, "type": "u16", "size": 2},
        ]
        with pytest.raises(ValueError, match="overlap"):
            validate_struct_fields(fields)

    def test_comment_field_optional(self):
        fields = [
            {"name": "y", "offset": 0, "type": "u8", "size": 1, "comment": "Y pos"},
            {"name": "x", "offset": 1, "type": "u8", "size": 1},
        ]
        validate_struct_fields(fields)  # should not raise


# ---------------------------------------------------------------------------
# validate_enum_values
# ---------------------------------------------------------------------------


class TestValidateEnumValues:
    def test_valid_values_accepted(self):
        validate_enum_values({"UP": 0, "DOWN": 1, "LEFT": 2, "RIGHT": 3})

    def test_empty_dict_raises_valueerror(self):
        with pytest.raises(ValueError, match="empty"):
            validate_enum_values({})

    def test_empty_name_raises_valueerror(self):
        with pytest.raises(ValueError, match="name"):
            validate_enum_values({"": 0})

    def test_whitespace_name_raises_valueerror(self):
        with pytest.raises(ValueError, match="name"):
            validate_enum_values({"  ": 0})

    def test_duplicate_numeric_values_raises_valueerror(self):
        with pytest.raises(ValueError, match="duplicate"):
            validate_enum_values({"A": 0, "B": 0})


# ---------------------------------------------------------------------------
# calculate_struct_total_size
# ---------------------------------------------------------------------------


class TestCalculateStructTotalSize:
    def test_single_field(self):
        fields = [{"offset": 0, "size": 1}]
        assert calculate_struct_total_size(fields) == 1

    def test_multiple_fields(self):
        fields = [{"offset": 0, "size": 1}, {"offset": 2, "size": 2}]
        assert calculate_struct_total_size(fields) == 4

    def test_gap_in_fields(self):
        fields = [{"offset": 0, "size": 1}, {"offset": 4, "size": 1}]
        assert calculate_struct_total_size(fields) == 5

    def test_empty_fields_returns_zero(self):
        assert calculate_struct_total_size([]) == 0


# ---------------------------------------------------------------------------
# decode_struct_fields
# ---------------------------------------------------------------------------


class TestDecodeStructFields:
    def test_u8_field(self):
        fields = [{"name": "val", "offset": 0, "type": "u8", "size": 1}]
        result = decode_struct_fields(fields, b"\x42")
        assert result[0]["value"] == 0x42

    def test_u16_field_little_endian(self):
        fields = [{"name": "val", "offset": 0, "type": "u16", "size": 2}]
        result = decode_struct_fields(fields, b"\x34\x12")
        assert result[0]["value"] == 0x1234

    def test_s8_field_negative(self):
        fields = [{"name": "val", "offset": 0, "type": "s8", "size": 1}]
        result = decode_struct_fields(fields, b"\xff")
        assert result[0]["value"] == -1

    def test_s16_field_negative(self):
        fields = [{"name": "val", "offset": 0, "type": "s16", "size": 2}]
        result = decode_struct_fields(fields, b"\x00\x80")
        assert result[0]["value"] == -32768

    def test_bool_field_true(self):
        fields = [{"name": "flag", "offset": 0, "type": "bool", "size": 1}]
        result = decode_struct_fields(fields, b"\x01")
        assert result[0]["value"] is True

    def test_bool_field_false(self):
        fields = [{"name": "flag", "offset": 0, "type": "bool", "size": 1}]
        result = decode_struct_fields(fields, b"\x00")
        assert result[0]["value"] is False

    def test_bytes_field(self):
        fields = [{"name": "raw", "offset": 0, "type": "bytes", "size": 4}]
        result = decode_struct_fields(fields, b"\xde\xad\xbe\xef")
        assert result[0]["value"] == "DEADBEEF"

    def test_multiple_fields(self):
        fields = [
            {"name": "y", "offset": 0, "type": "u8", "size": 1},
            {"name": "x", "offset": 1, "type": "u8", "size": 1},
        ]
        result = decode_struct_fields(fields, b"\x10\x20")
        assert result[0]["name"] == "y"
        assert result[0]["value"] == 0x10
        assert result[1]["name"] == "x"
        assert result[1]["value"] == 0x20

    def test_includes_raw_hex(self):
        fields = [{"name": "val", "offset": 0, "type": "u16", "size": 2}]
        result = decode_struct_fields(fields, b"\x34\x12")
        assert "raw_hex" in result[0]
        assert result[0]["raw_hex"] == "3412"
