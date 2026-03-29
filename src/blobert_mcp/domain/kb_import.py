"""Symbol import parsing — pure functions for .sym file formats.

No project imports; stdlib + dataclasses only.
"""

from __future__ import annotations

from dataclasses import dataclass

VALID_FORMATS: frozenset[str] = frozenset({"sym", "pokered", "auto"})

_ROM_LIMIT = 0x8000


@dataclass(frozen=True)
class ParsedSymbol:
    """A symbol parsed from a .sym file."""

    address: int
    bank: int | None
    label: str
    symbol_type: str  # "code" or "data"


@dataclass(frozen=True)
class ParseResult:
    """Result of parsing a .sym file."""

    symbols: list[ParsedSymbol]
    errors: int


def classify_address(address: int) -> str:
    """Classify a Game Boy address as 'code' (ROM) or 'data' (everything else)."""
    if address < _ROM_LIMIT:
        return "code"
    return "data"


def validate_format(fmt: str) -> None:
    """Raise ValueError if *fmt* is not a valid import format."""
    if fmt not in VALID_FORMATS:
        msg = f"Invalid format: {fmt!r}. Must be one of: {sorted(VALID_FORMATS)}"
        raise ValueError(msg)


def _parse_lines(content: str) -> ParseResult:
    """Shared parser for BB:XXXX label lines."""
    symbols: list[ParsedSymbol] = []
    errors = 0
    last_global: str | None = None

    for raw_line in content.splitlines():
        line = raw_line.strip()

        # Skip blank lines and comments
        if not line or line.startswith(";"):
            continue

        # Strip inline comments
        if ";" in line:
            line = line[: line.index(";")].strip()
            if not line:
                continue

        parts = line.split()
        if len(parts) < 2:
            errors += 1
            continue

        addr_part, label = parts[0], parts[1]

        # Parse BB:XXXX
        if ":" not in addr_part:
            errors += 1
            continue

        bank_str, addr_str = addr_part.split(":", 1)
        try:
            bank_val = int(bank_str, 16)
            address = int(addr_str, 16)
        except ValueError:
            errors += 1
            continue

        # Handle local labels
        if label.startswith("."):
            if last_global is None:
                errors += 1
                continue
            label = f"{last_global}{label}"
        else:
            # Only update last_global for non-hierarchical labels
            # (labels without dots are global; labels with dots are kept as-is)
            if "." not in label:
                last_global = label

        # Bank: preserve for ROM, None for RAM/IO
        bank = bank_val if address < _ROM_LIMIT else None
        symbol_type = classify_address(address)

        symbols.append(
            ParsedSymbol(
                address=address,
                bank=bank,
                label=label,
                symbol_type=symbol_type,
            )
        )

    return ParseResult(symbols=symbols, errors=errors)


def parse_sym(content: str) -> ParseResult:
    """Parse RGBDS .sym file content into a list of symbols."""
    return _parse_lines(content)


def parse_pokered(content: str) -> ParseResult:
    """Parse pokered/pokecrystal .sym file content into a list of symbols."""
    return _parse_lines(content)


def detect_format(content: str) -> str:
    """Detect whether content is 'sym' or 'pokered' format.

    Heuristic: if >30% of sampled labels contain dots, it's pokered.
    Defaults to 'sym' if ambiguous or empty.
    """
    lines = [
        raw.strip()
        for raw in content.splitlines()
        if raw.strip() and not raw.strip().startswith(";")
    ]

    # Sample up to 50 non-comment, non-blank lines
    sample = lines[:50]
    if not sample:
        return "sym"

    dot_count = 0
    label_count = 0
    for line in sample:
        parts = line.split()
        if len(parts) >= 2 and ":" in parts[0]:
            label = parts[1]
            # Skip local labels (starting with .) — they're in both formats
            if not label.startswith("."):
                label_count += 1
                if "." in label:
                    dot_count += 1

    if label_count > 0 and dot_count / label_count > 0.3:
        return "pokered"
    return "sym"
