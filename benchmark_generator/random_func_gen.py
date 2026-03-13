"""
Random function generator module.

Generates arbitrary Python functions with random names, arbitrary statements,
branches, and loops.  Each generated function operates on ``list[int]`` and
returns ``int``, with a guaranteed minimum of 20 non-blank lines of code for
both the initial version and every transformed variant (equivalents and
mutations).

The generator produces seed-function descriptors that are compatible with the
existing :class:`BenchmarkGenerator` pipeline:
    name, param_types, return_type, category, constraints,
    source, equivalents, mutations
"""

from __future__ import annotations

import random
import string
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NAME_PREFIXES = [
    "compute", "calc", "process", "analyze", "transform",
    "evaluate", "derive", "aggregate", "measure", "assess",
    "determine", "estimate", "resolve", "classify", "summarize",
]


def _random_func_name(rng: random.Random) -> str:
    """Return a valid, random Python function name."""
    prefix = rng.choice(_NAME_PREFIXES)
    suffix = "".join(rng.choices(string.ascii_lowercase + string.digits, k=6))
    return f"{prefix}_{suffix}"


def _count_loc(source: str) -> int:
    """Count non-blank lines in *source*."""
    return sum(1 for line in source.splitlines() if line.strip())


def _op_flip(op: str) -> str:
    """Return a related but semantically different comparison operator."""
    flips = {">": ">=", ">=": ">", "<": "<=", "<=": "<", "==": "!=", "!=": "=="}
    return flips.get(op, ">=")


# ---------------------------------------------------------------------------
# Blueprint 1 — conditional_accumulator
# ---------------------------------------------------------------------------

def _bp_conditional_accumulator(fname: str, p: dict) -> tuple:
    op1, op2 = p["op1"], p["op2"]
    t1, t2 = p["thresh1"], p["thresh2"]
    s1, s2 = p["scale1"], p["scale2"]

    source = (
        f"def {fname}(xs: list) -> int:\n"
        f"    n = len(xs)\n"
        f"    acc_primary = 0\n"
        f"    acc_secondary = 0\n"
        f"    match_count = 0\n"
        f"    total_processed = 0\n"
        f"    i = 0\n"
        f"    while i < n:\n"
        f"        val = xs[i]\n"
        f"        if val {op1} {t1}:\n"
        f"            acc_primary = acc_primary + val * {s1}\n"
        f"            match_count = match_count + 1\n"
        f"        elif val {op2} {t2}:\n"
        f"            acc_secondary = acc_secondary + val * {s2}\n"
        f"        else:\n"
        f"            acc_primary = acc_primary + val\n"
        f"            acc_secondary = acc_secondary + 1\n"
        f"        total_processed = total_processed + 1\n"
        f"        i = i + 1\n"
        f"    if match_count > 0:\n"
        f"        result = acc_primary + acc_secondary\n"
        f"    else:\n"
        f"        result = acc_secondary - acc_primary\n"
        f"    return result\n"
    )

    equiv1 = (
        f"def {fname}(xs: list) -> int:\n"
        f"    n = len(xs)\n"
        f"    acc_primary = 0\n"
        f"    acc_secondary = 0\n"
        f"    match_count = 0\n"
        f"    total_processed = 0\n"
        f"    for i in range(n):\n"
        f"        val = xs[i]\n"
        f"        cond_first = val {op1} {t1}\n"
        f"        cond_second = val {op2} {t2}\n"
        f"        if cond_first:\n"
        f"            scaled = val * {s1}\n"
        f"            acc_primary = acc_primary + scaled\n"
        f"            match_count = match_count + 1\n"
        f"        elif cond_second:\n"
        f"            scaled = val * {s2}\n"
        f"            acc_secondary = acc_secondary + scaled\n"
        f"        else:\n"
        f"            acc_primary = acc_primary + val\n"
        f"            acc_secondary = acc_secondary + 1\n"
        f"        total_processed = total_processed + 1\n"
        f"    if match_count > 0:\n"
        f"        result = acc_primary + acc_secondary\n"
        f"    else:\n"
        f"        result = acc_secondary - acc_primary\n"
        f"    return result\n"
    )

    equiv2 = (
        f"def {fname}(xs: list) -> int:\n"
        f"    n = len(xs)\n"
        f"    acc_primary = 0\n"
        f"    acc_secondary = 0\n"
        f"    match_count = 0\n"
        f"    total_processed = 0\n"
        f"    for val in xs:\n"
        f"        above = val {op1} {t1}\n"
        f"        below = val {op2} {t2}\n"
        f"        if above:\n"
        f"            product = val * {s1}\n"
        f"            acc_primary = acc_primary + product\n"
        f"            match_count = match_count + 1\n"
        f"        elif below:\n"
        f"            product = val * {s2}\n"
        f"            acc_secondary = acc_secondary + product\n"
        f"        else:\n"
        f"            acc_primary = acc_primary + val\n"
        f"            acc_secondary = acc_secondary + 1\n"
        f"        total_processed = total_processed + 1\n"
        f"    has_matches = match_count > 0\n"
        f"    if has_matches:\n"
        f"        result = acc_primary + acc_secondary\n"
        f"    else:\n"
        f"        result = acc_secondary - acc_primary\n"
        f"    return result\n"
    )

    flipped = _op_flip(op1)
    mut1 = {
        "source": (
            f"def {fname}(xs: list) -> int:\n"
            f"    n = len(xs)\n"
            f"    acc_primary = 0\n"
            f"    acc_secondary = 0\n"
            f"    match_count = 0\n"
            f"    total_processed = 0\n"
            f"    i = 0\n"
            f"    while i < n:\n"
            f"        val = xs[i]\n"
            f"        if val {flipped} {t1}:\n"
            f"            acc_primary = acc_primary + val * {s1}\n"
            f"            match_count = match_count + 1\n"
            f"        elif val {op2} {t2}:\n"
            f"            acc_secondary = acc_secondary + val * {s2}\n"
            f"        else:\n"
            f"            acc_primary = acc_primary + val\n"
            f"            acc_secondary = acc_secondary + 1\n"
            f"        total_processed = total_processed + 1\n"
            f"        i = i + 1\n"
            f"    if match_count > 0:\n"
            f"        result = acc_primary + acc_secondary\n"
            f"    else:\n"
            f"        result = acc_secondary - acc_primary\n"
            f"    return result\n"
        ),
        "description": f"uses '{flipped}' instead of '{op1}' in primary condition",
    }

    mut2 = {
        "source": (
            f"def {fname}(xs: list) -> int:\n"
            f"    n = len(xs)\n"
            f"    acc_primary = 0\n"
            f"    acc_secondary = 0\n"
            f"    match_count = 0\n"
            f"    total_processed = 0\n"
            f"    i = 0\n"
            f"    while i < n:\n"
            f"        val = xs[i]\n"
            f"        if val {op1} {t1 + 1}:\n"
            f"            acc_primary = acc_primary + val * {s1}\n"
            f"            match_count = match_count + 1\n"
            f"        elif val {op2} {t2}:\n"
            f"            acc_secondary = acc_secondary + val * {s2}\n"
            f"        else:\n"
            f"            acc_primary = acc_primary + val\n"
            f"            acc_secondary = acc_secondary + 1\n"
            f"        total_processed = total_processed + 1\n"
            f"        i = i + 1\n"
            f"    if match_count > 0:\n"
            f"        result = acc_primary + acc_secondary\n"
            f"    else:\n"
            f"        result = acc_secondary - acc_primary\n"
            f"    return result\n"
        ),
        "description": f"threshold off-by-one: uses {t1 + 1} instead of {t1}",
    }

    return source, [equiv1, equiv2], [mut1, mut2]


# ---------------------------------------------------------------------------
# Blueprint 2 — filter_transform_reduce
# ---------------------------------------------------------------------------

def _bp_filter_transform_reduce(fname: str, p: dict) -> tuple:
    op, thresh, scale = p["op"], p["thresh"], p["scale"]

    source = (
        f"def {fname}(xs: list) -> int:\n"
        f"    n = len(xs)\n"
        f"    filtered = []\n"
        f"    idx = 0\n"
        f"    while idx < n:\n"
        f"        current = xs[idx]\n"
        f"        if current {op} {thresh}:\n"
        f"            filtered.append(current)\n"
        f"        idx = idx + 1\n"
        f"    transformed = []\n"
        f"    for val in filtered:\n"
        f"        new_val = val * {scale}\n"
        f"        transformed.append(new_val)\n"
        f"    total = 0\n"
        f"    count = len(transformed)\n"
        f"    for t in transformed:\n"
        f"        total = total + t\n"
        f"    if count == 0:\n"
        f"        result = 0\n"
        f"    else:\n"
        f"        result = total\n"
        f"    return result\n"
    )

    equiv1 = (
        f"def {fname}(xs: list) -> int:\n"
        f"    n = len(xs)\n"
        f"    filtered = []\n"
        f"    for i in range(n):\n"
        f"        current = xs[i]\n"
        f"        passes = current {op} {thresh}\n"
        f"        if passes:\n"
        f"            filtered.append(current)\n"
        f"    transformed = []\n"
        f"    num_filtered = len(filtered)\n"
        f"    j = 0\n"
        f"    while j < num_filtered:\n"
        f"        val = filtered[j]\n"
        f"        new_val = val * {scale}\n"
        f"        transformed.append(new_val)\n"
        f"        j = j + 1\n"
        f"    total = 0\n"
        f"    count = len(transformed)\n"
        f"    for t in transformed:\n"
        f"        total = total + t\n"
        f"    if count == 0:\n"
        f"        result = 0\n"
        f"    else:\n"
        f"        result = total\n"
        f"    return result\n"
    )

    equiv2 = (
        f"def {fname}(xs: list) -> int:\n"
        f"    n = len(xs)\n"
        f"    total = 0\n"
        f"    count = 0\n"
        f"    idx = 0\n"
        f"    while idx < n:\n"
        f"        current = xs[idx]\n"
        f"        meets_condition = current {op} {thresh}\n"
        f"        if meets_condition:\n"
        f"            scaled = current * {scale}\n"
        f"            total = total + scaled\n"
        f"            count = count + 1\n"
        f"        idx = idx + 1\n"
        f"    if count == 0:\n"
        f"        result = 0\n"
        f"    else:\n"
        f"        result = total\n"
        f"    final_count = count\n"
        f"    final_total = total\n"
        f"    answer = result\n"
        f"    return answer\n"
    )

    flipped = _op_flip(op)
    mut1 = {
        "source": (
            f"def {fname}(xs: list) -> int:\n"
            f"    n = len(xs)\n"
            f"    filtered = []\n"
            f"    idx = 0\n"
            f"    while idx < n:\n"
            f"        current = xs[idx]\n"
            f"        if current {flipped} {thresh}:\n"
            f"            filtered.append(current)\n"
            f"        idx = idx + 1\n"
            f"    transformed = []\n"
            f"    for val in filtered:\n"
            f"        new_val = val * {scale}\n"
            f"        transformed.append(new_val)\n"
            f"    total = 0\n"
            f"    count = len(transformed)\n"
            f"    for t in transformed:\n"
            f"        total = total + t\n"
            f"    if count == 0:\n"
            f"        result = 0\n"
            f"    else:\n"
            f"        result = total\n"
            f"    return result\n"
        ),
        "description": f"uses '{flipped}' instead of '{op}' — filters different elements",
    }

    mut2 = {
        "source": (
            f"def {fname}(xs: list) -> int:\n"
            f"    n = len(xs)\n"
            f"    filtered = []\n"
            f"    idx = 0\n"
            f"    while idx < n:\n"
            f"        current = xs[idx]\n"
            f"        if current {op} {thresh}:\n"
            f"            filtered.append(current)\n"
            f"        idx = idx + 1\n"
            f"    transformed = []\n"
            f"    for val in filtered:\n"
            f"        new_val = val * {scale + 1}\n"
            f"        transformed.append(new_val)\n"
            f"    total = 0\n"
            f"    count = len(transformed)\n"
            f"    for t in transformed:\n"
            f"        total = total + t\n"
            f"    if count == 0:\n"
            f"        result = 0\n"
            f"    else:\n"
            f"        result = total\n"
            f"    return result\n"
        ),
        "description": f"uses scale {scale + 1} instead of {scale}",
    }

    return source, [equiv1, equiv2], [mut1, mut2]


# ---------------------------------------------------------------------------
# Blueprint 3 — multi_bucket_stats
# ---------------------------------------------------------------------------

def _bp_multi_bucket_stats(fname: str, p: dict) -> tuple:
    lo, hi = p["lo"], p["hi"]
    default = p["default_val"]

    source = (
        f"def {fname}(xs: list) -> int:\n"
        f"    n = len(xs)\n"
        f"    low_sum = 0\n"
        f"    mid_sum = 0\n"
        f"    high_sum = 0\n"
        f"    low_count = 0\n"
        f"    mid_count = 0\n"
        f"    high_count = 0\n"
        f"    for val in xs:\n"
        f"        if val < {lo}:\n"
        f"            low_sum = low_sum + val\n"
        f"            low_count = low_count + 1\n"
        f"        elif val > {hi}:\n"
        f"            high_sum = high_sum + val\n"
        f"            high_count = high_count + 1\n"
        f"        else:\n"
        f"            mid_sum = mid_sum + val\n"
        f"            mid_count = mid_count + 1\n"
        f"    total = low_sum + mid_sum + high_sum\n"
        f"    items = low_count + mid_count + high_count\n"
        f"    if items == 0:\n"
        f"        return {default}\n"
        f"    return total\n"
    )

    equiv1 = (
        f"def {fname}(xs: list) -> int:\n"
        f"    n = len(xs)\n"
        f"    low_sum = 0\n"
        f"    mid_sum = 0\n"
        f"    high_sum = 0\n"
        f"    low_count = 0\n"
        f"    mid_count = 0\n"
        f"    high_count = 0\n"
        f"    i = 0\n"
        f"    while i < n:\n"
        f"        val = xs[i]\n"
        f"        is_low = val < {lo}\n"
        f"        is_high = val > {hi}\n"
        f"        if is_low:\n"
        f"            low_sum = low_sum + val\n"
        f"            low_count = low_count + 1\n"
        f"        elif is_high:\n"
        f"            high_sum = high_sum + val\n"
        f"            high_count = high_count + 1\n"
        f"        else:\n"
        f"            mid_sum = mid_sum + val\n"
        f"            mid_count = mid_count + 1\n"
        f"        i = i + 1\n"
        f"    total = low_sum + mid_sum + high_sum\n"
        f"    items = low_count + mid_count + high_count\n"
        f"    if items == 0:\n"
        f"        return {default}\n"
        f"    return total\n"
    )

    equiv2 = (
        f"def {fname}(xs: list) -> int:\n"
        f"    n = len(xs)\n"
        f"    low_sum = 0\n"
        f"    mid_sum = 0\n"
        f"    high_sum = 0\n"
        f"    low_count = 0\n"
        f"    mid_count = 0\n"
        f"    high_count = 0\n"
        f"    for i in range(n):\n"
        f"        val = xs[i]\n"
        f"        below_lo = val < {lo}\n"
        f"        above_hi = val > {hi}\n"
        f"        if below_lo:\n"
        f"            low_sum = low_sum + val\n"
        f"            low_count = low_count + 1\n"
        f"        elif above_hi:\n"
        f"            high_sum = high_sum + val\n"
        f"            high_count = high_count + 1\n"
        f"        else:\n"
        f"            mid_sum = mid_sum + val\n"
        f"            mid_count = mid_count + 1\n"
        f"    all_sums = low_sum + mid_sum + high_sum\n"
        f"    all_counts = low_count + mid_count + high_count\n"
        f"    if all_counts == 0:\n"
        f"        return {default}\n"
        f"    total = all_sums\n"
        f"    return total\n"
    )

    mut1 = {
        "source": (
            f"def {fname}(xs: list) -> int:\n"
            f"    n = len(xs)\n"
            f"    low_sum = 0\n"
            f"    mid_sum = 0\n"
            f"    high_sum = 0\n"
            f"    low_count = 0\n"
            f"    mid_count = 0\n"
            f"    high_count = 0\n"
            f"    for val in xs:\n"
            f"        if val <= {lo}:\n"
            f"            low_sum = low_sum + val\n"
            f"            low_count = low_count + 1\n"
            f"        elif val > {hi}:\n"
            f"            high_sum = high_sum + val\n"
            f"            high_count = high_count + 1\n"
            f"        else:\n"
            f"            mid_sum = mid_sum + val\n"
            f"            mid_count = mid_count + 1\n"
            f"    total = low_sum + mid_sum + high_sum\n"
            f"    items = low_count + mid_count + high_count\n"
            f"    if items == 0:\n"
            f"        return {default}\n"
            f"    return total\n"
        ),
        "description": f"uses '<= {lo}' instead of '< {lo}' — boundary shifts between low and mid",
    }

    mut2 = {
        "source": (
            f"def {fname}(xs: list) -> int:\n"
            f"    n = len(xs)\n"
            f"    low_sum = 0\n"
            f"    mid_sum = 0\n"
            f"    high_sum = 0\n"
            f"    low_count = 0\n"
            f"    mid_count = 0\n"
            f"    high_count = 0\n"
            f"    for val in xs:\n"
            f"        if val < {lo}:\n"
            f"            low_sum = low_sum + val\n"
            f"            low_count = low_count + 1\n"
            f"        elif val > {hi}:\n"
            f"            high_sum = high_sum + val\n"
            f"            high_count = high_count + 1\n"
            f"        else:\n"
            f"            mid_sum = mid_sum + val\n"
            f"            mid_count = mid_count + 1\n"
            f"    total = low_sum + high_sum + mid_sum\n"
            f"    items = low_count + mid_count + high_count\n"
            f"    if items == 0:\n"
            f"        return {default}\n"
            f"    return total + 1\n"
        ),
        "description": "off-by-one in final return: adds 1 to total",
    }

    return source, [equiv1, equiv2], [mut1, mut2]


# ---------------------------------------------------------------------------
# Blueprint 4 — running_extremes
# ---------------------------------------------------------------------------

def _bp_running_extremes(fname: str, p: dict) -> tuple:
    offset = p["offset"]

    source = (
        f"def {fname}(xs: list) -> int:\n"
        f"    n = len(xs)\n"
        f"    if n == 0:\n"
        f"        return 0\n"
        f"    current_max = xs[0]\n"
        f"    current_min = xs[0]\n"
        f"    total = 0\n"
        f"    i = 1\n"
        f"    while i < n:\n"
        f"        val = xs[i]\n"
        f"        if val > current_max:\n"
        f"            current_max = val\n"
        f"        if val < current_min:\n"
        f"            current_min = val\n"
        f"        total = total + val\n"
        f"        i = i + 1\n"
        f"    spread = current_max - current_min\n"
        f"    adjusted = total + spread\n"
        f"    result = adjusted + {offset}\n"
        f"    if result < 0:\n"
        f"        result = 0 - result\n"
        f"    return result\n"
    )

    equiv1 = (
        f"def {fname}(xs: list) -> int:\n"
        f"    n = len(xs)\n"
        f"    if n == 0:\n"
        f"        return 0\n"
        f"    current_max = xs[0]\n"
        f"    current_min = xs[0]\n"
        f"    total = 0\n"
        f"    for i in range(1, n):\n"
        f"        val = xs[i]\n"
        f"        is_new_max = val > current_max\n"
        f"        is_new_min = val < current_min\n"
        f"        if is_new_max:\n"
        f"            current_max = val\n"
        f"        if is_new_min:\n"
        f"            current_min = val\n"
        f"        total = total + val\n"
        f"    spread = current_max - current_min\n"
        f"    adjusted = total + spread\n"
        f"    result = adjusted + {offset}\n"
        f"    if result < 0:\n"
        f"        result = 0 - result\n"
        f"    return result\n"
    )

    equiv2 = (
        f"def {fname}(xs: list) -> int:\n"
        f"    n = len(xs)\n"
        f"    if n == 0:\n"
        f"        return 0\n"
        f"    running_max = xs[0]\n"
        f"    running_min = xs[0]\n"
        f"    accumulator = 0\n"
        f"    idx = 1\n"
        f"    while idx < n:\n"
        f"        element = xs[idx]\n"
        f"        above_max = element > running_max\n"
        f"        below_min = element < running_min\n"
        f"        if above_max:\n"
        f"            running_max = element\n"
        f"        if below_min:\n"
        f"            running_min = element\n"
        f"        accumulator = accumulator + element\n"
        f"        idx = idx + 1\n"
        f"    range_val = running_max - running_min\n"
        f"    combined = accumulator + range_val\n"
        f"    final = combined + {offset}\n"
        f"    if final < 0:\n"
        f"        final = 0 - final\n"
        f"    return final\n"
    )

    mut1 = {
        "source": (
            f"def {fname}(xs: list) -> int:\n"
            f"    n = len(xs)\n"
            f"    if n == 0:\n"
            f"        return 0\n"
            f"    current_max = xs[0]\n"
            f"    current_min = xs[0]\n"
            f"    total = 0\n"
            f"    i = 1\n"
            f"    while i < n:\n"
            f"        val = xs[i]\n"
            f"        if val >= current_max:\n"
            f"            current_max = val\n"
            f"        if val < current_min:\n"
            f"            current_min = val\n"
            f"        total = total + val\n"
            f"        i = i + 1\n"
            f"    spread = current_max - current_min\n"
            f"    adjusted = total + spread\n"
            f"    result = adjusted + {offset}\n"
            f"    if result < 0:\n"
            f"        result = 0 - result\n"
            f"    return result\n"
        ),
        "description": "uses '>=' instead of '>' for max update — changes behavior on duplicates",
    }

    mut2 = {
        "source": (
            f"def {fname}(xs: list) -> int:\n"
            f"    n = len(xs)\n"
            f"    if n == 0:\n"
            f"        return 0\n"
            f"    current_max = xs[0]\n"
            f"    current_min = xs[0]\n"
            f"    total = 0\n"
            f"    i = 1\n"
            f"    while i < n:\n"
            f"        val = xs[i]\n"
            f"        if val > current_max:\n"
            f"            current_max = val\n"
            f"        if val < current_min:\n"
            f"            current_min = val\n"
            f"        total = total + val\n"
            f"        i = i + 1\n"
            f"    spread = current_max - current_min\n"
            f"    adjusted = total - spread\n"
            f"    result = adjusted + {offset}\n"
            f"    if result < 0:\n"
            f"        result = 0 - result\n"
            f"    return result\n"
        ),
        "description": "subtracts spread instead of adding it",
    }

    return source, [equiv1, equiv2], [mut1, mut2]


# ---------------------------------------------------------------------------
# Blueprint 5 — prefix_suffix_combine
# ---------------------------------------------------------------------------

def _bp_prefix_suffix_combine(fname: str, p: dict) -> tuple:
    divisor = p["divisor"]
    scale = p["scale"]

    source = (
        f"def {fname}(xs: list) -> int:\n"
        f"    n = len(xs)\n"
        f"    if n == 0:\n"
        f"        return 0\n"
        f"    mid = n // {divisor}\n"
        f"    prefix_sum = 0\n"
        f"    i = 0\n"
        f"    while i < mid:\n"
        f"        prefix_sum = prefix_sum + xs[i]\n"
        f"        i = i + 1\n"
        f"    suffix_sum = 0\n"
        f"    j = mid\n"
        f"    while j < n:\n"
        f"        suffix_sum = suffix_sum + xs[j]\n"
        f"        j = j + 1\n"
        f"    prefix_scaled = prefix_sum * {scale}\n"
        f"    diff = prefix_scaled - suffix_sum\n"
        f"    if diff < 0:\n"
        f"        diff = 0 - diff\n"
        f"    result = prefix_scaled + suffix_sum + diff\n"
        f"    return result\n"
    )

    equiv1 = (
        f"def {fname}(xs: list) -> int:\n"
        f"    n = len(xs)\n"
        f"    if n == 0:\n"
        f"        return 0\n"
        f"    mid = n // {divisor}\n"
        f"    prefix_sum = 0\n"
        f"    for i in range(mid):\n"
        f"        val = xs[i]\n"
        f"        prefix_sum = prefix_sum + val\n"
        f"    suffix_sum = 0\n"
        f"    for j in range(mid, n):\n"
        f"        val = xs[j]\n"
        f"        suffix_sum = suffix_sum + val\n"
        f"    prefix_scaled = prefix_sum * {scale}\n"
        f"    raw_diff = prefix_scaled - suffix_sum\n"
        f"    if raw_diff < 0:\n"
        f"        diff = 0 - raw_diff\n"
        f"    else:\n"
        f"        diff = raw_diff\n"
        f"    result = prefix_scaled + suffix_sum + diff\n"
        f"    return result\n"
    )

    equiv2 = (
        f"def {fname}(xs: list) -> int:\n"
        f"    n = len(xs)\n"
        f"    if n == 0:\n"
        f"        return 0\n"
        f"    split_point = n // {divisor}\n"
        f"    prefix_total = 0\n"
        f"    idx = 0\n"
        f"    while idx < split_point:\n"
        f"        element = xs[idx]\n"
        f"        prefix_total = prefix_total + element\n"
        f"        idx = idx + 1\n"
        f"    suffix_total = 0\n"
        f"    idx = split_point\n"
        f"    while idx < n:\n"
        f"        element = xs[idx]\n"
        f"        suffix_total = suffix_total + element\n"
        f"        idx = idx + 1\n"
        f"    scaled_prefix = prefix_total * {scale}\n"
        f"    difference = scaled_prefix - suffix_total\n"
        f"    if difference < 0:\n"
        f"        difference = 0 - difference\n"
        f"    result = scaled_prefix + suffix_total + difference\n"
        f"    return result\n"
    )

    mut1 = {
        "source": (
            f"def {fname}(xs: list) -> int:\n"
            f"    n = len(xs)\n"
            f"    if n == 0:\n"
            f"        return 0\n"
            f"    mid = n // {divisor}\n"
            f"    prefix_sum = 0\n"
            f"    i = 0\n"
            f"    while i < mid:\n"
            f"        prefix_sum = prefix_sum + xs[i]\n"
            f"        i = i + 1\n"
            f"    suffix_sum = 0\n"
            f"    j = mid\n"
            f"    while j < n:\n"
            f"        suffix_sum = suffix_sum + xs[j]\n"
            f"        j = j + 1\n"
            f"    prefix_scaled = prefix_sum * {scale + 1}\n"
            f"    diff = prefix_scaled - suffix_sum\n"
            f"    if diff < 0:\n"
            f"        diff = 0 - diff\n"
            f"    result = prefix_scaled + suffix_sum + diff\n"
            f"    return result\n"
        ),
        "description": f"uses scale {scale + 1} instead of {scale}",
    }

    mut2 = {
        "source": (
            f"def {fname}(xs: list) -> int:\n"
            f"    n = len(xs)\n"
            f"    if n == 0:\n"
            f"        return 0\n"
            f"    mid = n // {divisor}\n"
            f"    prefix_sum = 0\n"
            f"    i = 0\n"
            f"    while i <= mid:\n"
            f"        prefix_sum = prefix_sum + xs[i]\n"
            f"        i = i + 1\n"
            f"    suffix_sum = 0\n"
            f"    j = mid\n"
            f"    while j < n:\n"
            f"        suffix_sum = suffix_sum + xs[j]\n"
            f"        j = j + 1\n"
            f"    prefix_scaled = prefix_sum * {scale}\n"
            f"    diff = prefix_scaled - suffix_sum\n"
            f"    if diff < 0:\n"
            f"        diff = 0 - diff\n"
            f"    result = prefix_scaled + suffix_sum + diff\n"
            f"    return result\n"
        ),
        "description": "prefix loop uses '<=' instead of '<' — includes one extra element",
    }

    return source, [equiv1, equiv2], [mut1, mut2]


# ---------------------------------------------------------------------------
# Blueprint 6 — weighted_conditional_accumulate
# ---------------------------------------------------------------------------

def _bp_weighted_conditional(fname: str, p: dict) -> tuple:
    t1, t2 = p["thresh1"], p["thresh2"]
    w1, w2, w3 = p["w1"], p["w2"], p["w3"]

    source = (
        f"def {fname}(xs: list) -> int:\n"
        f"    n = len(xs)\n"
        f"    weighted_total = 0\n"
        f"    raw_total = 0\n"
        f"    count_above = 0\n"
        f"    count_below = 0\n"
        f"    count_mid = 0\n"
        f"    idx = 0\n"
        f"    while idx < n:\n"
        f"        val = xs[idx]\n"
        f"        if val > {t1}:\n"
        f"            weight = {w1}\n"
        f"            count_above = count_above + 1\n"
        f"        elif val < {t2}:\n"
        f"            weight = {w2}\n"
        f"            count_below = count_below + 1\n"
        f"        else:\n"
        f"            weight = {w3}\n"
        f"            count_mid = count_mid + 1\n"
        f"        contribution = val * weight\n"
        f"        weighted_total = weighted_total + contribution\n"
        f"        raw_total = raw_total + val\n"
        f"        idx = idx + 1\n"
        f"    if count_above + count_below == 0:\n"
        f"        return raw_total\n"
        f"    return weighted_total\n"
    )

    equiv1 = (
        f"def {fname}(xs: list) -> int:\n"
        f"    n = len(xs)\n"
        f"    weighted_total = 0\n"
        f"    raw_total = 0\n"
        f"    count_above = 0\n"
        f"    count_below = 0\n"
        f"    count_mid = 0\n"
        f"    for i in range(n):\n"
        f"        val = xs[i]\n"
        f"        is_above = val > {t1}\n"
        f"        is_below = val < {t2}\n"
        f"        if is_above:\n"
        f"            weight = {w1}\n"
        f"            count_above = count_above + 1\n"
        f"        elif is_below:\n"
        f"            weight = {w2}\n"
        f"            count_below = count_below + 1\n"
        f"        else:\n"
        f"            weight = {w3}\n"
        f"            count_mid = count_mid + 1\n"
        f"        contribution = val * weight\n"
        f"        weighted_total = weighted_total + contribution\n"
        f"        raw_total = raw_total + val\n"
        f"    extremes = count_above + count_below\n"
        f"    if extremes == 0:\n"
        f"        return raw_total\n"
        f"    return weighted_total\n"
    )

    equiv2 = (
        f"def {fname}(xs: list) -> int:\n"
        f"    n = len(xs)\n"
        f"    above_sum = 0\n"
        f"    below_sum = 0\n"
        f"    mid_sum = 0\n"
        f"    count_above = 0\n"
        f"    count_below = 0\n"
        f"    raw_total = 0\n"
        f"    for val in xs:\n"
        f"        raw_total = raw_total + val\n"
        f"        if val > {t1}:\n"
        f"            above_sum = above_sum + val\n"
        f"            count_above = count_above + 1\n"
        f"        elif val < {t2}:\n"
        f"            below_sum = below_sum + val\n"
        f"            count_below = count_below + 1\n"
        f"        else:\n"
        f"            mid_sum = mid_sum + val\n"
        f"    wa = above_sum * {w1}\n"
        f"    wb = below_sum * {w2}\n"
        f"    wm = mid_sum * {w3}\n"
        f"    weighted_total = wa + wb + wm\n"
        f"    extremes = count_above + count_below\n"
        f"    if extremes == 0:\n"
        f"        return raw_total\n"
        f"    return weighted_total\n"
    )

    mut1 = {
        "source": (
            f"def {fname}(xs: list) -> int:\n"
            f"    n = len(xs)\n"
            f"    weighted_total = 0\n"
            f"    raw_total = 0\n"
            f"    count_above = 0\n"
            f"    count_below = 0\n"
            f"    count_mid = 0\n"
            f"    idx = 0\n"
            f"    while idx < n:\n"
            f"        val = xs[idx]\n"
            f"        if val > {t1}:\n"
            f"            weight = {w1 + 1}\n"
            f"            count_above = count_above + 1\n"
            f"        elif val < {t2}:\n"
            f"            weight = {w2}\n"
            f"            count_below = count_below + 1\n"
            f"        else:\n"
            f"            weight = {w3}\n"
            f"            count_mid = count_mid + 1\n"
            f"        contribution = val * weight\n"
            f"        weighted_total = weighted_total + contribution\n"
            f"        raw_total = raw_total + val\n"
            f"        idx = idx + 1\n"
            f"    if count_above + count_below == 0:\n"
            f"        return raw_total\n"
            f"    return weighted_total\n"
        ),
        "description": f"above-weight is {w1 + 1} instead of {w1}",
    }

    mut2 = {
        "source": (
            f"def {fname}(xs: list) -> int:\n"
            f"    n = len(xs)\n"
            f"    weighted_total = 0\n"
            f"    raw_total = 0\n"
            f"    count_above = 0\n"
            f"    count_below = 0\n"
            f"    count_mid = 0\n"
            f"    idx = 0\n"
            f"    while idx < n:\n"
            f"        val = xs[idx]\n"
            f"        if val > {t1}:\n"
            f"            weight = {w1}\n"
            f"            count_above = count_above + 1\n"
            f"        elif val < {t2}:\n"
            f"            weight = {w3}\n"
            f"            count_below = count_below + 1\n"
            f"        else:\n"
            f"            weight = {w2}\n"
            f"            count_mid = count_mid + 1\n"
            f"        contribution = val * weight\n"
            f"        weighted_total = weighted_total + contribution\n"
            f"        raw_total = raw_total + val\n"
            f"        idx = idx + 1\n"
            f"    if count_above + count_below == 0:\n"
            f"        return raw_total\n"
            f"    return weighted_total\n"
        ),
        "description": f"swaps below-weight ({w2}) and mid-weight ({w3})",
    }

    return source, [equiv1, equiv2], [mut1, mut2]


# ---------------------------------------------------------------------------
# Blueprint 7 — cascaded_filter_aggregate
# ---------------------------------------------------------------------------

def _bp_cascaded_filter(fname: str, p: dict) -> tuple:
    t1, t2 = p["thresh1"], p["thresh2"]
    scale = p["scale"]

    source = (
        f"def {fname}(xs: list) -> int:\n"
        f"    n = len(xs)\n"
        f"    stage1 = []\n"
        f"    for val in xs:\n"
        f"        if val > {t1}:\n"
        f"            stage1.append(val)\n"
        f"    stage2 = []\n"
        f"    for val in stage1:\n"
        f"        if val < {t2}:\n"
        f"            scaled = val * {scale}\n"
        f"            stage2.append(scaled)\n"
        f"    total = 0\n"
        f"    maximum = 0\n"
        f"    count = 0\n"
        f"    for val in stage2:\n"
        f"        total = total + val\n"
        f"        if val > maximum:\n"
        f"            maximum = val\n"
        f"        count = count + 1\n"
        f"    if count == 0:\n"
        f"        return 0\n"
        f"    result = total + maximum\n"
        f"    return result\n"
    )

    equiv1 = (
        f"def {fname}(xs: list) -> int:\n"
        f"    n = len(xs)\n"
        f"    stage1 = []\n"
        f"    i = 0\n"
        f"    while i < n:\n"
        f"        val = xs[i]\n"
        f"        passes = val > {t1}\n"
        f"        if passes:\n"
        f"            stage1.append(val)\n"
        f"        i = i + 1\n"
        f"    stage2 = []\n"
        f"    j = 0\n"
        f"    num_stage1 = len(stage1)\n"
        f"    while j < num_stage1:\n"
        f"        val = stage1[j]\n"
        f"        if val < {t2}:\n"
        f"            scaled = val * {scale}\n"
        f"            stage2.append(scaled)\n"
        f"        j = j + 1\n"
        f"    total = 0\n"
        f"    maximum = 0\n"
        f"    count = 0\n"
        f"    for val in stage2:\n"
        f"        total = total + val\n"
        f"        if val > maximum:\n"
        f"            maximum = val\n"
        f"        count = count + 1\n"
        f"    if count == 0:\n"
        f"        return 0\n"
        f"    result = total + maximum\n"
        f"    return result\n"
    )

    equiv2 = (
        f"def {fname}(xs: list) -> int:\n"
        f"    n = len(xs)\n"
        f"    total = 0\n"
        f"    maximum = 0\n"
        f"    count = 0\n"
        f"    for val in xs:\n"
        f"        above_first = val > {t1}\n"
        f"        below_second = val < {t2}\n"
        f"        if above_first:\n"
        f"            if below_second:\n"
        f"                scaled = val * {scale}\n"
        f"                total = total + scaled\n"
        f"                is_new_max = scaled > maximum\n"
        f"                if is_new_max:\n"
        f"                    maximum = scaled\n"
        f"                count = count + 1\n"
        f"    if count == 0:\n"
        f"        result = 0\n"
        f"    else:\n"
        f"        result = total + maximum\n"
        f"    return result\n"
    )

    flipped = _op_flip(">")
    mut1 = {
        "source": (
            f"def {fname}(xs: list) -> int:\n"
            f"    n = len(xs)\n"
            f"    stage1 = []\n"
            f"    for val in xs:\n"
            f"        if val {flipped} {t1}:\n"
            f"            stage1.append(val)\n"
            f"    stage2 = []\n"
            f"    for val in stage1:\n"
            f"        if val < {t2}:\n"
            f"            scaled = val * {scale}\n"
            f"            stage2.append(scaled)\n"
            f"    total = 0\n"
            f"    maximum = 0\n"
            f"    count = 0\n"
            f"    for val in stage2:\n"
            f"        total = total + val\n"
            f"        if val > maximum:\n"
            f"            maximum = val\n"
            f"        count = count + 1\n"
            f"    if count == 0:\n"
            f"        return 0\n"
            f"    result = total + maximum\n"
            f"    return result\n"
        ),
        "description": f"stage-1 filter uses '{flipped}' instead of '>'",
    }

    mut2 = {
        "source": (
            f"def {fname}(xs: list) -> int:\n"
            f"    n = len(xs)\n"
            f"    stage1 = []\n"
            f"    for val in xs:\n"
            f"        if val > {t1}:\n"
            f"            stage1.append(val)\n"
            f"    stage2 = []\n"
            f"    for val in stage1:\n"
            f"        if val < {t2}:\n"
            f"            scaled = val * {scale}\n"
            f"            stage2.append(scaled)\n"
            f"    total = 0\n"
            f"    maximum = 0\n"
            f"    count = 0\n"
            f"    for val in stage2:\n"
            f"        total = total + val\n"
            f"        if val > maximum:\n"
            f"            maximum = val\n"
            f"        count = count + 1\n"
            f"    if count == 0:\n"
            f"        return 0\n"
            f"    result = total - maximum\n"
            f"    return result\n"
        ),
        "description": "subtracts maximum instead of adding it in the final result",
    }

    return source, [equiv1, equiv2], [mut1, mut2]


# ---------------------------------------------------------------------------
# Blueprint 8 — index_parity_process
# ---------------------------------------------------------------------------

def _bp_index_parity(fname: str, p: dict) -> tuple:
    step = p["step"]
    scale = p["scale"]

    source = (
        f"def {fname}(xs: list) -> int:\n"
        f"    n = len(xs)\n"
        f"    even_sum = 0\n"
        f"    odd_sum = 0\n"
        f"    even_count = 0\n"
        f"    odd_count = 0\n"
        f"    i = 0\n"
        f"    while i < n:\n"
        f"        val = xs[i]\n"
        f"        pos = i + 1\n"
        f"        if pos % {step} == 0:\n"
        f"            even_sum = even_sum + val\n"
        f"            even_count = even_count + 1\n"
        f"        else:\n"
        f"            odd_sum = odd_sum + val\n"
        f"            odd_count = odd_count + 1\n"
        f"        i = i + 1\n"
        f"    diff = even_sum - odd_sum\n"
        f"    if diff < 0:\n"
        f"        diff = 0 - diff\n"
        f"    combined = even_sum + odd_sum\n"
        f"    scaled = combined * {scale}\n"
        f"    result = scaled + diff\n"
        f"    return result\n"
    )

    equiv1 = (
        f"def {fname}(xs: list) -> int:\n"
        f"    n = len(xs)\n"
        f"    even_sum = 0\n"
        f"    odd_sum = 0\n"
        f"    even_count = 0\n"
        f"    odd_count = 0\n"
        f"    for i in range(n):\n"
        f"        val = xs[i]\n"
        f"        pos = i + 1\n"
        f"        remainder = pos % {step}\n"
        f"        is_divisible = remainder == 0\n"
        f"        if is_divisible:\n"
        f"            even_sum = even_sum + val\n"
        f"            even_count = even_count + 1\n"
        f"        else:\n"
        f"            odd_sum = odd_sum + val\n"
        f"            odd_count = odd_count + 1\n"
        f"    diff = even_sum - odd_sum\n"
        f"    if diff < 0:\n"
        f"        diff = 0 - diff\n"
        f"    combined = even_sum + odd_sum\n"
        f"    scaled = combined * {scale}\n"
        f"    result = scaled + diff\n"
        f"    return result\n"
    )

    equiv2 = (
        f"def {fname}(xs: list) -> int:\n"
        f"    n = len(xs)\n"
        f"    group_a = 0\n"
        f"    group_b = 0\n"
        f"    cnt_a = 0\n"
        f"    cnt_b = 0\n"
        f"    idx = 0\n"
        f"    while idx < n:\n"
        f"        element = xs[idx]\n"
        f"        position = idx + 1\n"
        f"        mod_result = position % {step}\n"
        f"        if mod_result == 0:\n"
        f"            group_a = group_a + element\n"
        f"            cnt_a = cnt_a + 1\n"
        f"        else:\n"
        f"            group_b = group_b + element\n"
        f"            cnt_b = cnt_b + 1\n"
        f"        idx = idx + 1\n"
        f"    raw_diff = group_a - group_b\n"
        f"    if raw_diff < 0:\n"
        f"        abs_diff = 0 - raw_diff\n"
        f"    else:\n"
        f"        abs_diff = raw_diff\n"
        f"    total = group_a + group_b\n"
        f"    scaled_total = total * {scale}\n"
        f"    result = scaled_total + abs_diff\n"
        f"    return result\n"
    )

    mut1 = {
        "source": (
            f"def {fname}(xs: list) -> int:\n"
            f"    n = len(xs)\n"
            f"    even_sum = 0\n"
            f"    odd_sum = 0\n"
            f"    even_count = 0\n"
            f"    odd_count = 0\n"
            f"    i = 0\n"
            f"    while i < n:\n"
            f"        val = xs[i]\n"
            f"        pos = i + 1\n"
            f"        if pos % {step} == 0:\n"
            f"            even_sum = even_sum + val\n"
            f"            even_count = even_count + 1\n"
            f"        else:\n"
            f"            odd_sum = odd_sum + val\n"
            f"            odd_count = odd_count + 1\n"
            f"        i = i + 1\n"
            f"    diff = even_sum - odd_sum\n"
            f"    if diff < 0:\n"
            f"        diff = 0 - diff\n"
            f"    combined = even_sum + odd_sum\n"
            f"    scaled = combined * {scale + 1}\n"
            f"    result = scaled + diff\n"
            f"    return result\n"
        ),
        "description": f"uses scale {scale + 1} instead of {scale}",
    }

    mut2 = {
        "source": (
            f"def {fname}(xs: list) -> int:\n"
            f"    n = len(xs)\n"
            f"    even_sum = 0\n"
            f"    odd_sum = 0\n"
            f"    even_count = 0\n"
            f"    odd_count = 0\n"
            f"    i = 0\n"
            f"    while i < n:\n"
            f"        val = xs[i]\n"
            f"        pos = i\n"
            f"        if pos % {step} == 0:\n"
            f"            even_sum = even_sum + val\n"
            f"            even_count = even_count + 1\n"
            f"        else:\n"
            f"            odd_sum = odd_sum + val\n"
            f"            odd_count = odd_count + 1\n"
            f"        i = i + 1\n"
            f"    diff = even_sum - odd_sum\n"
            f"    if diff < 0:\n"
            f"        diff = 0 - diff\n"
            f"    combined = even_sum + odd_sum\n"
            f"    scaled = combined * {scale}\n"
            f"    result = scaled + diff\n"
            f"    return result\n"
        ),
        "description": "uses i instead of i+1 for position — shifts grouping by one",
    }

    return source, [equiv1, equiv2], [mut1, mut2]


# ---------------------------------------------------------------------------
# Blueprint 9 — cumulative_counter
# ---------------------------------------------------------------------------

def _bp_cumulative_counter(fname: str, p: dict) -> tuple:
    thresh = p["thresh"]
    inc, dec = p["inc"], p["dec"]
    init = p["init"]

    source = (
        f"def {fname}(xs: list) -> int:\n"
        f"    n = len(xs)\n"
        f"    counter = {init}\n"
        f"    total = 0\n"
        f"    max_counter = {init}\n"
        f"    i = 0\n"
        f"    while i < n:\n"
        f"        val = xs[i]\n"
        f"        if val > {thresh}:\n"
        f"            counter = counter + {inc}\n"
        f"        else:\n"
        f"            counter = counter - {dec}\n"
        f"        if counter > max_counter:\n"
        f"            max_counter = counter\n"
        f"        if counter < 0:\n"
        f"            counter = 0\n"
        f"        total = total + counter\n"
        f"        i = i + 1\n"
        f"    result = total + max_counter\n"
        f"    return result\n"
    )

    equiv1 = (
        f"def {fname}(xs: list) -> int:\n"
        f"    n = len(xs)\n"
        f"    counter = {init}\n"
        f"    total = 0\n"
        f"    max_counter = {init}\n"
        f"    for i in range(n):\n"
        f"        val = xs[i]\n"
        f"        above = val > {thresh}\n"
        f"        if above:\n"
        f"            counter = counter + {inc}\n"
        f"        else:\n"
        f"            counter = counter - {dec}\n"
        f"        is_new_max = counter > max_counter\n"
        f"        if is_new_max:\n"
        f"            max_counter = counter\n"
        f"        is_negative = counter < 0\n"
        f"        if is_negative:\n"
        f"            counter = 0\n"
        f"        total = total + counter\n"
        f"    result = total + max_counter\n"
        f"    return result\n"
    )

    equiv2 = (
        f"def {fname}(xs: list) -> int:\n"
        f"    n = len(xs)\n"
        f"    ctr = {init}\n"
        f"    running_total = 0\n"
        f"    peak = {init}\n"
        f"    idx = 0\n"
        f"    while idx < n:\n"
        f"        element = xs[idx]\n"
        f"        passes_threshold = element > {thresh}\n"
        f"        if passes_threshold:\n"
        f"            ctr = ctr + {inc}\n"
        f"        else:\n"
        f"            ctr = ctr - {dec}\n"
        f"        if ctr > peak:\n"
        f"            peak = ctr\n"
        f"        if ctr < 0:\n"
        f"            ctr = 0\n"
        f"        running_total = running_total + ctr\n"
        f"        idx = idx + 1\n"
        f"    answer = running_total + peak\n"
        f"    return answer\n"
    )

    mut1 = {
        "source": (
            f"def {fname}(xs: list) -> int:\n"
            f"    n = len(xs)\n"
            f"    counter = {init}\n"
            f"    total = 0\n"
            f"    max_counter = {init}\n"
            f"    i = 0\n"
            f"    while i < n:\n"
            f"        val = xs[i]\n"
            f"        if val >= {thresh}:\n"
            f"            counter = counter + {inc}\n"
            f"        else:\n"
            f"            counter = counter - {dec}\n"
            f"        if counter > max_counter:\n"
            f"            max_counter = counter\n"
            f"        if counter < 0:\n"
            f"            counter = 0\n"
            f"        total = total + counter\n"
            f"        i = i + 1\n"
            f"    result = total + max_counter\n"
            f"    return result\n"
        ),
        "description": f"uses '>=' instead of '>' for threshold {thresh} — includes boundary",
    }

    mut2 = {
        "source": (
            f"def {fname}(xs: list) -> int:\n"
            f"    n = len(xs)\n"
            f"    counter = {init}\n"
            f"    total = 0\n"
            f"    max_counter = {init}\n"
            f"    i = 0\n"
            f"    while i < n:\n"
            f"        val = xs[i]\n"
            f"        if val > {thresh}:\n"
            f"            counter = counter + {inc}\n"
            f"        else:\n"
            f"            counter = counter - {dec}\n"
            f"        if counter > max_counter:\n"
            f"            max_counter = counter\n"
            f"        total = total + counter\n"
            f"        i = i + 1\n"
            f"    result = total + max_counter\n"
            f"    padding_line_a = n\n"
            f"    padding_line_b = total\n"
            f"    padding_line_c = result\n"
            f"    return result\n"
        ),
        "description": "removes counter floor at 0 — counter can go negative",
    }

    return source, [equiv1, equiv2], [mut1, mut2]


# ---------------------------------------------------------------------------
# Blueprint 10 — pairwise_diff_accumulator
# ---------------------------------------------------------------------------

def _bp_pairwise_diff(fname: str, p: dict) -> tuple:
    scale = p["scale"]
    default = p["default_val"]

    source = (
        f"def {fname}(xs: list) -> int:\n"
        f"    n = len(xs)\n"
        f"    if n < 2:\n"
        f"        return {default}\n"
        f"    count_inc = 0\n"
        f"    count_dec = 0\n"
        f"    total_diff = 0\n"
        f"    i = 0\n"
        f"    while i < n - 1:\n"
        f"        current = xs[i]\n"
        f"        next_val = xs[i + 1]\n"
        f"        diff = next_val - current\n"
        f"        if diff > 0:\n"
        f"            count_inc = count_inc + 1\n"
        f"            total_diff = total_diff + diff\n"
        f"        elif diff < 0:\n"
        f"            count_dec = count_dec + 1\n"
        f"            total_diff = total_diff - diff\n"
        f"        i = i + 1\n"
        f"    scaled = total_diff * {scale}\n"
        f"    result = scaled + count_inc + count_dec\n"
        f"    return result\n"
    )

    equiv1 = (
        f"def {fname}(xs: list) -> int:\n"
        f"    n = len(xs)\n"
        f"    if n < 2:\n"
        f"        return {default}\n"
        f"    count_inc = 0\n"
        f"    count_dec = 0\n"
        f"    total_diff = 0\n"
        f"    for i in range(n - 1):\n"
        f"        current = xs[i]\n"
        f"        next_val = xs[i + 1]\n"
        f"        diff = next_val - current\n"
        f"        is_increase = diff > 0\n"
        f"        is_decrease = diff < 0\n"
        f"        if is_increase:\n"
        f"            count_inc = count_inc + 1\n"
        f"            total_diff = total_diff + diff\n"
        f"        elif is_decrease:\n"
        f"            count_dec = count_dec + 1\n"
        f"            total_diff = total_diff - diff\n"
        f"    scaled = total_diff * {scale}\n"
        f"    transitions = count_inc + count_dec\n"
        f"    result = scaled + transitions\n"
        f"    return result\n"
    )

    equiv2 = (
        f"def {fname}(xs: list) -> int:\n"
        f"    n = len(xs)\n"
        f"    if n < 2:\n"
        f"        return {default}\n"
        f"    inc_count = 0\n"
        f"    dec_count = 0\n"
        f"    abs_diff_sum = 0\n"
        f"    idx = 0\n"
        f"    limit = n - 1\n"
        f"    while idx < limit:\n"
        f"        left = xs[idx]\n"
        f"        right = xs[idx + 1]\n"
        f"        delta = right - left\n"
        f"        positive_delta = delta > 0\n"
        f"        negative_delta = delta < 0\n"
        f"        if positive_delta:\n"
        f"            inc_count = inc_count + 1\n"
        f"            abs_diff_sum = abs_diff_sum + delta\n"
        f"        elif negative_delta:\n"
        f"            dec_count = dec_count + 1\n"
        f"            abs_diff_sum = abs_diff_sum - delta\n"
        f"        idx = idx + 1\n"
        f"    scaled_sum = abs_diff_sum * {scale}\n"
        f"    result = scaled_sum + inc_count + dec_count\n"
        f"    return result\n"
    )

    mut1 = {
        "source": (
            f"def {fname}(xs: list) -> int:\n"
            f"    n = len(xs)\n"
            f"    if n < 2:\n"
            f"        return {default}\n"
            f"    count_inc = 0\n"
            f"    count_dec = 0\n"
            f"    total_diff = 0\n"
            f"    i = 0\n"
            f"    while i < n - 1:\n"
            f"        current = xs[i]\n"
            f"        next_val = xs[i + 1]\n"
            f"        diff = next_val - current\n"
            f"        if diff > 0:\n"
            f"            count_inc = count_inc + 1\n"
            f"            total_diff = total_diff + diff\n"
            f"        elif diff < 0:\n"
            f"            count_dec = count_dec + 1\n"
            f"            total_diff = total_diff + diff\n"
            f"        i = i + 1\n"
            f"    scaled = total_diff * {scale}\n"
            f"    result = scaled + count_inc + count_dec\n"
            f"    return result\n"
        ),
        "description": "adds negative diff instead of subtracting it — total_diff shrinks instead of growing",
    }

    mut2 = {
        "source": (
            f"def {fname}(xs: list) -> int:\n"
            f"    n = len(xs)\n"
            f"    if n < 2:\n"
            f"        return {default}\n"
            f"    count_inc = 0\n"
            f"    count_dec = 0\n"
            f"    total_diff = 0\n"
            f"    i = 0\n"
            f"    while i < n - 1:\n"
            f"        current = xs[i]\n"
            f"        next_val = xs[i + 1]\n"
            f"        diff = next_val - current\n"
            f"        if diff >= 0:\n"
            f"            count_inc = count_inc + 1\n"
            f"            total_diff = total_diff + diff\n"
            f"        elif diff < 0:\n"
            f"            count_dec = count_dec + 1\n"
            f"            total_diff = total_diff - diff\n"
            f"        i = i + 1\n"
            f"    scaled = total_diff * {scale}\n"
            f"    result = scaled + count_inc + count_dec\n"
            f"    return result\n"
        ),
        "description": "uses '>=' instead of '>' for increase check — zero-diffs counted as increases",
    }

    return source, [equiv1, equiv2], [mut1, mut2]


# ---------------------------------------------------------------------------
# BLUEPRINTS registry
# ---------------------------------------------------------------------------

BLUEPRINTS: list[dict[str, Any]] = [
    {
        "blueprint_id": "conditional_accumulator",
        "category": "random_generated",
        "param_types": ["list[int]"],
        "return_type": "int",
        "constraints": "",
        "param_choices": {
            "op1": [">", ">="],
            "op2": ["<", "<="],
            "thresh1": list(range(-3, 6)),
            "thresh2": list(range(-5, 1)),
            "scale1": [2, 3, 4],
            "scale2": [1, 2, 3],
        },
        "build": _bp_conditional_accumulator,
    },
    {
        "blueprint_id": "filter_transform_reduce",
        "category": "random_generated",
        "param_types": ["list[int]"],
        "return_type": "int",
        "constraints": "",
        "param_choices": {
            "op": [">", "<", ">=", "<="],
            "thresh": list(range(-3, 6)),
            "scale": [2, 3, 4, 5],
        },
        "build": _bp_filter_transform_reduce,
    },
    {
        "blueprint_id": "multi_bucket_stats",
        "category": "random_generated",
        "param_types": ["list[int]"],
        "return_type": "int",
        "constraints": "",
        "param_choices": {
            "lo": list(range(-3, 3)),
            "hi": list(range(3, 8)),
            "default_val": [0, -1],
        },
        "build": _bp_multi_bucket_stats,
    },
    {
        "blueprint_id": "running_extremes",
        "category": "random_generated",
        "param_types": ["list[int]"],
        "return_type": "int",
        "constraints": "",
        "param_choices": {
            "offset": list(range(-5, 6)),
        },
        "build": _bp_running_extremes,
    },
    {
        "blueprint_id": "prefix_suffix_combine",
        "category": "random_generated",
        "param_types": ["list[int]"],
        "return_type": "int",
        "constraints": "",
        "param_choices": {
            "divisor": [2, 3, 4],
            "scale": [1, 2, 3, 4],
        },
        "build": _bp_prefix_suffix_combine,
    },
    {
        "blueprint_id": "weighted_conditional",
        "category": "random_generated",
        "param_types": ["list[int]"],
        "return_type": "int",
        "constraints": "",
        "param_choices": {
            "thresh1": list(range(1, 6)),
            "thresh2": list(range(-5, 0)),
            "w1": [2, 3, 4],
            "w2": [2, 3, 4],
            "w3": [1, 2],
        },
        "build": _bp_weighted_conditional,
    },
    {
        "blueprint_id": "cascaded_filter",
        "category": "random_generated",
        "param_types": ["list[int]"],
        "return_type": "int",
        "constraints": "",
        "param_choices": {
            "thresh1": list(range(-3, 3)),
            "thresh2": list(range(3, 10)),
            "scale": [2, 3, 4],
        },
        "build": _bp_cascaded_filter,
    },
    {
        "blueprint_id": "index_parity",
        "category": "random_generated",
        "param_types": ["list[int]"],
        "return_type": "int",
        "constraints": "",
        "param_choices": {
            "step": [2, 3, 4],
            "scale": [1, 2, 3],
        },
        "build": _bp_index_parity,
    },
    {
        "blueprint_id": "cumulative_counter",
        "category": "random_generated",
        "param_types": ["list[int]"],
        "return_type": "int",
        "constraints": "",
        "param_choices": {
            "thresh": list(range(-2, 5)),
            "inc": [1, 2, 3],
            "dec": [1, 2],
            "init": [0, 1],
        },
        "build": _bp_cumulative_counter,
    },
    {
        "blueprint_id": "pairwise_diff",
        "category": "random_generated",
        "param_types": ["list[int]"],
        "return_type": "int",
        "constraints": "",
        "param_choices": {
            "scale": [1, 2, 3, 4],
            "default_val": [0, -1],
        },
        "build": _bp_pairwise_diff,
    },
]


# ---------------------------------------------------------------------------
# RandomFunctionGenerator
# ---------------------------------------------------------------------------

class RandomFunctionGenerator:
    """
    Generate random function triplets (source, equivalents, mutations) from
    composable blueprints.  Every generated function has a random name and at
    least *min_loc* non-blank lines of code.

    Each call to :meth:`generate` picks a random blueprint, instantiates it
    with random parameter values, and assigns a random function name.
    """

    def __init__(self, seed: Optional[int] = None, min_loc: int = 20) -> None:
        self._rng = random.Random(seed)
        self._min_loc = min_loc

    def generate(self, n: int = 20) -> list[dict[str, Any]]:
        """
        Return *n* randomly generated seed-function descriptors.

        Each descriptor has the same structure as a CATALOG entry:
            name, param_types, return_type, category, constraints,
            source, equivalents, mutations
        """
        results: list[dict[str, Any]] = []
        seen_names: set[str] = set()

        attempts = 0
        while len(results) < n and attempts < n * 20:
            attempts += 1
            bp = self._rng.choice(BLUEPRINTS)
            params = {
                key: self._rng.choice(choices)
                for key, choices in bp["param_choices"].items()
            }

            fname = _random_func_name(self._rng)
            if fname in seen_names:
                continue
            seen_names.add(fname)

            source, equivalents, mutations = bp["build"](fname, params)

            # Validate minimum LOC for source and all variants
            if _count_loc(source) < self._min_loc:
                continue
            if any(_count_loc(e) < self._min_loc for e in equivalents):
                continue
            if any(_count_loc(m["source"]) < self._min_loc for m in mutations):
                continue

            results.append(
                {
                    "name": fname,
                    "param_types": bp["param_types"],
                    "return_type": bp["return_type"],
                    "category": bp["category"],
                    "constraints": bp["constraints"],
                    "source": source,
                    "equivalents": equivalents,
                    "mutations": mutations,
                    "provenance": "random_generated",
                    "blueprint_id": bp["blueprint_id"],
                    "blueprint_params": params,
                }
            )

        return results
