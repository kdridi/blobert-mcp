# blobert-mcp — Specification

> **blobert-mcp** — A Boy and His Blob MCP
>
> MCP server exposing an instrumented Game Boy emulator and a knowledge
> base, so that an LLM can interactively explore and decompile ROMs.
>
> Built on [PyBoy](https://github.com/Baekalfen/PyBoy) (Python Game Boy emulator) and the
> [Model Context Protocol](https://modelcontextprotocol.io/) (MCP), the standard for connecting
> LLMs to external tools via JSON-RPC.

### How to read this spec

Each tool is classified by **implementation priority**:
- **P0** = essential, the system does not work without it (implement first)
- **P1** = important, necessary for a complete analysis workflow
- **P2** = nice-to-have, improves quality but not blocking

**Implementation order:** Start with all P0 tools (18 tools), then add P1 tools by section. P0 alone gives a functional exploration system.

### Conventions

- **Parameter naming:** all tools use `address` + `length` for memory ranges. `bank` is always optional (defaults to current bank).
- **Output limits:** all tools returning variable-length data accept an optional `limit` parameter (default: 256 entries or 4KB, whichever applies). Truncated results include `"truncated": true` and `"total": N` in the response.
- **Error format:** all tools return `{"error": "<code>", "message": "<description>"}` on failure. Common codes: `NO_ROM_LOADED`, `INVALID_ADDRESS`, `INVALID_BANK`, `TIMEOUT`, `NOT_FOUND`.

### Example workflow

A typical exploration session might look like:

```
1. gb_load_rom("tetris.gb")          — start the emulator
2. get_rom_header()                   — learn about the ROM (title, MBC type, banks)
3. get_session_info()                 — confirm what's loaded
4. gb_screenshot()                    — see the title screen
5. gb_press_button("start")           — press Start
6. gb_step(count=60, mode="frame")    — advance 1 second
7. gb_screenshot()                    — see what happened
8. gb_read_memory(0xC000, length=64)  — inspect WRAM
9. disassemble_at_pc(before=5, after=20)  — see code around current execution
10. kb_annotate(0xC000, label="game_state", type="data", comment="Main game state byte")
```

---

## 1. Static analysis and ROM reading

### `get_rom_header` — P0
Extract ROM metadata.
- **Input:** none
- **Output:** JSON (title, MBC type, ROM/RAM size, licensee, CGB/SGB flag, checksums)
- **Usage:** configure the analysis environment, determine the number of banks
- **PyBoy:** `pyboy.memory[0x0100:0x0150]` — parse header bytes directly

### `get_memory_map` — P0
Return the Game Boy memory map.
- **Input:** none
- **Output:** list of segments (name, address range, access type)
- **Usage:** the LLM knows where VRAM, WRAM, I/O, HRAM are located
- **PyBoy:** static data, no API call needed

### `read_rom_bytes` — P0
Read raw bytes from the ROM.
- **Input:** `address`, `length` (max 4096), `bank` (optional)
- **Output:** hexdump + ASCII representation
- **Usage:** manual data inspection, table extraction
- **PyBoy:** `pyboy.memory[bank, address]` for banked reads

### `get_vector_table` — P0
Read interrupt and reset vectors.
- **Input:** none
- **Output:** map of addresses with the code at each vector:
  - RST vectors: 0x00, 0x08, 0x10, 0x18, 0x20, 0x28, 0x30, 0x38
  - Interrupt vectors: 0x40 (VBlank), 0x48 (STAT), 0x50 (Timer), 0x58 (Serial), 0x60 (Joypad)
  - Entry point: 0x100
- **Usage:** identify interrupt handlers and entry point
- **PyBoy:** `pyboy.memory[addr:addr+N]` — read and disassemble each vector

### `disassemble_range` — P0
Disassemble a range of addresses.
- **Input:** `address`, `length` or `end_address`, `bank` (optional)
- **Output:** list of instructions (address, hex opcode, mnemonic, operands), max 256 instructions
- **Usage:** read the disassembled code
- **PyBoy:** read bytes via `pyboy.memory`, decode with SM83 instruction table (custom implementation)

### `disassemble_function` — P0
Disassemble an entire function (up to unconditional RET/JP).
- **Input:** `entry_point`, `bank` (optional)
- **Output:** list of instructions + function size
- **Usage:** isolate a logical unit of code
- **PyBoy:** same as `disassemble_range` with dynamic endpoint detection

### `disassemble_at_pc` — P0
Disassemble code around the current program counter.
- **Input:** `before` (int, instructions before PC, default 5), `after` (int, instructions after PC, default 20)
- **Output:** list of instructions with current PC marked
- **Usage:** see what code is executing right now — the most common debugging operation
- **PyBoy:** read PC from `pyboy.register_file.PC`, then disassemble surrounding region

### `get_control_flow_graph` — P1
Build the control flow graph of a function.
- **Input:** `address`, `bank` (optional)
- **Output:** list of basic blocks + edges (adjacency list)
- **Usage:** understand conditional logic (if/else, loops, switch)
- **PyBoy:** custom implementation on top of disassembly

### `get_cross_references` — P1
Find all references to/from an address.
- **Input:** `address`, `direction` ("to" | "from" | "both")
- **Output:** list of source addresses with type (CALL, JP, JR, LD), max 100 results
- **Usage:** "who calls this function?", "who reads this variable?"
- **PyBoy:** requires full ROM scan — custom implementation

### `find_byte_pattern` — P1
Search for a byte sequence in the ROM (with wildcards).
- **Input:** `pattern` (hex, `??` for wildcard), `address` (optional start), `length` (optional range)
- **Output:** list of found addresses, max 100 results
- **Usage:** find known function signatures, DMA routines
- **PyBoy:** sequential scan of ROM bytes

### `find_strings` — P1
Find text strings in the ROM.
- **Input:** `encoding` ("ascii" | "gb_custom"), `min_length` (default 4)
- **Output:** list (address, decoded text), max 200 results
- **Usage:** locate dialogues, names, debug messages
- **PyBoy:** sequential scan with encoding table

### `calculate_entropy` — P2
Calculate Shannon entropy over a range.
- **Input:** `address`, `length`, `window_size` (default 256)
- **Output:** list of entropy scores (0.0 to 1.0) per window
- **Usage:** distinguish code (medium entropy) / compressed data (high) / padding (low)
- **PyBoy:** pure math on ROM bytes

---

## 2. Dynamic execution and debugging

### `gb_load_rom` — P0
Load a ROM into the emulator.
- **Input:** `rom_path`, `headless` (bool, default true)
- **Output:** status + loaded ROM header
- **Usage:** initialize the emulation session
- **PyBoy:** `PyBoy(rom_path, window='null')` for headless

### `gb_step` — P0
Advance execution.
- **Input:** `count` (int), `mode` ("frame" | "instruction")
- **Output:** current PC, current instruction, registers
- **Usage:** advance step by step or frame by frame
- **PyBoy:** `pyboy.tick()` for frames. Instruction-level stepping requires hook-based implementation — set a hook at the next instruction address
- **Note:** instruction-level stepping has overhead due to hook setup/teardown. Frame stepping is fast and preferred for bulk advancement

### `gb_run_until` — P0
Execute until an address or a timeout.
- **Input:** `target_address`, `timeout_frames` (int, default 600 = ~10s), `timeout_ms` (int, optional fallback)
- **Output:** registers at breakpoint or timeout error
- **Usage:** execute until the end of a function
- **PyBoy:** `pyboy.hook_register(bank, target_address, callback)` + tick loop with frame counter

### `gb_get_registers` — P0
Read all CPU registers.
- **Input:** none
- **Output:** JSON {A, B, C, D, E, F, H, L, AF, BC, DE, HL, SP, PC, flags: {Z, N, H, C}}
- **Usage:** understand the CPU state at any moment
- **PyBoy:** `pyboy.register_file` — access A, B, C, D, E, F, H, L, SP, PC directly

### `gb_set_register` — P1
Write to a register.
- **Input:** `register` (string), `value` (int)
- **Output:** confirmation
- **Usage:** test hypotheses ("what happens if A=0x42?")
- **PyBoy:** register_file properties are writable

### `gb_read_memory` — P0
Read memory (RAM, VRAM, I/O, etc.).
- **Input:** `address`, `length` (max 4096), `bank` (optional for CGB WRAM/VRAM)
- **Output:** hexdump + ASCII
- **Usage:** inspect variables, tiles, game state
- **PyBoy:** `pyboy.memory[address:address+length]` or `pyboy.memory[bank, address]`

### `gb_write_memory` — P1
Write to memory.
- **Input:** `address`, `data` (hex string or byte array)
- **Output:** confirmation
- **Usage:** modify game state for testing (force lives, change screen)
- **PyBoy:** `pyboy.memory[address] = value`

### `gb_memory_diff` — P1
Compare memory between two save states.
- **Input:** `address`, `length`, `state_a` (state_id), `state_b` (state_id)
- **Output:** list of addresses that changed with old/new values
- **Usage:** isolate variables modified by an action
- **Implementation:** load state_a, dump memory range, load state_b, dump memory range, diff. Restores original state after comparison.

### `gb_set_breakpoint` — P1
Set an execution breakpoint.
- **Input:** `address`, `bank` (optional), `condition` (optional, evaluated in callback: e.g. "A == 0x01")
- **Output:** breakpoint_id
- **Usage:** stop when a function is called
- **PyBoy:** `pyboy.hook_register(bank, address, callback)`. Conditions are evaluated in the Python callback by inspecting register_file.
- **V1 limitation:** execution breakpoints only. Memory read/write watchpoints are not supported by PyBoy and would require polling-based workarounds (deferred to V2).

### `gb_remove_breakpoint` — P1
Remove a breakpoint.
- **Input:** `breakpoint_id`
- **Output:** confirmation

### `gb_list_breakpoints` — P1
List active breakpoints.
- **Input:** none
- **Output:** list of breakpoints with their addresses, banks, and conditions

### `gb_get_call_stack` — P1
Reconstruct the call stack from the current SP.
- **Input:** `max_depth` (int, default 16)
- **Output:** list of return addresses found on the stack, with KB labels if available
- **Usage:** understand execution context when stopped at a breakpoint
- **Implementation:** read stack memory from SP upward, cross-reference return addresses with known function boundaries in the KB. Heuristic — may include false positives on non-CALL stack entries.

---

## 3. Traces and profiling

> **Feasibility warning:** PyBoy does not provide instruction-level tracing or memory access logging APIs. The tools in this section require custom instrumentation built on top of `hook_register()`. Full instruction tracing (hooking every address) is impractical. These tools use sampling and targeted approaches instead.

### `gb_trace_start` — P1
Start recording executed instructions at hooked addresses.
- **Input:** `address` (start of range), `length` (range to instrument), `format` ("minimal" | "verbose"), `max_instructions` (int, default 1000, max 10000)
- **Output:** trace_id
- **Usage:** record the execution path through a specific function or code region
- **Minimal format:** address + opcode
- **Verbose format:** address + opcode + registers
- **Implementation:** hooks are placed at known instruction boundaries within the specified range. This is feasible for small ranges (single functions, ~100-500 bytes) but not for full ROM banks.
- **PyBoy:** multiple `hook_register()` calls within the range

### `gb_trace_stop` — P1
Stop recording and retrieve the trace.
- **Input:** `trace_id`
- **Output:** list of executed instructions (chosen format), truncated at max_instructions

### `gb_get_hotspots` — P1
Profile the most executed addresses by sampling.
- **Input:** `top_n` (int, default 20), `duration_frames` (int, default 300)
- **Output:** sorted list (address, execution count, % of total)
- **Usage:** identify the main loop, rendering routines, "hot zones"
- **Implementation:** sample PC at regular intervals (e.g., every tick) during the duration. This gives statistical hotspots, not exact counts.
- **PyBoy:** read `register_file.PC` after each `tick()`

### `gb_get_memory_access_log` — P2 (deferred from P1)
Log memory accesses over a range.
- **Input:** `address`, `length`, `duration_frames`, `type` ("read" | "write" | "both")
- **Output:** list (frame, address, value, PC)
- **Usage:** "which function modifies 0xC100?"
- **Implementation:** PyBoy has no memory watchpoint API. This requires polling: snapshot the memory range each frame (or every N frames) and report changes. Only detects *writes* (by delta), not reads. For true access logging, an alternative emulator backend would be needed.
- **V1 alternative:** use `gb_memory_diff` between save states to approximate this.

### `gb_get_cycles` — P2
Count CPU cycles since a reference point.
- **Input:** none
- **Output:** CPU cycle count
- **Usage:** measure the cost of a routine, verify timing

---

## 4. Save states and exploration

### `gb_save_state` — P0
Save the complete emulator state.
- **Input:** `name` (string, optional)
- **Output:** state_id
- **Usage:** create checkpoints to explore different paths
- **PyBoy:** `pyboy.save_state(file_like_object)` — saves to BytesIO in memory

### `gb_load_state` — P0
Restore a saved state.
- **Input:** `state_id`
- **Output:** confirmation + PC and registers after restoration
- **PyBoy:** `pyboy.load_state(file_like_object)`

### `gb_list_states` — P1
List all available save states.
- **Input:** none
- **Output:** list (state_id, name, frame, PC, timestamp)

### `gb_delete_state` — P2
Delete a save state.
- **Input:** `state_id`
- **Output:** confirmation

---

## 5. Inputs and input sequences

> **Terminology:** an "input sequence" is a list of timestamped button presses, similar to a TAS movie file. The LLM generates the sequence; the emulator plays it deterministically.

### `gb_press_button` — P0
Press or release a button.
- **Input:** `button` ("a" | "b" | "start" | "select" | "up" | "down" | "left" | "right"), `action` ("press" | "release")
- **Output:** confirmation
- **PyBoy:** `pyboy.button_press(button)` / `pyboy.button_release(button)`

### `gb_play_input_sequence` — P1
Play a sequence of timestamped inputs.
- **Input:** `sequence` (list of {frame, button, action}), `max_frames` (int, default 3600 = ~60s)
- **Output:** final state (registers, PC, screenshot)
- **Usage:** deterministically replay a series of inputs
- **PyBoy:** loop of `button_press`/`button_release` + `tick()` with frame counter

### `gb_record_input_sequence` — P2
Record inputs during execution (for human-player mode).
- **Input:** `duration_frames`
- **Output:** recorded sequence (list of {frame, button, action})

---

## 6. Visual and multimodal

### `gb_screenshot` — P0
Capture the game screen.
- **Input:** `format` ("png" | "webp", default "png"), `scale` (int, default 1)
- **Output:** base64 image
- **Usage:** the LLM SEES what is happening on screen
- **PyBoy:** `pyboy.screen.image` returns a PIL Image — convert to base64

### `gb_inspect_vram` — P1
Visualize the VRAM contents (tiles).
- **Input:** `bank` (0 or 1 for CGB)
- **Output:** composite image of all tiles + JSON (tile IDs)
- **Usage:** identify graphics, understand ROM -> VRAM mapping
- **PyBoy:** tile API via `pyboy.tilemap_background` / `pyboy.tilemap_window`, individual tiles via tile objects

### `gb_get_tilemap` — P1
Extract the tilemap (background or window).
- **Input:** `layer` ("background" | "window"), `show_grid` (bool)
- **Output:** annotated image + JSON (position -> tile ID)
- **Usage:** understand level structure
- **PyBoy:** `pyboy.tilemap_background` / `pyboy.tilemap_window` — `tile_identifier(col, row)`

### `gb_list_sprites` — P1
List active sprites (OAM).
- **Input:** none
- **Output:** list of 40 entries (x, y, tile_id, attributes, on_screen) + images of visible sprites
- **Usage:** identify game entities (player, enemies, projectiles)
- **PyBoy:** `pyboy.sprite(index)` — properties: x, y, tile_identifier, attributes, on_screen

### `gb_read_palettes` — P2
Read color palettes.
- **Input:** none
- **Output:** JSON of palettes (DMG: BGP, OBP0, OBP1 / CGB: 8xBG + 8xOBJ)
- **Usage:** understand visual effects (fade, flash, night/day)
- **DMG implementation:** read I/O registers 0xFF47 (BGP), 0xFF48 (OBP0), 0xFF49 (OBP1)
- **CGB implementation:** CGB palettes are accessed through indexed I/O (BCPS/BCPD at 0xFF68/0xFF69 and OCPS/OCPD at 0xFF6A/0xFF6B). Requires sequential reads through the index registers.

### `gb_visual_diff` — P2
Compare two screenshots.
- **Input:** `image_a` (base64 or state_id), `image_b`
- **Output:** heatmap image of differences
- **Usage:** "what changed on screen when I pressed A?"

---

## 7. Hardware-specific and edge cases

### `gb_get_bank_info` — P0
Bank switching information.
- **Input:** none
- **Output:** MBC type, current ROM bank, current RAM bank, total number of banks
- **Usage:** know in which context the code is executing
- **PyBoy:** MBC type from header. Current bank: read the MBC register at the cartridge address (MBC-type dependent, e.g., 0x2000-0x3FFF for ROM bank). PyBoy does not expose current bank directly — requires reading MBC state from memory.

### `gb_read_banked` — P0
Read memory from a specific bank.
- **Input:** `bank`, `address`, `length` (max 4096)
- **Output:** hexdump
- **Usage:** access code/data in any ROM/RAM bank
- **PyBoy:** `pyboy.memory[bank, address]`

### `gb_trace_bank_switches` — P1
Log bank switches over a duration.
- **Input:** `duration_frames`
- **Output:** list (frame, PC, new bank, MBC write address)
- **Usage:** understand the multi-bank structure of the ROM
- **Implementation:** hook writes to MBC register addresses (0x2000-0x3FFF for most MBCs). Log each write with PC and written value.

### `gb_get_interrupt_status` — P0 (promoted from P1)
Interrupt status.
- **Input:** none
- **Output:** JSON {IME, IE (0xFFFF), IF (0xFF0F)} with individual flags: VBlank, STAT, Timer, Serial, Joypad
- **Usage:** know which interrupts are active — fundamental to understanding any GB program's execution
- **PyBoy:** read memory at 0xFFFF (IE) and 0xFF0F (IF). IME is not directly readable via PyBoy's public API — may need to track DI/EI instructions.

### `gb_get_lcd_status` — P1
LCD status registers.
- **Input:** none
- **Output:** JSON {LCDC (0xFF40), STAT (0xFF41), SCY (0xFF42), SCX (0xFF43), LY (0xFF44), LYC (0xFF45), WY (0xFF4A), WX (0xFF4B)}
- **Usage:** understand scanline-based rendering effects, STAT interrupt timing, window positioning
- **PyBoy:** direct memory reads of I/O registers

### `gb_detect_ram_execution` — P1
Check if the current PC points to RAM (self-modifying code or code copied to RAM).
- **Input:** none
- **Output:** bool + RAM address if detected + disassembly of code at that location
- **Usage:** identify routines copied to HRAM (typically OAM DMA)
- **Implementation:** check whether current PC falls in RAM ranges (0xC000-0xDFFF for WRAM, 0xFF80-0xFFFE for HRAM). Point-in-time check, not continuous monitoring.
- **PyBoy:** read `register_file.PC` and compare against RAM address ranges

### `gb_get_timer_state` — P2
Timer status.
- **Input:** none
- **Output:** JSON {DIV (0xFF04), TIMA (0xFF05), TMA (0xFF06), TAC (0xFF07), enabled, frequency}

### `gb_get_audio_state` — P2
Audio register status.
- **Input:** `channel` (1-4, optional for all)
- **Output:** JSON of NRxx registers + wave RAM (channel 3)

### `gb_get_serial_state` — P2
Serial interface status (Link Cable).
- **Input:** none
- **Output:** JSON {SB (0xFF01), SC (0xFF02), transfer_in_progress}

### `gb_get_cgb_state` — P2
Game Boy Color specific status.
- **Input:** none
- **Output:** JSON {double_speed, vram_bank, wram_bank, hdma_status}

---

## 8. Knowledge base and annotations

### `kb_annotate` — P0
Annotate an address.
- **Input:** `address`, `bank` (optional), `label` (string), `type` ("code" | "data" | "gfx" | "audio" | "text"), `comment` (string)
- **Output:** annotation_id
- **Usage:** progressively build understanding of the ROM

### `kb_define_function` — P0
Define a function.
- **Input:** `address`, `end_address`, `bank` (optional), `name`, `params` (list), `description`, `returns`
- **Output:** function_id

### `kb_define_struct` — P1
Define a data structure.
- **Input:** `name`, `fields` (list of {name, offset, type, size, comment})
- **Output:** struct_id

### `kb_apply_struct` — P1
Apply a struct to a memory region.
- **Input:** `address`, `struct_name`, `count` (for arrays)
- **Output:** address -> field mapping

### `kb_define_enum` — P1
Define an enumeration.
- **Input:** `name`, `values` (dict name -> value)
- **Output:** enum_id

### `kb_define_variable` — P0
Name a RAM variable.
- **Input:** `address`, `name`, `type` (u8/u16/bool/enum), `description`
- **Output:** variable_id

### `kb_search` — P0
Search the knowledge base.
- **Input:** `query` (text), `filter` ("label" | "comment" | "address" | "type")
- **Output:** results sorted by relevance, max 50 results
- **Search behavior:** exact match on addresses, substring match on labels and comments, type filtering via enum match

### `kb_get_function_info` — P1
Retrieve all information about a function.
- **Input:** `address` or `name`
- **Output:** definition + local variables + calls + callers + comments

### `kb_export` — P1
Export the knowledge base in an exploitable format.
- **Input:** `format` ("sym" | "asm" | "c_header" | "json")
- **Output:** file contents
- **Usage:** generate the final annotated source code

### `kb_import_symbols` — P1
Import existing symbols.
- **Input:** `file_path`, `format` ("sym" | "pokered" | "auto")
- **Output:** number of imported annotations

### `kb_get_history` — P2
History of modifications to an annotation.
- **Input:** `address`
- **Output:** chronological list (date, old value, new value, reason)

### `kb_stats` — P2
Statistics on decompilation progress.
- **Input:** none
- **Output:** JSON {total_addresses, annotated, functions_named, variables_named, coverage_pct}

---

## 9. Session management

### `get_session_info` — P0
Get the current session state.
- **Input:** none
- **Output:** JSON {rom_loaded, rom_title, frame_count, pc, annotations_count, save_states_count, breakpoints_count}
- **Usage:** helps the LLM orient itself, especially at the start of a conversation or after context window truncation

### `gb_reset` — P0
Reset the emulator (without reloading the ROM).
- **Input:** none
- **Output:** confirmation

### `gb_get_frame_count` — P1
Number of frames elapsed since startup.
- **Input:** none
- **Output:** frame_count (int)

### `gb_set_speed` — P2
Change the emulation speed.
- **Input:** `multiplier` (int, 0 = unlimited)
- **Output:** confirmation
- **PyBoy:** `pyboy.set_emulation_speed(multiplier)`

---

## Future: RAG and pattern matching

> **Note:** These tools require a pre-built vector database of annotated Game Boy code (e.g., from pokered, pokecrystal). Building this database is a significant effort and is deferred to V2. The tools are documented here for completeness and to guide future development.

### `rag_search_similar` — future
Search for similar ASM blocks in a reference database.
- **Input:** `asm_block` (ASM text), `top_n`
- **Output:** list of results (source, name, similarity score, corresponding annotated code)
- **Usage:** "this block resembles ReadJoypad from pokered at 92%"

### `rag_find_signature` — future
Search for a known function signature.
- **Input:** `hex_pattern` (with wildcards), `library` ("gbdk" | "pokered" | "all")
- **Output:** matches (function name, library, score)

### `rag_detect_engine` — future
Identify the development toolchain or library used.
- **Input:** none (analyzes the header + first code blocks)
- **Output:** JSON {toolchain_name, confidence, known_functions}
- **Note:** Game Boy games don't have "engines" in the modern sense. This detects toolchains (GBDK-compiled vs hand-written ASM) and known library routines, not game engines.

### `rag_index_pair` — future
Add a raw ASM <-> annotated ASM pair to the reference database.
- **Input:** `raw_asm`, `annotated_asm`, `source` (e.g.: "pokered"), `function_name`
- **Output:** confirmation

---

## Recommended storage

**SQLite** for the knowledge base (kb_*):
- Relational queries ("all functions that write to this struct")
- Referential integrity
- History via versioning table
- Single file, portable

**JSON files** for exports and save states.

**Vector embeddings** (ChromaDB or FAISS) for RAG (future/V2).

---

## Summary by priority

| Priority | Tool count | Categories |
|:--------:|:----------:|------------|
| P0 | 25 | ROM reading, disassembly (incl. at-PC), execution, registers, memory, save states, inputs, screenshot, session, bank info, interrupt status, basic annotations |
| P1 | 29 | CFG, cross-refs, patterns, strings, breakpoints, call stack, traces (targeted), profiling, advanced visuals, LCD status, bank switch logging, KB structs/enums/export/import |
| P2 | 14 | Entropy, memory access log, cycles, speed, palettes, visual diff, timing, audio, serial, CGB, input recording, KB history/stats |
| Future | 4 | RAG search, signature matching, toolchain detection, reference indexing |

**Total: 72 MCP tools** (68 active + 4 future)
