"""Emulator session wrapping PyBoy lifecycle."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pyboy import PyBoy

from blobert_mcp.kb.database import KnowledgeBase, kb_path_for_rom


class EmulatorSession:
    """Shared emulator state for all MCP tool handlers.

    One instance per server process. Holds the PyBoy emulator,
    save states, breakpoints, and knowledge base reference.
    """

    def __init__(self) -> None:
        self.pyboy: PyBoy | None = None
        self.rom_path: str | None = None
        self.save_states: dict[str, Any] = {}
        self.breakpoints: dict[str, Any] = {}
        self.kb: KnowledgeBase | None = None

    @property
    def rom_loaded(self) -> bool:
        return self.pyboy is not None

    def load_rom(self, path: str, *, headless: bool = True) -> None:
        """Load a ROM into the emulator."""
        self.shutdown()
        rom = Path(path)
        if not rom.is_file():
            raise FileNotFoundError(f"ROM not found: {path}")
        window = "null" if headless else "SDL2"
        self.pyboy = PyBoy(str(rom), window=window)
        self.rom_path = str(rom)
        self.kb = KnowledgeBase(kb_path_for_rom(str(rom)))

    def shutdown(self) -> None:
        """Stop the emulator and release resources."""
        if self.kb is not None:
            self.kb.close()
            self.kb = None
        if self.pyboy is not None:
            self.pyboy.stop()
            self.pyboy = None
            self.rom_path = None
