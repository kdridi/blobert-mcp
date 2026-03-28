# Development Journal — blobert-mcp

> **blobert-mcp** — A Boy and His Blob MCP
>
> Just as Blobert transforms into a different tool depending on the
> jellybean you feed him, each MCP tool is a transformation: disassembler,
> emulator, visualizer, knowledge base, RAG...

# Game Boy Decompiler

## What We Are Trying to Build

We are building a universal decompiler for Game Boy ROMs.

Not a disassembler — those already exist. Not a tool that spits out
unreadable code — Ghidra does that. We want a system capable of taking a
raw ROM, a binary blob of 32KB to 2MB whose contents are unknown to
anyone, and producing complete source code that is annotated, structured,
and populated with meaningful function names, identified data structures,
and comments that explain *why* the code does what it does. Code that a
developer can open and understand as if they had written it themselves.

No one has ever done this automatically. The most accomplished community
projects — pokered, pokecrystal, the Zelda Link's Awakening disassembly
— took years of manual work by dozens of people, byte by byte. It is
painstaking craftsmanship. It is magnificent. And it is humanly
impossible to replicate for every ROM that exists.

We are operating on the premise that LLMs change the game. Not because
they are magical, but because they possess specific cognitive capabilities
— pattern matching, translation between representations, reasoning by
analogy, synthesis across large contexts — that correspond precisely to
the tasks reverse engineers have been performing by hand for decades. The
question is not "can an LLM do it" but rather "how do we architect a
system where the LLM does what it does best, combined with deterministic
tools that do what *they* do best."

This journal documents all of the preparatory work: the ideas we had,
the ones we tested, the ones we discarded and why, the dead ends, the
genuine insights, and the brutal self-criticism we imposed to avoid
building on sand. We invested time understanding the problem before
rushing to code. This project is too ambitious to fail through haste.

Everything that follows is the path we traveled to lay the first bricks.

---

## Table of Contents

1. [Phase 1 — Autoresearch: The Initial Approach](#phase-1)
2. [Phase 2 — The Failure and the Diagnosis](#phase-2)
3. [Phase 3 — The Pivot: Rethinking from First Principles](#phase-3)
4. [Phase 4 — The Strengths of the LLM](#phase-4)
5. [Phase 5 — How to Obtain the Data: The Scriptable Emulator](#phase-5)
6. [Phase 6 — DSPy: Structuring the Exploration](#phase-6)
7. [Phase 7 — The Target Architecture](#phase-7)
8. [Ideas to Explore](#ideas-to-explore)
9. [Abandoned Ideas](#abandoned-ideas)
10. [Decisions Made](#decisions-made)
11. [Open Questions](#open-questions)

---

<a name="phase-1"></a>
## Phase 1 — Autoresearch: The Initial Approach

### The Concept

We used Karpathy's **autoresearch** pattern to attempt to build a Game Boy
decompiler. The idea:

- **program.md**: instructions for the agent (objective, constraints, Game
  Boy technical reference)
- **annotate.py**: a Python script modifiable by the agent. It parses ASM
  code, detects patterns, and calls an LLM to annotate routines
- **judge.py**: a fixed script that evaluates annotation quality along 3
  axes (accuracy, semantics, readability) scored 1 to 10
- **run_experiment.sh**: an orchestrator that copies sources, annotates,
  compiles, verifies the checksum, evaluates, and logs the score
- **Loop**: the agent modifies annotate.py, runs the experiment; if the
  score improves, it keeps that version and iterates

### What Was Built

- `annotate.py` (~400 lines): parses `hardware.inc`, splits into routines,
  builds the call graph, detects patterns, calls GLM-5 via
  `https://api.z.ai/api/anthropic` to annotate each routine
- `judge.py` (~200 lines): evaluates quality, score = 60% LLM quality +
  20% coverage + 20% rename ratio
- `run_experiment.sh`: adapted for WSL/Windows, with environment detection
- `annotate_all.py`: version for annotating the entire ROM (~1,400 routines)
- MD5 checksum validation: `compile(annotate(ROM)) == ROM`
  (md5: e6ae995010f14b569114f5eb71b68209)

### The Results

- Score achieved: **8.66/10** (high coverage, good rename ratio)
- The checksum was preserved after annotations
- The agent iterated throughout an entire night

### Technical Issues Encountered

1. **Duplicate labels**: two routines renamed to "InitSystem" — fixed with
   suffixes (_2, _3)
2. **Checksum overflow**: added comments caused sections to exceed the 16KB
   limit — fixed by prohibiting inline renaming
3. **ImportError on WSL**: .venv created by Windows uv was incompatible
   with WSL — resolved by recreating the venv under WSL
4. **PowerShell buffering**: no output until the process terminates —
   never truly resolved, only worked around
5. **WSL/Windows paths**: path conversion issues — resolved via environment
   detection

---

<a name="phase-2"></a>
## Phase 2 — The Failure and the Diagnosis

### The Brutal Assessment

Despite a score of 8-9/10, the approach was judged to be **garbage**. Here
is why:

### Problem 1: LLM judging LLM = hallucinations judged by hallucinations

The judge (judge.py) uses an LLM to evaluate annotation quality produced by
another LLM. This is a vicious circle: the judge can award a high score to
incorrect annotations because they "sound right."

**Concrete example**: an annotation with accuracy=2 that confused "OAM DMA"
with "sound and VBlank waiting" still received a globally acceptable score.

> "It's beautifully wrong."

### Problem 2: We were optimizing the script, not the annotated ROM

Autoresearch modified `annotate.py` (the annotation script) at each
iteration. But the final product — the annotated ROM — was never
accumulated. Each run started from scratch. We were improving the tool,
not the output.

### Problem 3: Fundamental limitations of static analysis

- **Code vs. data**: it is impossible to distinguish code from data
  without executing the ROM. A `db $3E` could be the opcode
  `LD A, imm8` or graphical data. Only execution can determine which.
- **Indirect jumps**: `jp hl` — it is impossible to know where HL points
  without knowing the register state at that moment during execution.
- **Non-determinism**: the same script can produce different annotations
  on each run (the LLM is stochastic).

### Problem 4: The high score is meaningless

A score of 8.66 is **misleading**. The LLM judge can be "fooled" by
annotations that read fluently but are factually incorrect. There is no
ground truth for comparison.

### The Conclusion

> "No, I think all of this is garbage — frankly not the right approach.
> I think I have another idea."

**Key lesson**: autoresearch is a good pattern for optimizing things that
are objectively measurable (e.g., algorithm performance). But when the
metric itself is subjective (LLM-as-judge), you are optimizing thin air.

---

<a name="phase-3"></a>
## Phase 3 — The Pivot: Rethinking from First Principles

### The Initial Pivot Idea: LLM as Emulator

The initial pivot concept:
- Describe the entire Game Boy architecture in a program.md
- Ask the LLM to BEHAVE like an emulator
- It "executes" code step by step within its context
- It progressively builds a JSON mapping addresses to types/labels
- It can save states and explore different paths
- End result: JSON + raw source code = annotated source code

### The Challenge by 6 Agents

We deployed 6 agents with vastly different profiles to challenge this idea:

1. **Computational biologist (AlphaFold)** — Enthusiastic: "You have the
   AlphaFold of reverse engineering." But: do not emulate every cycle;
   use the LLM as a trace orchestrator.

2. **Mars rover engineer** — The analogy holds: exploration of unknown
   terrain. Recommends: frontier exploration, pruning, look-ahead.

3. **Ken Thompson** — The most brutal: "It's the same con job in a fancier
   costume. The LLM does not compute; it tells a story about computation.
   One carry flag error and the entire JSON is fiction."

4. **Retrogaming speedrunner** — The most enthusiastic: confirms this is
   how a human works. But bank switching is the real wall. Dreams of a
   temporal debugger boosted by AI.

5. **Neuroscientist** — The LLM suffers from state erosion. Its strength
   is pattern matching, not exact computation. JSON as external memory is
   a good idea (a "cognitive exoskeleton").

6. **Serial entrepreneur** — MVP: one single routine + a real emulator
   that provides traces, then the LLM explains. Trap: do not slide from
   "decompiler" into "intelligent log tracer."

### The Consensus

**Everyone converges**: the insight is sound (moving from static analysis
to dynamic comprehension), but the LLM must not BE the emulator. It must
**watch a real emulator run** and interpret what it observes.

### The Top 10 Approaches

We ranked 10 approaches:

| # | Approach | Score |
|---|----------|:-----:|
| 1 | PyBoy + LLM | 94 |
| 2 | Ghidra-GB + LLM | 88 |
| 3 | BGB Traces + LLM | 82 |
| 4 | Symbolic Execution with Z3 | 78 |
| 5 | Automated pokered Method | 76 |
| 6 | LLM4Decompile adapted for GB | 74 |
| 7 | Rizin scripting + LLM | 72 |
| 8 | Hybrid Rust Emulator | 70 |
| 9 | Pure LLM Emulator | 65 |
| 10 | Community-driven Approach | 60 |

### The "Strawberry-Superglue" Critique

> "Putting two powerful things together does not automatically create
> something miraculous. I love strawberries and I love superglue, but
> combining them serves no purpose."

This critique forced us to articulate WHY PyBoy + LLM would be useful,
not merely HOW to combine them.

### The Brutal Truth of the Numbers

- Game Boy = 1M instructions/second
- 1 line of trace ~ 80 bytes = ~20 tokens
- 1 second of execution = 20M tokens
- 200K context window = **0.01 seconds of trace**
- The LLM physically CANNOT "watch" the emulator run continuously

### What the LLM Is USELESS For

| Task | Python alone sufficient? | LLM required? |
|------|:------------------------:|:-------------:|
| Separating code/data | YES (execution trace) | NO |
| Call graph | YES (trace CALL/RET/JP) | NO |
| Resolving jp hl | YES (read HL during execution) | NO |
| Identifying hardware I/O | YES (table 0xFF00-0xFFFF) | NO |
| Detecting routines/loops | YES (graph analysis) | NO |
| Bank switching | YES (trace MBC writes) | NO |
| **Naming functions** | NO | **YES** |
| **Data structures** | NO | **YES** |
| **Explaining logic** | NO | **YES** |

**The LLM is only useful for the semantic layer.**

---

<a name="phase-4"></a>
## Phase 4 — The Strengths of the LLM

### The Fundamental Question

Instead of asking "which tool should we use," we asked: "what are the real
strengths of an LLM, and how do we leverage them?"

### Top 5 Strengths (Validated)

1. **Massive pattern matching** — recognizing previously seen structures
2. **Translation between representations** — ASM to C, code to explanation
3. **Reasoning by analogy** — connecting different domains
4. **Large context synthesis** — cross-referencing 100K+ heterogeneous tokens
5. **Constrained generation** — satisfying N constraints simultaneously

### What Is NOT a Strength

- Exact computation
- Maintaining mutable state
- Deterministic execution
- Long-term memory

### The 25 Game Changers

For each strength, we identified 5 concrete game changers applied to Game
Boy decompilation, along with the required data and how to obtain it.

**Documented in detail in: `gb-decompiler/LLM_FORCES.md`**

### The Inverted Approach

Instead of starting with a tool and looking for what to do with it, we
start from the **required data** for each game changer and determine
**which tool produces it**:

- **YES** — the tool does it natively
- **NO** — it is irrelevant
- **MAYBE** — the tool needs to be adapted or repurposed

---

<a name="phase-5"></a>
## Phase 5 — How to Obtain the Data: The Scriptable Emulator

### The 4 Control Modes Identified

1. **MCP** (Model Context Protocol): a server exposing tools that the LLM
   calls directly (load_rom, tick, read_memory, save_state, press_button,
   screenshot...). Interactive mode.

2. **Score** (input sequence): a file describing a timestamped sequence of
   inputs (frame to buttons), like a TAS file. The LLM generates the
   score; the emulator plays it. For systematic exploration.

3. **Script**: Python code using the PyBoy API directly. Pre-computed, not
   interactive. For heavy-duty work (massive traces, graphs).

4. **Static**: data obtained without execution (disassembly, hex dump,
   documentation). No emulator needed.

### PyBoy: The Emulator Choice

**PyBoy** (Baekalfen/PyBoy) is a Python library. `pip install pyboy`.

Verified capabilities:
- `pyboy.tick()` — advances by one frame
- `pyboy.button("start")` — presses a button
- `pyboy.memory[addr]` — reads memory like an array
- `pyboy.memory[bank, addr]` — reads by bank
- `pyboy.registers` — dictionary of CPU registers
- `pyboy.save_state(f)` / `load_state(f)` — checkpoints
- `pyboy.screen.image` — PIL screenshot
- `pyboy.hook_register(bank, addr, callback)` — breakpoints
- `window="null"` — headless, 300-500 FPS
- Parallelizable via multiprocessing

### PyBoy MCP Server

Estimate: ~100-150 lines of Python, ~2-4 hours of development.

MCP tools to expose:
- `load_rom(path)` — loads a ROM
- `tick(n)` — advances by N frames
- `send_input(button, duration)` — presses a button
- `read_memory(addr, length)` — reads memory
- `write_memory(addr, value)` — writes to memory
- `save_state()` / `load_state(id)` — checkpoints
- `screenshot()` — base64 screen capture
- `get_registers()` — CPU register state

### Frida: Evaluated and Rejected

Frida (frida.re) is a dynamic instrumentation toolkit for injecting code
into native processes.

**Verdict: unnecessary for our use case.**

- PyBoy ALREADY provides everything Frida would offer
- In native Python (not injected JS)
- Synchronized with the emulation loop (no jitter)
- Without hook overhead (~5-15us per Frida hook)
- With perfect determinism

Frida would only be useful for instrumenting a closed-source emulator
without an API (e.g., an old VBA without scripting). That is not our case.

### TAS: The Score Format

TAS (Tool-Assisted Speedrun) files are exactly our "scores":

`.bk2` format (BizHawk) = a ZIP containing a text file:
```
|........|  (Frame 1: nothing)
|..S.U...|  (Frame 2: Select + Up)
|A.......|  (Frame 3: A button)
```

Each line = one frame. Each character = one button. The LLM can generate
this effortlessly.

### The Twitch Plays Pokemon Analogy

The MCP PyBoy architecture is structurally identical to Twitch Plays
Pokemon (2014):

| Twitch Plays Pokemon | Our Project |
|---|---|
| Viewers type in chat | The LLM generates commands |
| The bot parses messages | The MCP server parses tool calls |
| The emulator executes inputs | PyBoy executes inputs |
| The stream shows the result | The screenshot returns to the LLM |
| Viewers react and adjust | The LLM reasons and adjusts |

The LLM is multimodal: it can SEE the screenshot and understand what is
displayed on screen (menus, sprites, in-game text).

---

<a name="phase-6"></a>
## Phase 6 — DSPy: Structuring the Exploration

### Why DSPy

Not for prompt optimization (its primary use case), but for:

1. **The plumbing** — input/output signatures; we wire modules together.
   "The responses from this LLM become the inputs for another."
2. **Checkpoints** — we can save intermediate results
3. **Invisible prompts** — DSPy generates the prompts; we never see them.
   We only define signatures (what goes in, what comes out).

### The Exploration Tree

DSPy will structure a tree of questions where each node is an isolated LLM
call (no context pollution between branches):

**Phase 1**: What are the challenges of a GB decompiler?
-> For each challenge: chain of 5 whys -> root of the problem

**Phase 2**: What are the strengths of an LLM?
-> For each strength: 5 whys -> root of the strength
-> For each strength: what game changers?
-> For each game changer: what input data is required?

**Phase 3**: For each required piece of data, which tool produces it?
-> For each candidate tool: YES / NO / MAYBE
-> If YES: how, concretely?
-> If MAYBE: what needs to be adapted?
-> If NO: alternative?

**Phase 4**: Cross-referencing
-> Problems x Strengths matrix
-> Data x Tools matrix
-> Gap identification

**Phase 5**: Specification document
-> Mechanical aggregation (no LLM) of all results

Each phase produces an intermediate JSON (checkpoint). The process can be
relaunched from any point.

**Documented in detail in: `gb-decompiler/EXPLORATION_TREE.md`**

---

<a name="phase-7"></a>
## Phase 7 — The Target Architecture

### The Current Vision

The LLM drives a Game Boy emulator (PyBoy) via an MCP server. It can:

1. **Explore interactively**: load a ROM, advance frame by frame, set
   breakpoints, read memory, take screenshots
2. **Generate input scores**: create input sequences to systematically
   explore all execution paths
3. **Save/restore checkpoints**: rewind to test different hypotheses (e.g.,
   "what happens if I press Start vs. Select?")
4. **Collaborate with a human**: the LLM pauses, shows a screenshot, asks
   "what do you see?", the human describes what is happening, and the LLM
   learns and continues

### The Human-LLM Workflow

```
LLM:   [loads ROM, takes screenshot] "What do you see?"
Human: "It's the title screen — you need to press Start."
LLM:   [press Start, advance, screenshot, memory dump]
       "0xC100 changed. This is probably player_x."
       "What now?"
Human: "The character moved; there's an enemy."
LLM:   [save_state] "I'm testing two paths..."
```

### Components to Build

1. **PyBoy MCP Server** (~150 lines Python) — PRIORITY 1
2. **JSON score format** (~10 lines) — trivial
3. **DSPy exploration pipeline** — PRIORITY 2
4. **Annotated score recorder** — PRIORITY 3

---

<a name="ideas-to-explore"></a>
## Ideas to Explore

### Annotated Score Recorder

A mode where the human plays the game, pauses, and narrates aloud what
they are doing. The system records a score that interleaves:
- Inputs (frame to button)
- Human commentary ("I'm in the menu, I'm pressing Start")
- Memory snapshots / screenshots

```json
[
  {"frame": 0, "type": "comment", "text": "Mario title screen"},
  {"frame": 1, "type": "input", "button": "start", "action": "press"},
  {"frame": 120, "type": "comment", "text": "The game has started"},
  {"frame": 121, "type": "input", "button": "right", "action": "press"},
  {"frame": 180, "type": "snapshot", "screenshot": "f180.png"}
]
```

Value: the LLM has both the inputs AND the human intent. When it replays
the score, it knows WHY each button was pressed.

### Semantic ROM Fuzzing

Mutate one byte of the ROM, execute, and observe:
- PC diverges — it is code
- VRAM changes — it is a graphical asset
- Nothing changes — it is padding

Automatic code/data cartography without a disassembler.

### Code Thermodynamics

Measure the access frequency of every byte of RAM/ROM:
- "Hot" zone = rendering engine (executed 60 times/second)
- "Cold" zone = endgame data

An instant bird's-eye view of the entire ROM.

### Comparative Archaeology

Vectorize patterns from already-decompiled ROMs (pokered, Tetris) and
search for similarities in unknown ROMs.

### Ghost Input Explorer

MCTS over button combinations to explore all execution paths tied to
player inputs.

### Sonic Pi / Live Coding

Draw inspiration from Sonic Pi (real-time music composition through code)
to create an expressive "score" language that the LLM can write and the
emulator can play.

### RAG from Synthetic C Code: Compiled/Decompiled

Generate thousands of typical Game Boy C functions with an LLM (sprite
management, scrolling, input handling, audio, DMA, timers...), compile
them with GBDK/RGBDS, disassemble them with mgbdis, and index the pairs
raw ASM <-> annotated C in a RAG.

Pipeline:
```
LLM generates annotated C -> compile -> ROM -> disassemble -> raw ASM
We now have: raw ASM <-> annotated C (ground truth)
Facing an unknown ROM: "this ASM block resembles scroll_background"
```

Strengths:
- No hallucination: the correspondence is produced by the compiler
- Scalable: we can generate millions of pairs
- We can vary compilation options (O0, O1, O2) to make the RAG robust
  against variations

Limitations:
- Only covers code compiled with GBDK. Pure ASM code (common on Game Boy)
  has different patterns
- The generated code is "generic"; real game code has hardware-specific
  hacks

Status: **worth exploring as a bootstrap layer**

### RAG from Community Decompilation Projects (pokered, etc.)

Leverage existing community decompilation projects as a training base.
These projects contain TWO invaluable assets:
1. The annotated source code (labels, comments, structures)
2. The compiled ROM (which can be disassembled into a "raw" version)

Available corpus:

| Project | Game | ASM Lines | Status |
|---------|------|:---------:|--------|
| pokered | Pokemon Red | ~80,000 | 100% complete |
| pokeyellow | Pokemon Yellow | ~85,000 | 100% complete |
| pokecrystal | Pokemon Crystal | ~120,000 | 100% complete |
| pokegold | Pokemon Gold | ~100,000 | 100% complete |
| ladx | Zelda Link's Awakening | ~60,000 | nearly complete |
| Tetris | Tetris | ~5,000 | 100% complete |

For each function, we have the perfect training pair:
```
RAW:       sub_1A3F: ld a, [ff85] / and 0F / jr z, .label_1A48
ANNOTATED: ReadJoypad: ld a, [hJoyHeld] / and D_PAD_MASK / jr z, .noMovement
```

This is REAL game code, not laboratory code. The patterns, the idioms,
the hacks — everything is there.

Status: **high priority — this is the best source of ground truth**

### Three-Layer Architecture

The RAG + MCP ideas combine into three mutually reinforcing layers:

1. **RAG** (static pattern matching): "what does this look like?"
   - Community projects (pokered, etc.) = real-world patterns
   - Synthetic C code = complementary generic patterns
2. **PyBoy MCP** (dynamic verification): "what does it actually do?"
   - RAG says "this looks like ReadJoypad"
   - The emulator confirms: "when I press a button, this routine is
     called and 0xFF85 changes"
3. **LLM** (semantics): "what does this mean?"
   - Naming, explanation, documentation, ASM-to-C translation

Status: **this is the current architectural vision**

### LLM Trained on Emulator Traces

Idea: play games on an instrumented emulator, dump the traces (memory,
registers, inputs) and fine-tune an LLM on them so it "understands" Game
Boy behavior.

Analysis:
- An emulator is a deterministic function. Training an LLM to simulate
  this is like training a neural network to perform addition.
- Error accumulation: 0.1% error/instruction -> after 1,000 instructions,
  37% chance everything is correct. After 10,000: ~0%.
- However, if we train at a MACRO level (not instruction-by-instruction
  but "when the player presses Start, the state transitions from X to
  Y"), it could work. But a base LLM already does this without
  fine-tuning.

Status: **rejected for low-level emulation; worth exploring for
macro-level behavior**

---

<a name="abandoned-ideas"></a>
## Abandoned Ideas

### Autoresearch for Decompilation

**Rejected.** The autoresearch pattern optimizes a script, not a result.
And the metric (LLM-as-judge) is circular.

### LLM as a Pure Emulator

**Rejected.** The LLM cannot maintain coherent state across thousands of
instructions. Cognitive erosion, carry flag errors, non-determinism. "It
tells a story about execution; it does not execute."

### Frida + Emulator

**Rejected.** PyBoy already provides everything Frida would offer — more
simply, more quickly, and in sync. Frida is a jackhammer for watchmaking.

### LLM "Watching" Raw Traces

**Rejected.** 1 second of Game Boy = 20M tokens. The context window can
hold only 0.01 seconds. Data must be filtered, summarized, and only the
relevant portions shown to the LLM.

---

<a name="decisions-made"></a>
## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Abandon autoresearch for this project | Circular metric (LLM judges LLM) |
| Use a real emulator | The LLM cannot emulate faithfully |
| Choose PyBoy | Native Python, rich API, headless, parallelizable |
| MCP server | The LLM drives the emulator interactively |
| DSPy for exploration | Clean plumbing, context isolation, checkpoints |
| LLM for semantics only | Everything else (traces, graphs, I/O) = pure Python |
| JSON score format | The LLM generates; PyBoy plays |
| Human-LLM collaboration | The human provides visual semantics |

---

<a name="open-questions"></a>
## Open Questions

1. **Which LLM model to use?** Claude (multimodal, can see screenshots)
   vs. a specialized code model?

2. **How to manage context size?** Traces are enormous. What level of
   summarization/filtering is needed before showing them to the LLM?

3. **How to validate annotations?** We rejected LLM-as-judge. What
   objective metric should we use? The checksum (compile -> same ROM) is
   necessary but not sufficient.

4. **How to handle bank switching?** This is the hardest problem according
   to community experts. Does PyBoy expose the current bank?

5. **Is DSPy the right tool?** We are using it for plumbing and
   signatures, not for optimization. Is this overkill?

6. **What format for the knowledge base?** JSON? SQLite? A graph? How
   should accumulated annotations be stored?

7. **How to scale?** One game changer at a time on one routine works.
   1,400 routines x 25 game changers = 35,000 LLM calls. Cost? Time?

8. **Live coding (Sonic Pi)** as inspiration for the score format — does
   it offer something concrete?
