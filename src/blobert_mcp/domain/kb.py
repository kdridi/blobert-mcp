"""Knowledge base domain logic — pure validation and search ranking.

No project imports; stdlib + dataclasses only.
"""

from __future__ import annotations

ANNOTATION_TYPES: frozenset[str] = frozenset({"code", "data", "gfx", "audio", "text"})
VARIABLE_TYPES: frozenset[str] = frozenset({"u8", "u16", "bool", "enum"})
STRUCT_FIELD_TYPES: frozenset[str] = frozenset(
    {"u8", "u16", "s8", "s16", "bool", "bytes"}
)
MAX_ADDRESS = 0xFFFF
MAX_SEARCH_RESULTS = 50
ROM_ADDRESS_LIMIT = 0x8000


def validate_annotation_type(value: str | None) -> None:
    """Raise ValueError if *value* is not a valid annotation type (None is allowed)."""
    if value is not None and value not in ANNOTATION_TYPES:
        valid = sorted(ANNOTATION_TYPES)
        msg = f"Invalid annotation type: {value!r}. Must be one of {valid}."
        raise ValueError(msg)


def validate_variable_type(value: str) -> None:
    """Raise ValueError if *value* is not a valid variable type."""
    if value not in VARIABLE_TYPES:
        valid = sorted(VARIABLE_TYPES)
        msg = f"Invalid variable type: {value!r}. Must be one of {valid}."
        raise ValueError(msg)


def validate_address(address: int) -> None:
    """Raise ValueError if *address* is outside the 16-bit range [0, 0xFFFF]."""
    if address < 0 or address > MAX_ADDRESS:
        hi = f"0x{MAX_ADDRESS:X}"
        msg = f"Invalid address: 0x{address:X}. Must be between 0x0000 and {hi}."
        raise ValueError(msg)


def validate_name(name: str, field: str = "name") -> None:
    """Raise ValueError if *name* is empty or whitespace-only."""
    if not name or not name.strip():
        msg = f"Invalid {field}: must be a non-empty string."
        raise ValueError(msg)


def rank_search_results(results: list[dict], query: str) -> list[dict]:
    """Sort *results* by relevance to *query* and cap at 50.

    Ranking tiers (lower is better):
    0 — exact match (case-insensitive)
    1 — prefix match
    2 — substring match
    3 — no match on the ranking key (keep original order)
    """
    query_lower = query.lower()

    def _rank_key(result: dict) -> int:
        text = result.get("label") or result.get("name") or ""
        text_lower = text.lower()
        if text_lower == query_lower:
            return 0
        if text_lower.startswith(query_lower):
            return 1
        if query_lower in text_lower:
            return 2
        return 3

    ranked = sorted(results, key=_rank_key)
    return ranked[:MAX_SEARCH_RESULTS]


def calculate_coverage_pct(annotated: int, total_addresses: int) -> float:
    """Return ROM coverage percentage: annotated / total_addresses * 100.

    Returns 0.0 if *total_addresses* is zero.
    """
    if total_addresses == 0:
        return 0.0
    return annotated / total_addresses * 100


def validate_struct_field_type(value: str) -> None:
    """Raise ValueError if *value* is not a valid struct field type."""
    if value not in STRUCT_FIELD_TYPES:
        valid = sorted(STRUCT_FIELD_TYPES)
        msg = f"Invalid struct field type: {value!r}. Must be one of {valid}."
        raise ValueError(msg)


def validate_struct_fields(fields: list[dict]) -> None:
    """Validate a list of struct field dicts.

    Each dict must have: name (str), offset (int >= 0), type (str), size (int > 0).
    Optional: comment (str).
    """
    if not fields:
        raise ValueError("Struct fields must not be empty.")

    for f in fields:
        if "name" not in f or not f["name"] or not str(f["name"]).strip():
            raise ValueError("Each field must have a non-empty name.")
        if "offset" not in f:
            raise ValueError(f"Field {f['name']!r}: missing offset.")
        if f["offset"] < 0:
            raise ValueError(f"Field {f['name']!r}: offset must be >= 0.")
        if "type" not in f:
            raise ValueError(f"Field {f['name']!r}: missing type.")
        validate_struct_field_type(f["type"])
        if "size" not in f:
            raise ValueError(f"Field {f['name']!r}: missing size.")
        if f["size"] <= 0:
            raise ValueError(f"Field {f['name']!r}: size must be > 0.")

    # Check for overlapping byte ranges
    sorted_fields = sorted(fields, key=lambda x: x["offset"])
    for i in range(1, len(sorted_fields)):
        prev = sorted_fields[i - 1]
        curr = sorted_fields[i]
        if curr["offset"] < prev["offset"] + prev["size"]:
            raise ValueError(
                f"Fields {prev['name']!r} and {curr['name']!r} overlap "
                f"at offset {curr['offset']}."
            )


def validate_enum_values(values: dict[str, int]) -> None:
    """Validate enum name-to-value mapping."""
    if not values:
        raise ValueError("Enum values must not be empty.")

    for name in values:
        if not name or not name.strip():
            raise ValueError("Each enum value must have a non-empty name.")

    seen: dict[int, str] = {}
    for name, val in values.items():
        if val in seen:
            raise ValueError(
                f"Duplicate numeric value {val} for names {seen[val]!r} and {name!r}."
            )
        seen[val] = name


def calculate_struct_total_size(fields: list[dict]) -> int:
    """Return the total byte size of a struct: max(offset + size) across fields."""
    if not fields:
        return 0
    return max(f["offset"] + f["size"] for f in fields)


def decode_struct_fields(fields: list[dict], data: bytes) -> list[dict]:
    """Decode raw bytes into field values based on struct field definitions."""
    results = []
    for f in sorted(fields, key=lambda x: x["offset"]):
        raw = data[f["offset"] : f["offset"] + f["size"]]
        raw_hex = raw.hex().upper()
        t = f["type"]

        if t in ("u8", "u16"):
            value = int.from_bytes(raw, byteorder="little", signed=False)
        elif t in ("s8", "s16"):
            value = int.from_bytes(raw, byteorder="little", signed=True)
        elif t == "bool":
            value = raw[0] != 0
        elif t == "bytes":
            value = raw_hex
        else:
            value = raw_hex

        results.append(
            {
                "name": f["name"],
                "offset": f["offset"],
                "type": t,
                "size": f["size"],
                "value": value,
                "raw_hex": raw_hex.lower(),
            }
        )
    return results
