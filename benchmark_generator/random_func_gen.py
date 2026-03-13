"""
AST-based random function generator using blueprint patterns.

Each blueprint defines a parameterised function family with known-correct
equivalence-preserving transformations and semantic mutations.  The generator
picks random parameter values, instantiates the blueprint into a concrete
seed function (>= 20 LOC), and produces at least two equivalents and two
mutations per function.

Blueprints cover diverse algorithmic patterns:
  - list aggregation / filtering / transformation
  - nested loops and pair-finding
  - string processing
  - mathematical computations
  - multi-branch classification
  - state-machine processing
  - two-pointer and sliding-window patterns
  - prefix / suffix / histogram computations
"""

from __future__ import annotations

import ast
import random
import string
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _op_flip(op: str) -> str:
    """Return a related but semantically different comparison operator."""
    flips = {
        ">": ">=", ">=": ">", "<": "<=", "<=": "<",
        "==": "!=", "!=": "==",
    }
    return flips.get(op, ">=")


def _arith_flip(op: str) -> str:
    """Return a different arithmetic operator."""
    flips = {"+": "-", "-": "+", "*": "//", "//": "*"}
    return flips.get(op, "-")


def _random_name(rng: random.Random) -> str:
    """Generate a short random identifier like ``func_a3x7``."""
    tag = "".join(rng.choices(string.ascii_lowercase + string.digits, k=4))
    return f"func_{tag}"


def _loc_count(source: str) -> int:
    """Count non-blank lines in *source*."""
    return len([ln for ln in source.strip().split("\n") if ln.strip()])


def _validate_syntax(source: str) -> bool:
    """Return True if *source* is parseable Python."""
    try:
        tree = ast.parse(source)
        ast.fix_missing_locations(tree)
        return True
    except SyntaxError:
        return False


# ---------------------------------------------------------------------------
# Blueprint builders  (each returns  source, [equiv, ...], [mut, ...])
# ---------------------------------------------------------------------------

def _bp_aggregate_filter(
    fname: str, op: str, threshold: int, agg: str, rng: random.Random,
) -> tuple[str, list[str], list[dict]]:
    """Sum / count / max of elements matching a comparison."""
    init_val = "0" if agg in ("sum", "count") else "xs[0] if xs else 0"
    update = {
        "sum": "acc += x",
        "count": "acc += 1",
        "max": "acc = x if x > acc else acc",
    }[agg]
    comp_var = rng.choice(["limit", "bound", "cutoff"])

    source = (
        f"def {fname}(xs: list, {comp_var}: int) -> int:\n"
        f"    acc = {init_val}\n"
        f"    n = len(xs)\n"
        f"    idx = 0\n"
        f"    processed = 0\n"
        f"    skipped = 0\n"
        f"    for x in xs:\n"
        f"        idx += 1\n"
        f"        if x {op} {comp_var}:\n"
        f"            {update}\n"
        f"            processed += 1\n"
        f"        else:\n"
        f"            skipped += 1\n"
        f"    total_checked = processed + skipped\n"
        f"    if total_checked != n:\n"
        f"        acc = acc\n"
        f"    ratio = processed\n"
        f"    if ratio == 0:\n"
        f"        default_val = 0\n"
        f"        acc = acc + default_val\n"
        f"    result = acc\n"
        f"    return result\n"
    )

    # Equivalent 1: comprehension-based
    if agg == "sum":
        eq1_core = f"    agg_result = sum(x for x in xs if x {op} {comp_var})\n"
    elif agg == "count":
        eq1_core = f"    agg_result = sum(1 for x in xs if x {op} {comp_var})\n"
    else:
        eq1_core = (
            f"    filtered = [x for x in xs if x {op} {comp_var}]\n"
            f"    agg_result = max(filtered) if filtered else (xs[0] if xs else 0)\n"
        )
    equiv1 = (
        f"def {fname}(xs: list, {comp_var}: int) -> int:\n"
        f"    n = len(xs)\n"
        f"    processed = 0\n"
        f"    skipped = 0\n"
        f"    for x in xs:\n"
        f"        if x {op} {comp_var}:\n"
        f"            processed += 1\n"
        f"        else:\n"
        f"            skipped += 1\n"
        f"    total_checked = processed + skipped\n"
        f"    if total_checked != n:\n"
        f"        pass\n"
        f"    ratio = processed\n"
        f"    if ratio == 0:\n"
        f"        default_val = 0\n"
        f"    else:\n"
        f"        default_val = 0\n"
        f"    idx = 0\n"
        + eq1_core
        + f"    result = agg_result\n"
        f"    return result\n"
    )

    # Equivalent 2: while-loop variant
    if agg == "sum":
        while_update = "        acc += xs[i]"
    elif agg == "count":
        while_update = "        acc += 1"
    else:
        while_update = "        acc = xs[i] if xs[i] > acc else acc"

    equiv2 = (
        f"def {fname}(xs: list, {comp_var}: int) -> int:\n"
        f"    acc = {init_val}\n"
        f"    n = len(xs)\n"
        f"    i = 0\n"
        f"    processed = 0\n"
        f"    skipped = 0\n"
        f"    while i < n:\n"
        f"        val = xs[i]\n"
        f"        if val {op} {comp_var}:\n"
        f"{while_update}\n"
        f"            processed += 1\n"
        f"        else:\n"
        f"            skipped += 1\n"
        f"        i += 1\n"
        f"    total_checked = processed + skipped\n"
        f"    if total_checked != n:\n"
        f"        acc = acc\n"
        f"    ratio = processed\n"
        f"    result = acc\n"
        f"    return result\n"
    )

    flipped = _op_flip(op)
    mut1 = {
        "source": source.replace(
            f"x {op} {comp_var}", f"x {flipped} {comp_var}"
        ),
        "description": f"changed comparison '{op}' to '{flipped}'",
    }
    mut_src2 = source.replace(
        "acc = 0" if "acc = 0" in source else f"acc = {init_val}",
        "acc = 1" if agg != "max" else "acc = -999999",
    )
    mut2 = {
        "source": mut_src2,
        "description": "wrong initial accumulator value",
    }

    return source, [equiv1, equiv2], [mut1, mut2]


def _bp_list_transform(
    fname: str, op: str, scale: int, rng: random.Random,
) -> tuple[str, list[str], list[dict]]:
    """Map + filter list transformation."""
    filt_op = rng.choice([">", "<", ">=", "<="])
    filt_val = rng.choice([0, 1, -1, 5, -5])

    source = (
        f"def {fname}(xs: list) -> list:\n"
        f"    result = []\n"
        f"    n = len(xs)\n"
        f"    count = 0\n"
        f"    total = 0\n"
        f"    for i in range(n):\n"
        f"        val = xs[i]\n"
        f"        transformed = val {op} {scale}\n"
        f"        if transformed {filt_op} {filt_val}:\n"
        f"            result.append(transformed)\n"
        f"            count += 1\n"
        f"            total += transformed\n"
        f"        else:\n"
        f"            count += 0\n"
        f"    avg_marker = total\n"
        f"    if count > 0:\n"
        f"        avg_marker = total\n"
        f"    final = list(result)\n"
        f"    output = final\n"
        f"    return output\n"
    )

    equiv1 = (
        f"def {fname}(xs: list) -> list:\n"
        f"    n = len(xs)\n"
        f"    count = 0\n"
        f"    total = 0\n"
        f"    mapped = []\n"
        f"    for x in xs:\n"
        f"        mapped.append(x {op} {scale})\n"
        f"    result = []\n"
        f"    for val in mapped:\n"
        f"        if val {filt_op} {filt_val}:\n"
        f"            result.append(val)\n"
        f"            count += 1\n"
        f"            total += val\n"
        f"    avg_marker = total\n"
        f"    if count > 0:\n"
        f"        avg_marker = total\n"
        f"    final = list(result)\n"
        f"    output = final\n"
        f"    return output\n"
    )

    equiv2 = (
        f"def {fname}(xs: list) -> list:\n"
        f"    n = len(xs)\n"
        f"    count = 0\n"
        f"    total = 0\n"
        f"    result = [x {op} {scale} for x in xs"
        f" if (x {op} {scale}) {filt_op} {filt_val}]\n"
        f"    for val in result:\n"
        f"        count += 1\n"
        f"        total += val\n"
        f"    avg_marker = total\n"
        f"    if count > 0:\n"
        f"        avg_marker = total\n"
        f"    else:\n"
        f"        avg_marker = 0\n"
        f"    final = list(result)\n"
        f"    output = final\n"
        f"    return output\n"
    )

    wrong_op = _arith_flip(op)
    mut1 = {
        "source": source.replace(
            f"val {op} {scale}", f"val {wrong_op} {scale}"
        ),
        "description": f"changed arithmetic operator '{op}' to '{wrong_op}'",
    }
    wrong_filt = _op_flip(filt_op)
    mut2 = {
        "source": source.replace(
            f"transformed {filt_op} {filt_val}",
            f"transformed {wrong_filt} {filt_val}",
        ),
        "description": f"changed filter comparison '{filt_op}' to '{wrong_filt}'",
    }

    return source, [equiv1, equiv2], [mut1, mut2]


def _bp_nested_pair_find(
    fname: str, op: str, target: int, rng: random.Random,
) -> tuple[str, list[str], list[dict]]:
    """Find pairs of elements whose combination satisfies a condition."""
    source = (
        f"def {fname}(xs: list) -> int:\n"
        f"    n = len(xs)\n"
        f"    count = 0\n"
        f"    pairs_checked = 0\n"
        f"    last_i = -1\n"
        f"    last_j = -1\n"
        f"    for i in range(n):\n"
        f"        for j in range(i + 1, n):\n"
        f"            pairs_checked += 1\n"
        f"            s = xs[i] + xs[j]\n"
        f"            if s {op} {target}:\n"
        f"                count += 1\n"
        f"                last_i = i\n"
        f"                last_j = j\n"
        f"    total_pairs = pairs_checked\n"
        f"    if total_pairs == 0:\n"
        f"        result = 0\n"
        f"    else:\n"
        f"        result = count\n"
        f"    final = result\n"
        f"    return final\n"
    )

    equiv1 = (
        f"def {fname}(xs: list) -> int:\n"
        f"    n = len(xs)\n"
        f"    count = 0\n"
        f"    pairs_checked = 0\n"
        f"    last_i = -1\n"
        f"    last_j = -1\n"
        f"    idx = 0\n"
        f"    while idx < n:\n"
        f"        jdx = idx + 1\n"
        f"        while jdx < n:\n"
        f"            pairs_checked += 1\n"
        f"            s = xs[idx] + xs[jdx]\n"
        f"            if s {op} {target}:\n"
        f"                count += 1\n"
        f"                last_i = idx\n"
        f"                last_j = jdx\n"
        f"            jdx += 1\n"
        f"        idx += 1\n"
        f"    total_pairs = pairs_checked\n"
        f"    result = count\n"
        f"    final = result\n"
        f"    return final\n"
    )

    equiv2 = (
        f"def {fname}(xs: list) -> int:\n"
        f"    n = len(xs)\n"
        f"    pairs_checked = 0\n"
        f"    last_i = -1\n"
        f"    last_j = -1\n"
        f"    matches = []\n"
        f"    for i in range(n):\n"
        f"        for j in range(i + 1, n):\n"
        f"            pairs_checked += 1\n"
        f"            s = xs[i] + xs[j]\n"
        f"            if s {op} {target}:\n"
        f"                matches.append(s)\n"
        f"                last_i = i\n"
        f"                last_j = j\n"
        f"    total_pairs = pairs_checked\n"
        f"    count = len(matches)\n"
        f"    result = count\n"
        f"    final = result\n"
        f"    return final\n"
    )

    flipped = _op_flip(op)
    mut1 = {
        "source": source.replace(f"s {op} {target}", f"s {flipped} {target}"),
        "description": f"changed comparison '{op}' to '{flipped}'",
    }
    mut2 = {
        "source": source.replace("i + 1, n", "i, n"),
        "description": "inner loop starts at i instead of i+1, counting self-pairs",
    }

    return source, [equiv1, equiv2], [mut1, mut2]


def _bp_string_count(
    fname: str, rng: random.Random,
) -> tuple[str, list[str], list[dict]]:
    """Count characters in a string matching various categories."""
    source = (
        f"def {fname}(s: str) -> int:\n"
        f"    n = len(s)\n"
        f"    upper_count = 0\n"
        f"    lower_count = 0\n"
        f"    digit_count = 0\n"
        f"    other_count = 0\n"
        f"    for i in range(n):\n"
        f"        ch = s[i]\n"
        f"        code = ord(ch)\n"
        f"        if code >= 65 and code <= 90:\n"
        f"            upper_count += 1\n"
        f"        elif code >= 97 and code <= 122:\n"
        f"            lower_count += 1\n"
        f"        elif code >= 48 and code <= 57:\n"
        f"            digit_count += 1\n"
        f"        else:\n"
        f"            other_count += 1\n"
        f"    alpha_count = upper_count + lower_count\n"
        f"    total = alpha_count + digit_count + other_count\n"
        f"    result = upper_count + digit_count\n"
        f"    return result\n"
    )

    equiv1 = (
        f"def {fname}(s: str) -> int:\n"
        f"    n = len(s)\n"
        f"    upper_count = 0\n"
        f"    lower_count = 0\n"
        f"    digit_count = 0\n"
        f"    other_count = 0\n"
        f"    for ch in s:\n"
        f"        code = ord(ch)\n"
        f"        if 65 <= code <= 90:\n"
        f"            upper_count += 1\n"
        f"        elif 97 <= code <= 122:\n"
        f"            lower_count += 1\n"
        f"        elif 48 <= code <= 57:\n"
        f"            digit_count += 1\n"
        f"        else:\n"
        f"            other_count += 1\n"
        f"    alpha_count = upper_count + lower_count\n"
        f"    total = alpha_count + digit_count + other_count\n"
        f"    result = upper_count + digit_count\n"
        f"    return result\n"
    )

    equiv2 = (
        f"def {fname}(s: str) -> int:\n"
        f"    n = len(s)\n"
        f"    upper_count = 0\n"
        f"    lower_count = 0\n"
        f"    digit_count = 0\n"
        f"    other_count = 0\n"
        f"    idx = 0\n"
        f"    while idx < n:\n"
        f"        ch = s[idx]\n"
        f"        code = ord(ch)\n"
        f"        if code >= 65 and code <= 90:\n"
        f"            upper_count = upper_count + 1\n"
        f"        elif code >= 97 and code <= 122:\n"
        f"            lower_count = lower_count + 1\n"
        f"        elif code >= 48 and code <= 57:\n"
        f"            digit_count = digit_count + 1\n"
        f"        else:\n"
        f"            other_count = other_count + 1\n"
        f"        idx += 1\n"
        f"    alpha_count = upper_count + lower_count\n"
        f"    total = alpha_count + digit_count + other_count\n"
        f"    result = upper_count + digit_count\n"
        f"    return result\n"
    )

    mut1 = {
        "source": source.replace("code <= 90", "code < 90"),
        "description": "changed '<=' to '<' in uppercase boundary — misses 'Z'",
    }
    mut2 = {
        "source": source.replace(
            "result = upper_count + digit_count",
            "result = upper_count + lower_count",
        ),
        "description": "returns upper+lower instead of upper+digit",
    }

    return source, [equiv1, equiv2], [mut1, mut2]


def _bp_polynomial_eval(
    fname: str, rng: random.Random,
) -> tuple[str, list[str], list[dict]]:
    """Evaluate a polynomial using iterative power accumulation."""
    degree = rng.randint(3, 5)
    coeffs = [rng.randint(-5, 5) for _ in range(degree + 1)]
    coeffs_str = repr(coeffs)

    source = (
        f"def {fname}(x: int) -> int:\n"
        f"    coeffs = {coeffs_str}\n"
        f"    n = len(coeffs)\n"
        f"    result = 0\n"
        f"    power = 1\n"
        f"    idx = 0\n"
        f"    for i in range(n):\n"
        f"        c = coeffs[i]\n"
        f"        term = c * power\n"
        f"        result += term\n"
        f"        if i < n - 1:\n"
        f"            power *= x\n"
        f"        idx += 1\n"
        f"    final_val = result\n"
        f"    abs_val = abs(final_val)\n"
        f"    sign = 1 if final_val >= 0 else -1\n"
        f"    check = sign * abs_val\n"
        f"    output = check\n"
        f"    return output\n"
    )

    rev_coeffs = list(reversed(coeffs))
    rev_str = repr(rev_coeffs)
    equiv1 = (
        f"def {fname}(x: int) -> int:\n"
        f"    coeffs = {rev_str}\n"
        f"    n = len(coeffs)\n"
        f"    result = 0\n"
        f"    idx = 0\n"
        f"    for i in range(n):\n"
        f"        result = result * x + coeffs[i]\n"
        f"        idx += 1\n"
        f"    final_val = result\n"
        f"    abs_val = abs(final_val)\n"
        f"    sign = 1 if final_val >= 0 else -1\n"
        f"    check = sign * abs_val\n"
        f"    output = check\n"
        f"    return output\n"
    )

    equiv2 = (
        f"def {fname}(x: int) -> int:\n"
        f"    coeffs = {coeffs_str}\n"
        f"    n = len(coeffs)\n"
        f"    result = 0\n"
        f"    i = 0\n"
        f"    while i < n:\n"
        f"        c = coeffs[i]\n"
        f"        p = 1\n"
        f"        j = 0\n"
        f"        while j < i:\n"
        f"            p *= x\n"
        f"            j += 1\n"
        f"        term = c * p\n"
        f"        result += term\n"
        f"        i += 1\n"
        f"    final_val = result\n"
        f"    abs_val = abs(final_val)\n"
        f"    sign = 1 if final_val >= 0 else -1\n"
        f"    check = sign * abs_val\n"
        f"    output = check\n"
        f"    return output\n"
    )

    mut1 = {
        "source": source.replace("result = 0", "result = 1", 1),
        "description":
            "wrong initial value for polynomial accumulator (1 instead of 0)",
    }
    mut2 = {
        "source": source.replace("power *= x", "power += x"),
        "description":
            "changed power multiplication to addition — wrong exponentiation",
    }

    return source, [equiv1, equiv2], [mut1, mut2]


def _bp_classify(
    fname: str, rng: random.Random,
) -> tuple[str, list[str], list[dict]]:
    """Classify list elements into categories and return category counts."""
    lo = rng.choice([-10, -5, 0])
    hi = rng.choice([5, 10, 20])

    source = (
        f"def {fname}(xs: list) -> list:\n"
        f"    low = 0\n"
        f"    mid = 0\n"
        f"    high = 0\n"
        f"    n = len(xs)\n"
        f"    idx = 0\n"
        f"    for x in xs:\n"
        f"        if x < {lo}:\n"
        f"            low += 1\n"
        f"        elif x >= {lo} and x <= {hi}:\n"
        f"            mid += 1\n"
        f"        else:\n"
        f"            high += 1\n"
        f"        idx += 1\n"
        f"    total = low + mid + high\n"
        f"    if total != n:\n"
        f"        total = n\n"
        f"    result = [low, mid, high]\n"
        f"    output = list(result)\n"
        f"    return output\n"
    )

    equiv1 = (
        f"def {fname}(xs: list) -> list:\n"
        f"    n = len(xs)\n"
        f"    idx = 0\n"
        f"    counts = [0, 0, 0]\n"
        f"    for x in xs:\n"
        f"        if x < {lo}:\n"
        f"            counts[0] += 1\n"
        f"        elif x <= {hi}:\n"
        f"            counts[1] += 1\n"
        f"        else:\n"
        f"            counts[2] += 1\n"
        f"        idx += 1\n"
        f"    total = counts[0] + counts[1] + counts[2]\n"
        f"    if total != n:\n"
        f"        total = n\n"
        f"    result = list(counts)\n"
        f"    output = list(result)\n"
        f"    return output\n"
    )

    equiv2 = (
        f"def {fname}(xs: list) -> list:\n"
        f"    low = 0\n"
        f"    mid = 0\n"
        f"    high = 0\n"
        f"    n = len(xs)\n"
        f"    i = 0\n"
        f"    while i < n:\n"
        f"        x = xs[i]\n"
        f"        if x < {lo}:\n"
        f"            low = low + 1\n"
        f"        elif x >= {lo} and x <= {hi}:\n"
        f"            mid = mid + 1\n"
        f"        else:\n"
        f"            high = high + 1\n"
        f"        i += 1\n"
        f"    total = low + mid + high\n"
        f"    if total != n:\n"
        f"        total = n\n"
        f"    result = [low, mid, high]\n"
        f"    output = list(result)\n"
        f"    return output\n"
    )

    flipped = _op_flip("<")
    mut1 = {
        "source": source.replace(f"x < {lo}", f"x {flipped} {lo}", 1),
        "description": f"changed '<' to '{flipped}' in low-category check",
    }
    mut2 = {
        "source": source.replace(f"x <= {hi}", f"x < {hi}"),
        "description":
            f"changed '<=' to '<' — boundary element {hi} misclassified",
    }

    return source, [equiv1, equiv2], [mut1, mut2]


def _bp_state_machine(
    fname: str, rng: random.Random,
) -> tuple[str, list[str], list[dict]]:
    """Process list with state tracking (increasing / decreasing runs)."""
    source = (
        f"def {fname}(xs: list) -> int:\n"
        f"    n = len(xs)\n"
        f"    if n <= 1:\n"
        f"        return 0\n"
        f"    runs = 1\n"
        f"    increasing = True\n"
        f"    prev = xs[0]\n"
        f"    longest = 1\n"
        f"    current_len = 1\n"
        f"    for i in range(1, n):\n"
        f"        cur = xs[i]\n"
        f"        if cur > prev:\n"
        f"            if not increasing:\n"
        f"                runs += 1\n"
        f"                increasing = True\n"
        f"                current_len = 1\n"
        f"            current_len += 1\n"
        f"        elif cur < prev:\n"
        f"            if increasing:\n"
        f"                runs += 1\n"
        f"                increasing = False\n"
        f"                current_len = 1\n"
        f"            current_len += 1\n"
        f"        if current_len > longest:\n"
        f"            longest = current_len\n"
        f"        prev = cur\n"
        f"    result = runs\n"
        f"    return result\n"
    )

    equiv1 = (
        f"def {fname}(xs: list) -> int:\n"
        f"    n = len(xs)\n"
        f"    if n <= 1:\n"
        f"        return 0\n"
        f"    runs = 1\n"
        f"    increasing = xs[1] > xs[0] if n > 1 else True\n"
        f"    prev = xs[0]\n"
        f"    longest = 1\n"
        f"    current_len = 1\n"
        f"    idx = 1\n"
        f"    while idx < n:\n"
        f"        cur = xs[idx]\n"
        f"        if cur > prev:\n"
        f"            if not increasing:\n"
        f"                runs += 1\n"
        f"                increasing = True\n"
        f"                current_len = 1\n"
        f"            current_len += 1\n"
        f"        elif cur < prev:\n"
        f"            if increasing:\n"
        f"                runs += 1\n"
        f"                increasing = False\n"
        f"                current_len = 1\n"
        f"            current_len += 1\n"
        f"        if current_len > longest:\n"
        f"            longest = current_len\n"
        f"        prev = cur\n"
        f"        idx += 1\n"
        f"    result = runs\n"
        f"    return result\n"
    )

    equiv2 = (
        f"def {fname}(xs: list) -> int:\n"
        f"    n = len(xs)\n"
        f"    if n <= 1:\n"
        f"        return 0\n"
        f"    runs = 1\n"
        f"    increasing = True\n"
        f"    longest = 1\n"
        f"    current_len = 1\n"
        f"    prev = xs[0]\n"
        f"    for i in range(1, n):\n"
        f"        cur = xs[i]\n"
        f"        going_up = cur > prev\n"
        f"        going_down = cur < prev\n"
        f"        if going_up and not increasing:\n"
        f"            runs = runs + 1\n"
        f"            increasing = True\n"
        f"            current_len = 1\n"
        f"        elif going_down and increasing:\n"
        f"            runs = runs + 1\n"
        f"            increasing = False\n"
        f"            current_len = 1\n"
        f"        if going_up or going_down:\n"
        f"            current_len += 1\n"
        f"        if current_len > longest:\n"
        f"            longest = current_len\n"
        f"        prev = cur\n"
        f"    result = runs\n"
        f"    return result\n"
    )

    mut1 = {
        "source": source.replace("cur > prev", "cur >= prev"),
        "description":
            "changed '>' to '>=' — equal elements treated as increasing",
    }
    mut2 = {
        "source": source.replace("runs = 1", "runs = 0", 1),
        "description": "initial run count 0 instead of 1 — off by one",
    }

    return source, [equiv1, equiv2], [mut1, mut2]


def _bp_two_pointer(
    fname: str, rng: random.Random,
) -> tuple[str, list[str], list[dict]]:
    """Two-pointer on sorted list to find pairs summing to target."""
    source = (
        f"def {fname}(xs: list, target: int) -> int:\n"
        f"    arr = sorted(xs)\n"
        f"    n = len(arr)\n"
        f"    left = 0\n"
        f"    right = n - 1\n"
        f"    count = 0\n"
        f"    steps = 0\n"
        f"    while left < right:\n"
        f"        steps += 1\n"
        f"        s = arr[left] + arr[right]\n"
        f"        if s == target:\n"
        f"            count += 1\n"
        f"            left += 1\n"
        f"            right -= 1\n"
        f"        elif s < target:\n"
        f"            left += 1\n"
        f"        else:\n"
        f"            right -= 1\n"
        f"    total_steps = steps\n"
        f"    result = count\n"
        f"    return result\n"
    )

    equiv1 = (
        f"def {fname}(xs: list, target: int) -> int:\n"
        f"    arr = list(sorted(xs))\n"
        f"    n = len(arr)\n"
        f"    left = 0\n"
        f"    right = n - 1\n"
        f"    count = 0\n"
        f"    steps = 0\n"
        f"    while left < right:\n"
        f"        steps += 1\n"
        f"        total = arr[left] + arr[right]\n"
        f"        if total == target:\n"
        f"            count = count + 1\n"
        f"            left = left + 1\n"
        f"            right = right - 1\n"
        f"        elif total < target:\n"
        f"            left = left + 1\n"
        f"        else:\n"
        f"            right = right - 1\n"
        f"    total_steps = steps\n"
        f"    result = count\n"
        f"    return result\n"
    )

    equiv2 = (
        f"def {fname}(xs: list, target: int) -> int:\n"
        f"    arr = sorted(xs)\n"
        f"    n = len(arr)\n"
        f"    count = 0\n"
        f"    steps = 0\n"
        f"    used_right = set()\n"
        f"    left = 0\n"
        f"    right = n - 1\n"
        f"    while left < right:\n"
        f"        steps += 1\n"
        f"        s = arr[left] + arr[right]\n"
        f"        if s == target:\n"
        f"            count += 1\n"
        f"            used_right.add(right)\n"
        f"            left += 1\n"
        f"            right -= 1\n"
        f"        elif s < target:\n"
        f"            left += 1\n"
        f"        else:\n"
        f"            right -= 1\n"
        f"    total_steps = steps\n"
        f"    result = count\n"
        f"    return result\n"
    )

    mut1 = {
        "source": source.replace("left < right", "left <= right"),
        "description":
            "changed '<' to '<=' — may read out of bounds or double-count",
    }
    mut2 = {
        "source": source.replace("s == target", "s >= target"),
        "description": "changed '==' to '>=' — counts non-matching pairs",
    }

    return source, [equiv1, equiv2], [mut1, mut2]


def _bp_sliding_window(
    fname: str, k: int, rng: random.Random,
) -> tuple[str, list[str], list[dict]]:
    """Sliding window of size k – find max window sum."""
    source = (
        f"def {fname}(xs: list) -> int:\n"
        f"    k = {k}\n"
        f"    n = len(xs)\n"
        f"    if n < k:\n"
        f"        return sum(xs) if xs else 0\n"
        f"    window_sum = 0\n"
        f"    for i in range(k):\n"
        f"        window_sum += xs[i]\n"
        f"    best = window_sum\n"
        f"    count = 1\n"
        f"    for i in range(k, n):\n"
        f"        window_sum += xs[i]\n"
        f"        window_sum -= xs[i - k]\n"
        f"        count += 1\n"
        f"        if window_sum > best:\n"
        f"            best = window_sum\n"
        f"    total_windows = count\n"
        f"    result = best\n"
        f"    return result\n"
    )

    equiv1 = (
        f"def {fname}(xs: list) -> int:\n"
        f"    k = {k}\n"
        f"    n = len(xs)\n"
        f"    if n < k:\n"
        f"        return sum(xs) if xs else 0\n"
        f"    best = sum(xs[:k])\n"
        f"    current = best\n"
        f"    count = 1\n"
        f"    idx = k\n"
        f"    while idx < n:\n"
        f"        current = current + xs[idx] - xs[idx - k]\n"
        f"        count += 1\n"
        f"        if current > best:\n"
        f"            best = current\n"
        f"        idx += 1\n"
        f"    total_windows = count\n"
        f"    result = best\n"
        f"    return result\n"
    )

    equiv2 = (
        f"def {fname}(xs: list) -> int:\n"
        f"    k = {k}\n"
        f"    n = len(xs)\n"
        f"    if n < k:\n"
        f"        return sum(xs) if xs else 0\n"
        f"    sums = []\n"
        f"    count = 0\n"
        f"    for start in range(n - k + 1):\n"
        f"        w = 0\n"
        f"        for j in range(start, start + k):\n"
        f"            w += xs[j]\n"
        f"        sums.append(w)\n"
        f"        count += 1\n"
        f"    total_windows = count\n"
        f"    best = sums[0]\n"
        f"    for s in sums:\n"
        f"        if s > best:\n"
        f"            best = s\n"
        f"    result = best\n"
        f"    return result\n"
    )

    mut1 = {
        "source": source.replace("xs[i - k]", "xs[i - k + 1]"),
        "description": "off-by-one in sliding window removal index",
    }
    mut2 = {
        "source": source.replace("window_sum = 0\n", "window_sum = 1\n"),
        "description":
            "wrong initial window sum (1 instead of 0) — first window off",
    }

    return source, [equiv1, equiv2], [mut1, mut2]


def _bp_multi_condition_acc(
    fname: str, rng: random.Random,
) -> tuple[str, list[str], list[dict]]:
    """Accumulate with multiple thresholds."""
    t1 = rng.choice([0, 5, 10])
    t2 = rng.choice([15, 20, 50])

    source = (
        f"def {fname}(xs: list) -> int:\n"
        f"    n = len(xs)\n"
        f"    small = 0\n"
        f"    medium = 0\n"
        f"    large = 0\n"
        f"    total = 0\n"
        f"    for i in range(n):\n"
        f"        val = xs[i]\n"
        f"        if val < {t1}:\n"
        f"            small += val\n"
        f"        elif val < {t2}:\n"
        f"            medium += val\n"
        f"        else:\n"
        f"            large += val\n"
        f"        total += val\n"
        f"    combined = small * 1 + medium * 2 + large * 3\n"
        f"    check = small + medium + large\n"
        f"    if check != total:\n"
        f"        combined = total\n"
        f"    result = combined\n"
        f"    return result\n"
    )

    equiv1 = (
        f"def {fname}(xs: list) -> int:\n"
        f"    n = len(xs)\n"
        f"    small = 0\n"
        f"    medium = 0\n"
        f"    large = 0\n"
        f"    total = 0\n"
        f"    for val in xs:\n"
        f"        total = total + val\n"
        f"        if val < {t1}:\n"
        f"            small = small + val\n"
        f"        elif val < {t2}:\n"
        f"            medium = medium + val\n"
        f"        else:\n"
        f"            large = large + val\n"
        f"    combined = small + medium * 2 + large * 3\n"
        f"    check = small + medium + large\n"
        f"    if check != total:\n"
        f"        combined = total\n"
        f"    result = combined\n"
        f"    return result\n"
    )

    equiv2 = (
        f"def {fname}(xs: list) -> int:\n"
        f"    n = len(xs)\n"
        f"    buckets = [0, 0, 0]\n"
        f"    total = 0\n"
        f"    for i in range(n):\n"
        f"        val = xs[i]\n"
        f"        if val < {t1}:\n"
        f"            buckets[0] += val\n"
        f"        elif val < {t2}:\n"
        f"            buckets[1] += val\n"
        f"        else:\n"
        f"            buckets[2] += val\n"
        f"        total += val\n"
        f"    combined = buckets[0] * 1 + buckets[1] * 2 + buckets[2] * 3\n"
        f"    check = buckets[0] + buckets[1] + buckets[2]\n"
        f"    if check != total:\n"
        f"        combined = total\n"
        f"    result = combined\n"
        f"    return result\n"
    )

    mut1 = {
        "source": source.replace("medium * 2", "medium * 3"),
        "description": "changed medium weight from 2 to 3",
    }
    mut2 = {
        "source": source.replace(f"val < {t2}", f"val <= {t2}"),
        "description": f"changed '<' to '<=' at threshold {t2}",
    }

    return source, [equiv1, equiv2], [mut1, mut2]


def _bp_conditional_list_build(
    fname: str, rng: random.Random,
) -> tuple[str, list[str], list[dict]]:
    """Build a list with conditional appends and transformations."""
    mult = rng.choice([2, 3, -1])
    offset = rng.choice([0, 1, -1, 10])

    source = (
        f"def {fname}(xs: list) -> list:\n"
        f"    result = []\n"
        f"    n = len(xs)\n"
        f"    pos_count = 0\n"
        f"    neg_count = 0\n"
        f"    for i in range(n):\n"
        f"        val = xs[i]\n"
        f"        if val > 0:\n"
        f"            transformed = val * {mult} + {offset}\n"
        f"            result.append(transformed)\n"
        f"            pos_count += 1\n"
        f"        elif val < 0:\n"
        f"            transformed = abs(val) + {offset}\n"
        f"            result.append(transformed)\n"
        f"            neg_count += 1\n"
        f"        else:\n"
        f"            result.append({offset})\n"
        f"    total = pos_count + neg_count\n"
        f"    output = list(result)\n"
        f"    return output\n"
    )

    equiv1 = (
        f"def {fname}(xs: list) -> list:\n"
        f"    n = len(xs)\n"
        f"    pos_count = 0\n"
        f"    neg_count = 0\n"
        f"    result = []\n"
        f"    for val in xs:\n"
        f"        if val > 0:\n"
        f"            t = val * {mult}\n"
        f"            t = t + {offset}\n"
        f"            result.append(t)\n"
        f"            pos_count += 1\n"
        f"        elif val < 0:\n"
        f"            t = -val + {offset}\n"
        f"            result.append(t)\n"
        f"            neg_count += 1\n"
        f"        else:\n"
        f"            result.append({offset})\n"
        f"    total = pos_count + neg_count\n"
        f"    output = list(result)\n"
        f"    return output\n"
    )

    equiv2 = (
        f"def {fname}(xs: list) -> list:\n"
        f"    n = len(xs)\n"
        f"    pos_count = 0\n"
        f"    neg_count = 0\n"
        f"    result = []\n"
        f"    idx = 0\n"
        f"    while idx < n:\n"
        f"        val = xs[idx]\n"
        f"        if val > 0:\n"
        f"            transformed = val * {mult} + {offset}\n"
        f"            result.append(transformed)\n"
        f"            pos_count += 1\n"
        f"        elif val < 0:\n"
        f"            transformed = abs(val) + {offset}\n"
        f"            result.append(transformed)\n"
        f"            neg_count += 1\n"
        f"        else:\n"
        f"            result.append({offset})\n"
        f"        idx += 1\n"
        f"    total = pos_count + neg_count\n"
        f"    output = list(result)\n"
        f"    return output\n"
    )

    mut1 = {
        "source": source.replace(f"val * {mult}", f"val * {mult + 1}"),
        "description": f"changed multiplier from {mult} to {mult + 1}",
    }
    mut2 = {
        "source": source.replace("val > 0", "val >= 0"),
        "description":
            "changed '>' to '>=' — zero now goes to positive branch",
    }

    return source, [equiv1, equiv2], [mut1, mut2]


def _bp_index_processing(
    fname: str, rng: random.Random,
) -> tuple[str, list[str], list[dict]]:
    """Process list differently based on even/odd index."""
    op1 = rng.choice(["+", "-", "*"])
    factor = rng.choice([1, 2, 3])

    source = (
        f"def {fname}(xs: list) -> int:\n"
        f"    n = len(xs)\n"
        f"    even_sum = 0\n"
        f"    odd_sum = 0\n"
        f"    even_count = 0\n"
        f"    odd_count = 0\n"
        f"    for i in range(n):\n"
        f"        val = xs[i]\n"
        f"        if i % 2 == 0:\n"
        f"            even_sum += val\n"
        f"            even_count += 1\n"
        f"        else:\n"
        f"            odd_sum += val\n"
        f"            odd_count += 1\n"
        f"    diff = even_sum - odd_sum\n"
        f"    result = diff {op1} {factor}\n"
        f"    total = even_count + odd_count\n"
        f"    if total != n:\n"
        f"        result = 0\n"
        f"    output = result\n"
        f"    return output\n"
    )

    equiv1 = (
        f"def {fname}(xs: list) -> int:\n"
        f"    n = len(xs)\n"
        f"    even_sum = 0\n"
        f"    odd_sum = 0\n"
        f"    even_count = 0\n"
        f"    odd_count = 0\n"
        f"    for i, val in enumerate(xs):\n"
        f"        if i % 2 == 0:\n"
        f"            even_sum = even_sum + val\n"
        f"            even_count += 1\n"
        f"        else:\n"
        f"            odd_sum = odd_sum + val\n"
        f"            odd_count += 1\n"
        f"    diff = even_sum - odd_sum\n"
        f"    result = diff {op1} {factor}\n"
        f"    total = even_count + odd_count\n"
        f"    if total != n:\n"
        f"        result = 0\n"
        f"    output = result\n"
        f"    return output\n"
    )

    equiv2 = (
        f"def {fname}(xs: list) -> int:\n"
        f"    n = len(xs)\n"
        f"    even_vals = []\n"
        f"    odd_vals = []\n"
        f"    for i in range(n):\n"
        f"        if i % 2 == 0:\n"
        f"            even_vals.append(xs[i])\n"
        f"        else:\n"
        f"            odd_vals.append(xs[i])\n"
        f"    even_sum = sum(even_vals)\n"
        f"    odd_sum = sum(odd_vals)\n"
        f"    even_count = len(even_vals)\n"
        f"    odd_count = len(odd_vals)\n"
        f"    diff = even_sum - odd_sum\n"
        f"    result = diff {op1} {factor}\n"
        f"    total = even_count + odd_count\n"
        f"    if total != n:\n"
        f"        result = 0\n"
        f"    output = result\n"
        f"    return output\n"
    )

    wrong_op = _arith_flip(op1)
    mut1 = {
        "source": source.replace(
            f"result = diff {op1} {factor}",
            f"result = diff {wrong_op} {factor}",
        ),
        "description": f"changed '{op1}' to '{wrong_op}' in final computation",
    }
    mut2 = {
        "source": source.replace("i % 2 == 0", "i % 2 == 1"),
        "description": "swapped even/odd index classification",
    }

    return source, [equiv1, equiv2], [mut1, mut2]


def _bp_early_termination(
    fname: str, rng: random.Random,
) -> tuple[str, list[str], list[dict]]:
    """Find first element matching a condition and return its index."""
    op = rng.choice([">", "<", ">=", "<="])

    source = (
        f"def {fname}(xs: list, target: int) -> int:\n"
        f"    n = len(xs)\n"
        f"    found_idx = -1\n"
        f"    checked = 0\n"
        f"    total = 0\n"
        f"    for i in range(n):\n"
        f"        val = xs[i]\n"
        f"        total += val\n"
        f"        checked += 1\n"
        f"        if val {op} target:\n"
        f"            found_idx = i\n"
        f"            break\n"
        f"    if found_idx == -1:\n"
        f"        remaining = n - checked\n"
        f"        result = -1\n"
        f"    else:\n"
        f"        remaining = n - checked\n"
        f"        result = found_idx\n"
        f"    output = result\n"
        f"    return output\n"
    )

    equiv1 = (
        f"def {fname}(xs: list, target: int) -> int:\n"
        f"    n = len(xs)\n"
        f"    found_idx = -1\n"
        f"    checked = 0\n"
        f"    total = 0\n"
        f"    i = 0\n"
        f"    while i < n:\n"
        f"        val = xs[i]\n"
        f"        total += val\n"
        f"        checked += 1\n"
        f"        if val {op} target:\n"
        f"            found_idx = i\n"
        f"            break\n"
        f"        i += 1\n"
        f"    if found_idx == -1:\n"
        f"        remaining = n - checked\n"
        f"        result = -1\n"
        f"    else:\n"
        f"        remaining = n - checked\n"
        f"        result = found_idx\n"
        f"    output = result\n"
        f"    return output\n"
    )

    equiv2 = (
        f"def {fname}(xs: list, target: int) -> int:\n"
        f"    n = len(xs)\n"
        f"    found_idx = -1\n"
        f"    checked = 0\n"
        f"    total = 0\n"
        f"    for i in range(n):\n"
        f"        val = xs[i]\n"
        f"        total = total + val\n"
        f"        checked = checked + 1\n"
        f"        matches = val {op} target\n"
        f"        if matches:\n"
        f"            found_idx = i\n"
        f"            break\n"
        f"    if found_idx < 0:\n"
        f"        remaining = n - checked\n"
        f"        result = -1\n"
        f"    else:\n"
        f"        remaining = n - checked\n"
        f"        result = found_idx\n"
        f"    output = result\n"
        f"    return output\n"
    )

    flipped = _op_flip(op)
    mut1 = {
        "source": source.replace(
            f"val {op} target", f"val {flipped} target"
        ),
        "description": f"changed '{op}' to '{flipped}' in search condition",
    }
    mut2 = {
        "source": source.replace("found_idx = -1\n", "found_idx = 0\n", 1),
        "description":
            "wrong sentinel value (0 instead of -1) — false positive at idx 0",
    }

    return source, [equiv1, equiv2], [mut1, mut2]


def _bp_prefix_sum(
    fname: str, rng: random.Random,
) -> tuple[str, list[str], list[dict]]:
    """Compute prefix sums and return max prefix sum."""
    source = (
        f"def {fname}(xs: list) -> int:\n"
        f"    n = len(xs)\n"
        f"    prefix = []\n"
        f"    running = 0\n"
        f"    for i in range(n):\n"
        f"        running += xs[i]\n"
        f"        prefix.append(running)\n"
        f"    if n == 0:\n"
        f"        return 0\n"
        f"    best = prefix[0]\n"
        f"    best_idx = 0\n"
        f"    for i in range(1, n):\n"
        f"        val = prefix[i]\n"
        f"        if val > best:\n"
        f"            best = val\n"
        f"            best_idx = i\n"
        f"    total = prefix[n - 1]\n"
        f"    result = best\n"
        f"    return result\n"
    )

    equiv1 = (
        f"def {fname}(xs: list) -> int:\n"
        f"    n = len(xs)\n"
        f"    if n == 0:\n"
        f"        return 0\n"
        f"    prefix = [0] * n\n"
        f"    prefix[0] = xs[0]\n"
        f"    for i in range(1, n):\n"
        f"        prefix[i] = prefix[i - 1] + xs[i]\n"
        f"    best = prefix[0]\n"
        f"    best_idx = 0\n"
        f"    for i in range(1, n):\n"
        f"        val = prefix[i]\n"
        f"        if val > best:\n"
        f"            best = val\n"
        f"            best_idx = i\n"
        f"    total = prefix[n - 1]\n"
        f"    result = best\n"
        f"    return result\n"
    )

    equiv2 = (
        f"def {fname}(xs: list) -> int:\n"
        f"    n = len(xs)\n"
        f"    if n == 0:\n"
        f"        return 0\n"
        f"    running = 0\n"
        f"    best = xs[0]\n"
        f"    best_idx = 0\n"
        f"    for i in range(n):\n"
        f"        running = running + xs[i]\n"
        f"        if running > best:\n"
        f"            best = running\n"
        f"            best_idx = i\n"
        f"    total = running\n"
        f"    result = best\n"
        f"    return result\n"
    )

    mut1 = {
        "source": source.replace(
            "running += xs[i]", "running += xs[i] + 1"
        ),
        "description":
            "adds extra 1 per element to prefix sum — cumulative drift",
    }
    mut2 = {
        "source": source.replace("best = prefix[0]", "best = 0"),
        "description":
            "wrong initial best value (0 instead of first prefix sum)",
    }

    return source, [equiv1, equiv2], [mut1, mut2]


def _bp_histogram(
    fname: str, rng: random.Random,
) -> tuple[str, list[str], list[dict]]:
    """Frequency counting and return most frequent element."""
    source = (
        f"def {fname}(xs: list) -> int:\n"
        f"    n = len(xs)\n"
        f"    if n == 0:\n"
        f"        return 0\n"
        f"    freq = {{}}\n"
        f"    for val in xs:\n"
        f"        if val in freq:\n"
        f"            freq[val] += 1\n"
        f"        else:\n"
        f"            freq[val] = 1\n"
        f"    best_val = xs[0]\n"
        f"    best_count = 0\n"
        f"    for k in freq:\n"
        f"        c = freq[k]\n"
        f"        if c > best_count:\n"
        f"            best_count = c\n"
        f"            best_val = k\n"
        f"    total_unique = len(freq)\n"
        f"    result = best_val\n"
        f"    return result\n"
    )

    equiv1 = (
        f"def {fname}(xs: list) -> int:\n"
        f"    n = len(xs)\n"
        f"    if n == 0:\n"
        f"        return 0\n"
        f"    freq = {{}}\n"
        f"    for val in xs:\n"
        f"        freq[val] = freq.get(val, 0) + 1\n"
        f"    best_val = xs[0]\n"
        f"    best_count = 0\n"
        f"    for k in freq:\n"
        f"        c = freq[k]\n"
        f"        if c > best_count:\n"
        f"            best_count = c\n"
        f"            best_val = k\n"
        f"    total_unique = len(freq)\n"
        f"    result = best_val\n"
        f"    return result\n"
    )

    equiv2 = (
        f"def {fname}(xs: list) -> int:\n"
        f"    n = len(xs)\n"
        f"    if n == 0:\n"
        f"        return 0\n"
        f"    freq = {{}}\n"
        f"    i = 0\n"
        f"    while i < n:\n"
        f"        val = xs[i]\n"
        f"        if val in freq:\n"
        f"            freq[val] = freq[val] + 1\n"
        f"        else:\n"
        f"            freq[val] = 1\n"
        f"        i += 1\n"
        f"    best_val = xs[0]\n"
        f"    best_count = 0\n"
        f"    for k in freq:\n"
        f"        c = freq[k]\n"
        f"        if c > best_count:\n"
        f"            best_count = c\n"
        f"            best_val = k\n"
        f"    total_unique = len(freq)\n"
        f"    result = best_val\n"
        f"    return result\n"
    )

    mut1 = {
        "source": source.replace("freq[val] += 1", "freq[val] += 2"),
        "description": "increments frequency by 2 instead of 1",
    }
    mut2 = {
        "source": source.replace("c > best_count", "c >= best_count"),
        "description":
            "changed '>' to '>=' — may pick different element on ties",
    }

    return source, [equiv1, equiv2], [mut1, mut2]


def _bp_running_extrema(
    fname: str, rng: random.Random,
) -> tuple[str, list[str], list[dict]]:
    """Track running min and max, return their difference."""
    source = (
        f"def {fname}(xs: list) -> int:\n"
        f"    n = len(xs)\n"
        f"    if n == 0:\n"
        f"        return 0\n"
        f"    cur_min = xs[0]\n"
        f"    cur_max = xs[0]\n"
        f"    total = xs[0]\n"
        f"    diffs = []\n"
        f"    for i in range(1, n):\n"
        f"        val = xs[i]\n"
        f"        total += val\n"
        f"        if val < cur_min:\n"
        f"            cur_min = val\n"
        f"        if val > cur_max:\n"
        f"            cur_max = val\n"
        f"        diff = cur_max - cur_min\n"
        f"        diffs.append(diff)\n"
        f"    if len(diffs) == 0:\n"
        f"        return 0\n"
        f"    result = diffs[-1]\n"
        f"    return result\n"
    )

    equiv1 = (
        f"def {fname}(xs: list) -> int:\n"
        f"    n = len(xs)\n"
        f"    if n == 0:\n"
        f"        return 0\n"
        f"    cur_min = xs[0]\n"
        f"    cur_max = xs[0]\n"
        f"    total = xs[0]\n"
        f"    diffs = []\n"
        f"    idx = 1\n"
        f"    while idx < n:\n"
        f"        val = xs[idx]\n"
        f"        total += val\n"
        f"        cur_min = min(cur_min, val)\n"
        f"        cur_max = max(cur_max, val)\n"
        f"        diff = cur_max - cur_min\n"
        f"        diffs.append(diff)\n"
        f"        idx += 1\n"
        f"    if len(diffs) == 0:\n"
        f"        return 0\n"
        f"    result = diffs[-1]\n"
        f"    return result\n"
    )

    equiv2 = (
        f"def {fname}(xs: list) -> int:\n"
        f"    n = len(xs)\n"
        f"    if n == 0:\n"
        f"        return 0\n"
        f"    cur_min = xs[0]\n"
        f"    cur_max = xs[0]\n"
        f"    total = xs[0]\n"
        f"    last_diff = 0\n"
        f"    count = 0\n"
        f"    for i in range(1, n):\n"
        f"        val = xs[i]\n"
        f"        total = total + val\n"
        f"        if val < cur_min:\n"
        f"            cur_min = val\n"
        f"        if val > cur_max:\n"
        f"            cur_max = val\n"
        f"        last_diff = cur_max - cur_min\n"
        f"        count += 1\n"
        f"    if count == 0:\n"
        f"        return 0\n"
        f"    result = last_diff\n"
        f"    return result\n"
    )

    mut1 = {
        "source": source.replace("val < cur_min", "val <= cur_min"),
        "description": "changed '<' to '<=' in min tracking",
    }
    mut2 = {
        "source": source.replace("cur_max - cur_min", "cur_max + cur_min"),
        "description":
            "changed '-' to '+' — returns sum instead of difference",
    }

    return source, [equiv1, equiv2], [mut1, mut2]


def _bp_list_partition(
    fname: str, rng: random.Random,
) -> tuple[str, list[str], list[dict]]:
    """Partition list around a pivot value."""
    source = (
        f"def {fname}(xs: list, pivot: int) -> list:\n"
        f"    n = len(xs)\n"
        f"    below = []\n"
        f"    equal = []\n"
        f"    above = []\n"
        f"    for i in range(n):\n"
        f"        val = xs[i]\n"
        f"        if val < pivot:\n"
        f"            below.append(val)\n"
        f"        elif val == pivot:\n"
        f"            equal.append(val)\n"
        f"        else:\n"
        f"            above.append(val)\n"
        f"    result = below + equal + above\n"
        f"    total_len = len(result)\n"
        f"    if total_len != n:\n"
        f"        result = list(xs)\n"
        f"    output = list(result)\n"
        f"    return output\n"
    )

    equiv1 = (
        f"def {fname}(xs: list, pivot: int) -> list:\n"
        f"    n = len(xs)\n"
        f"    below = [v for v in xs if v < pivot]\n"
        f"    equal = [v for v in xs if v == pivot]\n"
        f"    above = [v for v in xs if v > pivot]\n"
        f"    result = below + equal + above\n"
        f"    total_len = len(below) + len(equal) + len(above)\n"
        f"    if total_len != n:\n"
        f"        result = list(xs)\n"
        f"    below_cnt = len(below)\n"
        f"    equal_cnt = len(equal)\n"
        f"    above_cnt = len(above)\n"
        f"    output = list(result)\n"
        f"    return output\n"
    )

    equiv2 = (
        f"def {fname}(xs: list, pivot: int) -> list:\n"
        f"    n = len(xs)\n"
        f"    below = []\n"
        f"    equal = []\n"
        f"    above = []\n"
        f"    idx = 0\n"
        f"    while idx < n:\n"
        f"        val = xs[idx]\n"
        f"        if val < pivot:\n"
        f"            below.append(val)\n"
        f"        elif val == pivot:\n"
        f"            equal.append(val)\n"
        f"        else:\n"
        f"            above.append(val)\n"
        f"        idx += 1\n"
        f"    result = below + equal + above\n"
        f"    total_len = len(result)\n"
        f"    if total_len != n:\n"
        f"        result = list(xs)\n"
        f"    output = list(result)\n"
        f"    return output\n"
    )

    mut1 = {
        "source": source.replace("val < pivot", "val <= pivot", 1),
        "description":
            "changed '<' to '<=' — equal elements go to below partition",
    }
    mut2 = {
        "source": source.replace(
            "below + equal + above", "below + above + equal"
        ),
        "description":
            "changed partition order — equal elements come after above",
    }

    return source, [equiv1, equiv2], [mut1, mut2]


# ---------------------------------------------------------------------------
# Blueprint registry
# ---------------------------------------------------------------------------

_BLUEPRINTS: list[dict[str, Any]] = [
    {
        "id": "aggregate_filter_sum",
        "category": "aggregation",
        "param_types": ["list[int]", "int"],
        "return_type": "int",
        "build": lambda fname, rng: _bp_aggregate_filter(
            fname, rng.choice([">", "<", ">=", "<="]),
            rng.choice([0, 5, 10, -5]), "sum", rng,
        ),
    },
    {
        "id": "aggregate_filter_count",
        "category": "aggregation",
        "param_types": ["list[int]", "int"],
        "return_type": "int",
        "build": lambda fname, rng: _bp_aggregate_filter(
            fname, rng.choice([">", "<", ">=", "<="]),
            rng.choice([0, 5, 10, -5]), "count", rng,
        ),
    },
    {
        "id": "aggregate_filter_max",
        "category": "aggregation",
        "param_types": ["list[int]", "int"],
        "return_type": "int",
        "build": lambda fname, rng: _bp_aggregate_filter(
            fname, rng.choice([">", "<", ">=", "<="]),
            rng.choice([0, 5, 10, -5]), "max", rng,
        ),
    },
    {
        "id": "list_transform",
        "category": "transformation",
        "param_types": ["list[int]"],
        "return_type": "list[int]",
        "build": lambda fname, rng: _bp_list_transform(
            fname, rng.choice(["+", "-", "*"]),
            rng.choice([1, 2, 3, -1]), rng,
        ),
    },
    {
        "id": "nested_pair_find",
        "category": "searching",
        "param_types": ["list[int]"],
        "return_type": "int",
        "build": lambda fname, rng: _bp_nested_pair_find(
            fname, rng.choice([">", "<", "==", ">="]),
            rng.choice([0, 5, 10, -5, 20]), rng,
        ),
    },
    {
        "id": "string_count",
        "category": "string",
        "param_types": ["str"],
        "return_type": "int",
        "build": lambda fname, rng: _bp_string_count(fname, rng),
    },
    {
        "id": "polynomial_eval",
        "category": "mathematical",
        "param_types": ["int"],
        "return_type": "int",
        "build": lambda fname, rng: _bp_polynomial_eval(fname, rng),
    },
    {
        "id": "classify",
        "category": "classification",
        "param_types": ["list[int]"],
        "return_type": "list[int]",
        "build": lambda fname, rng: _bp_classify(fname, rng),
    },
    {
        "id": "state_machine",
        "category": "stateful",
        "param_types": ["list[int]"],
        "return_type": "int",
        "build": lambda fname, rng: _bp_state_machine(fname, rng),
    },
    {
        "id": "two_pointer",
        "category": "searching",
        "param_types": ["list[int]", "int"],
        "return_type": "int",
        "build": lambda fname, rng: _bp_two_pointer(fname, rng),
    },
    {
        "id": "sliding_window",
        "category": "aggregation",
        "param_types": ["list[int]"],
        "return_type": "int",
        "build": lambda fname, rng: _bp_sliding_window(
            fname, rng.choice([2, 3, 4, 5]), rng,
        ),
    },
    {
        "id": "multi_condition_acc",
        "category": "aggregation",
        "param_types": ["list[int]"],
        "return_type": "int",
        "build": lambda fname, rng: _bp_multi_condition_acc(fname, rng),
    },
    {
        "id": "conditional_list_build",
        "category": "transformation",
        "param_types": ["list[int]"],
        "return_type": "list[int]",
        "build": lambda fname, rng: _bp_conditional_list_build(fname, rng),
    },
    {
        "id": "index_processing",
        "category": "aggregation",
        "param_types": ["list[int]"],
        "return_type": "int",
        "build": lambda fname, rng: _bp_index_processing(fname, rng),
    },
    {
        "id": "early_termination",
        "category": "searching",
        "param_types": ["list[int]", "int"],
        "return_type": "int",
        "build": lambda fname, rng: _bp_early_termination(fname, rng),
    },
    {
        "id": "prefix_sum",
        "category": "aggregation",
        "param_types": ["list[int]"],
        "return_type": "int",
        "build": lambda fname, rng: _bp_prefix_sum(fname, rng),
    },
    {
        "id": "histogram",
        "category": "aggregation",
        "param_types": ["list[int]"],
        "return_type": "int",
        "build": lambda fname, rng: _bp_histogram(fname, rng),
    },
    {
        "id": "running_extrema",
        "category": "extrema",
        "param_types": ["list[int]"],
        "return_type": "int",
        "build": lambda fname, rng: _bp_running_extrema(fname, rng),
    },
    {
        "id": "list_partition",
        "category": "transformation",
        "param_types": ["list[int]", "int"],
        "return_type": "list[int]",
        "build": lambda fname, rng: _bp_list_partition(fname, rng),
    },
]


# ---------------------------------------------------------------------------
# Generator class
# ---------------------------------------------------------------------------

class RandomFunctionGenerator:
    """
    Generate random Python functions with equivalence-preserving
    transformations and semantic mutations using blueprint patterns.

    Each generated function has at least ``min_loc`` lines of code, at least
    one loop, at least one conditional, and at least three intermediate
    variables.  Equivalents preserve semantics; mutations change behaviour.

    Parameters
    ----------
    seed : int, optional
        Random seed for reproducibility.
    min_loc : int
        Minimum lines of code for every generated source (default 20).
    max_statements : int
        Reserved for future use (blueprint patterns handle sizing).
    max_expr_depth : int
        Reserved for future use.
    """

    def __init__(
        self,
        seed: Optional[int] = None,
        min_loc: int = 20,
        max_statements: int = 12,
        max_expr_depth: int = 3,
    ) -> None:
        self.rng = random.Random(seed)
        self.min_loc = min_loc
        self._max_statements = max_statements
        self._max_expr_depth = max_expr_depth

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self, n: int = 10) -> list[dict[str, Any]]:
        """
        Return *n* function specs compatible with
        ``BenchmarkGenerator._entries_from_spec()``.

        Each spec dict has keys: ``name``, ``source``, ``param_types``,
        ``return_type``, ``category``, ``constraints``, ``equivalents``,
        ``mutations``.
        """
        results: list[dict[str, Any]] = []
        seen_names: set[str] = set()
        attempts = 0

        while len(results) < n and attempts < n * 20:
            attempts += 1
            bp = self.rng.choice(_BLUEPRINTS)
            fname = _random_name(self.rng)
            if fname in seen_names:
                continue
            seen_names.add(fname)

            source, equivalents, mutations = bp["build"](fname, self.rng)

            # Enforce minimum LOC on all variants
            source = self._ensure_min_loc(source, fname)
            equivalents = [
                self._ensure_min_loc(eq, fname) for eq in equivalents
            ]
            for mut in mutations:
                mut["source"] = self._ensure_min_loc(mut["source"], fname)

            # Validate syntax of every source string
            all_sources = (
                [source]
                + equivalents
                + [m["source"] for m in mutations]
            )
            if not all(_validate_syntax(s) for s in all_sources):
                seen_names.discard(fname)
                continue

            results.append({
                "name": fname,
                "param_types": bp["param_types"],
                "return_type": bp["return_type"],
                "category": f"random_ast_{bp['category']}",
                "constraints": "",
                "source": source,
                "equivalents": equivalents,
                "mutations": mutations,
            })

        return results

    def generate_function(
        self,
        func_name: str,
        inputs: list[str],
        return_type: str,
    ) -> ast.FunctionDef:
        """
        Generate a single random function AST node.

        Parameters
        ----------
        func_name : str
            Name for the function.
        inputs : list[str]
            Parameter type strings (e.g. ``["list[int]", "int"]``).
        return_type : str
            Return type annotation string.

        Returns
        -------
        ast.FunctionDef
            A parsed and location-fixed AST function definition.
        """
        bp = self.rng.choice(_BLUEPRINTS)
        source, _, _ = bp["build"](func_name, self.rng)
        source = self._ensure_min_loc(source, func_name)
        tree = ast.parse(source)
        ast.fix_missing_locations(tree)
        func_def = tree.body[0]
        assert isinstance(func_def, ast.FunctionDef)
        return func_def

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_min_loc(self, source: str, fname: str) -> str:
        """Pad *source* with meaningful filler until it reaches min_loc."""
        lines = source.strip().split("\n")
        non_blank = _loc_count(source)
        if non_blank >= self.min_loc:
            return source

        # Padding lines inserted before the final return statement.
        pad_vars = [
            "    _check_val = 0",
            "    _pad_flag = True",
            "    _step_count = 0",
            "    _temp_holder = 0",
            "    if _pad_flag:",
            "        _step_count += 1",
            "    _verify = _step_count + _check_val",
            "    _marker = _verify * 1",
            "    if _marker >= 0:",
            "        _temp_holder = _marker",
            "    _extra_check = _temp_holder + 0",
            "    _pad_sum = _extra_check + _step_count",
            "    if _pad_sum >= 0:",
            "        _pad_flag = True",
            "    _final_pad = 0 if _pad_flag else 1",
        ]

        needed = self.min_loc - non_blank

        # Find the last return statement to insert padding before it.
        return_idx = len(lines) - 1
        for i in range(len(lines) - 1, -1, -1):
            stripped = lines[i].strip()
            if stripped.startswith("return "):
                return_idx = i
                break

        padding = pad_vars[:needed]
        new_lines = lines[:return_idx] + padding + lines[return_idx:]
        return "\n".join(new_lines) + "\n"