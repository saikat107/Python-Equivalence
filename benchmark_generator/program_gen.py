"""
Template-based random program generator.

Each TEMPLATE entry describes a parameterised function family.  The generator
picks random parameter values and instantiates the template into a concrete
seed function, together with its equivalent variants and mutations.

Supported template categories
------------------------------
* filter_threshold   – keep elements satisfying a comparison to a constant
* count_threshold    – count elements satisfying a comparison
* sum_threshold      – sum elements satisfying a comparison
* map_scale          – multiply every element by a constant
* find_first         – return index of first element satisfying a comparison
"""

from __future__ import annotations

import random
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Template definitions
# ---------------------------------------------------------------------------

# Each template is a dict with:
#   template_id      – unique name
#   category         – functional category
#   param_types      – list of type-annotation strings
#   return_type      – return type string
#   constraints      – precondition string (empty = none)
#   param_choices    – mapping name -> list of possible values
#   build_source     – callable(params) -> canonical source string
#   build_equivalents – callable(params) -> list of equivalent source strings
#   build_mutations   – callable(params) -> list of {source, description} dicts

def _op_flip(op: str) -> str:
    """Return a related but semantically different operator."""
    flips = {">": ">=", ">=": ">", "<": "<=", "<=": "<", "==": "!=", "!=": "=="}
    return flips.get(op, ">=")


def _op_to_str(op: str) -> str:
    return {">": "gt", ">=": "gte", "<": "lt", "<=": "lte"}.get(op, op)


# ------ filter_threshold -----------------------------------------------

def _filter_threshold_source(op: str, threshold: int, fname: str) -> str:
    return (
        f"def {fname}(xs: list) -> list:\n"
        f"    result = []\n"
        f"    for x in xs:\n"
        f"        if x {op} {threshold}:\n"
        f"            result.append(x)\n"
        f"    return result\n"
    )


def _filter_threshold_equiv(op: str, threshold: int, fname: str) -> list[str]:
    return [
        (
            f"def {fname}(xs: list) -> list:\n"
            f"    return [x for x in xs if x {op} {threshold}]\n"
        ),
        (
            f"def {fname}(xs: list) -> list:\n"
            f"    return list(filter(lambda x: x {op} {threshold}, xs))\n"
        ),
    ]


def _filter_threshold_mutations(op: str, threshold: int, fname: str) -> list[dict]:
    flipped_op = _op_flip(op)
    return [
        {
            "source": (
                f"def {fname}(xs: list) -> list:\n"
                f"    return [x for x in xs if x {flipped_op} {threshold}]\n"
            ),
            "description": f"uses '{flipped_op}' instead of '{op}' — boundary inclusion changed",
        },
        {
            "source": (
                f"def {fname}(xs: list) -> list:\n"
                f"    return [x for x in xs if x {op} {threshold + 1}]\n"
            ),
            "description": f"threshold off-by-one: uses {threshold + 1} instead of {threshold}",
        },
    ]


# ------ count_threshold -----------------------------------------------

def _count_threshold_source(op: str, threshold: int, fname: str) -> str:
    return (
        f"def {fname}(xs: list) -> int:\n"
        f"    count = 0\n"
        f"    for x in xs:\n"
        f"        if x {op} {threshold}:\n"
        f"            count += 1\n"
        f"    return count\n"
    )


def _count_threshold_equiv(op: str, threshold: int, fname: str) -> list[str]:
    return [
        (
            f"def {fname}(xs: list) -> int:\n"
            f"    return sum(1 for x in xs if x {op} {threshold})\n"
        ),
        (
            f"def {fname}(xs: list) -> int:\n"
            f"    return len([x for x in xs if x {op} {threshold}])\n"
        ),
    ]


def _count_threshold_mutations(op: str, threshold: int, fname: str) -> list[dict]:
    flipped_op = _op_flip(op)
    return [
        {
            "source": (
                f"def {fname}(xs: list) -> int:\n"
                f"    return sum(1 for x in xs if x {flipped_op} {threshold})\n"
            ),
            "description": f"uses '{flipped_op}' instead of '{op}'",
        },
        {
            "source": (
                f"def {fname}(xs: list) -> int:\n"
                f"    return len(xs)\n"
            ),
            "description": "always returns total list length — ignores condition",
        },
    ]


# ------ sum_threshold -----------------------------------------------

def _sum_threshold_source(op: str, threshold: int, fname: str) -> str:
    return (
        f"def {fname}(xs: list) -> int:\n"
        f"    total = 0\n"
        f"    for x in xs:\n"
        f"        if x {op} {threshold}:\n"
        f"            total += x\n"
        f"    return total\n"
    )


def _sum_threshold_equiv(op: str, threshold: int, fname: str) -> list[str]:
    return [
        (
            f"def {fname}(xs: list) -> int:\n"
            f"    return sum(x for x in xs if x {op} {threshold})\n"
        ),
        (
            f"def {fname}(xs: list) -> int:\n"
            f"    filtered = [x for x in xs if x {op} {threshold}]\n"
            f"    total = 0\n"
            f"    for v in filtered:\n"
            f"        total += v\n"
            f"    return total\n"
        ),
    ]


def _sum_threshold_mutations(op: str, threshold: int, fname: str) -> list[dict]:
    flipped_op = _op_flip(op)
    return [
        {
            "source": (
                f"def {fname}(xs: list) -> int:\n"
                f"    return sum(x for x in xs if x {flipped_op} {threshold})\n"
            ),
            "description": f"uses '{flipped_op}' instead of '{op}'",
        },
        {
            "source": (
                f"def {fname}(xs: list) -> int:\n"
                f"    return sum(xs)\n"
            ),
            "description": "sums all elements instead of only those satisfying the condition",
        },
    ]


# ------ map_scale -----------------------------------------------

def _map_scale_source(scale: int, fname: str) -> str:
    return (
        f"def {fname}(xs: list) -> list:\n"
        f"    result = []\n"
        f"    for x in xs:\n"
        f"        result.append(x * {scale})\n"
        f"    return result\n"
    )


def _map_scale_equiv(scale: int, fname: str) -> list[str]:
    return [
        (
            f"def {fname}(xs: list) -> list:\n"
            f"    return [x * {scale} for x in xs]\n"
        ),
        (
            f"def {fname}(xs: list) -> list:\n"
            f"    return list(map(lambda x: x * {scale}, xs))\n"
        ),
    ]


def _map_scale_mutations(scale: int, fname: str) -> list[dict]:
    wrong_scale = scale + 1
    return [
        {
            "source": (
                f"def {fname}(xs: list) -> list:\n"
                f"    return [x * {wrong_scale} for x in xs]\n"
            ),
            "description": f"uses scale {wrong_scale} instead of {scale}",
        },
        {
            "source": (
                f"def {fname}(xs: list) -> list:\n"
                f"    return [x + {scale} for x in xs]\n"
            ),
            "description": f"adds {scale} instead of multiplying by {scale}",
        },
    ]


# ------ find_first -----------------------------------------------

def _find_first_source(op: str, threshold: int, fname: str) -> str:
    return (
        f"def {fname}(xs: list) -> int:\n"
        f"    for i, x in enumerate(xs):\n"
        f"        if x {op} {threshold}:\n"
        f"            return i\n"
        f"    return -1\n"
    )


def _find_first_equiv(op: str, threshold: int, fname: str) -> list[str]:
    return [
        (
            f"def {fname}(xs: list) -> int:\n"
            f"    i = 0\n"
            f"    while i < len(xs):\n"
            f"        if xs[i] {op} {threshold}:\n"
            f"            return i\n"
            f"        i += 1\n"
            f"    return -1\n"
        ),
        (
            f"def {fname}(xs: list) -> int:\n"
            f"    matches = [i for i, x in enumerate(xs) if x {op} {threshold}]\n"
            f"    return matches[0] if matches else -1\n"
        ),
    ]


def _find_first_mutations(op: str, threshold: int, fname: str) -> list[dict]:
    flipped_op = _op_flip(op)
    return [
        {
            "source": (
                f"def {fname}(xs: list) -> int:\n"
                f"    for i, x in enumerate(xs):\n"
                f"        if x {op} {threshold}:\n"
                f"            return i + 1\n"
                f"    return -1\n"
            ),
            "description": "off-by-one: returns i+1 instead of i",
        },
        {
            "source": (
                f"def {fname}(xs: list) -> int:\n"
                f"    for i, x in enumerate(xs):\n"
                f"        if x {flipped_op} {threshold}:\n"
                f"            return i\n"
                f"    return -1\n"
            ),
            "description": f"uses '{flipped_op}' instead of '{op}' in the condition",
        },
    ]


# ---------------------------------------------------------------------------
# TEMPLATES registry
# ---------------------------------------------------------------------------

TEMPLATES: list[dict[str, Any]] = [
    {
        "template_id": "filter_threshold",
        "category": "filtering",
        "param_types": ["list[int]"],
        "return_type": "list[int]",
        "constraints": "",
        "param_choices": {
            "op": [">", "<", ">=", "<="],
            "threshold": list(range(-3, 6)),
        },
        "build_source": lambda p, name: _filter_threshold_source(p["op"], p["threshold"], name),
        "build_equivalents": lambda p, name: _filter_threshold_equiv(p["op"], p["threshold"], name),
        "build_mutations": lambda p, name: _filter_threshold_mutations(p["op"], p["threshold"], name),
    },
    {
        "template_id": "count_threshold",
        "category": "aggregation",
        "param_types": ["list[int]"],
        "return_type": "int",
        "constraints": "",
        "param_choices": {
            "op": [">", "<", ">=", "<="],
            "threshold": list(range(-3, 6)),
        },
        "build_source": lambda p, name: _count_threshold_source(p["op"], p["threshold"], name),
        "build_equivalents": lambda p, name: _count_threshold_equiv(p["op"], p["threshold"], name),
        "build_mutations": lambda p, name: _count_threshold_mutations(p["op"], p["threshold"], name),
    },
    {
        "template_id": "sum_threshold",
        "category": "aggregation",
        "param_types": ["list[int]"],
        "return_type": "int",
        "constraints": "",
        "param_choices": {
            "op": [">", "<", ">=", "<="],
            "threshold": list(range(-3, 6)),
        },
        "build_source": lambda p, name: _sum_threshold_source(p["op"], p["threshold"], name),
        "build_equivalents": lambda p, name: _sum_threshold_equiv(p["op"], p["threshold"], name),
        "build_mutations": lambda p, name: _sum_threshold_mutations(p["op"], p["threshold"], name),
    },
    {
        "template_id": "map_scale",
        "category": "transformation",
        "param_types": ["list[int]"],
        "return_type": "list[int]",
        "constraints": "",
        "param_choices": {
            "scale": [2, 3, 4, 5, 10],
        },
        "build_source": lambda p, name: _map_scale_source(p["scale"], name),
        "build_equivalents": lambda p, name: _map_scale_equiv(p["scale"], name),
        "build_mutations": lambda p, name: _map_scale_mutations(p["scale"], name),
    },
    {
        "template_id": "find_first",
        "category": "searching",
        "param_types": ["list[int]"],
        "return_type": "int",
        "constraints": "",
        "param_choices": {
            "op": [">", "<", ">=", "<="],
            "threshold": list(range(-2, 5)),
        },
        "build_source": lambda p, name: _find_first_source(p["op"], p["threshold"], name),
        "build_equivalents": lambda p, name: _find_first_equiv(p["op"], p["threshold"], name),
        "build_mutations": lambda p, name: _find_first_mutations(p["op"], p["threshold"], name),
    },
]


# ---------------------------------------------------------------------------
# Generator class
# ---------------------------------------------------------------------------

class RandomProgramGenerator:
    """
    Generates random function triplets (source, equivalents, mutations) from
    the TEMPLATES registry.

    Each call to :meth:`generate` picks a random template and instantiates it
    with a random combination of parameter values.
    """

    def __init__(self, seed: Optional[int] = None) -> None:
        self._rng = random.Random(seed)

    def generate(self, n: int = 20) -> list[dict[str, Any]]:
        """
        Return *n* randomly instantiated seed-function descriptors.

        Each descriptor has the same structure as a CATALOG entry:
            name, param_types, return_type, category, constraints,
            source, equivalents, mutations
        """
        results: list[dict[str, Any]] = []
        seen: set = set()

        attempts = 0
        while len(results) < n and attempts < n * 10:
            attempts += 1
            template = self._rng.choice(TEMPLATES)
            params = {
                key: self._rng.choice(choices)
                for key, choices in template["param_choices"].items()
            }

            # Build a deterministic function name from template + params
            # Sanitise values so the resulting identifier is valid Python.
            def _safe(v: Any) -> str:
                return (
                    str(v)
                    .replace(">=", "gte")
                    .replace("<=", "lte")
                    .replace(">", "gt")
                    .replace("<", "lt")
                    .replace("-", "m")
                )

            suffix = "_".join(_safe(v) for v in params.values())
            fname = f"{template['template_id']}_{suffix}"

            if fname in seen:
                continue
            seen.add(fname)

            source = template["build_source"](params, fname)
            equivalents = template["build_equivalents"](params, fname)
            mutations = template["build_mutations"](params, fname)

            results.append(
                {
                    "name": fname,
                    "param_types": template["param_types"],
                    "return_type": template["return_type"],
                    "category": template["category"],
                    "constraints": template["constraints"],
                    "source": source,
                    "equivalents": equivalents,
                    "mutations": mutations,
                    "provenance": "template",
                    "template_id": template["template_id"],
                    "template_params": params,
                }
            )

        return results
