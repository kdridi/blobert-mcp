# The 6 LLM Capabilities Applied to Game Boy Decompilation

> This document identifies 6 fundamental capabilities of LLMs and the
> concrete advantages they bring to Game Boy ROM reverse engineering —
> when the LLM receives the right data through the right interface.
>
> For each capability, we describe:
> - **What it enables** — specific game-changing applications
> - **Required Data** — what must be provided to the LLM
> - **How to Obtain** — which tool or control mode
> - **Limitations** — where this capability breaks down
>
> ### Emulator control modes
>
> - **MCP**: the LLM calls blobert-mcp tools directly (load_rom, read_memory,
>   set_breakpoint, save_state, press_button, screenshot...) within its
>   reasoning loop. Interactive and exploratory.
> - **Input Sequence**: a JSON list of timestamped button presses
>   (similar to a TAS movie file). The LLM generates it via
>   `gb_play_input_sequence`; the emulator plays it deterministically and
>   returns the results. Useful for "do X, then observe Y" experiments.
> - **Script**: Python code using the PyBoy API directly. The LLM writes
>   the script; the human (or a tool) runs it. Best for batch operations
>   that would be too slow interactively (e.g., hooking 100 addresses).
> - **Static**: data obtained without execution (disassembly, hexdump,
>   documentation). No emulator needed.

---

## Executive Summary

The 6 capabilities, ranked by impact on V1 (human+LLM collaborative decompilation):

| # | Capability | V1 Impact | Key application |
|---|---|---|---|
| 1 | Collaborative Reasoning | Critical | The human+LLM conversation itself is the methodology |
| 2 | Pattern Matching | High | Function naming, algorithm recognition, code vs data |
| 3 | Translation Between Representations | High | ASM -> explanation, ASM -> C, binary -> semantic names |
| 4 | Reasoning by Analogy | Medium | Cross-domain insights, genre-based deduction |
| 5 | Broad Context Synthesis | Medium | Cross-bank coherence, documentation generation |
| 6 | Constrained Generation | Aspirational | Binary-identical recompilable code (long-term goal) |

---

## Chapter 1 — Collaborative Reasoning

**Definition:** The LLM is not just an analyzer — it is an interactive reasoning partner.
It asks clarifying questions, proposes hypotheses, explains its thinking, adjusts based
on feedback, and maintains a structured investigation. The human-in-the-loop conversation
IS the core methodology for V1.

### 1. Interactive Hypothesis Testing

The LLM proposes: "I think 0xC100 is the player's X position." The human moves the
character right. The LLM reads memory: "0xC100 incremented from 0x30 to 0x38 — hypothesis
confirmed." This propose-test-confirm loop is the fundamental workflow.

- **Required Data:** emulator access + human observations
- **How to Obtain:**
  - **MCP**: save state, propose hypothesis, ask human to perform action, read memory, compare
  - **Input Sequence**: the LLM generates inputs to test its own hypotheses automatically
- **Why this matters:** traditional tools require the human to form AND test every hypothesis. Here, the AI proposes; the human validates or corrects.

### 2. On-the-Fly Script Generation

The LLM doesn't just analyze — it *writes tools*. "I'll write a Python script that hooks
every CALL instruction in bank 3 and logs the call graph." It generates the PyBoy script,
the human runs it, the results feed back into the conversation.

- **Required Data:** PyBoy API documentation + analysis context
- **How to Obtain:**
  - **Script**: the LLM generates Python code tailored to the current investigation
  - **MCP**: for simpler operations, the LLM uses MCP tools directly
- **Why this matters:** the LLM isn't limited to the pre-built MCP tools. It can create custom analysis tools on demand — a programmer that writes its own instruments.

### 3. Progressive Knowledge Building

Over multiple sessions, the LLM and human build a shared knowledge base: named functions,
documented structs, annotated memory regions. Each session starts where the last left off.
The knowledge base is the LLM's long-term memory.

- **Required Data:** persistent knowledge base (KB) + session context
- **How to Obtain:**
  - **MCP**: `kb_annotate`, `kb_define_function`, `kb_search`, `kb_export`
  - The KB compensates for the LLM's context window limits by storing discoveries persistently

**Limitations:**
- The LLM's reasoning quality degrades in very long conversations (100+ turns). The KB mitigates this, but the human should watch for the LLM "forgetting" earlier discoveries.
- The LLM may propose confidently wrong hypotheses. The human must remain the skeptic. Trust but verify — always check against the emulator.
- Script generation can produce buggy code. The human should review scripts before running them, especially those that modify emulator state.

---

## Chapter 2 — Pattern Matching

**Definition:** An LLM has been trained on billions of tokens of code,
technical documentation, reverse engineering, hardware architecture, and
game design. It recognizes structures it has seen before, even when optimized
or fragmented.

### 1. Context-Aided Function Identification

An anonymous routine `sub_1234` becomes `UpdateSpriteAnimation`. The LLM
recognizes intent through the structure of the control flow graph and the
registers used. A regex searches for exact bytes; the LLM searches for intent.

- **Required Data:** disassembled ASM code + control flow graph (CFG) + surrounding context (what calls this function, what memory it accesses)
- **How to Obtain:**
  - ASM code -> **Static**: mgbdis or Ghidra disassemble the ROM directly
  - CFG -> **Static**: Ghidra/Rizin generate the CFG through static analysis
  - Enriched CFG -> **MCP**: the LLM sets breakpoints at conditional branches, explores both paths via save_state/load_state, and builds a dynamic CFG more complete than the static one
- **Note:** the LLM needs significant context to name well. A function in isolation gets a vague name; a function with its callers, callees, and memory access patterns gets a meaningful one. Always provide context.

### 2. Data Structure Reconstruction and Semantic Typing

Address `0xC001` is not "a byte" — it is `player.currentHP` in a
`PlayerStats` struct. The LLM correlates memory accesses across the codebase:
three consecutive `ld` instructions to `$C000-$C002` suggest a struct
`Entity {x, y, sprite_id}`. Ghidra sees numeric offsets. The LLM sees a
logical object with named fields.

- **Required Data:** memory dumps at different game states + ASM code of all functions accessing the region
- **How to Obtain:**
  - Memory dumps -> **MCP**: the LLM requests snapshots at key moments (after a battle, after a screen change), uses `gb_memory_diff` to isolate changes
  - ASM code of accessors -> **Script**: cross-reference execution traces with the disassembly
  - Targeted exploration -> **MCP + Input Sequence**: the LLM generates input sequences that exercise different mechanics (combat, menu, movement) to see which functions access which regions

### 3. Toolchain and Library Detection

The LLM recognizes patterns characteristic of GBDK-compiled code versus
hand-written assembly, or identifies common library routines (DMA transfer,
joypad reading, VBlank wait). It can say "this ROM was compiled with GBDK"
by looking at function prologues and calling conventions.

- **Required Data:** interrupt vector table + prologues of main functions
- **How to Obtain:**
  - Interrupt vectors -> **Static**: fixed addresses (0x40=VBlank, 0x48=STAT, 0x50=Timer, 0x58=Serial, 0x60=Joypad), direct ROM read
  - Prologues -> **Static**: mgbdis/Ghidra extract the first instructions of each identified routine
  - Dynamic prologues -> **MCP**: the LLM triggers interrupts (via write to 0xFF0F, requires IME enabled and corresponding IE bit set) and observes which routine is called
- **Note:** Game Boy games don't have "engines" in the modern sense — they're mostly bespoke assembly. This capability detects *toolchains* and *common library patterns*, not game engines. Don't expect "this is the Link's Awakening engine."

### 4. Code vs Data Discrimination

The LLM detects entropy and repetitive structures typical of tiles or
audio, where a linear disassembler blindly attempts to decode sprites as
CPU instructions. High-entropy bytes in the middle of regular code are
likely compressed data.

- **Required Data:** raw hexdump + local entropy analysis + execution traces
- **How to Obtain:**
  - Hexdump -> **Static**: direct ROM read
  - Entropy -> **Script**: Shannon entropy via sliding window
  - Code/data validation -> **MCP**: compare hexdump with actually executed addresses. Anything never executed = confirmed data

### 5. Algorithm Recognition

A sequence of shifts and XORs -> the LLM recognizes an LFSR (pseudo-random
number generator). A decrement pattern with lookup table -> LZ compression.
It recognizes AABB collision tests, RLE decoders, PRNGs — even when
optimized for the SM83 architecture. It has seen these patterns thousands
of times in other contexts.

- **Required Data:** isolated function ASM code + register input/output values
- **How to Obtain:**
  - Isolated ASM code -> **Static**: extract routine between label and RET
  - I/O values -> **MCP**: breakpoint at function entry and exit, read registers. Replay with different inputs via save_state/load_state
  - Systematic I/O -> **Input Sequence**: generate sequences with varied inputs, capture registers at each pass

**Limitations:**
- **Hallucinated patterns.** The LLM will sometimes "recognize" patterns that aren't there — confidently naming a function based on superficial similarity. Always verify named functions by testing them in the emulator (does the behavior match the name?).
- **Context dependency.** Function naming quality drops sharply without context. An isolated function gets a generic name; the same function with its callers and memory map gets a precise one.
- **Toolchain detection is probabilistic.** The LLM is guessing based on patterns, not running a definitive test. Confidence scores should be treated as rough estimates.

---

## Chapter 3 — Translation Between Representations

**Definition:** An LLM is a universal translator. It converts
assembly code -> C, code -> natural language, low-level operations ->
high-level algorithms, binary structures -> semantic names. The translation
is always approximate but often useful.

### 1. Variable Naming by Hardware Context

If a function manipulates `LCDC` and `STAT` registers, the LLM names
a local variable `is_vblank` rather than `uVar1`. IDA cannot invent names.
The LLM uses the Game Boy memory map and Pandocs as a dictionary.

- **Required Data:** LR35902 hardware specifications + routine ASM code
- **How to Obtain:**
  - Hardware specs -> **Static**: Pandocs, public LR35902 documentation. Injected into LLM context
  - ASM code -> **Static**: standard disassembly
  - No emulator needed — pure pattern matching on code + documentation

### 2. ASM -> Readable C (Iterative)

Transform `jr nz` into `while()`, cascades of `cp` into `switch/case`.
The LLM produces C code that captures the intent of the original assembly,
not "garbage C" with `goto` everywhere.

- **Required Data:** clean ASM code + target C style example (e.g., pokered source)
- **How to Obtain:**
  - ASM code -> **Static**: standard disassembly
  - Style examples -> **Static**: existing open source projects (pokered, pokecrystal) as reference
  - Validation -> **Script**: recompile with GBDK/RGBDS, compare checksum
- **Important caveat:** LLMs produce *plausible* C but rarely *compilable* C for SM83 assembly on the first try. Binary-identical recompilation is extraordinarily difficult — even pokered's human contributors iterated on this for years. The workflow is iterative: generate C, compile, compare, fix, repeat. The LLM accelerates each iteration but does not eliminate them.

### 3. Inter-Function State Machine Extraction

Multiple interrupt handlers -> the LLM synthesizes a state diagram of the
Link Cable protocol or the rendering cycle. Traditional tools analyze functions
in isolation. The LLM sees the logic BETWEEN functions and reconstructs
the complete protocol.

- **Required Data:** set of functions related to interrupts (VBlank, Serial, Timer) + their shared state variables
- **How to Obtain:**
  - Interrupt handlers -> **Static**: fixed addresses (0x40, 0x48, 0x50, 0x58, 0x60), plus everything they call
  - Call graph -> **Script**: recursively trace all CALLs from each vector
  - Dynamic behavior -> **MCP**: trigger each interrupt and observe the complete execution chain

**Limitations:**
- **Plausible but wrong translations.** LLM-generated C code may look correct but have subtle logic errors — especially around carry flag handling, 8-bit overflow, and banked memory access. The compile-and-compare loop is essential.
- **SM83 is niche.** The LLM has seen far more x86 and ARM assembly than SM83. Uncommon SM83 idioms (DAA for BCD, STOP for speed switching on CGB) may be mistranslated.
- **Naming quality varies.** Hardware-context naming (Chapter 3.1) is reliable. Game-logic naming requires domain knowledge and should be treated as a hypothesis.

---

## Chapter 4 — Reasoning by Analogy

**Definition:** An LLM connects different domains. It sees that a Game Boy
routine resembles a Linux driver, that a data structure resembles a quad-tree,
that a serial protocol resembles modern SPI.

### 1. Cross-Domain Protocol Mapping

A Link Cable routine -> the LLM draws an analogy with modern SPI/UART.
It names functions `Serial_Send_Byte`, `Handshake_Init` based on patterns
from serial drivers across architectures.

- **Required Data:** code manipulating serial I/O registers + LR35902 documentation
- **How to Obtain:**
  - Serial I/O code -> **Static**: filter disassembly for accesses to 0xFF01 (SB) and 0xFF02 (SC)
  - Documentation -> **Static**: Pandocs
  - Actual behavior -> **MCP**: write to serial registers and observe behavior. Note: the GB serial protocol requires a second device (or careful register manipulation) — simulating a full exchange in a single emulator is more complex than it sounds.

### 2. Game Logic Deduction by Genre

"In an RPG, this variable is probably XP." The LLM transfers knowledge of
1990s game design to identify `ATK_Def_Calculation` because the formula
resembles Dragon Quest or Final Fantasy damage calculations.

- **Required Data:** calculation code + stat tables in ROM + screenshots of stat screens
- **How to Obtain:**
  - Stat tables -> **MCP**: navigate menus via input sequences, take screenshots to identify stat screens, read corresponding memory
  - Menu code -> **Script**: trace execution while in a menu (executed addresses = menu code)
  - Cross-reference -> **MCP**: compare screenshot (displayed values) with RAM to locate stat variables
- **Critical caveat:** genre-based deduction generates *hypotheses*, not conclusions. The LLM WILL confidently say "this is XP" based on patterns and be wrong — RPG-like memory patterns could be anything. **Always verify empirically via the emulator.** Label these annotations as "hypothesis" until confirmed.

### 3. Structural Pattern Recognition

"This linked list traversal pattern resembles a binary heap used in A*
pathfinding." A traditional tool sees sequential memory accesses. The LLM sees
a high-level algorithm from an entirely different domain.

- **Required Data:** ordered RAM access traces + hexdump of the region
- **How to Obtain:**
  - Access traces -> **Script**: PyBoy hooks on the memory range, log access order
  - Contextualized patterns -> **MCP**: observe access patterns during different game phases

### 4. Programmer's Stylistic Fingerprint

The LLM recognizes a programmer's "style" — how they organize routines,
use the stack, handle interrupts — and transfers this to predict the behavior
of unanalyzed functions in the same ROM.

- **Required Data:** several already-analyzed functions from the same ROM
- **How to Obtain:**
  - Analyzed functions -> cumulative result of previous work. This is a meta-capability: it uses the output of other analyses as input
  - Bootstrap -> **Static**: start with the most obvious functions (interrupt handlers, entry point) and propagate

**Limitations:**
- **Wrong analogies applied confidently.** The LLM may see patterns that aren't there — mapping a simple loop to a sophisticated algorithm because the surface structure matches. Cross-domain analogies are hypotheses to investigate, not conclusions to trust.
- **Game Boy games vary enormously.** Tetris and Pokemon Red have almost nothing in common architecturally. Genre-based assumptions that work for one game may be wrong for another.
- **Many GB games use custom/proprietary compression**, not standard LZ77 or Huffman. Don't assume known algorithms — the LLM may "recognize" LZ77 in something that's actually a game-specific format.

---

## Chapter 5 — Broad Context Synthesis

**Definition:** An LLM can ingest tens of thousands of tokens of heterogeneous
information simultaneously: hardware documentation, assembly code, memory dumps,
comments, technical specs. It extracts coherent understanding that no single
source contains.

> **Context window reality check:** Modern LLMs support 100K-200K token contexts,
> but attention quality degrades for information in the middle of long contexts
> ("lost in the middle" effect). A 200K context full of raw disassembly will NOT
> be processed uniformly. **The knowledge base is the mitigation**: store summaries
> and annotations rather than raw data, and retrieve only what's relevant to the
> current question.

### 1. Naming by Trace + Documentation Correlation

The LLM sees that `func_0123` writes to `NR10` (audio register) after reading
a table in ROM -> it deduces `play_jump_sound_effect`. This cross-reference
between code, execution flow, and hardware documentation is where LLMs excel.

- **Required Data:** ASM code + execution context + Pandocs I/O Map
- **How to Obtain:**
  - ASM code -> **Static**: standard disassembly
  - Execution context -> **MCP**: observe what happens when the function is called (what changed, what was on screen)
  - Pandocs I/O Map -> **Static**: public documentation, injected into context

### 2. Compiler Pattern Identification

15 different functions access the same RAM offsets -> the LLM identifies an
`Entity` struct generated by GBDK. It recognizes idioms specific to 1990s
C compilers and deduces the original structure.

- **Required Data:** WRAM dumps + all functions accessing the same memory region
- **How to Obtain:**
  - WRAM dump -> **MCP**: dump 0xC000-0xDFFF at different game states
  - Functions by region -> **Script**: cross-reference memory access traces with PC
  - Correlation -> **MCP**: combine dumps and traces for the cross-view

### 3. Global State Machine Reconstruction

Code fragmented across 15 ROM banks -> the LLM maintains coherence across
bank switches to understand that a variable tracks `game_state`, and
reconstructs: Menu -> World -> Battle -> Victory.

- **Required Data:** bank switch log + entry points per bank
- **How to Obtain:**
  - Bank switch log -> **MCP**: `gb_trace_bank_switches` hooks writes to MBC registers
  - Entry points -> derived from the log: each bank switch followed by a JP/CALL gives the new bank's entry
  - Exhaustive exploration -> **MCP + Input Sequence**: generate sequences that explore different game areas

### 4. Reverse Engineering Through World Knowledge

The LLM projects its training knowledge onto raw ASM to identify compression
routines, encryption schemes, or hardware workarounds whose implementations
match no known signature in conventional databases.

- **Required Data:** routine code + memory dumps before/after + known format specs
- **How to Obtain:**
  - Routine code -> **MCP**: identify routines that write heavily to VRAM by observing execution, then isolate their code
  - Before/after dumps -> **MCP**: save_state before the call, let it execute, dump after. Compare
  - Format specs -> **Static**: documentation on common GB compression formats
- **Note:** many GB games use custom or proprietary compression, not standard LZ77. The LLM's world knowledge is a starting point for investigation, not a definitive identification.

### 5. Emergent Architectural Documentation

From hundreds of analyzed functions, the LLM produces high-level
documentation: "This game uses an Entity-Component architecture with a
scanline rendering engine and a timer-based event system." No single tool
can synthesize this overview.

- **Required Data:** all annotated code + identified assets + call graph
- **How to Obtain:**
  - Annotated code -> cumulative result of all previous work
  - Assets -> **Script**: extract tiles/sprites from VRAM via PyBoy
  - Call graph -> **Script**: built from execution traces
  - This is the final phase — it synthesizes everything produced before

**Limitations:**
- **Context window saturation.** Even with large context windows, the LLM cannot hold an entire ROM's disassembly in memory. The knowledge base must summarize and index. Raw data should be loaded on demand, not all at once.
- **Multi-turn state degradation.** In a long session (50+ turns), the LLM may lose track of annotations made in earlier turns. Always persist important findings to the KB immediately — don't rely on the LLM "remembering."
- **Cross-bank coherence is hard.** The LLM may not track the connection between a function in bank 3 and a variable it reads in bank 7 unless both are explicitly loaded into context. The KB's search function helps bridge this gap.

---

## Chapter 6 — Constrained Generation

**Definition:** An LLM can produce code that SIMULTANEOUSLY satisfies
multiple heterogeneous constraints: syntax validity, semantic correctness,
readability, naming consistency. The challenge is making all constraints
hold at once.

> **Status: aspirational.** The capabilities in this chapter represent the
> long-term goal of the project, not current LLM capabilities. No LLM today
> reliably produces binary-identical recompilable code from arbitrary Game Boy
> assembly. The state of the art (LLM4Decompile, DecLLM) shows ~21% improvement
> in re-executability on x86 — SM83 is untested. These capabilities will improve
> with better models, more training data, and tighter feedback loops.

### 1. Binary-Identical Recompilable Code (Goal)

The ultimate constraint: produce C (or annotated ASM) that compiles back to the
exact same bytes as the original ROM. This requires simultaneously satisfying:
valid syntax, binary equivalence, readability, and naming conventions.

- **Required Data:** source ASM + LR35902 opcode table + style examples
- **How to Obtain:**
  - ASM code -> **Static**: standard disassembly
  - Style examples -> **Static**: pokered, pokecrystal source code
  - Binary validation -> **Script**: recompile with GBDK/RGBDS, compare MD5 checksum
- **Why this is hard:** even pokered's human contributors iterated for over a decade on binary equivalence. The LLM accelerates each iteration (generate candidate, compile, compare, identify mismatch, fix) but does not skip the iteration.

### 2. Contextual Naming by Semantic Cross-Reference

The value `$15` loaded before a call -> the LLM cross-references with the
game's name table -> `func_4021` becomes `PlayPokemonCry`. This requires
simultaneously matching code patterns, data tables, and project conventions.

- **Required Data:** ASM code + character tables (TBL) + extracted dialogue scripts
- **How to Obtain:**
  - Character tables -> **Script**: scan ROM for text sequences
  - Dialogue scripts -> **MCP**: play the game, observe dialogue (screenshot), search for strings in ROM
  - Cross-reference -> **MCP**: note PC address when dialogue appears -> identifies the text display routine

### 3. Architectural Comments with Hardware Justification

The LLM explains WHY a `halt` is placed exactly there (battery saving), why
DMA runs during VBlank (the only time OAM is accessible), why there's a
`nop` after `ei` (interrupt activation delay).

- **Required Data:** ASM code + SM83 timing specifications + Pandocs
- **How to Obtain:**
  - Timing specs -> **Static**: Pandocs, SM83 documentation
  - Comment validation -> **MCP**: verify timing hypotheses by measuring actual cycles

### 4. Project-Wide Naming Consistency

All names follow the same convention across the entire ROM. No `playerHP`
in one function and `p_health` in another. The LLM maintains a global naming
dictionary and applies it uniformly.

- **Required Data:** existing KB entries + function dependency graph
- **How to Obtain:**
  - KB search -> **MCP**: `kb_search` to check existing naming patterns before proposing new names
  - Dependency graph -> derived from call graph analysis
  - This is a consistency pass that standardizes everything produced earlier

**Limitations:**
- **Binary equivalence is the hardest constraint.** The LLM can produce readable, well-named code that is semantically correct but doesn't compile to identical bytes. Tiny differences in register allocation, instruction selection, or alignment can break binary equivalence.
- **Constraints can conflict.** Readability sometimes requires deviating from the exact assembly structure. Binary equivalence sometimes requires ugly constructs. The LLM must be told which constraint takes priority in each context.
- **Naming consistency at scale is fragile.** Without the KB, the LLM will drift in naming conventions across sessions. The KB is not optional — it's the backbone of consistency.

---

## Appendix: A Real Example

> The following is a representative example of what a human+LLM session looks like
> in practice. This is the kind of interaction blobert-mcp is designed to support.

```
Human: "I loaded Tetris. I'm at the title screen. What's in the interrupt vector table?"

AI: [calls get_vector_table]
    "Here's what I see:
     - 0x40 (VBlank): JP 0x0150 — this is the main VBlank handler
     - 0x48 (STAT):   RETI — not used (just returns immediately)
     - 0x50 (Timer):  RETI — not used
     - 0x58 (Serial): JP 0x0214 — Link Cable handler (Tetris has multiplayer!)
     - 0x60 (Joypad): RETI — not used

     So this game uses VBlank and Serial interrupts. Let me disassemble 0x0150."

AI: [calls disassemble_function(0x0150)]
    "The VBlank handler pushes AF, reads 0xFF85, checks a flag...
     I think 0xFF85 is a 'VBlank occurred' flag. I'll annotate it."

AI: [calls kb_annotate(0xFF85, label="vblank_flag", type="data", comment="Set during VBlank handler")]
    "Done. Want me to explore the serial handler next, or should we press Start
     and see what changes in memory?"
