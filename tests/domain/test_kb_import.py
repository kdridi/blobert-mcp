"""Domain tests for symbol import parsing — TDD red."""

from __future__ import annotations

import pytest

from blobert_mcp.domain.kb_import import (
    ParsedSymbol,
    ParseResult,
    classify_address,
    detect_format,
    parse_pokered,
    parse_sym,
    validate_format,
)

# ---------------------------------------------------------------------------
# ParsedSymbol dataclass
# ---------------------------------------------------------------------------


class TestParsedSymbol:
    def test_fields(self):
        s = ParsedSymbol(address=0x0100, bank=0, label="main", symbol_type="code")
        assert s.address == 0x0100
        assert s.bank == 0
        assert s.label == "main"
        assert s.symbol_type == "code"

    def test_frozen(self):
        s = ParsedSymbol(address=0x0100, bank=0, label="main", symbol_type="code")
        with pytest.raises(AttributeError):
            s.label = "other"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ParseResult dataclass
# ---------------------------------------------------------------------------


class TestParseResult:
    def test_fields(self):
        r = ParseResult(symbols=[], errors=0)
        assert r.symbols == []
        assert r.errors == 0


# ---------------------------------------------------------------------------
# classify_address
# ---------------------------------------------------------------------------


class TestClassifyAddress:
    def test_address_zero_is_code(self):
        assert classify_address(0x0000) == "code"

    def test_rom_bank0_is_code(self):
        assert classify_address(0x0100) == "code"

    def test_rom_bankN_is_code(self):
        assert classify_address(0x4000) == "code"

    def test_rom_boundary_is_code(self):
        assert classify_address(0x7FFF) == "code"

    def test_vram_is_data(self):
        assert classify_address(0x8000) == "data"

    def test_sram_is_data(self):
        assert classify_address(0xA000) == "data"

    def test_wram_is_data(self):
        assert classify_address(0xC000) == "data"

    def test_io_is_data(self):
        assert classify_address(0xFF00) == "data"

    def test_hram_is_data(self):
        assert classify_address(0xFF80) == "data"

    def test_ie_register_is_data(self):
        assert classify_address(0xFFFF) == "data"


# ---------------------------------------------------------------------------
# validate_format
# ---------------------------------------------------------------------------


class TestValidateFormat:
    def test_sym_accepted(self):
        validate_format("sym")  # should not raise

    def test_pokered_accepted(self):
        validate_format("pokered")  # should not raise

    def test_auto_accepted(self):
        validate_format("auto")  # should not raise

    def test_invalid_raises_valueerror(self):
        with pytest.raises(ValueError, match="format"):
            validate_format("invalid")

    def test_empty_raises_valueerror(self):
        with pytest.raises(ValueError, match="format"):
            validate_format("")


# ---------------------------------------------------------------------------
# parse_sym
# ---------------------------------------------------------------------------


class TestParseSym:
    def test_basic_line(self):
        result = parse_sym("00:0100 main\n")
        assert len(result.symbols) == 1
        s = result.symbols[0]
        assert s.address == 0x0100
        assert s.bank == 0
        assert s.label == "main"
        assert s.symbol_type == "code"

    def test_comment_lines_skipped(self):
        content = "; this is a comment\n00:0100 main\n"
        result = parse_sym(content)
        assert len(result.symbols) == 1
        assert result.errors == 0

    def test_blank_lines_skipped(self):
        content = "\n\n00:0100 main\n\n"
        result = parse_sym(content)
        assert len(result.symbols) == 1
        assert result.errors == 0

    def test_bank_from_file(self):
        result = parse_sym("01:4000 bank1_start\n")
        assert result.symbols[0].bank == 1

    def test_bank0_rom(self):
        result = parse_sym("00:0100 entry\n")
        assert result.symbols[0].bank == 0

    def test_ram_address_bank_none(self):
        result = parse_sym("00:C000 wram_var\n")
        s = result.symbols[0]
        assert s.bank is None
        assert s.symbol_type == "data"

    def test_vram_address_bank_none(self):
        result = parse_sym("00:8000 tileset\n")
        s = result.symbols[0]
        assert s.bank is None
        assert s.symbol_type == "data"

    def test_hram_address_bank_none(self):
        result = parse_sym("00:FF80 hram_var\n")
        s = result.symbols[0]
        assert s.bank is None
        assert s.symbol_type == "data"

    def test_local_label_qualified(self):
        content = "00:0100 main\n00:0105 .loop\n"
        result = parse_sym(content)
        assert len(result.symbols) == 2
        assert result.symbols[1].label == "main.loop"

    def test_local_label_orphaned_is_error(self):
        content = "00:0105 .loop\n"
        result = parse_sym(content)
        assert len(result.symbols) == 0
        assert result.errors == 1

    def test_multiple_symbols(self):
        content = "00:0100 main\n00:0150 init\n01:4000 bank1\n"
        result = parse_sym(content)
        assert len(result.symbols) == 3

    def test_malformed_line_counted_as_error(self):
        content = "invalid line\n"
        result = parse_sym(content)
        assert len(result.symbols) == 0
        assert result.errors == 1

    def test_mixed_valid_and_invalid(self):
        content = "00:0100 main\ninvalid\n00:0150 init\n"
        result = parse_sym(content)
        assert len(result.symbols) == 2
        assert result.errors == 1

    def test_empty_content(self):
        result = parse_sym("")
        assert len(result.symbols) == 0
        assert result.errors == 0

    def test_whitespace_only_content(self):
        result = parse_sym("   \n  \n")
        assert len(result.symbols) == 0
        assert result.errors == 0

    def test_address_classification_code(self):
        result = parse_sym("00:0100 entry\n")
        assert result.symbols[0].symbol_type == "code"

    def test_address_classification_data(self):
        result = parse_sym("00:C000 wram_var\n")
        assert result.symbols[0].symbol_type == "data"

    def test_high_bank_number(self):
        result = parse_sym("1F:4000 bank31_start\n")
        assert result.symbols[0].bank == 0x1F

    def test_inline_comment_after_label(self):
        # Label is just the first token after address
        result = parse_sym("00:0100 main ; entry point\n")
        assert result.symbols[0].label == "main"


# ---------------------------------------------------------------------------
# parse_pokered
# ---------------------------------------------------------------------------


class TestParsePokered:
    def test_basic_line(self):
        result = parse_pokered("00:0100 main\n")
        assert len(result.symbols) == 1
        s = result.symbols[0]
        assert s.address == 0x0100
        assert s.label == "main"

    def test_hierarchical_label_preserved(self):
        result = parse_pokered("00:0100 VBlank.done\n")
        assert result.symbols[0].label == "VBlank.done"

    def test_local_label_construction(self):
        content = "00:0100 main\n00:0105 .loop\n"
        result = parse_pokered(content)
        assert result.symbols[1].label == "main.loop"

    def test_comment_lines_skipped(self):
        content = "; section\n00:0100 main\n"
        result = parse_pokered(content)
        assert len(result.symbols) == 1

    def test_blank_lines_skipped(self):
        content = "\n00:0100 main\n\n"
        result = parse_pokered(content)
        assert len(result.symbols) == 1

    def test_multiple_symbols(self):
        content = "00:0100 main\n00:0150 VBlank\n01:4000 Text.draw\n"
        result = parse_pokered(content)
        assert len(result.symbols) == 3

    def test_malformed_counted_as_error(self):
        content = "bad line\n00:0100 main\n"
        result = parse_pokered(content)
        assert len(result.symbols) == 1
        assert result.errors == 1

    def test_address_classification(self):
        result = parse_pokered("00:C000 wVariable\n")
        assert result.symbols[0].symbol_type == "data"
        assert result.symbols[0].bank is None


# ---------------------------------------------------------------------------
# detect_format
# ---------------------------------------------------------------------------


class TestDetectFormat:
    def test_simple_sym_detected(self):
        content = "00:0100 main\n00:0150 init\n00:0200 loop\n"
        assert detect_format(content) == "sym"

    def test_pokered_detected(self):
        content = (
            "00:0100 VBlank.handler\n"
            "00:0150 Timer.tick\n"
            "00:0200 Serial.receive\n"
            "00:0250 Input.check\n"
        )
        assert detect_format(content) == "pokered"

    def test_empty_content_defaults_sym(self):
        assert detect_format("") == "sym"

    def test_ambiguous_defaults_sym(self):
        # Only one dotted label out of many — not enough to trigger pokered
        content = "00:0100 main\n00:0150 init\n00:0200 VBlank.done\n"
        assert detect_format(content) == "sym"

    def test_majority_dotted_labels(self):
        content = (
            "00:0100 Func.a\n"
            "00:0150 Func.b\n"
            "00:0200 Func.c\n"
            "00:0250 Func.d\n"
            "00:0300 plain\n"
        )
        assert detect_format(content) == "pokered"
