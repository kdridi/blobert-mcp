"""TDD tests for register formatting domain module — written before implementation."""

from __future__ import annotations

import pytest

from blobert_mcp.domain.registers import (
    ALL_REGISTERS,
    REGISTERS_8BIT,
    REGISTERS_16BIT,
    format_registers,
    get_register_size,
    normalize_register_name,
    validate_register_name,
    validate_register_value,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _all_zeros():
    return format_registers(0, 0, 0, 0, 0, 0, 0, 0, 0, 0)


def _all_max():
    return format_registers(
        0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFFFF, 0xFFFF
    )


# ---------------------------------------------------------------------------
# 8-bit register formatting
# ---------------------------------------------------------------------------


class TestEightBitRegisters:
    def test_a_formatted_as_hex(self):
        result = format_registers(0xAB, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        assert result["A"] == "0xAB"

    def test_b_formatted_as_hex(self):
        result = format_registers(0, 0x12, 0, 0, 0, 0, 0, 0, 0, 0)
        assert result["B"] == "0x12"

    def test_c_formatted_as_hex(self):
        result = format_registers(0, 0, 0x34, 0, 0, 0, 0, 0, 0, 0)
        assert result["C"] == "0x34"

    def test_d_formatted_as_hex(self):
        result = format_registers(0, 0, 0, 0x56, 0, 0, 0, 0, 0, 0)
        assert result["D"] == "0x56"

    def test_e_formatted_as_hex(self):
        result = format_registers(0, 0, 0, 0, 0x78, 0, 0, 0, 0, 0)
        assert result["E"] == "0x78"

    def test_f_formatted_as_hex(self):
        result = format_registers(0, 0, 0, 0, 0, 0xF0, 0, 0, 0, 0)
        assert result["F"] == "0xF0"

    def test_h_formatted_as_hex(self):
        result = format_registers(0, 0, 0, 0, 0, 0, 0x9A, 0, 0, 0)
        assert result["H"] == "0x9A"

    def test_l_formatted_as_hex(self):
        result = format_registers(0, 0, 0, 0, 0, 0, 0, 0xBC, 0, 0)
        assert result["L"] == "0xBC"

    def test_zero_formatted_as_two_digits(self):
        result = _all_zeros()
        assert result["A"] == "0x00"
        assert result["B"] == "0x00"
        assert result["F"] == "0x00"

    def test_max_byte_formatted(self):
        result = _all_max()
        assert result["A"] == "0xFF"
        assert result["L"] == "0xFF"


# ---------------------------------------------------------------------------
# 16-bit SP and PC
# ---------------------------------------------------------------------------


class TestSixteenBitRegisters:
    def test_sp_formatted_as_four_digit_hex(self):
        result = format_registers(0, 0, 0, 0, 0, 0, 0, 0, 0xFFFE, 0)
        assert result["SP"] == "0xFFFE"

    def test_pc_formatted_as_four_digit_hex(self):
        result = format_registers(0, 0, 0, 0, 0, 0, 0, 0, 0, 0x0150)
        assert result["PC"] == "0x0150"

    def test_sp_zero_formatted_as_four_digits(self):
        result = _all_zeros()
        assert result["SP"] == "0x0000"

    def test_pc_zero_formatted_as_four_digits(self):
        result = _all_zeros()
        assert result["PC"] == "0x0000"


# ---------------------------------------------------------------------------
# Composite 16-bit registers
# ---------------------------------------------------------------------------


class TestCompositeRegisters:
    def test_af_combines_a_and_f(self):
        # A=0x12, F=0x34 → AF=0x1234
        result = format_registers(0x12, 0, 0, 0, 0, 0x34, 0, 0, 0, 0)
        assert result["AF"] == "0x1234"

    def test_bc_combines_b_and_c(self):
        # B=0x56, C=0x78 → BC=0x5678
        result = format_registers(0, 0x56, 0x78, 0, 0, 0, 0, 0, 0, 0)
        assert result["BC"] == "0x5678"

    def test_de_combines_d_and_e(self):
        # D=0x9A, E=0xBC → DE=0x9ABC
        result = format_registers(0, 0, 0, 0x9A, 0xBC, 0, 0, 0, 0, 0)
        assert result["DE"] == "0x9ABC"

    def test_hl_combines_h_and_l(self):
        # H=0xDE, L=0xF0 → HL=0xDEF0
        result = format_registers(0, 0, 0, 0, 0, 0, 0xDE, 0xF0, 0, 0)
        assert result["HL"] == "0xDEF0"

    def test_all_composites_zero(self):
        result = _all_zeros()
        assert result["AF"] == "0x0000"
        assert result["BC"] == "0x0000"
        assert result["DE"] == "0x0000"
        assert result["HL"] == "0x0000"

    def test_all_composites_max(self):
        result = _all_max()
        assert result["AF"] == "0xFFFF"
        assert result["BC"] == "0xFFFF"
        assert result["HL"] == "0xFFFF"


# ---------------------------------------------------------------------------
# Flags from F register (upper 4 bits only)
# ---------------------------------------------------------------------------


class TestFlags:
    def test_z_flag_set_when_bit7(self):
        # F=0x80 → Z=True
        result = format_registers(0, 0, 0, 0, 0, 0x80, 0, 0, 0, 0)
        assert result["flags"]["Z"] is True

    def test_z_flag_clear_when_bit7_unset(self):
        result = format_registers(0, 0, 0, 0, 0, 0x70, 0, 0, 0, 0)
        assert result["flags"]["Z"] is False

    def test_n_flag_set_when_bit6(self):
        # F=0x40 → N=True
        result = format_registers(0, 0, 0, 0, 0, 0x40, 0, 0, 0, 0)
        assert result["flags"]["N"] is True

    def test_n_flag_clear(self):
        result = format_registers(0, 0, 0, 0, 0, 0x00, 0, 0, 0, 0)
        assert result["flags"]["N"] is False

    def test_h_flag_set_when_bit5(self):
        # F=0x20 → H=True
        result = format_registers(0, 0, 0, 0, 0, 0x20, 0, 0, 0, 0)
        assert result["flags"]["H"] is True

    def test_c_flag_set_when_bit4(self):
        # F=0x10 → C=True
        result = format_registers(0, 0, 0, 0, 0, 0x10, 0, 0, 0, 0)
        assert result["flags"]["C"] is True

    def test_all_flags_set_with_f0xF0(self):
        # F=0xF0 → Z=N=H=C=True
        result = format_registers(0, 0, 0, 0, 0, 0xF0, 0, 0, 0, 0)
        assert result["flags"]["Z"] is True
        assert result["flags"]["N"] is True
        assert result["flags"]["H"] is True
        assert result["flags"]["C"] is True

    def test_no_flags_set_with_f0x00(self):
        result = format_registers(0, 0, 0, 0, 0, 0x00, 0, 0, 0, 0)
        assert result["flags"]["Z"] is False
        assert result["flags"]["N"] is False
        assert result["flags"]["H"] is False
        assert result["flags"]["C"] is False

    def test_lower_nibble_of_f_does_not_affect_flags(self):
        # F=0xFF — lower nibble irrelevant on real hardware; must not corrupt flags
        result_ff = format_registers(0, 0, 0, 0, 0, 0xFF, 0, 0, 0, 0)
        result_f0 = format_registers(0, 0, 0, 0, 0, 0xF0, 0, 0, 0, 0)
        # Flags should be identical regardless of lower nibble
        assert result_ff["flags"] == result_f0["flags"]

    def test_flags_dict_has_exactly_four_keys(self):
        result = _all_zeros()
        assert set(result["flags"].keys()) == {"Z", "N", "H", "C"}


# ---------------------------------------------------------------------------
# Return structure
# ---------------------------------------------------------------------------


class TestReturnStructure:
    def test_all_expected_keys_present(self):
        result = _all_zeros()
        expected_keys = {
            "A",
            "B",
            "C",
            "D",
            "E",
            "F",
            "H",
            "L",
            "AF",
            "BC",
            "DE",
            "HL",
            "SP",
            "PC",
            "flags",
        }
        assert set(result.keys()) == expected_keys

    @pytest.mark.parametrize("reg", ["A", "B", "C", "D", "E", "F", "H", "L"])
    def test_eight_bit_regs_are_strings(self, reg):
        result = _all_zeros()
        assert isinstance(result[reg], str)

    @pytest.mark.parametrize("reg", ["AF", "BC", "DE", "HL", "SP", "PC"])
    def test_sixteen_bit_regs_are_strings(self, reg):
        result = _all_zeros()
        assert isinstance(result[reg], str)

    @pytest.mark.parametrize("flag", ["Z", "N", "H", "C"])
    def test_flags_are_bools(self, flag):
        result = _all_zeros()
        assert isinstance(result["flags"][flag], bool)


# ---------------------------------------------------------------------------
# Register constants
# ---------------------------------------------------------------------------


class TestRegisterConstants:
    def test_registers_8bit_set(self):
        assert REGISTERS_8BIT == {"A", "B", "C", "D", "E", "F", "H", "L"}

    def test_registers_16bit_set(self):
        assert REGISTERS_16BIT == {"SP", "PC"}

    def test_all_registers_is_union(self):
        assert ALL_REGISTERS == REGISTERS_8BIT | REGISTERS_16BIT

    def test_constants_are_frozensets(self):
        assert isinstance(REGISTERS_8BIT, frozenset)
        assert isinstance(REGISTERS_16BIT, frozenset)
        assert isinstance(ALL_REGISTERS, frozenset)


# ---------------------------------------------------------------------------
# normalize_register_name
# ---------------------------------------------------------------------------


class TestNormalizeRegisterName:
    def test_lowercase_to_uppercase(self):
        assert normalize_register_name("a") == "A"

    def test_already_uppercase(self):
        assert normalize_register_name("SP") == "SP"

    def test_mixed_case(self):
        assert normalize_register_name("sP") == "SP"

    def test_strips_whitespace(self):
        assert normalize_register_name("  a  ") == "A"


# ---------------------------------------------------------------------------
# validate_register_name
# ---------------------------------------------------------------------------


class TestValidateRegisterName:
    @pytest.mark.parametrize(
        "name", ["A", "B", "C", "D", "E", "F", "H", "L", "SP", "PC"]
    )
    def test_valid_names_accepted(self, name):
        assert validate_register_name(name) == name

    def test_returns_normalized_uppercase(self):
        assert validate_register_name("sp") == "SP"

    def test_invalid_name_raises_valueerror(self):
        with pytest.raises(ValueError, match="X"):
            validate_register_name("X")

    def test_composite_name_rejected(self):
        with pytest.raises(ValueError, match="AF"):
            validate_register_name("AF")

    def test_empty_string_raises_valueerror(self):
        with pytest.raises(ValueError):
            validate_register_name("")


# ---------------------------------------------------------------------------
# validate_register_value
# ---------------------------------------------------------------------------


class TestValidateRegisterValue:
    @pytest.mark.parametrize("reg", ["A", "B", "C", "D", "E", "H", "L"])
    def test_8bit_zero_accepted(self, reg):
        assert validate_register_value(reg, 0x00) == 0x00

    @pytest.mark.parametrize("reg", ["A", "B", "C", "D", "E", "H", "L"])
    def test_8bit_max_accepted(self, reg):
        assert validate_register_value(reg, 0xFF) == 0xFF

    def test_8bit_over_max_raises(self):
        with pytest.raises(ValueError):
            validate_register_value("A", 0x100)

    def test_8bit_negative_raises(self):
        with pytest.raises(ValueError):
            validate_register_value("A", -1)

    @pytest.mark.parametrize("reg", ["SP", "PC"])
    def test_16bit_zero_accepted(self, reg):
        assert validate_register_value(reg, 0x0000) == 0x0000

    @pytest.mark.parametrize("reg", ["SP", "PC"])
    def test_16bit_max_accepted(self, reg):
        assert validate_register_value(reg, 0xFFFF) == 0xFFFF

    def test_16bit_over_max_raises(self):
        with pytest.raises(ValueError):
            validate_register_value("SP", 0x10000)

    def test_16bit_negative_raises(self):
        with pytest.raises(ValueError):
            validate_register_value("PC", -1)

    def test_f_register_masks_lower_nibble(self):
        assert validate_register_value("F", 0xFF) == 0xF0

    def test_f_register_0x0f_masked_to_0x00(self):
        assert validate_register_value("F", 0x0F) == 0x00

    def test_f_register_0xf0_unchanged(self):
        assert validate_register_value("F", 0xF0) == 0xF0

    def test_non_f_8bit_returns_value_unchanged(self):
        assert validate_register_value("A", 0x42) == 0x42

    def test_16bit_returns_value_unchanged(self):
        assert validate_register_value("SP", 0x1234) == 0x1234


# ---------------------------------------------------------------------------
# get_register_size
# ---------------------------------------------------------------------------


class TestGetRegisterSize:
    @pytest.mark.parametrize("reg", ["A", "B", "C", "D", "E", "F", "H", "L"])
    def test_8bit_registers_return_8(self, reg):
        assert get_register_size(reg) == 8

    @pytest.mark.parametrize("reg", ["SP", "PC"])
    def test_16bit_registers_return_16(self, reg):
        assert get_register_size(reg) == 16

    def test_invalid_register_raises(self):
        with pytest.raises(ValueError):
            get_register_size("X")
