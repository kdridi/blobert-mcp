"""Hardware I/O register MCP tools."""

from __future__ import annotations

from blobert_mcp.domain import io_registers


def register_io_register_tools(mcp, session) -> None:
    """Register hardware I/O register tools with the FastMCP instance."""

    @mcp.tool()
    def gb_get_lcd_status() -> dict:
        """Read LCD/PPU registers and return parsed state.

        Reads LCDC (0xFF40), STAT (0xFF41), SCY/SCX, LY/LYC, WY/WX.
        LCDC and STAT bits are decoded into named fields.
        Returns error if no ROM loaded.
        """
        if not session.rom_loaded:
            return {
                "error": "NO_ROM_LOADED",
                "message": "Load a ROM first with gb_load_rom.",
            }
        mem = session.pyboy.memory
        return io_registers.parse_lcd_status(
            lcdc=mem[0xFF40],
            stat=mem[0xFF41],
            scy=mem[0xFF42],
            scx=mem[0xFF43],
            ly=mem[0xFF44],
            lyc=mem[0xFF45],
            wy=mem[0xFF4A],
            wx=mem[0xFF4B],
        )

    @mcp.tool()
    def gb_get_timer_state() -> dict:
        """Read timer registers and return parsed state.

        Reads DIV (0xFF04), TIMA (0xFF05), TMA (0xFF06), TAC (0xFF07).
        TAC is decoded into enabled flag and frequency.
        Returns error if no ROM loaded.
        """
        if not session.rom_loaded:
            return {
                "error": "NO_ROM_LOADED",
                "message": "Load a ROM first with gb_load_rom.",
            }
        mem = session.pyboy.memory
        return io_registers.parse_timer_state(
            div=mem[0xFF04],
            tima=mem[0xFF05],
            tma=mem[0xFF06],
            tac=mem[0xFF07],
        )

    @mcp.tool()
    def gb_get_audio_state(channel: int | None = None) -> dict:
        """Read audio registers and return parsed state.

        Optional channel param (1-4) for a single channel.
        Without channel, returns all channels plus master control.
        Channel 3 includes wave RAM (0xFF30-0xFF3F).
        Returns error if no ROM loaded or invalid channel.
        """
        if not session.rom_loaded:
            return {
                "error": "NO_ROM_LOADED",
                "message": "Load a ROM first with gb_load_rom.",
            }
        if channel is not None and channel not in (1, 2, 3, 4):
            return {
                "error": "INVALID_PARAMETER",
                "message": f"Channel must be 1-4, got {channel}.",
            }
        mem = session.pyboy.memory
        regs = {
            "nr10": mem[0xFF10],
            "nr11": mem[0xFF11],
            "nr12": mem[0xFF12],
            "nr13": mem[0xFF13],
            "nr14": mem[0xFF14],
            "nr21": mem[0xFF16],
            "nr22": mem[0xFF17],
            "nr23": mem[0xFF18],
            "nr24": mem[0xFF19],
            "nr30": mem[0xFF1A],
            "nr31": mem[0xFF1B],
            "nr32": mem[0xFF1C],
            "nr33": mem[0xFF1D],
            "nr34": mem[0xFF1E],
            "nr41": mem[0xFF20],
            "nr42": mem[0xFF21],
            "nr43": mem[0xFF22],
            "nr44": mem[0xFF23],
            "nr50": mem[0xFF24],
            "nr51": mem[0xFF25],
            "nr52": mem[0xFF26],
            "wave_ram": list(mem[0xFF30:0xFF40]),
        }
        return io_registers.parse_audio_state(regs, channel=channel)

    @mcp.tool()
    def gb_get_serial_state() -> dict:
        """Read serial port registers and return parsed state.

        Reads SB (0xFF01) and SC (0xFF02). SC is decoded into
        transfer_in_progress and clock_source fields.
        Returns error if no ROM loaded.
        """
        if not session.rom_loaded:
            return {
                "error": "NO_ROM_LOADED",
                "message": "Load a ROM first with gb_load_rom.",
            }
        mem = session.pyboy.memory
        return io_registers.parse_serial_state(
            sb=mem[0xFF01],
            sc=mem[0xFF02],
        )
