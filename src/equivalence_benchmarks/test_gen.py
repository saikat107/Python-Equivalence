"""
Type-directed test input generator.

Given a list of parameter-type annotation strings, the generator creates a
diverse set of input tuples suitable for:
  * verifying equivalence  (ptests — 1 000+ distinct inputs)
  * finding counterexamples (ntests — at least one differing input)

Supported type strings
-----------------------
  int          float         bool          str
  list[int]    list[str]     list[float]
  set[int]     dict[str,int] tuple[int,...]

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


# Floats: include 0.0, ±1.0, boundaries, and random values.
FLOAT_EDGE: list[float] = [
    -10.0, -5.5, -3.0, -2.5, -1.0, -0.5, -0.1, 0.0,
    0.1, 0.5, 1.0, 2.5, 3.0, 5.5, 10.0, 100.0, -100.0,
]

def _float_values(rng: random.Random, n: int = 60) -> list[float]:
    """Return *n* diverse floats including edge cases and a wide spread."""
    vals = list(FLOAT_EDGE)
    for v in range(-20, 21):
        fv = float(v)
        if fv not in vals:
            vals.append(fv)
        fv_half = v + 0.5
        if fv_half not in vals:
            vals.append(fv_half)
    while len(vals) < n:
        vals.append(round(rng.uniform(-200.0, 200.0), 2))
    seen: set = set()
    result = []
    for v in vals:
        if v not in seen:
            seen.add(v)
            result.append(v)
    return result


def _list_float_values(
    rng: random.Random,
    n: int = 60,
    min_length: int = 0,
    max_length: int = 8,
    value_range: Tuple[float, float] = (-10.0, 10.0),
) -> list[Tuple[float, ...]]:
    """Return *n* distinct tuples-of-float."""
    lo, hi = value_range
    vals: list[Tuple[float, ...]] = []

    if min_length == 0:
        vals.append(())
    for v in [-3.0, -1.5, 0.0, 1.5, 3.0]:
        vals.append((v,))

    for length in range(max(2, min_length), min(6, max_length) + 1):
        base = sorted(round(rng.uniform(lo, hi), 2) for _ in range(length))
        vals.append(tuple(base))
        vals.append(tuple(reversed(base)))

    for length in range(max(2, min_length), min(5, max_length) + 1):
        v = round(rng.uniform(lo, hi), 2)
        vals.append(tuple([v] * length))

    while len(vals) < n * 2:
        length = rng.randint(min_length, max_length)
        vals.append(tuple(round(rng.uniform(lo, hi), 2) for _ in range(length)))

    seen: set = set()
    result = []
    for v in vals:
        if v not in seen:
            seen.add(v)
            result.append(v)
    return result[:n]


def _set_int_values(rng: random.Random, n: int = 60) -> list[frozenset]:
    """Return *n* distinct frozensets-of-int (each represents one set argument)."""
    vals: list[frozenset] = []

    vals.append(frozenset())
    for v in range(-3, 4):
        vals.append(frozenset([v]))

    for size in range(2, 6):
        elements = sorted(rng.randint(-10, 10) for _ in range(size))
        vals.append(frozenset(elements))

    while len(vals) < n * 2:
        size = rng.randint(0, 8)
        vals.append(frozenset(rng.randint(-10, 10) for _ in range(size)))

    seen: set = set()
    result = []
    for v in vals:
        if v not in seen:
            seen.add(v)
            result.append(v)
    return result[:n]


DICT_KEYS_POOL: list[str] = ["a", "b", "c", "d", "e", "x", "y", "z"]

def _dict_str_int_values(rng: random.Random, n: int = 60) -> list[tuple]:
    """Return *n* distinct dicts (as sorted-item tuples for hashing)."""
    vals: list[tuple] = []

    vals.append(())  # empty dict
    for k in DICT_KEYS_POOL[:3]:
        vals.append(((k, 0),))
    vals.append((("a", 1), ("b", 2)))
    vals.append((("a", -1), ("b", -2), ("c", 3)))

    while len(vals) < n * 2:
        size = rng.randint(0, 5)
        keys = rng.sample(DICT_KEYS_POOL, min(size, len(DICT_KEYS_POOL)))
        items = tuple(sorted((k, rng.randint(-10, 10)) for k in keys))
        vals.append(items)

    seen: set = set()
    result = []
    for v in vals:
        if v not in seen:
            seen.add(v)
            result.append(v)
    return result[:n]


def _tuple_int_values(
    rng: random.Random,
    n: int = 60,
    min_length: int = 0,
    max_length: int = 8,
) -> list[Tuple[int, ...]]:
    """Return *n* distinct tuples-of-int for tuple[int,...] type."""
    vals: list[Tuple[int, ...]] = []

    if min_length == 0:
        vals.append(())
    for v in range(-3, 4):
        vals.append((v,))

    for length in range(max(2, min_length), min(6, max_length) + 1):
        base = sorted(rng.randint(-10, 10) for _ in range(length))
        vals.append(tuple(base))
        vals.append(tuple(reversed(base)))

    while len(vals) < n * 2:
        length = rng.randint(min_length, max_length)
        vals.append(tuple(rng.randint(-10, 10) for _ in range(length)))

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

        # Types whose _values_for returns tuples that need list conversion
        _LIST_TYPES = {"list[int]", "list", "list[str]", "list[float]"}

        # Start with the full Cartesian product for small parameter counts
        candidates: list[Tuple] = []
        if len(self.param_types) <= 2:
            for combo in product(*per_type):
                # Unpack tuple-of-int values back to lists for list types only
                candidates.append(tuple(
                    list(v) if isinstance(v, tuple) and self.param_types[i].strip() in _LIST_TYPES else v
                    for i, v in enumerate(combo)
                ))

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
        if t == "float":
            return _float_values(self._rng, n=20)
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
        if t == "list[float]":
            raw = _list_float_values(
                self._rng, n=40,
                min_length=self._min_list_length,
            )
            return [list(v) for v in raw]
        if t == "set[int]":
            raw = _set_int_values(self._rng, n=40)
            return [set(v) for v in raw]
        if t == "dict[str,int]":
            raw = _dict_str_int_values(self._rng, n=40)
            return [dict(v) for v in raw]
        if t == "tuple[int,...]":
            raw = _tuple_int_values(
                self._rng, n=40,
                min_length=self._min_list_length,
            )
            return [v for v in raw]
        # Fallback: treat as int
        return _int_values(self._rng, n=10)

    def _random_value(self, type_str: str) -> Any:
        """Return one random value for a given type string."""
        t = type_str.strip()
        if t == "int":
            # Use a wide range so we can accumulate 1 000+ distinct integers
            return self._rng.randint(-700, 700)
        if t == "float":
            return round(self._rng.uniform(-700.0, 700.0), 2)
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
        if t == "list[float]":
            length = self._rng.randint(self._min_list_length, 8)
            return [round(self._rng.uniform(-10.0, 10.0), 2) for _ in range(length)]
        if t == "set[int]":
            size = self._rng.randint(0, 8)
            return set(self._rng.randint(-10, 10) for _ in range(size))
        if t == "dict[str,int]":
            size = self._rng.randint(0, 5)
            keys = self._rng.sample(
                DICT_KEYS_POOL, min(size, len(DICT_KEYS_POOL))
            )
            return {k: self._rng.randint(-10, 10) for k in keys}
        if t == "tuple[int,...]":
            length = self._rng.randint(self._min_list_length, 8)
            return tuple(self._rng.randint(-10, 10) for _ in range(length))
        # Fallback
        return self._rng.randint(-10, 10)
