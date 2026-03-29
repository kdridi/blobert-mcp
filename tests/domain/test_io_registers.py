"""Tests for domain/io_registers.py — I/O register parsing (TDD)."""

from __future__ import annotations

import pytest

from blobert_mcp.domain.io_registers import (
    parse_audio_channel1,
    parse_audio_channel2,
    parse_audio_channel3,
    parse_audio_channel4,
    parse_audio_master,
    parse_audio_state,
    parse_lcd_status,
    parse_lcdc,
    parse_sc,
    parse_serial_state,
    parse_stat,
    parse_tac,
    parse_timer_state,
)

# ---------------------------------------------------------------------------
# parse_lcdc
# ---------------------------------------------------------------------------


class TestParseLcdc:
    def test_all_zeros(self) -> None:
        result = parse_lcdc(0x00)
        assert result["lcd_enable"] is False
        assert result["window_tilemap"] is False
        assert result["window_enable"] is False
        assert result["bg_window_tile_data"] is False
        assert result["bg_tilemap"] is False
        assert result["obj_size"] is False
        assert result["obj_enable"] is False
        assert result["bg_window_priority"] is False

    def test_all_ones(self) -> None:
        result = parse_lcdc(0xFF)
        assert result["lcd_enable"] is True
        assert result["window_tilemap"] is True
        assert result["window_enable"] is True
        assert result["bg_window_tile_data"] is True
        assert result["bg_tilemap"] is True
        assert result["obj_size"] is True
        assert result["obj_enable"] is True
        assert result["bg_window_priority"] is True

    def test_lcd_enable_only(self) -> None:
        result = parse_lcdc(0x80)
        assert result["lcd_enable"] is True
        assert result["window_enable"] is False
        assert result["obj_enable"] is False

    def test_typical_value(self) -> None:
        # 0x91 = bit7 + bit4 + bit0 = LCD on, BG tile data area, BG priority
        result = parse_lcdc(0x91)
        assert result["lcd_enable"] is True
        assert result["bg_window_tile_data"] is True
        assert result["bg_window_priority"] is True
        assert result["window_tilemap"] is False
        assert result["window_enable"] is False
        assert result["bg_tilemap"] is False
        assert result["obj_size"] is False
        assert result["obj_enable"] is False

    def test_expected_keys(self) -> None:
        result = parse_lcdc(0x00)
        expected = {
            "lcd_enable",
            "window_tilemap",
            "window_enable",
            "bg_window_tile_data",
            "bg_tilemap",
            "obj_size",
            "obj_enable",
            "bg_window_priority",
        }
        assert set(result.keys()) == expected


# ---------------------------------------------------------------------------
# parse_stat
# ---------------------------------------------------------------------------


class TestParseStat:
    def test_all_zeros(self) -> None:
        result = parse_stat(0x00)
        assert result["mode"] == 0
        assert result["coincidence_flag"] is False
        assert result["hblank_interrupt"] is False
        assert result["vblank_interrupt"] is False
        assert result["oam_interrupt"] is False
        assert result["lyc_interrupt"] is False

    def test_mode_values(self) -> None:
        for mode in range(4):
            result = parse_stat(mode)
            assert result["mode"] == mode

    def test_coincidence_flag(self) -> None:
        result = parse_stat(0x04)
        assert result["coincidence_flag"] is True
        assert result["mode"] == 0

    def test_lyc_interrupt_enabled(self) -> None:
        result = parse_stat(0x40)
        assert result["lyc_interrupt"] is True
        assert result["oam_interrupt"] is False

    def test_all_interrupts_enabled(self) -> None:
        # bits 6,5,4,3 = 0x78
        result = parse_stat(0x78)
        assert result["lyc_interrupt"] is True
        assert result["oam_interrupt"] is True
        assert result["vblank_interrupt"] is True
        assert result["hblank_interrupt"] is True

    def test_typical_vblank(self) -> None:
        # 0x45 = LYC int (bit6) + coincidence (bit2) + mode 1
        result = parse_stat(0x45)
        assert result["lyc_interrupt"] is True
        assert result["coincidence_flag"] is True
        assert result["mode"] == 1

    def test_expected_keys(self) -> None:
        result = parse_stat(0x00)
        expected = {
            "mode",
            "coincidence_flag",
            "hblank_interrupt",
            "vblank_interrupt",
            "oam_interrupt",
            "lyc_interrupt",
        }
        assert set(result.keys()) == expected


# ---------------------------------------------------------------------------
# parse_lcd_status
# ---------------------------------------------------------------------------


class TestParseLcdStatus:
    def test_keys(self) -> None:
        result = parse_lcd_status(0, 0, 0, 0, 0, 0, 0, 0)
        expected = {
            "lcdc_raw",
            "stat_raw",
            "lcdc",
            "stat",
            "scy",
            "scx",
            "ly",
            "lyc",
            "wy",
            "wx",
        }
        assert set(result.keys()) == expected

    def test_raw_values_preserved(self) -> None:
        result = parse_lcd_status(0x91, 0x45, 10, 20, 30, 40, 50, 60)
        assert result["lcdc_raw"] == 0x91
        assert result["stat_raw"] == 0x45

    def test_scroll_values(self) -> None:
        result = parse_lcd_status(0, 0, 10, 20, 144, 153, 0, 7)
        assert result["scy"] == 10
        assert result["scx"] == 20
        assert result["ly"] == 144
        assert result["lyc"] == 153
        assert result["wy"] == 0
        assert result["wx"] == 7

    def test_delegates_to_lcdc_parser(self) -> None:
        result = parse_lcd_status(0x80, 0, 0, 0, 0, 0, 0, 0)
        assert result["lcdc"]["lcd_enable"] is True

    def test_delegates_to_stat_parser(self) -> None:
        result = parse_lcd_status(0, 0x03, 0, 0, 0, 0, 0, 0)
        assert result["stat"]["mode"] == 3


# ---------------------------------------------------------------------------
# parse_tac
# ---------------------------------------------------------------------------


class TestParseTac:
    def test_disabled_freq_4096(self) -> None:
        result = parse_tac(0x00)
        assert result["enabled"] is False
        assert result["clock_select"] == 0
        assert result["frequency_hz"] == 4096

    def test_enabled_freq_4096(self) -> None:
        result = parse_tac(0x04)
        assert result["enabled"] is True
        assert result["frequency_hz"] == 4096

    def test_enabled_freq_262144(self) -> None:
        result = parse_tac(0x05)
        assert result["enabled"] is True
        assert result["clock_select"] == 1
        assert result["frequency_hz"] == 262144

    def test_enabled_freq_65536(self) -> None:
        result = parse_tac(0x06)
        assert result["enabled"] is True
        assert result["clock_select"] == 2
        assert result["frequency_hz"] == 65536

    def test_enabled_freq_16384(self) -> None:
        result = parse_tac(0x07)
        assert result["enabled"] is True
        assert result["clock_select"] == 3
        assert result["frequency_hz"] == 16384

    def test_high_bits_ignored(self) -> None:
        # 0xF4 = all high bits set + enabled + clock_select=0
        result = parse_tac(0xF4)
        assert result["enabled"] is True
        assert result["frequency_hz"] == 4096

    def test_expected_keys(self) -> None:
        result = parse_tac(0x00)
        assert set(result.keys()) == {"enabled", "clock_select", "frequency_hz"}


# ---------------------------------------------------------------------------
# parse_timer_state
# ---------------------------------------------------------------------------


class TestParseTimerState:
    def test_keys(self) -> None:
        result = parse_timer_state(0, 0, 0, 0)
        assert set(result.keys()) == {"div", "tima", "tma", "tac_raw", "tac"}

    def test_values_passthrough(self) -> None:
        result = parse_timer_state(0xAB, 0x10, 0xFF, 0x05)
        assert result["div"] == 0xAB
        assert result["tima"] == 0x10
        assert result["tma"] == 0xFF
        assert result["tac_raw"] == 0x05

    def test_tac_delegation(self) -> None:
        result = parse_timer_state(0, 0, 0, 0x05)
        assert result["tac"]["enabled"] is True
        assert result["tac"]["frequency_hz"] == 262144


# ---------------------------------------------------------------------------
# parse_sc
# ---------------------------------------------------------------------------


class TestParseSc:
    def test_idle_external(self) -> None:
        result = parse_sc(0x00)
        assert result["transfer_in_progress"] is False
        assert result["clock_source"] == "external"

    def test_idle_internal(self) -> None:
        result = parse_sc(0x01)
        assert result["transfer_in_progress"] is False
        assert result["clock_source"] == "internal"

    def test_transfer_external(self) -> None:
        result = parse_sc(0x80)
        assert result["transfer_in_progress"] is True
        assert result["clock_source"] == "external"

    def test_transfer_internal(self) -> None:
        result = parse_sc(0x81)
        assert result["transfer_in_progress"] is True
        assert result["clock_source"] == "internal"

    def test_middle_bits_ignored(self) -> None:
        # 0xFE = all bits except bit0 → transfer=True, clock=external
        result = parse_sc(0xFE)
        assert result["transfer_in_progress"] is True
        assert result["clock_source"] == "external"

    def test_expected_keys(self) -> None:
        result = parse_sc(0x00)
        assert set(result.keys()) == {"transfer_in_progress", "clock_source"}


# ---------------------------------------------------------------------------
# parse_serial_state
# ---------------------------------------------------------------------------


class TestParseSerialState:
    def test_keys(self) -> None:
        result = parse_serial_state(0, 0)
        assert set(result.keys()) == {"sb", "sc_raw", "sc"}

    def test_values_passthrough(self) -> None:
        result = parse_serial_state(0x42, 0x81)
        assert result["sb"] == 0x42
        assert result["sc_raw"] == 0x81

    def test_sc_delegation(self) -> None:
        result = parse_serial_state(0, 0x81)
        assert result["sc"]["transfer_in_progress"] is True
        assert result["sc"]["clock_source"] == "internal"


# ---------------------------------------------------------------------------
# parse_audio_channel1
# ---------------------------------------------------------------------------


class TestParseAudioChannel1:
    def test_all_zeros(self) -> None:
        result = parse_audio_channel1(0, 0, 0, 0, 0)
        assert result["sweep_pace"] == 0
        assert result["sweep_direction"] == "increase"
        assert result["sweep_step"] == 0
        assert result["wave_duty"] == 0
        assert result["length_timer"] == 0
        assert result["initial_volume"] == 0
        assert result["envelope_direction"] == "decrease"
        assert result["envelope_pace"] == 0
        assert result["frequency_low"] == 0
        assert result["trigger"] is False
        assert result["length_enable"] is False
        assert result["frequency_high"] == 0

    def test_typical(self) -> None:
        # NR10=0x1A: sweep_pace=1, dir=decrease (bit3=1), step=2
        # NR11=0x80: duty=2, length=0
        # NR12=0xFB: vol=15, dir=increase (bit3=1), pace=3
        # NR13=0x73: freq_low=0x73
        # NR14=0xC6: trigger=1, length_enable=1, freq_high=6
        result = parse_audio_channel1(0x1A, 0x80, 0xFB, 0x73, 0xC6)
        assert result["sweep_pace"] == 1
        assert result["sweep_direction"] == "decrease"
        assert result["sweep_step"] == 2
        assert result["wave_duty"] == 2
        assert result["initial_volume"] == 15
        assert result["envelope_direction"] == "increase"
        assert result["envelope_pace"] == 3
        assert result["frequency_low"] == 0x73
        assert result["trigger"] is True
        assert result["length_enable"] is True
        assert result["frequency_high"] == 6

    def test_expected_keys(self) -> None:
        result = parse_audio_channel1(0, 0, 0, 0, 0)
        expected = {
            "sweep_pace",
            "sweep_direction",
            "sweep_step",
            "wave_duty",
            "length_timer",
            "initial_volume",
            "envelope_direction",
            "envelope_pace",
            "frequency_low",
            "trigger",
            "length_enable",
            "frequency_high",
        }
        assert set(result.keys()) == expected


# ---------------------------------------------------------------------------
# parse_audio_channel2
# ---------------------------------------------------------------------------


class TestParseAudioChannel2:
    def test_all_zeros(self) -> None:
        result = parse_audio_channel2(0, 0, 0, 0)
        assert result["wave_duty"] == 0
        assert result["length_timer"] == 0
        assert result["initial_volume"] == 0
        assert result["envelope_direction"] == "decrease"
        assert result["envelope_pace"] == 0
        assert result["frequency_low"] == 0
        assert result["trigger"] is False
        assert result["length_enable"] is False
        assert result["frequency_high"] == 0

    def test_typical(self) -> None:
        # NR21=0x40: duty=1, length=0
        # NR22=0xA5: vol=10, dir=decrease, pace=5
        # NR23=0xFF: freq_low=0xFF
        # NR24=0x87: trigger=1, length_enable=0, freq_high=7
        result = parse_audio_channel2(0x40, 0xA5, 0xFF, 0x87)
        assert result["wave_duty"] == 1
        assert result["initial_volume"] == 10
        assert result["envelope_direction"] == "decrease"
        assert result["envelope_pace"] == 5
        assert result["frequency_low"] == 0xFF
        assert result["trigger"] is True
        assert result["frequency_high"] == 7

    def test_expected_keys(self) -> None:
        result = parse_audio_channel2(0, 0, 0, 0)
        expected = {
            "wave_duty",
            "length_timer",
            "initial_volume",
            "envelope_direction",
            "envelope_pace",
            "frequency_low",
            "trigger",
            "length_enable",
            "frequency_high",
        }
        assert set(result.keys()) == expected


# ---------------------------------------------------------------------------
# parse_audio_channel3
# ---------------------------------------------------------------------------


class TestParseAudioChannel3:
    def test_all_zeros(self) -> None:
        result = parse_audio_channel3(0, 0, 0, 0, 0, [0] * 16)
        assert result["dac_enable"] is False
        assert result["length_timer"] == 0
        assert result["output_level"] == 0
        assert result["frequency_low"] == 0
        assert result["trigger"] is False
        assert result["length_enable"] is False
        assert result["frequency_high"] == 0
        assert result["wave_ram"] == "00" * 16

    def test_with_wave_ram(self) -> None:
        wave = [0x01, 0x23, 0x45, 0x67, 0x89, 0xAB, 0xCD, 0xEF] + [0xFF] * 8
        result = parse_audio_channel3(0x80, 0, 0x40, 0, 0, wave)
        assert result["dac_enable"] is True
        assert result["output_level"] == 2
        assert result["wave_ram"] == "0123456789abcdefffffffffffffffff"

    def test_expected_keys(self) -> None:
        result = parse_audio_channel3(0, 0, 0, 0, 0, [0] * 16)
        expected = {
            "dac_enable",
            "length_timer",
            "output_level",
            "frequency_low",
            "trigger",
            "length_enable",
            "frequency_high",
            "wave_ram",
        }
        assert set(result.keys()) == expected


# ---------------------------------------------------------------------------
# parse_audio_channel4
# ---------------------------------------------------------------------------


class TestParseAudioChannel4:
    def test_all_zeros(self) -> None:
        result = parse_audio_channel4(0, 0, 0, 0)
        assert result["length_timer"] == 0
        assert result["initial_volume"] == 0
        assert result["envelope_direction"] == "decrease"
        assert result["envelope_pace"] == 0
        assert result["clock_shift"] == 0
        assert result["lfsr_width"] == "15-bit"
        assert result["clock_divider"] == 0
        assert result["trigger"] is False
        assert result["length_enable"] is False

    def test_typical(self) -> None:
        # NR41=0x3F: length=63
        # NR42=0x80: vol=8, dir=decrease, pace=0
        # NR43=0x5A: shift=5, lfsr=7-bit, divider=2
        # NR44=0xC0: trigger=1, length_enable=1
        result = parse_audio_channel4(0x3F, 0x80, 0x5A, 0xC0)
        assert result["length_timer"] == 63
        assert result["initial_volume"] == 8
        assert result["clock_shift"] == 5
        assert result["lfsr_width"] == "7-bit"
        assert result["clock_divider"] == 2
        assert result["trigger"] is True
        assert result["length_enable"] is True

    def test_expected_keys(self) -> None:
        result = parse_audio_channel4(0, 0, 0, 0)
        expected = {
            "length_timer",
            "initial_volume",
            "envelope_direction",
            "envelope_pace",
            "clock_shift",
            "lfsr_width",
            "clock_divider",
            "trigger",
            "length_enable",
        }
        assert set(result.keys()) == expected


# ---------------------------------------------------------------------------
# parse_audio_master
# ---------------------------------------------------------------------------


class TestParseAudioMaster:
    def test_all_zeros(self) -> None:
        result = parse_audio_master(0, 0, 0)
        assert result["vin_left"] is False
        assert result["left_volume"] == 0
        assert result["vin_right"] is False
        assert result["right_volume"] == 0
        assert result["audio_enable"] is False
        for ch in ("ch1_active", "ch2_active", "ch3_active", "ch4_active"):
            assert result[ch] is False

    def test_all_on(self) -> None:
        # NR50=0xFF: vin_left, vol=7, vin_right, vol=7
        # NR51=0xFF: all channels both sides
        # NR52=0x8F: audio on, all channels active
        result = parse_audio_master(0xFF, 0xFF, 0x8F)
        assert result["vin_left"] is True
        assert result["left_volume"] == 7
        assert result["vin_right"] is True
        assert result["right_volume"] == 7
        assert result["audio_enable"] is True
        assert result["ch1_active"] is True
        assert result["ch4_active"] is True
        # Panning: all channels on both sides
        assert result["panning"]["ch1_left"] is True
        assert result["panning"]["ch1_right"] is True
        assert result["panning"]["ch4_left"] is True
        assert result["panning"]["ch4_right"] is True

    def test_expected_keys(self) -> None:
        result = parse_audio_master(0, 0, 0)
        expected = {
            "vin_left",
            "left_volume",
            "vin_right",
            "right_volume",
            "audio_enable",
            "ch1_active",
            "ch2_active",
            "ch3_active",
            "ch4_active",
            "panning",
        }
        assert set(result.keys()) == expected

    def test_panning_keys(self) -> None:
        result = parse_audio_master(0, 0, 0)
        expected = {
            "ch1_left",
            "ch2_left",
            "ch3_left",
            "ch4_left",
            "ch1_right",
            "ch2_right",
            "ch3_right",
            "ch4_right",
        }
        assert set(result["panning"].keys()) == expected


# ---------------------------------------------------------------------------
# parse_audio_state
# ---------------------------------------------------------------------------

_ALL_ZERO_REGS: dict = {
    "nr10": 0,
    "nr11": 0,
    "nr12": 0,
    "nr13": 0,
    "nr14": 0,
    "nr21": 0,
    "nr22": 0,
    "nr23": 0,
    "nr24": 0,
    "nr30": 0,
    "nr31": 0,
    "nr32": 0,
    "nr33": 0,
    "nr34": 0,
    "nr41": 0,
    "nr42": 0,
    "nr43": 0,
    "nr44": 0,
    "nr50": 0,
    "nr51": 0,
    "nr52": 0,
    "wave_ram": [0] * 16,
}


class TestParseAudioState:
    def test_all_channels(self) -> None:
        result = parse_audio_state(_ALL_ZERO_REGS, channel=None)
        assert "channel1" in result
        assert "channel2" in result
        assert "channel3" in result
        assert "channel4" in result
        assert "master" in result

    def test_channel_1_only(self) -> None:
        result = parse_audio_state(_ALL_ZERO_REGS, channel=1)
        assert "channel1" in result
        assert "master" in result
        assert "channel2" not in result
        assert "channel3" not in result
        assert "channel4" not in result

    def test_channel_2_only(self) -> None:
        result = parse_audio_state(_ALL_ZERO_REGS, channel=2)
        assert "channel2" in result
        assert "master" in result
        assert "channel1" not in result

    def test_channel_3_only(self) -> None:
        result = parse_audio_state(_ALL_ZERO_REGS, channel=3)
        assert "channel3" in result
        assert "master" in result
        assert "wave_ram" in result["channel3"]

    def test_channel_4_only(self) -> None:
        result = parse_audio_state(_ALL_ZERO_REGS, channel=4)
        assert "channel4" in result
        assert "master" in result
        assert "channel1" not in result

    def test_invalid_channel_raises(self) -> None:
        with pytest.raises(ValueError):
            parse_audio_state(_ALL_ZERO_REGS, channel=5)
        with pytest.raises(ValueError):
            parse_audio_state(_ALL_ZERO_REGS, channel=0)
