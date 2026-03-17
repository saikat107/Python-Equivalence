#!/usr/bin/env python3
"""
equivalence_checker.py — Check if two Python functions are equivalent.

Given two Python functions (in one or two source files), this script:
  1. Parses both functions' type annotations via the AST.
  2. Verifies their signatures are compatible (same param types & return type).
  3. Generates random inputs and executes both functions on them.
  4. Continues fuzzing with unique inputs up to the given time limit.
  5. Reports whether a counterexample was found or the functions appear equivalent.

Supports arbitrarily complex nested type annotations such as
``dict[str, list[tuple[str, str, bool]]]``.

Usage
-----
    # Both functions in the same file:
    python src/fuzzer/equivalence_checker.py funcs.py func_a func_b

    # Functions in different files:
    python src/fuzzer/equivalence_checker.py file1.py func_a --file2 file2.py func_b

Options
-------
    --time-limit SECS   Maximum fuzzing time in seconds (default: 30)
    --num-inputs N       Maximum number of unique inputs (default: 1000)
    --seed S             Random seed for reproducibility
    --timeout SECS       Per-call timeout (default: 5)

Security note
-------------
This script executes arbitrary Python code from the provided files.
Only use with trusted source files.
"""

from __future__ import annotations

import argparse
import os
import sys
import threading
import time
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Make the package importable when run from the repo root
# ---------------------------------------------------------------------------
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_SRC_DIR = os.path.dirname(_THIS_DIR)
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from fuzzer.type_parser import (
    FunctionSignature,
    TypeNode,
    extract_function_signature,
    list_functions,
)
from fuzzer.value_generator import ValueGenerator


# ---------------------------------------------------------------------------
# Safe execution helper
# ---------------------------------------------------------------------------

def _run_with_timeout(
    fn: Any, args: tuple, timeout: float = 5.0
) -> tuple[Any, Optional[str]]:
    """Execute *fn(*args)* with a per-call timeout using a daemon thread."""
    result: list[Any] = [None, None]

    def _target() -> None:
        try:
            result[0] = fn(*args)
        except Exception as exc:
            result[1] = f"{type(exc).__name__}: {exc}"

    t = threading.Thread(target=_target, daemon=True)
    t.start()
    t.join(timeout)
    if t.is_alive():
        return None, f"TimeoutError: exceeded {timeout}s"
    return result[0], result[1]


# ---------------------------------------------------------------------------
# Signature compatibility check
# ---------------------------------------------------------------------------

def signatures_compatible(
    sig1: FunctionSignature, sig2: FunctionSignature
) -> tuple[bool, str]:
    """Check whether two function signatures are type-compatible.

    Returns (compatible, reason_string).
    """
    types1 = sig1.param_types()
    types2 = sig2.param_types()

    if len(types1) != len(types2):
        return False, (
            f"Parameter count mismatch: "
            f"{sig1.name} has {len(types1)}, {sig2.name} has {len(types2)}"
        )

    for i, (t1, t2) in enumerate(zip(types1, types2)):
        if t1 != t2:
            return False, (
                f"Parameter {i} type mismatch: "
                f"{sig1.name} has {t1!r}, {sig2.name} has {t2!r}"
            )

    if sig1.return_type is not None and sig2.return_type is not None:
        if sig1.return_type != sig2.return_type:
            return False, (
                f"Return type mismatch: "
                f"{sig1.name} returns {sig1.return_type!r}, "
                f"{sig2.name} returns {sig2.return_type!r}"
            )

    return True, "Signatures are compatible"


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def check_equivalence(
    source1: str,
    func_name1: str,
    source2: str,
    func_name2: str,
    num_inputs: int = 1000,
    time_limit: float = 30.0,
    seed: int | None = None,
    per_call_timeout: float = 5.0,
    coverage_guided: bool = False,
) -> dict:
    """Check whether two functions are equivalent via fuzzing.

    Parameters
    ----------
    source1, func_name1 : first function source and name.
    source2, func_name2 : second function source and name.
    num_inputs : maximum number of unique inputs to test.
    time_limit : maximum wall-clock seconds to spend fuzzing.
    seed : optional random seed for reproducibility.
    per_call_timeout : per-call timeout in seconds.
    coverage_guided : when ``True``, use :class:`~equivalence_benchmarks.whitebox.CoverageTracker`
        to measure coverage of both functions and prefer inputs that reach
        new lines or branches in either.  AST-derived hints from both sources
        are merged to bias value generation toward boundary values.

    Returns a dict with:
      - ``equivalent``: True / False / None (if inconclusive)
      - ``inputs_tested``: number of unique inputs tested
      - ``counterexample``: the first input where outputs differ (or None)
      - ``time_elapsed``: wall-clock seconds spent
      - ``errors``: number of inputs that caused errors
      - ``compatible``: whether signatures matched
      - ``reason``: explanation string
      - ``coverage_lines``: lines covered (only when *coverage_guided* is True)
      - ``coverage_branches``: branches covered (only when *coverage_guided* is True)
    """
    sig1 = extract_function_signature(source1, func_name1)
    sig2 = extract_function_signature(source2, func_name2)

    compatible, reason = signatures_compatible(sig1, sig2)
    if not compatible:
        return {
            "equivalent": None,
            "inputs_tested": 0,
            "counterexample": None,
            "time_elapsed": 0.0,
            "errors": 0,
            "compatible": False,
            "reason": reason,
        }

    # Compile both functions
    ns1: dict[str, Any] = {}
    exec(compile(source1, "<func1>", "exec"), ns1)  # noqa: S102
    fn1 = ns1.get(func_name1)
    if fn1 is None:
        raise RuntimeError(f"Function '{func_name1}' not found after compilation")

    ns2: dict[str, Any] = {}
    exec(compile(source2, "<func2>", "exec"), ns2)  # noqa: S102
    fn2 = ns2.get(func_name2)
    if fn2 is None:
        raise RuntimeError(f"Function '{func_name2}' not found after compilation")

    param_types = sig1.param_types()

    if coverage_guided:
        return _check_equivalence_coverage_guided(
            source1=source1,
            func_name1=func_name1,
            fn1=fn1,
            source2=source2,
            func_name2=func_name2,
            fn2=fn2,
            param_types=param_types,
            num_inputs=num_inputs,
            time_limit=time_limit,
            seed=seed,
            per_call_timeout=per_call_timeout,
        )

    gen = ValueGenerator(seed=seed)

    seen_keys: set[str] = set()
    tested = 0
    error_count = 0
    start = time.monotonic()

    while tested < num_inputs and (time.monotonic() - start) < time_limit:
        inp = tuple(gen.generate(t) for t in param_types)
        key = repr(inp)
        if key in seen_keys:
            continue
        seen_keys.add(key)

        r1, e1 = _run_with_timeout(fn1, inp, per_call_timeout)
        r2, e2 = _run_with_timeout(fn2, inp, per_call_timeout)
        tested += 1

        if e1 is not None or e2 is not None:
            error_count += 1
            # If one errors and the other doesn't, they differ
            if (e1 is None) != (e2 is None):
                elapsed = time.monotonic() - start
                return {
                    "equivalent": False,
                    "inputs_tested": tested,
                    "counterexample": {
                        "input": inp,
                        "output1": r1,
                        "error1": e1,
                        "output2": r2,
                        "error2": e2,
                    },
                    "time_elapsed": round(elapsed, 2),
                    "errors": error_count,
                    "compatible": True,
                    "reason": (
                        f"Counterexample found: one function errored "
                        f"while the other did not"
                    ),
                }
            continue

        if r1 != r2:
            elapsed = time.monotonic() - start
            return {
                "equivalent": False,
                "inputs_tested": tested,
                "counterexample": {
                    "input": inp,
                    "output1": r1,
                    "error1": None,
                    "output2": r2,
                    "error2": None,
                },
                "time_elapsed": round(elapsed, 2),
                "errors": error_count,
                "compatible": True,
                "reason": (
                    f"Counterexample found: "
                    f"{func_name1} returned {r1!r}, "
                    f"{func_name2} returned {r2!r}"
                ),
            }

    elapsed = time.monotonic() - start
    return {
        "equivalent": True,
        "inputs_tested": tested,
        "counterexample": None,
        "time_elapsed": round(elapsed, 2),
        "errors": error_count,
        "compatible": True,
        "reason": (
            f"No counterexample found after {tested} unique inputs "
            f"in {elapsed:.1f}s"
        ),
    }


def _check_equivalence_coverage_guided(
    *,
    source1: str,
    func_name1: str,
    fn1: Any,
    source2: str,
    func_name2: str,
    fn2: Any,
    param_types: list[TypeNode],
    num_inputs: int,
    time_limit: float,
    seed: int | None,
    per_call_timeout: float,
) -> dict:
    """Coverage-guided equivalence check.

    Tracks coverage for both functions independently; inputs that increase
    coverage in either function are added to a mutation corpus (AFL-style).
    AST hints from both sources are merged to bias value generation.
    """
    try:
        from equivalence_benchmarks.whitebox import CoverageTracker, analyse_source
    except ImportError as exc:
        raise ImportError(
            "Coverage-guided fuzzing requires the equivalence_benchmarks package. "
            "Ensure the src/ directory is on PYTHONPATH."
        ) from exc

    # Merge AST hints from both sources
    hints1 = analyse_source(source1)
    hints2 = analyse_source(source2)
    # Produce a merged hints object by combining constant pools
    from equivalence_benchmarks.whitebox import ASTHints
    merged = ASTHints()
    merged.int_constants = hints1.int_constants | hints2.int_constants
    merged.float_constants = hints1.float_constants | hints2.float_constants
    merged.str_constants = hints1.str_constants | hints2.str_constants
    merged.bool_constants = hints1.bool_constants | hints2.bool_constants
    merged.branch_count = hints1.branch_count + hints2.branch_count
    merged.comparison_ops = hints1.comparison_ops + hints2.comparison_ops

    gen = ValueGenerator(seed=seed, hints=merged)
    tracker1 = CoverageTracker()
    tracker2 = CoverageTracker()
    corpus: list[tuple] = []
    seen_keys: set[str] = set()
    tested = 0
    error_count = 0
    prev_lines = 0
    prev_branches = 0
    start = time.monotonic()

    while tested < num_inputs and (time.monotonic() - start) < time_limit:
        if corpus and gen._rng.random() < 0.4:
            seed_inp = gen._rng.choice(corpus)
            inp = gen.mutate(seed_inp, param_types)
        else:
            inp = tuple(gen.generate(t) for t in param_types)

        key = repr(inp)
        if key in seen_keys:
            continue
        seen_keys.add(key)

        r1, e1 = tracker1.run(fn1, inp, timeout=per_call_timeout, filename="<func1>")
        r2, e2 = tracker2.run(fn2, inp, timeout=per_call_timeout, filename="<func2>")
        tested += 1

        # Check whether this input increased combined coverage
        cur_lines = tracker1.lines_covered_count + tracker2.lines_covered_count
        cur_branches = (
            tracker1.branches_covered_count + tracker2.branches_covered_count
        )
        if cur_lines > prev_lines or cur_branches > prev_branches:
            corpus.append(inp)
            prev_lines = cur_lines
            prev_branches = cur_branches

        if e1 is not None or e2 is not None:
            error_count += 1
            if (e1 is None) != (e2 is None):
                elapsed = time.monotonic() - start
                return {
                    "equivalent": False,
                    "inputs_tested": tested,
                    "counterexample": {
                        "input": inp,
                        "output1": r1,
                        "error1": e1,
                        "output2": r2,
                        "error2": e2,
                    },
                    "time_elapsed": round(elapsed, 2),
                    "errors": error_count,
                    "compatible": True,
                    "reason": (
                        "Counterexample found: one function errored "
                        "while the other did not"
                    ),
                    "coverage_lines": cur_lines,
                    "coverage_branches": cur_branches,
                }
            continue

        if r1 != r2:
            elapsed = time.monotonic() - start
            return {
                "equivalent": False,
                "inputs_tested": tested,
                "counterexample": {
                    "input": inp,
                    "output1": r1,
                    "error1": None,
                    "output2": r2,
                    "error2": None,
                },
                "time_elapsed": round(elapsed, 2),
                "errors": error_count,
                "compatible": True,
                "reason": (
                    f"Counterexample found: "
                    f"{func_name1} returned {r1!r}, "
                    f"{func_name2} returned {r2!r}"
                ),
                "coverage_lines": cur_lines,
                "coverage_branches": cur_branches,
            }

    elapsed = time.monotonic() - start
    final_lines = tracker1.lines_covered_count + tracker2.lines_covered_count
    final_branches = (
        tracker1.branches_covered_count + tracker2.branches_covered_count
    )
    return {
        "equivalent": True,
        "inputs_tested": tested,
        "counterexample": None,
        "time_elapsed": round(elapsed, 2),
        "errors": error_count,
        "compatible": True,
        "reason": (
            f"No counterexample found after {tested} unique inputs "
            f"in {elapsed:.1f}s"
        ),
        "coverage_lines": final_lines,
        "coverage_branches": final_branches,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check equivalence of two Python functions via random fuzzing.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "file1",
        help="Path to the Python source file containing the first function",
    )
    parser.add_argument(
        "func1",
        help="Name of the first function",
    )
    parser.add_argument(
        "func2",
        help="Name of the second function (in --file2, or in file1 if --file2 is omitted)",
    )
    parser.add_argument(
        "--file2",
        default=None,
        metavar="FILE",
        help="Path to the source file for the second function (default: same as file1)",
    )
    parser.add_argument(
        "--time-limit",
        type=float,
        default=3600.0,
        metavar="SECS",
        help="Maximum fuzzing time in seconds (default: 30)",
    )
    parser.add_argument(
        "--num-inputs",
        type=int,
        default=100000,
        metavar="N",
        help="Maximum number of unique inputs to test (default: 1000)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        metavar="S",
        help="Random seed for reproducibility",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        metavar="SECS",
        help="Per-call timeout in seconds (default: 5)",
    )
    parser.add_argument(
        "--coverage-guided",
        action="store_true",
        default=False,
        help=(
            "Use coverage-guided generation: track line/branch coverage of "
            "both functions and bias inputs toward unexplored code paths using "
            "AST-derived hints merged from both sources. "
            "Requires the equivalence_benchmarks package on PYTHONPATH."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    """Entry point for the equivalence_checker CLI."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    # Read source files
    if not os.path.isfile(args.file1):
        parser.error(f"File not found: {args.file1}")

    with open(args.file1, encoding="utf-8") as fh:
        source1 = fh.read()

    if args.file2 is not None:
        if not os.path.isfile(args.file2):
            parser.error(f"File not found: {args.file2}")
        with open(args.file2, encoding="utf-8") as fh:
            source2 = fh.read()
    else:
        source2 = source1

    # Validate functions exist
    funcs1 = list_functions(source1)
    if args.func1 not in funcs1:
        parser.error(
            f"Function '{args.func1}' not found in {args.file1}. "
            f"Available: {', '.join(funcs1) or '(none)'}"
        )

    file2_label = args.file2 or args.file1
    funcs2 = list_functions(source2)
    if args.func2 not in funcs2:
        parser.error(
            f"Function '{args.func2}' not found in {file2_label}. "
            f"Available: {', '.join(funcs2) or '(none)'}"
        )

    # Extract and display signatures
    sig1 = extract_function_signature(source1, args.func1)
    sig2 = extract_function_signature(source2, args.func2)

    def _sig_str(sig: FunctionSignature) -> str:
        params = ", ".join(f"{n}: {t}" for n, t in sig.params)
        ret = f" -> {sig.return_type}" if sig.return_type else ""
        return f"{sig.name}({params}){ret}"

    print(f"Function 1: {_sig_str(sig1)}")
    print(f"Function 2: {_sig_str(sig2)}")

    # Check compatibility
    compatible, reason = signatures_compatible(sig1, sig2)
    if not compatible:
        print(f"\n✗ Signatures are NOT compatible: {reason}")
        sys.exit(1)

    mode = "coverage-guided" if args.coverage_guided else "random"
    print(f"\n✓ Signatures are compatible")
    print(
        f"Mode: {mode} | Up to {args.num_inputs} inputs "
        f"(time limit: {args.time_limit}s, seed: {args.seed})\n"
    )

    result = check_equivalence(
        source1=source1,
        func_name1=args.func1,
        source2=source2,
        func_name2=args.func2,
        num_inputs=args.num_inputs,
        time_limit=args.time_limit,
        seed=args.seed,
        per_call_timeout=args.timeout,
        coverage_guided=args.coverage_guided,
    )

    print(f"Tested {result['inputs_tested']} unique inputs in {result['time_elapsed']}s")
    if result["errors"]:
        print(f"  ({result['errors']} inputs caused errors)")
    if "coverage_lines" in result:
        print(
            f"  Coverage: {result['coverage_lines']} lines, "
            f"{result['coverage_branches']} branches"
        )

    if result["equivalent"] is True:
        print(f"\n✓ Functions appear EQUIVALENT")
        print(f"  {result['reason']}")
    elif result["equivalent"] is False:
        print(f"\n✗ Functions are NOT EQUIVALENT")
        cx = result["counterexample"]
        inp_str = ", ".join(repr(v) for v in cx["input"])
        print(f"  Counterexample input: ({inp_str})")
        if cx["error1"] is not None:
            print(f"  {args.func1}: ERROR: {cx['error1']}")
        else:
            print(f"  {args.func1} returned: {cx['output1']!r}")
        if cx["error2"] is not None:
            print(f"  {args.func2}: ERROR: {cx['error2']}")
        else:
            print(f"  {args.func2} returned: {cx['output2']!r}")
        sys.exit(1)
    else:
        print(f"\n? Inconclusive: {result['reason']}")
        sys.exit(2)


if __name__ == "__main__":
    main()
