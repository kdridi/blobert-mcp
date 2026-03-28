# DSPy Exploration Tree — Game Boy Decompiler

> This document describes the structure of the question tree that DSPy will
> explore. Each node represents a question posed to an LLM, isolated from the
> context of all other nodes. The responses from parent nodes become the inputs
> for child nodes. At the end, the leaf nodes are aggregated to produce a
> comprehensive specification document.

---

## Overview

```
PHASE 1: Understand the Problem
"What are the difficulties of building a GB decompiler?"
  +-- For each difficulty: 5 Whys --> root causes

PHASE 2: Understand the Strengths of the LLM
"What are the fundamental strengths of an LLM?"
  +-- For each strength: 5 Whys --> root strengths
  +-- For each strength: what game changers does it unlock?
      +-- For each game changer: what input data is required?

PHASE 3: Identify the Tools
For each required data item:
  "Which tool can produce this data?"
  +-- For each candidate tool: YES / NO / MAYBE
      |-- If YES: how exactly? (API, format, example)
      |-- If NO: why not? (technical limitation)
      +-- If MAYBE: what would need to be adapted?

PHASE 4: Cross-Reference and Synthesize
Root causes x Root strengths --> compatibility matrix
Required data x Available tools --> coverage matrix
Identified gaps --> what do we need to build ourselves?

PHASE 5: Specification Document
Aggregation of all results --> final document
```

---

## Phase 1 — Understand the Problem

### Root Node

```
Signature : "" --> difficulties: list[str]
Prompt    : "What are the 5 greatest technical difficulties involved
             in decompiling a Game Boy ROM (transforming binary machine
             code into readable, annotated source code)?"
Output    : List of 5 difficulties
```

### Subtree: The 5 Whys (for each difficulty)

```
Signature : difficulty: str --> why: str
Prompt    : "Why is '{difficulty}' a difficulty for Game Boy
             decompilation?"

Then chain 4 additional iterations:
Signature : previous_why: str --> deeper_why: str
Prompt    : "You stated that it is difficult because '{previous_why}'.
             But why is that the case?"

--> By the 5th iteration, we have reached the root cause.
```

### Phase 1 Output

```json
{
  "difficulty_1": {
    "name": "Distinguishing code from data",
    "why_chain": ["because...", "because...", ..., "ROOT CAUSE"],
    "root_cause": "..."
  },
  "difficulty_2": { ... },
  ...
}
```

---

## Phase 2 — Understand the Strengths of the LLM

### Root Node

```
Signature : "" --> strengths: list[str]
Prompt    : "What are the 5 fundamental strengths of an LLM
             (not use cases, but core cognitive capabilities)?"
Output    : List of 5 strengths
```

### Subtree: The 5 Whys (for each strength)

```
Same mechanism as Phase 1.
Signature : strength: str --> why: str
--> 5 iterations --> root of the strength
```

### Subtree: Game Changers (for each strength)

```
Signature : strength: str, strength_root: str --> game_changers: list[str]
Prompt    : "Given that the strength '{strength}' exists because of
             '{strength_root}', what are the 5 game-changing applications
             of this strength for Game Boy decompilation?"
```

### Subtree: Required Data (for each game changer)

```
Signature : game_changer: str, strength: str --> required_data: list[str]
Prompt    : "To accomplish '{game_changer}', what are the exact data
             items that must be provided to the LLM as input?
             Be exhaustive and precise about formats."
```

### Phase 2 Output

```json
{
  "strength_1": {
    "name": "Massive pattern matching",
    "why_chain": [...],
    "root": "...",
    "game_changers": [
      {
        "name": "Semantic identification of functions",
        "required_data": ["disassembled ASM code", "control flow graph"]
      },
      ...
    ]
  },
  ...
}
```

---

## Phase 3 — Identify the Tools

### Collecting Unique Required Data Items

All `required_data` entries from Phase 2 are deduplicated to produce a flat list
of data items that need to be generated.

### Node: Which candidate tools?

```
Signature : required_data: str --> tool_candidates: list[str]
Prompt    : "Which existing tools (emulators, disassemblers, debuggers,
             libraries, scripts) could produce '{required_data}' in
             the context of Game Boy / SM83 / Z80?"
```

### Node: Evaluation of each tool

```
Signature : required_data: str, tool: str --> verdict: str, explanation: str
Prompt    : "Is the tool '{tool}' capable of producing
             '{required_data}'?
             Answer YES, NO, or MAYBE.
             Explain why in 2-3 sentences."
```

### Subtree if YES

```
Signature : tool: str, required_data: str --> how: str
Prompt    : "How exactly should '{tool}' be used to produce
             '{required_data}'? Provide a code or command example.
             What is the output format?"
```

### Subtree if MAYBE

```
Signature : tool: str, required_data: str, explanation: str --> adaptation: str
Prompt    : "You indicated that '{tool}' could potentially produce
             '{required_data}' because '{explanation}'.
             What modifications or adaptations would be required for
             it to work? Is this realistic?"
```

### Subtree if NO

```
Signature : tool: str, required_data: str, explanation: str --> alternative: str
Prompt    : "'{tool}' cannot produce '{required_data}'.
             Does another tool exist, or does one need to be built?"
```

### Phase 3 Output

```json
{
  "required_data_1": {
    "name": "control flow graph",
    "tools": {
      "PyBoy":  { "verdict": "MAYBE", "how": "...", "adaptation": "..." },
      "Ghidra": { "verdict": "YES",   "how": "...", "example": "..." },
      "Rizin":  { "verdict": "YES",   "how": "...", "example": "..." },
      "mgbdis": { "verdict": "NO",    "why": "...", "alternative": "..." }
    }
  },
  ...
}
```

---

## Phase 4 — Cross-Reference and Synthesize

### Problems x Strengths Matrix

```
Signature : root_cause: str, strength_root: str --> compatibility: str
Prompt    : "The fundamental problem is '{root_cause}'.
             The fundamental LLM strength is '{strength_root}'.
             Can this strength solve this problem?
             YES / PARTIALLY / NO. Explain."
```

### Data x Tools Matrix (automated)

No LLM is needed here. The verdicts from Phase 3 are compiled into a table:

```
                       | PyBoy | Ghidra | Rizin | BGB | Custom Script |
Disassembled ASM code  |  NO   |  YES   |  YES  | NO  |     YES       |
Control flow graph     | MAYBE |  YES   |  YES  | NO  |    MAYBE      |
Read/Write traces      |  YES  |  NO    |  NO   | YES |     NO        |
Memory dumps           |  YES  |  NO    |  NO   | YES |     NO        |
...
```

### Gap Identification

```
Signature : uncovered_data: list[str] --> build_plan: str
Prompt    : "The following data items are not produced by any existing
             tool: {uncovered_data}.
             How can they be produced? Is a custom tool required?
             What level of effort does this represent?"
```

---

## Phase 5 — Specification Document

Final aggregation. No LLM is used here — results are compiled mechanically:

1. **Objective**: Game Boy decompiler
2. **Fundamental problems**: (root causes from Phase 1)
3. **Applicable LLM strengths**: (root strengths from Phase 2)
4. **Retained game changers**: (those where problem x strength = YES)
5. **Required data**: (deduplicated list from Phase 2)
6. **Selected tools**: (those with a YES verdict in Phase 3)
7. **Required adaptations**: (MAYBE verdicts from Phase 3)
8. **To be built**: (gaps identified in Phase 4)
9. **Pipeline architecture**: tool --> data --> LLM --> result
10. **Execution plan**: where to begin, in what order

---

## DSPy Implementation Notes

### Required DSPy Modules

- `ListGenerator`: produces a list of N items (difficulties, strengths, etc.)
- `WhyChain`: chains 5 "why" questions in series
- `GameChangerFinder`: given a strength, lists the game changers it enables
- `DataRequirements`: given a game changer, lists the required input data
- `ToolEvaluator`: evaluates a tool against a data item (YES / NO / MAYBE)
- `ToolHowTo`: explains how to use a tool in practice
- `CompatibilityChecker`: cross-references a problem with a strength
- `Aggregator`: compiles all results into a specification document (no LLM)

### Checkpoints

Each phase produces an intermediate JSON file:
- `phase1_difficulties.json`
- `phase2_strengths.json`
- `phase3_tools.json`
- `phase4_crossings.json`
- `phase5_specification.md`

Execution can be resumed from any checkpoint without recomputing earlier phases.
