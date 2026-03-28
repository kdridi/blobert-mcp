# blobert-mcp

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status: Early Development](https://img.shields.io/badge/status-early%20development-orange.svg)]()

**An MCP server that lets LLMs play, inspect, and understand Game Boy ROMs.**

Load a ROM, press buttons, read memory, take screenshots, set breakpoints, trace execution, and build a knowledge base — all through natural conversation with an AI.

> Named after Blobert from *A Boy and His Blob* (Game Boy, 1990) — the companion who transforms into whatever tool you need. Give Blobert a jellybean, he becomes the tool you need.

---

## What does this look like?

A human and an AI sit down with a Game Boy ROM. The human plays; the AI watches the machine.

```
You:  "Load Tetris and press Start"
AI:   [loads ROM, presses Start, takes screenshot]
      "I see the game started. Memory at 0xFFE1 changed — that's probably the game state flag."

You:  "What happens when a line is cleared?"
AI:   [saves state, plays until line clear, diffs memory]
      "12 addresses changed. 0xFF9E decremented — that's the remaining lines counter.
       The function at 0x2B4F handles line clearing. I'll name it ClearCompletedLines."

You:  "Can you write a Python script to trace all writes to that address?"
AI:   [generates and runs a PyBoy hook script]
      "Done. Here are the 4 functions that modify the lines counter..."
```

The AI **sees the screen**, **reads the memory**, **controls the inputs**, and **builds understanding** — one jellybean at a time. The human brings intent, context, and domain knowledge. Together, they work faster than either could alone.

---

## How it works

```
┌─────────┐              ┌──────────┐     MCP      ┌──────────┐   PyBoy API   ┌─────────┐
│  Human  │◄────────────►│ Claude / │◄────────────►│ blobert  │◄────────────►│  PyBoy  │
│ (plays, │ conversation │ any LLM  │    tools     │   -mcp   │              │emulator │
│ observes)│              └──────────┘              │  + KB    │              └─────────┘
└─────────┘                                        └──────────┘
```

- **The human** plays the game, describes what they see, and guides the investigation
- **The LLM** calls MCP tools, reasons about the results, and builds understanding
- **blobert-mcp** wraps PyBoy as MCP tools and adds a persistent knowledge base
- **PyBoy** runs the Game Boy emulation (headless, fast, Python-native)

The **knowledge base** persists across sessions — so the AI builds understanding incrementally, not limited by any single context window.

---

## Planned tools

Like Blobert transforming with each jellybean flavor, every tool serves a different purpose:

| Category | What the AI will be able to do | Status |
|---|---|---|
| **Emulation** | Load ROMs, advance frames, press buttons, save/restore states | Planned |
| **Static analysis** | Disassemble code, read ROM bytes, find byte patterns, locate strings | Planned |
| **Debugging** | Set execution breakpoints, step through instructions, read/write registers | Planned |
| **Visual** | Screenshots, VRAM tiles, sprite inspection, tilemap viewer | Planned |
| **Knowledge base** | Name functions, define structs, annotate addresses, export symbols | Planned |
| **Hardware** | Bank switching info, interrupt status, timer/audio/serial state | Planned |

[Full specification (68 tools + 4 future) ->](docs/mcp-spec.md)

---

## Getting started

> **Status: Early development.** The MCP server is not yet implemented. What exists today is the specification, research, and vision described below.

Once the core is built, setup will look like:

```bash
# Clone and install from source
git clone https://github.com/user/blobert-mcp.git
cd blobert-mcp
uv pip install -e .

# Run the server with your own ROM
uv run blobert-mcp --rom your-game.gb
```

```json
// Claude Desktop config (future)
{
  "mcpServers": {
    "blobert": {
      "command": "uvx",
      "args": ["blobert-mcp", "--rom", "your-game.gb"]
    }
  }
}
```

Then just talk to Claude. Ask it to explore the ROM.

> **Note:** You must provide your own legally obtained ROM files. This project does not include or distribute any copyrighted game data.

---

## Why?

The Game Boy library spans thousands of games. A handful have been reverse-engineered by dedicated communities ([pokered](https://github.com/pret/pokered), [pokeyellow](https://github.com/pret/pokeyellow), [Zelda LADX](https://github.com/zladx/LADX-Disassembly)) — years of manual work by dozens of people, byte by byte.

Existing tools are powerful — BGB, mgbdis, Ghidra with GhidraBoy — but they require deep expertise and enormous time investment. **blobert-mcp** doesn't replace these tools or the people who use them. It adds a new collaborator to the workbench: an AI that can process large amounts of disassembly, recognize patterns across codebases, and maintain a structured knowledge base while the human drives the investigation.

The long-term aspiration: **accelerate ROM exploration so that any curious person can start understanding how their favorite games work**, and contribute to the collective effort of preserving game history through decompilation.

---

## How this differs from traditional RE tools

| Traditional workflow | With blobert-mcp |
|---|---|
| Open BGB, set breakpoints manually, take notes in a text file | Describe what you want to investigate in natural language; the AI sets breakpoints and annotates automatically |
| Cross-reference memory accesses by hand across disassembly listings | Ask "what writes to this address?" and get an answer with context |
| Build mental model of game logic over weeks/months | The knowledge base accumulates understanding across sessions, shareable and exportable |
| Requires deep GB hardware knowledge to start | The AI knows the memory map, register names, and hardware quirks — it explains as it goes |

This is not "AI replaces reverse engineers." It's "AI makes reverse engineering accessible to more people and faster for everyone."

---

## Status

**Early development** — this is the beginning of something ambitious.

We have:
- [x] [Detailed specification](docs/mcp-spec.md) of 68 MCP tools across 10 categories
- [x] [Research on LLM capabilities](docs/llm-forces.md) applied to Game Boy decompilation
- [x] [Exploration tree](docs/exploration-tree.md) for systematic knowledge building
- [x] [Development journal](docs/journal.md) documenting every idea, failure, and insight

We're building:
- [ ] Core MCP server (emulation, memory, registers, inputs)
- [ ] Static analysis tools (disassembly, cross-references)
- [ ] Visual tools (screenshots, VRAM, sprites)
- [ ] Knowledge base (annotations, functions, structs, export)

---

## FAQ

**Do I need to own the ROM?**
Yes. This project provides tools, not games. You must supply your own legally obtained ROM files.

**Which LLM works best?**
Any LLM that supports MCP tool use. Claude (Sonnet or Opus) is recommended for its strong reasoning and large context window. The multimodal capability (seeing screenshots) is important.

**Can this fully decompile a game automatically?**
Not yet — and that's not the V1 goal. V1 is a human+AI collaborative workflow. The AI assists; the human drives. Full automation is a long-term research direction.

**How is this different from using Ghidra or IDA?**
Those are powerful standalone tools for experts. blobert-mcp is a conversational interface — you describe what you want to understand, and the AI handles the tool orchestration. Think of it as a knowledgeable pair-programming partner for reverse engineering.

---

## Contributing

This project is at the intersection of emulation, reverse engineering, and AI. If any of these excite you, there's a place for you here.

**Read the [journal](docs/journal.md)** to understand where we've been and where we're going.

Ways to contribute:
- **Try the spec** — read [mcp-spec.md](docs/mcp-spec.md) and tell us if anything is unclear, infeasible, or missing
- **Implement a tool** — pick a P0 tool from the spec and build it
- **Test with a ROM** — once the core exists, try it on your favorite game and share what you learn
- **Open an issue** — questions, ideas, and feedback are all welcome

---

## Acknowledgments

- **[PyBoy](https://github.com/Baekalfen/PyBoy)** — the Python Game Boy emulator that makes this possible
- **[pret community](https://github.com/pret)** — pokered, pokecrystal, and other decompilation projects that show what's possible and inspire this work
- **[Pan Docs](https://gbdev.io/pandocs/)** — the definitive Game Boy technical reference
- **[Model Context Protocol](https://modelcontextprotocol.io/)** — the protocol that connects LLMs to tools
- **[mgbdis](https://github.com/mattcurrie/mgbdis)**, **[BGB](https://bgb.bircd.org/)**, **[GhidraBoy](https://github.com/Gekkio/GhidraBoy)** — the RE tools we stand on the shoulders of

---

## License

MIT

---
