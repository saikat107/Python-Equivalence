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


# ------ sliding_window_sum ------------------------------------------------

def _sliding_window_sum_source(ws: int, fname: str) -> str:
    return (
        f"def {fname}(xs: list) -> list:\n"
        f"    n = len(xs)\n"
        f"    if n < {ws}:\n"
        f"        return []\n"
        f"    result = []\n"
        f"    window_total = 0\n"
        f"    for k in range({ws}):\n"
        f"        window_total = window_total + xs[k]\n"
        f"    result.append(window_total)\n"
        f"    pos = {ws}\n"
        f"    while pos < n:\n"
        f"        window_total = window_total + xs[pos]\n"
        f"        window_total = window_total - xs[pos - {ws}]\n"
        f"        result.append(window_total)\n"
        f"        pos = pos + 1\n"
        f"    return result\n"
    )


def _sliding_window_sum_equiv(ws: int, fname: str) -> list[str]:
    return [
        (
            f"def {fname}(xs: list) -> list:\n"
            f"    n = len(xs)\n"
            f"    ws = {ws}\n"
            f"    if n < ws:\n"
            f"        return []\n"
            f"    result = []\n"
            f"    i = 0\n"
            f"    while i <= n - ws:\n"
            f"        total = 0\n"
            f"        j = i\n"
            f"        while j < i + ws:\n"
            f"            total = total + xs[j]\n"
            f"            j = j + 1\n"
            f"        result.append(total)\n"
            f"        i = i + 1\n"
            f"    return result\n"
        ),
        (
            f"def {fname}(xs: list) -> list:\n"
            f"    n = len(xs)\n"
            f"    ws = {ws}\n"
            f"    if n < ws:\n"
            f"        return []\n"
            f"    sums = []\n"
            f"    idx = 0\n"
            f"    limit = n - ws + 1\n"
            f"    while idx < limit:\n"
            f"        start = idx\n"
            f"        end = idx + ws\n"
            f"        window = xs[start:end]\n"
            f"        window_sum = sum(window)\n"
            f"        sums.append(window_sum)\n"
            f"        idx = idx + 1\n"
            f"    return sums\n"
        ),
    ]


def _sliding_window_sum_mutations(ws: int, fname: str) -> list[dict]:
    return [
        {
            "source": (
                f"def {fname}(xs: list) -> list:\n"
                f"    n = len(xs)\n"
                f"    if n < {ws}:\n"
                f"        return []\n"
                f"    result = []\n"
                f"    window_total = 0\n"
                f"    for k in range({ws} - 1):\n"
                f"        window_total = window_total + xs[k]\n"
                f"    result.append(window_total)\n"
                f"    pos = {ws}\n"
                f"    while pos < n:\n"
                f"        window_total = window_total + xs[pos]\n"
                f"        window_total = window_total - xs[pos - {ws}]\n"
                f"        result.append(window_total)\n"
                f"        pos = pos + 1\n"
                f"    return result\n"
            ),
            "description": f"initial window uses {ws}-1 elements — first sum is wrong",
        },
        {
            "source": (
                f"def {fname}(xs: list) -> list:\n"
                f"    n = len(xs)\n"
                f"    if n < {ws}:\n"
                f"        return []\n"
                f"    result = []\n"
                f"    window_total = 0\n"
                f"    for k in range({ws}):\n"
                f"        window_total = window_total + xs[k]\n"
                f"    result.append(window_total)\n"
                f"    pos = {ws}\n"
                f"    while pos < n:\n"
                f"        window_total = window_total + xs[pos]\n"
                f"        window_total = window_total - xs[pos - {ws} + 1]\n"
                f"        result.append(window_total)\n"
                f"        pos = pos + 1\n"
                f"    return result\n"
            ),
            "description": "wrong subtraction index (off-by-one) — sliding window drifts",
        },
    ]


# ------ partition_count ------------------------------------------------

def _partition_count_source(lo: int, hi: int, fname: str) -> str:
    return (
        f"def {fname}(xs: list) -> list:\n"
        f"    low_count = 0\n"
        f"    mid_count = 0\n"
        f"    high_count = 0\n"
        f"    idx = 0\n"
        f"    n = len(xs)\n"
        f"    while idx < n:\n"
        f"        val = xs[idx]\n"
        f"        if val < {lo}:\n"
        f"            low_count = low_count + 1\n"
        f"        elif val > {hi}:\n"
        f"            high_count = high_count + 1\n"
        f"        else:\n"
        f"            mid_count = mid_count + 1\n"
        f"        idx = idx + 1\n"
        f"    result = [low_count, mid_count, high_count]\n"
        f"    return result\n"
    )


def _partition_count_equiv(lo: int, hi: int, fname: str) -> list[str]:
    return [
        (
            f"def {fname}(xs: list) -> list:\n"
            f"    low = 0\n"
            f"    mid = 0\n"
            f"    high = 0\n"
            f"    for val in xs:\n"
            f"        is_below = val < {lo}\n"
            f"        is_above = val > {hi}\n"
            f"        if is_below:\n"
            f"            low = low + 1\n"
            f"        elif is_above:\n"
            f"            high = high + 1\n"
            f"        else:\n"
            f"            mid = mid + 1\n"
            f"    counts = [low, mid, high]\n"
            f"    return counts\n"
        ),
        (
            f"def {fname}(xs: list) -> list:\n"
            f"    n = len(xs)\n"
            f"    low = 0\n"
            f"    high = 0\n"
            f"    i = 0\n"
            f"    while i < n:\n"
            f"        if xs[i] < {lo}:\n"
            f"            low = low + 1\n"
            f"        elif xs[i] > {hi}:\n"
            f"            high = high + 1\n"
            f"        i = i + 1\n"
            f"    mid = n - low - high\n"
            f"    result = []\n"
            f"    result.append(low)\n"
            f"    result.append(mid)\n"
            f"    result.append(high)\n"
            f"    return result\n"
        ),
    ]


def _partition_count_mutations(lo: int, hi: int, fname: str) -> list[dict]:
    return [
        {
            "source": (
                f"def {fname}(xs: list) -> list:\n"
                f"    low_count = 0\n"
                f"    mid_count = 0\n"
                f"    high_count = 0\n"
                f"    idx = 0\n"
                f"    n = len(xs)\n"
                f"    while idx < n:\n"
                f"        val = xs[idx]\n"
                f"        if val <= {lo}:\n"
                f"            low_count = low_count + 1\n"
                f"        elif val > {hi}:\n"
                f"            high_count = high_count + 1\n"
                f"        else:\n"
                f"            mid_count = mid_count + 1\n"
                f"        idx = idx + 1\n"
                f"    result = [low_count, mid_count, high_count]\n"
                f"    return result\n"
            ),
            "description": f"uses <= {lo} instead of < {lo} — boundary values shift between low and mid",
        },
        {
            "source": (
                f"def {fname}(xs: list) -> list:\n"
                f"    low_count = 0\n"
                f"    mid_count = 0\n"
                f"    high_count = 0\n"
                f"    idx = 0\n"
                f"    n = len(xs)\n"
                f"    while idx < n:\n"
                f"        val = xs[idx]\n"
                f"        if val < {lo}:\n"
                f"            low_count = low_count + 1\n"
                f"        elif val > {hi}:\n"
                f"            high_count = high_count + 1\n"
                f"        else:\n"
                f"            mid_count = mid_count + 1\n"
                f"        idx = idx + 1\n"
                f"    result = [low_count, high_count, mid_count]\n"
                f"    return result\n"
            ),
            "description": "swaps mid and high counts in result — positions 1 and 2 are exchanged",
        },
    ]


# ------ weighted_sum ---------------------------------------------------

def _weighted_sum_source(threshold: int, pos_w: int, neg_w: int, fname: str) -> str:
    return (
        f"def {fname}(xs: list) -> int:\n"
        f"    total = 0\n"
        f"    n = len(xs)\n"
        f"    idx = 0\n"
        f"    while idx < n:\n"
        f"        val = xs[idx]\n"
        f"        if val > {threshold}:\n"
        f"            weight = {pos_w}\n"
        f"        elif val < -{threshold}:\n"
        f"            weight = {neg_w}\n"
        f"        else:\n"
        f"            weight = 1\n"
        f"        contribution = val * weight\n"
        f"        total = total + contribution\n"
        f"        idx = idx + 1\n"
        f"    return total\n"
    )


def _weighted_sum_equiv(threshold: int, pos_w: int, neg_w: int, fname: str) -> list[str]:
    return [
        (
            f"def {fname}(xs: list) -> int:\n"
            f"    result = 0\n"
            f"    n = len(xs)\n"
            f"    for i in range(n):\n"
            f"        val = xs[i]\n"
            f"        is_above = val > {threshold}\n"
            f"        is_below = val < -{threshold}\n"
            f"        if is_above:\n"
            f"            w = {pos_w}\n"
            f"        elif is_below:\n"
            f"            w = {neg_w}\n"
            f"        else:\n"
            f"            w = 1\n"
            f"        scaled = val * w\n"
            f"        result = result + scaled\n"
            f"    return result\n"
        ),
        (
            f"def {fname}(xs: list) -> int:\n"
            f"    above_sum = 0\n"
            f"    below_sum = 0\n"
            f"    middle_sum = 0\n"
            f"    for val in xs:\n"
            f"        if val > {threshold}:\n"
            f"            above_sum = above_sum + val\n"
            f"        elif val < -{threshold}:\n"
            f"            below_sum = below_sum + val\n"
            f"        else:\n"
            f"            middle_sum = middle_sum + val\n"
            f"    weighted_above = above_sum * {pos_w}\n"
            f"    weighted_below = below_sum * {neg_w}\n"
            f"    weighted_mid = middle_sum * 1\n"
            f"    total = weighted_above + weighted_below + weighted_mid\n"
            f"    return total\n"
        ),
    ]


def _weighted_sum_mutations(threshold: int, pos_w: int, neg_w: int, fname: str) -> list[dict]:
    return [
        {
            "source": (
                f"def {fname}(xs: list) -> int:\n"
                f"    total = 0\n"
                f"    n = len(xs)\n"
                f"    idx = 0\n"
                f"    while idx < n:\n"
                f"        val = xs[idx]\n"
                f"        if val > {threshold}:\n"
                f"            weight = {pos_w + 1}\n"
                f"        elif val < -{threshold}:\n"
                f"            weight = {neg_w}\n"
                f"        else:\n"
                f"            weight = 1\n"
                f"        contribution = val * weight\n"
                f"        total = total + contribution\n"
                f"        idx = idx + 1\n"
                f"    return total\n"
            ),
            "description": f"positive weight is {pos_w + 1} instead of {pos_w} — over-weighs large values",
        },
        {
            "source": (
                f"def {fname}(xs: list) -> int:\n"
                f"    total = 0\n"
                f"    n = len(xs)\n"
                f"    idx = 0\n"
                f"    while idx < n:\n"
                f"        val = xs[idx]\n"
                f"        if val > {threshold}:\n"
                f"            weight = {pos_w}\n"
                f"        elif val < -{threshold}:\n"
                f"            weight = 1\n"
                f"        else:\n"
                f"            weight = 1\n"
                f"        contribution = val * weight\n"
                f"        total = total + contribution\n"
                f"        idx = idx + 1\n"
                f"    return total\n"
            ),
            "description": f"negative weight is 1 instead of {neg_w} — under-weighs negative values",
        },
    ]


# ------ multi_pass_transform ------------------------------------------

def _multi_pass_transform_source(op: str, threshold: int, scale: int, fname: str) -> str:
    return (
        f"def {fname}(xs: list) -> int:\n"
        f"    filtered = []\n"
        f"    for x in xs:\n"
        f"        if x {op} {threshold}:\n"
        f"            filtered.append(x)\n"
        f"    scaled = []\n"
        f"    for val in filtered:\n"
        f"        new_val = val * {scale}\n"
        f"        scaled.append(new_val)\n"
        f"    total = 0\n"
        f"    for s in scaled:\n"
        f"        total = total + s\n"
        f"    n_items = len(scaled)\n"
        f"    if n_items == 0:\n"
        f"        return 0\n"
        f"    return total\n"
    )


def _multi_pass_transform_equiv(op: str, threshold: int, scale: int, fname: str) -> list[str]:
    return [
        (
            f"def {fname}(xs: list) -> int:\n"
            f"    total = 0\n"
            f"    count = 0\n"
            f"    n = len(xs)\n"
            f"    idx = 0\n"
            f"    while idx < n:\n"
            f"        val = xs[idx]\n"
            f"        if val {op} {threshold}:\n"
            f"            scaled_val = val * {scale}\n"
            f"            total = total + scaled_val\n"
            f"            count = count + 1\n"
            f"        idx = idx + 1\n"
            f"    if count == 0:\n"
            f"        return 0\n"
            f"    return total\n"
        ),
        (
            f"def {fname}(xs: list) -> int:\n"
            f"    passing = [x for x in xs if x {op} {threshold}]\n"
            f"    n = len(passing)\n"
            f"    if n == 0:\n"
            f"        return 0\n"
            f"    transformed = []\n"
            f"    i = 0\n"
            f"    while i < n:\n"
            f"        original = passing[i]\n"
            f"        scaled = original * {scale}\n"
            f"        transformed.append(scaled)\n"
            f"        i = i + 1\n"
            f"    result = 0\n"
            f"    for t in transformed:\n"
            f"        result = result + t\n"
            f"    return result\n"
        ),
    ]


def _multi_pass_transform_mutations(op: str, threshold: int, scale: int, fname: str) -> list[dict]:
    flipped_op = _op_flip(op)
    return [
        {
            "source": (
                f"def {fname}(xs: list) -> int:\n"
                f"    filtered = []\n"
                f"    for x in xs:\n"
                f"        if x {op} {threshold}:\n"
                f"            filtered.append(x)\n"
                f"    scaled = []\n"
                f"    for val in filtered:\n"
                f"        new_val = val * {scale + 1}\n"
                f"        scaled.append(new_val)\n"
                f"    total = 0\n"
                f"    for s in scaled:\n"
                f"        total = total + s\n"
                f"    n_items = len(scaled)\n"
                f"    if n_items == 0:\n"
                f"        return 0\n"
                f"    return total\n"
            ),
            "description": f"uses scale factor {scale + 1} instead of {scale}",
        },
        {
            "source": (
                f"def {fname}(xs: list) -> int:\n"
                f"    filtered = []\n"
                f"    for x in xs:\n"
                f"        if x {flipped_op} {threshold}:\n"
                f"            filtered.append(x)\n"
                f"    scaled = []\n"
                f"    for val in filtered:\n"
                f"        new_val = val * {scale}\n"
                f"        scaled.append(new_val)\n"
                f"    total = 0\n"
                f"    for s in scaled:\n"
                f"        total = total + s\n"
                f"    n_items = len(scaled)\n"
                f"    if n_items == 0:\n"
                f"        return 0\n"
                f"    return total\n"
            ),
            "description": f"uses '{flipped_op}' instead of '{op}' — filters different elements",
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

    # --- Complex templates (15+ LOC bodies) ---

    {
        "template_id": "sliding_window_sum",
        "category": "aggregation",
        "param_types": ["list[int]"],
        "return_type": "list[int]",
        "constraints": "",
        "param_choices": {
            "window_size": [2, 3, 4, 5],
        },
        "build_source": lambda p, name: _sliding_window_sum_source(p["window_size"], name),
        "build_equivalents": lambda p, name: _sliding_window_sum_equiv(p["window_size"], name),
        "build_mutations": lambda p, name: _sliding_window_sum_mutations(p["window_size"], name),
    },
    {
        "template_id": "partition_count",
        "category": "aggregation",
        "param_types": ["list[int]"],
        "return_type": "list[int]",
        "constraints": "",
        "param_choices": {
            "lo_thresh": list(range(-3, 3)),
            "hi_thresh": list(range(3, 8)),
        },
        "build_source": lambda p, name: _partition_count_source(p["lo_thresh"], p["hi_thresh"], name),
        "build_equivalents": lambda p, name: _partition_count_equiv(p["lo_thresh"], p["hi_thresh"], name),
        "build_mutations": lambda p, name: _partition_count_mutations(p["lo_thresh"], p["hi_thresh"], name),
    },
    {
        "template_id": "weighted_sum",
        "category": "mathematical",
        "param_types": ["list[int]"],
        "return_type": "int",
        "constraints": "",
        "param_choices": {
            "threshold": [1, 2, 3, 4, 5],
            "pos_weight": [2, 3, 4],
            "neg_weight": [2, 3, 4],
        },
        "build_source": lambda p, name: _weighted_sum_source(p["threshold"], p["pos_weight"], p["neg_weight"], name),
        "build_equivalents": lambda p, name: _weighted_sum_equiv(p["threshold"], p["pos_weight"], p["neg_weight"], name),
        "build_mutations": lambda p, name: _weighted_sum_mutations(p["threshold"], p["pos_weight"], p["neg_weight"], name),
    },
    {
        "template_id": "multi_pass_transform",
        "category": "transformation",
        "param_types": ["list[int]"],
        "return_type": "int",
        "constraints": "",
        "param_choices": {
            "op": [">", "<", ">=", "<="],
            "threshold": list(range(-3, 6)),
            "scale": [2, 3, 4, 5],
        },
        "build_source": lambda p, name: _multi_pass_transform_source(p["op"], p["threshold"], p["scale"], name),
        "build_equivalents": lambda p, name: _multi_pass_transform_equiv(p["op"], p["threshold"], p["scale"], name),
        "build_mutations": lambda p, name: _multi_pass_transform_mutations(p["op"], p["threshold"], p["scale"], name),
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
