"""
Recursive random value generator for arbitrary Python type annotations.

Generates diverse test inputs for types ranging from simple primitives to
complex nested types like ``dict[str, list[tuple[str, str, bool]]]``.

Uses a :class:`TypeNode` tree (produced by :mod:`fuzzer.type_parser`) to
drive generation, recursing into container element types as needed.
"""

from __future__ import annotations

import random
import string
from typing import Any

from .type_parser import TypeNode


class ValueGenerator:
    """Generate random values that conform to a :class:`TypeNode` specification.

    Parameters
    ----------
    seed : optional random seed for reproducibility
    max_collection_size : upper bound for generated list/dict/set sizes
    max_depth : recursion guard for deeply nested types
    """

    def __init__(
        self,
        seed: int | None = None,
        max_collection_size: int = 5,
        max_depth: int = 4,
    ) -> None:
        self._rng = random.Random(seed)
        self._max_size = max_collection_size
        self._max_depth = max_depth

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self, type_node: TypeNode, *, _depth: int = 0) -> Any:
        """Return a single random value conforming to *type_node*."""
        if _depth > self._max_depth:
            return self._primitive_fallback()

        dispatch = {
            "int": self._gen_int,
            "float": self._gen_float,
            "str": self._gen_str,
            "bool": self._gen_bool,
            "None": lambda: None,
            "NoneType": lambda: None,
            "bytes": self._gen_bytes,
            "list": lambda: self._gen_list(type_node, _depth),
            "dict": lambda: self._gen_dict(type_node, _depth),
            "tuple": lambda: self._gen_tuple(type_node, _depth),
            "set": lambda: self._gen_set(type_node, _depth),
            "frozenset": lambda: self._gen_frozenset(type_node, _depth),
            "Optional": lambda: self._gen_optional(type_node, _depth),
            "Union": lambda: self._gen_union(type_node, _depth),
            "Any": self._primitive_fallback,
        }

        handler = dispatch.get(type_node.name)
        if handler is not None:
            return handler()

        # Unknown type → fall back to int
        return self._gen_int()

    def generate_inputs(
        self,
        param_types: list[TypeNode],
        n: int = 100,
    ) -> list[tuple]:
        """Generate up to *n* unique input tuples for a function.

        Each tuple has one element per entry in *param_types*.
        Deduplication uses ``repr()`` as key.
        """
        seen: set[str] = set()
        results: list[tuple] = []
        max_attempts = n * 20

        for _ in range(max_attempts):
            if len(results) >= n:
                break
            inp = tuple(self.generate(t) for t in param_types)
            key = repr(inp)
            if key not in seen:
                seen.add(key)
                results.append(inp)

        return results

    # ------------------------------------------------------------------
    # Primitives
    # ------------------------------------------------------------------

    def _gen_int(self) -> int:
        strategy = self._rng.randint(0, 3)
        if strategy == 0:
            return self._rng.choice(
                [-100, -10, -3, -2, -1, 0, 1, 2, 3, 10, 100]
            )
        if strategy == 1:
            return self._rng.randint(-30, 30)
        if strategy == 2:
            return self._rng.randint(-500, 500)
        return self._rng.choice([0, 1, -1])

    def _gen_float(self) -> float:
        strategy = self._rng.randint(0, 2)
        if strategy == 0:
            return self._rng.choice(
                [-10.0, -1.0, -0.5, 0.0, 0.5, 1.0, 10.0]
            )
        if strategy == 1:
            return round(self._rng.uniform(-30.0, 30.0), 2)
        return round(self._rng.uniform(-500.0, 500.0), 2)

    def _gen_str(self) -> str:
        strategy = self._rng.randint(0, 2)
        if strategy == 0:
            return self._rng.choice(
                ["", "a", "ab", "abc", "hello", "racecar", "HELLO"]
            )
        if strategy == 1:
            length = self._rng.randint(0, 8)
            return "".join(
                self._rng.choice(string.ascii_lowercase)
                for _ in range(length)
            )
        length = self._rng.randint(1, 5)
        return "".join(
            self._rng.choice(string.ascii_letters + string.digits)
            for _ in range(length)
        )

    def _gen_bool(self) -> bool:
        return self._rng.choice([True, False])

    def _gen_bytes(self) -> bytes:
        length = self._rng.randint(0, 8)
        return bytes(self._rng.randint(0, 255) for _ in range(length))

    def _primitive_fallback(self) -> Any:
        choice = self._rng.randint(0, 3)
        if choice == 0:
            return self._gen_int()
        if choice == 1:
            return self._gen_float()
        if choice == 2:
            return self._gen_str()
        return self._gen_bool()

    # ------------------------------------------------------------------
    # Containers
    # ------------------------------------------------------------------

    def _gen_list(self, node: TypeNode, depth: int) -> list:
        elem = node.args[0] if node.args else TypeNode("int")
        length = self._rng.randint(0, self._max_size)
        return [self.generate(elem, _depth=depth + 1) for _ in range(length)]

    def _gen_dict(self, node: TypeNode, depth: int) -> dict:
        key_t = node.args[0] if len(node.args) >= 1 else TypeNode("str")
        val_t = node.args[1] if len(node.args) >= 2 else TypeNode("int")
        size = self._rng.randint(0, self._max_size)
        result: dict = {}
        for _ in range(size * 3):
            if len(result) >= size:
                break
            key = self.generate(key_t, _depth=depth + 1)
            try:
                hash(key)
            except TypeError:
                continue
            result[key] = self.generate(val_t, _depth=depth + 1)
        return result

    def _gen_tuple(self, node: TypeNode, depth: int) -> tuple:
        if node.is_variadic:
            elem = node.args[0] if node.args else TypeNode("int")
            length = self._rng.randint(0, self._max_size)
            return tuple(
                self.generate(elem, _depth=depth + 1) for _ in range(length)
            )
        if node.args:
            return tuple(
                self.generate(arg, _depth=depth + 1) for arg in node.args
            )
        # Bare ``tuple`` with no args → treat as variable-length int tuple
        length = self._rng.randint(0, 3)
        return tuple(self._gen_int() for _ in range(length))

    def _gen_set(self, node: TypeNode, depth: int) -> set:
        elem = node.args[0] if node.args else TypeNode("int")
        size = self._rng.randint(0, self._max_size)
        result: set = set()
        for _ in range(size * 3):
            if len(result) >= size:
                break
            val = self.generate(elem, _depth=depth + 1)
            try:
                hash(val)
                result.add(val)
            except TypeError:
                continue
        return result

    def _gen_frozenset(self, node: TypeNode, depth: int) -> frozenset:
        return frozenset(self._gen_set(node, depth))

    # ------------------------------------------------------------------
    # Union / Optional
    # ------------------------------------------------------------------

    def _gen_optional(self, node: TypeNode, depth: int) -> Any:
        if self._rng.random() < 0.2:
            return None
        if node.args:
            return self.generate(node.args[0], _depth=depth + 1)
        return None

    def _gen_union(self, node: TypeNode, depth: int) -> Any:
        if node.args:
            chosen = self._rng.choice(node.args)
            return self.generate(chosen, _depth=depth + 1)
        return None
