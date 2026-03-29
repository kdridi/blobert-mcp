"""I/O register parsing for Game Boy hardware registers.

Pure functions that decode raw register bytes into structured dicts.
No project imports; stdlib only.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Address constants (consumed by tools layer, not by domain functions)
# ---------------------------------------------------------------------------

# LCD registers
LCDC_ADDR = 0xFF40
STAT_ADDR = 0xFF41
SCY_ADDR = 0xFF42
SCX_ADDR = 0xFF43
LY_ADDR = 0xFF44
LYC_ADDR = 0xFF45
WY_ADDR = 0xFF4A
WX_ADDR = 0xFF4B

# Timer registers
DIV_ADDR = 0xFF04
TIMA_ADDR = 0xFF05
TMA_ADDR = 0xFF06
TAC_ADDR = 0xFF07

# Serial registers
SB_ADDR = 0xFF01
SC_ADDR = 0xFF02

# Audio registers
NR10_ADDR = 0xFF10
NR11_ADDR = 0xFF11
NR12_ADDR = 0xFF12
NR13_ADDR = 0xFF13
NR14_ADDR = 0xFF14
NR21_ADDR = 0xFF16
NR22_ADDR = 0xFF17
NR23_ADDR = 0xFF18
NR24_ADDR = 0xFF19
NR30_ADDR = 0xFF1A
NR31_ADDR = 0xFF1B
NR32_ADDR = 0xFF1C
NR33_ADDR = 0xFF1D
NR34_ADDR = 0xFF1E
NR41_ADDR = 0xFF20
NR42_ADDR = 0xFF21
NR43_ADDR = 0xFF22
NR44_ADDR = 0xFF23
NR50_ADDR = 0xFF24
NR51_ADDR = 0xFF25
NR52_ADDR = 0xFF26
WAVE_RAM_START = 0xFF30
WAVE_RAM_END = 0xFF3F

# TAC frequency lookup
TAC_FREQUENCIES: dict[int, int] = {0: 4096, 1: 262144, 2: 65536, 3: 16384}


# ---------------------------------------------------------------------------
# LCD
# ---------------------------------------------------------------------------


def parse_lcdc(value: int) -> dict:
    """Decode LCDC register (0xFF40) bits into named flags."""
    return {
        "lcd_enable": bool(value & 0x80),
        "window_tilemap": bool(value & 0x40),
        "window_enable": bool(value & 0x20),
        "bg_window_tile_data": bool(value & 0x10),
        "bg_tilemap": bool(value & 0x08),
        "obj_size": bool(value & 0x04),
        "obj_enable": bool(value & 0x02),
        "bg_window_priority": bool(value & 0x01),
    }


def parse_stat(value: int) -> dict:
    """Decode STAT register (0xFF41) bits into named fields."""
    return {
        "lyc_interrupt": bool(value & 0x40),
        "oam_interrupt": bool(value & 0x20),
        "vblank_interrupt": bool(value & 0x10),
        "hblank_interrupt": bool(value & 0x08),
        "coincidence_flag": bool(value & 0x04),
        "mode": value & 0x03,
    }


def parse_lcd_status(
    lcdc: int,
    stat: int,
    scy: int,
    scx: int,
    ly: int,
    lyc: int,
    wy: int,
    wx: int,
) -> dict:
    """Aggregate all LCD/PPU register state into a single dict."""
    return {
        "lcdc_raw": lcdc,
        "stat_raw": stat,
        "lcdc": parse_lcdc(lcdc),
        "stat": parse_stat(stat),
        "scy": scy,
        "scx": scx,
        "ly": ly,
        "lyc": lyc,
        "wy": wy,
        "wx": wx,
    }


# ---------------------------------------------------------------------------
# Timer
# ---------------------------------------------------------------------------


def parse_tac(value: int) -> dict:
    """Decode TAC register (0xFF07) into enabled flag and frequency."""
    clock_select = value & 0x03
    return {
        "enabled": bool(value & 0x04),
        "clock_select": clock_select,
        "frequency_hz": TAC_FREQUENCIES[clock_select],
    }


def parse_timer_state(div: int, tima: int, tma: int, tac: int) -> dict:
    """Aggregate all timer register state into a single dict."""
    return {
        "div": div,
        "tima": tima,
        "tma": tma,
        "tac_raw": tac,
        "tac": parse_tac(tac),
    }


# ---------------------------------------------------------------------------
# Serial
# ---------------------------------------------------------------------------


def parse_sc(value: int) -> dict:
    """Decode SC register (0xFF02) into transfer and clock fields."""
    return {
        "transfer_in_progress": bool(value & 0x80),
        "clock_source": "internal" if value & 0x01 else "external",
    }


def parse_serial_state(sb: int, sc: int) -> dict:
    """Aggregate serial port register state into a single dict."""
    return {
        "sb": sb,
        "sc_raw": sc,
        "sc": parse_sc(sc),
    }


# ---------------------------------------------------------------------------
# Audio
# ---------------------------------------------------------------------------


def parse_audio_channel1(nr10: int, nr11: int, nr12: int, nr13: int, nr14: int) -> dict:
    """Decode channel 1 (pulse + sweep) registers NR10-NR14."""
    return {
        "sweep_pace": (nr10 >> 4) & 0x07,
        "sweep_direction": "decrease" if nr10 & 0x08 else "increase",
        "sweep_step": nr10 & 0x07,
        "wave_duty": (nr11 >> 6) & 0x03,
        "length_timer": nr11 & 0x3F,
        "initial_volume": (nr12 >> 4) & 0x0F,
        "envelope_direction": "increase" if nr12 & 0x08 else "decrease",
        "envelope_pace": nr12 & 0x07,
        "frequency_low": nr13,
        "trigger": bool(nr14 & 0x80),
        "length_enable": bool(nr14 & 0x40),
        "frequency_high": nr14 & 0x07,
    }


def parse_audio_channel2(nr21: int, nr22: int, nr23: int, nr24: int) -> dict:
    """Decode channel 2 (pulse) registers NR21-NR24."""
    return {
        "wave_duty": (nr21 >> 6) & 0x03,
        "length_timer": nr21 & 0x3F,
        "initial_volume": (nr22 >> 4) & 0x0F,
        "envelope_direction": "increase" if nr22 & 0x08 else "decrease",
        "envelope_pace": nr22 & 0x07,
        "frequency_low": nr23,
        "trigger": bool(nr24 & 0x80),
        "length_enable": bool(nr24 & 0x40),
        "frequency_high": nr24 & 0x07,
    }


def parse_audio_channel3(
    nr30: int, nr31: int, nr32: int, nr33: int, nr34: int, wave_ram: list[int]
) -> dict:
    """Decode channel 3 (wave) registers NR30-NR34 + wave RAM."""
    return {
        "dac_enable": bool(nr30 & 0x80),
        "length_timer": nr31,
        "output_level": (nr32 >> 5) & 0x03,
        "frequency_low": nr33,
        "trigger": bool(nr34 & 0x80),
        "length_enable": bool(nr34 & 0x40),
        "frequency_high": nr34 & 0x07,
        "wave_ram": "".join(f"{b:02x}" for b in wave_ram),
    }


def parse_audio_channel4(nr41: int, nr42: int, nr43: int, nr44: int) -> dict:
    """Decode channel 4 (noise) registers NR41-NR44."""
    return {
        "length_timer": nr41 & 0x3F,
        "initial_volume": (nr42 >> 4) & 0x0F,
        "envelope_direction": "increase" if nr42 & 0x08 else "decrease",
        "envelope_pace": nr42 & 0x07,
        "clock_shift": (nr43 >> 4) & 0x0F,
        "lfsr_width": "7-bit" if nr43 & 0x08 else "15-bit",
        "clock_divider": nr43 & 0x07,
        "trigger": bool(nr44 & 0x80),
        "length_enable": bool(nr44 & 0x40),
    }


def parse_audio_master(nr50: int, nr51: int, nr52: int) -> dict:
    """Decode master audio control registers NR50, NR51, NR52."""
    return {
        "vin_left": bool(nr50 & 0x80),
        "left_volume": (nr50 >> 4) & 0x07,
        "vin_right": bool(nr50 & 0x08),
        "right_volume": nr50 & 0x07,
        "audio_enable": bool(nr52 & 0x80),
        "ch1_active": bool(nr52 & 0x01),
        "ch2_active": bool(nr52 & 0x02),
        "ch3_active": bool(nr52 & 0x04),
        "ch4_active": bool(nr52 & 0x08),
        "panning": {
            "ch1_right": bool(nr51 & 0x01),
            "ch2_right": bool(nr51 & 0x02),
            "ch3_right": bool(nr51 & 0x04),
            "ch4_right": bool(nr51 & 0x08),
            "ch1_left": bool(nr51 & 0x10),
            "ch2_left": bool(nr51 & 0x20),
            "ch3_left": bool(nr51 & 0x40),
            "ch4_left": bool(nr51 & 0x80),
        },
    }


def parse_audio_state(registers: dict, channel: int | None = None) -> dict:
    """Aggregate audio register state, optionally filtered by channel.

    Args:
        registers: Dict with keys like "nr10", "nr11", ..., "nr52", "wave_ram".
        channel: 1-4 for a single channel, None for all channels.

    Raises:
        ValueError: If channel is not None and not in 1-4.
    """
    if channel is not None and channel not in (1, 2, 3, 4):
        raise ValueError(f"Channel must be 1-4, got {channel}")

    master = parse_audio_master(registers["nr50"], registers["nr51"], registers["nr52"])

    channels: dict = {}
    if channel is None or channel == 1:
        channels["channel1"] = parse_audio_channel1(
            registers["nr10"],
            registers["nr11"],
            registers["nr12"],
            registers["nr13"],
            registers["nr14"],
        )
    if channel is None or channel == 2:
        channels["channel2"] = parse_audio_channel2(
            registers["nr21"],
            registers["nr22"],
            registers["nr23"],
            registers["nr24"],
        )
    if channel is None or channel == 3:
        channels["channel3"] = parse_audio_channel3(
            registers["nr30"],
            registers["nr31"],
            registers["nr32"],
            registers["nr33"],
            registers["nr34"],
            registers["wave_ram"],
        )
    if channel is None or channel == 4:
        channels["channel4"] = parse_audio_channel4(
            registers["nr41"],
            registers["nr42"],
            registers["nr43"],
            registers["nr44"],
        )

    return {**channels, "master": master}
