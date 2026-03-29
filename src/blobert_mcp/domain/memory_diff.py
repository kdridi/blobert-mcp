"""Memory diff computation between two byte sequences.

No project imports; stdlib + dataclasses only.
"""

from __future__ import annotations

from dataclasses import dataclass

MAX_CHANGES: int = 512


@dataclass(frozen=True)
class MemoryChange:
    """A single byte difference between two memory snapshots."""

    address: int
    old: int
    new: int


def diff_memory(
    bytes_a: bytes,
    bytes_b: bytes,
    base_address: int,
) -> list[MemoryChange]:
    """Compare two byte sequences and return a list of changed bytes.

    Each change records the absolute address (base_address + offset),
    the old value (from bytes_a), and the new value (from bytes_b).

    Raises ValueError if the two sequences have different lengths.
    """
    if len(bytes_a) != len(bytes_b):
        msg = (
            f"Byte sequences must have equal length, "
            f"got {len(bytes_a)} and {len(bytes_b)}"
        )
        raise ValueError(msg)
    changes: list[MemoryChange] = []
    for i, (a, b) in enumerate(zip(bytes_a, bytes_b)):
        if a != b:
            changes.append(
                MemoryChange(
                    address=base_address + i,
                    old=a,
                    new=b,
                )
            )
    return changes
