"""
Type-directed test input generator.

Given a list of parameter-type annotation strings, the generator creates a
diverse set of input tuples suitable for:
  * verifying equivalence  (ptests — 1 000+ distinct inputs)
  * finding counterexamples (ntests — at least one differing input)

Supported type strings
-----------------------
  int        list[int]   list[str]   str   bool

For functions with "non-empty list" constraints, pass
``min_list_length=1``.
"""

from __future__ import annotations

import random
import string
from itertools import product
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Per-type value generators
# ---------------------------------------------------------------------------

# Integers: always include 0, ±1, boundaries, and a range of randoms.
# We keep the edge list small and rely on _random_value to cover larger ranges.
INT_EDGE: list[int] = [-10, -5, -3, -2, -1, 0, 1, 2, 3, 5, 10, 100, -100]

def _int_values(rng: random.Random, n: int = 60) -> list[int]:
    """Return *n* diverse integers including edge cases and a wide spread."""
    vals = list(INT_EDGE)
    # Wide range so the Cartesian-product seed is already large enough
    for v in range(-30, 31):
        if v not in vals:
            vals.append(v)
    while len(vals) < n:
        vals.append(rng.randint(-200, 200))
    seen: set = set()
    result = []
    for v in vals:
        if v not in seen:
            seen.add(v)
            result.append(v)
    return result


def _bool_values() -> list[bool]:
    return [False, True]


STR_EDGE: list[str] = [
    "",
    "a",
    "ab",
    "aa",
    "abc",
    "aba",
    "racecar",
    "hello",
    "aeiou",
    "AEIOU",
    "Hello",
    "Aba",
    "12321",
]

def _str_values(rng: random.Random, n: int = 20) -> list[str]:
    vals = list(STR_EDGE)
    chars = string.ascii_lowercase
    while len(vals) < n:
        length = rng.randint(0, 6)
        vals.append("".join(rng.choice(chars) for _ in range(length)))
    seen: set = set()
    result = []
    for v in vals:
        if v not in seen:
            seen.add(v)
            result.append(v)
    return result


def _list_int_values(
    rng: random.Random,
    n: int = 60,
    min_length: int = 0,
    max_length: int = 8,
    value_range: Tuple[int, int] = (-10, 10),
) -> list[Tuple[int, ...]]:
    """Return *n* distinct tuples-of-int (each represents one list argument)."""
    lo, hi = value_range
    vals: list[Tuple[int, ...]] = []

    # Edge cases: empty (if allowed), singletons, sorted, reversed, duplicates
    if min_length == 0:
        vals.append(())
    for v in range(-3, 4):
        vals.append((v,))

    # Sorted lists
    for length in range(max(2, min_length), min(6, max_length) + 1):
        base = sorted(rng.randint(lo, hi) for _ in range(length))
        vals.append(tuple(base))
        vals.append(tuple(reversed(base)))

    # Lists with duplicates
    for length in range(max(2, min_length), min(5, max_length) + 1):
        v = rng.randint(lo, hi)
        vals.append(tuple([v] * length))

    # All-negative, all-positive
    for length in range(max(1, min_length), min(5, max_length) + 1):
        vals.append(tuple(-(rng.randint(1, 10)) for _ in range(length)))
        vals.append(tuple(rng.randint(1, 10) for _ in range(length)))

    # Fully random
    while len(vals) < n * 2:
        length = rng.randint(min_length, max_length)
        vals.append(tuple(rng.randint(lo, hi) for _ in range(length)))

    # Deduplicate while preserving order
    seen: set = set()
    result = []
    for v in vals:
        if v not in seen:
            seen.add(v)
            result.append(v)
    return result[:n]


def _list_str_values(rng: random.Random, n: int = 40) -> list[Tuple[str, ...]]:
    chars = list(string.ascii_lowercase[:8])
    vals: list[Tuple[str, ...]] = [
        (),
        ("a",),
        ("a", "b"),
        ("a", "a"),
        ("a", "b", "a"),
    ]
    while len(vals) < n * 2:
        length = rng.randint(0, 5)
        vals.append(tuple(rng.choice(chars) for _ in range(length)))
    seen: set = set()
    result = []
    for v in vals:
        if v not in seen:
            seen.add(v)
            result.append(v)
    return result[:n]


# ---------------------------------------------------------------------------
# InputGenerator
# ---------------------------------------------------------------------------

class InputGenerator:
    """
    Generate diverse input tuples for a given function signature.

    Parameters
    ----------
    param_types : list of type-annotation strings, e.g. ["list[int]", "int"]
    seed        : optional random seed for reproducibility
    min_list_length : 0 (default) or 1 for functions requiring non-empty lists
    """

    def __init__(
        self,
        param_types: list[str],
        seed: Optional[int] = None,
        min_list_length: int = 0,
    ) -> None:
        self.param_types = param_types
        self._rng = random.Random(seed)
        self._min_list_length = min_list_length

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self, n: int = 2000) -> list[Tuple]:
        """
        Return up to *n* distinct input tuples.

        We first generate a large pool of candidates by taking the Cartesian
        product of per-type value sets, then sample randomly until we have
        enough.
        """
        per_type = [self._values_for(t) for t in self.param_types]

        # Start with the full Cartesian product for small parameter counts
        candidates: list[Tuple] = []
        if len(self.param_types) <= 2:
            for combo in product(*per_type):
                # Unpack tuple-of-int values back to lists
                candidates.append(tuple(list(v) if isinstance(v, tuple) else v for v in combo))

        # Add random combinations
        attempts = 0
        while len(candidates) < n * 3 and attempts < n * 10:
            attempts += 1
            combo = tuple(
                self._random_value(t) for t in self.param_types
            )
            candidates.append(combo)

        # Deduplicate using repr as key (handles lists/nested structures)
        seen: set = set()
        result: list[Tuple] = []
        for c in candidates:
            key = repr(c)
            if key not in seen:
                seen.add(key)
                result.append(c)
            if len(result) >= n:
                break

        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _values_for(self, type_str: str) -> list[Any]:
        """Return a small representative set for one parameter type."""
        t = type_str.strip()
        if t == "int":
            return _int_values(self._rng, n=20)
        if t == "bool":
            return _bool_values()
        if t == "str":
            return _str_values(self._rng, n=15)
        if t in ("list[int]", "list"):
            raw = _list_int_values(
                self._rng, n=40,
                min_length=self._min_list_length,
            )
            return [list(v) for v in raw]
        if t == "list[str]":
            raw = _list_str_values(self._rng, n=20)
            return [list(v) for v in raw]
        # Fallback: treat as int
        return _int_values(self._rng, n=10)

    def _random_value(self, type_str: str) -> Any:
        """Return one random value for a given type string."""
        t = type_str.strip()
        if t == "int":
            # Use a wide range so we can accumulate 1 000+ distinct integers
            return self._rng.randint(-700, 700)
        if t == "bool":
            return self._rng.choice([True, False])
        if t == "str":
            length = self._rng.randint(0, 8)
            return "".join(
                self._rng.choice(string.ascii_lowercase) for _ in range(length)
            )
        if t in ("list[int]", "list"):
            length = self._rng.randint(self._min_list_length, 8)
            return [self._rng.randint(-10, 10) for _ in range(length)]
        if t == "list[str]":
            length = self._rng.randint(0, 5)
            chars = list(string.ascii_lowercase[:8])
            return [self._rng.choice(chars) for _ in range(length)]
        # Fallback
        return self._rng.randint(-10, 10)
