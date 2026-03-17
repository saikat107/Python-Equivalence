#!/usr/bin/env python3
"""
fuzz_function.py — Fuzz a Python function with random type-aware inputs.

Given a Python source file and function name, this script:
  1. Parses the function's type annotations via the AST.
  2. Generates diverse random inputs matching those types.
  3. Executes the function on each input (with timeout protection).
  4. Prints every (input → output) pair.

Supports arbitrarily complex nested type annotations such as
``dict[str, list[tuple[str, str, bool]]]``, as long as the function
parameters and return type are annotated.

Usage
-----
    python src/fuzzer/fuzz_function.py <file.py> <function_name> [options]

Examples
--------
    python src/fuzzer/fuzz_function.py examples/funcs.py sum_list
    python src/fuzzer/fuzz_function.py examples/funcs.py sum_list --num-inputs 50
    python src/fuzzer/fuzz_function.py examples/funcs.py sum_list --seed 42

Security note
-------------
This script executes arbitrary Python code from the provided file.
Only use with trusted source files.
"""

from __future__ import annotations

import argparse
import os
import sys
import threading
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
    result: list[Any] = [None, None]  # [return_value, error_string]

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
# Core logic
# ---------------------------------------------------------------------------

def _fuzz_coverage_guided_with_stats(
    source: str,
    func_name: str,
    num_inputs: int,
    seed: int | None,
    per_call_timeout: float,
) -> tuple[list[dict], dict]:
    """Coverage-guided fuzzing variant.

    Uses :class:`~equivalence_benchmarks.whitebox.CoverageTracker` to
    measure line and branch coverage and :func:`~equivalence_benchmarks.whitebox.analyse_source`
    to extract boundary-value hints from the target source.  Inputs that
    increase coverage are added to a corpus; subsequent inputs are generated
    either as mutations of corpus entries (40 %) or as fresh random values
    (60 %).

    Returns ``(results, stats)`` where *stats* is a dict containing
    ``lines_covered``, ``branches_covered``, and ``corpus_size``.
    """
    try:
        from equivalence_benchmarks.whitebox import CoverageTracker, analyse_source
    except ImportError as exc:
        raise ImportError(
            "Coverage-guided fuzzing requires the equivalence_benchmarks package. "
            "Ensure the src/ directory is on PYTHONPATH."
        ) from exc

    hints = analyse_source(source)
    sig = extract_function_signature(source, func_name)
    param_types = sig.param_types()

    gen = ValueGenerator(seed=seed, hints=hints)

    compile_filename = "<fuzz_target>"
    namespace: dict[str, Any] = {}
    exec(compile(source, compile_filename, "exec"), namespace)  # noqa: S102
    fn = namespace.get(func_name)
    if fn is None:
        raise RuntimeError(f"Function '{func_name}' not found after compilation")

    tracker = CoverageTracker()
    corpus: list[tuple] = []
    seen_keys: set[str] = set()
    results: list[dict] = []
    prev_lines = 0
    prev_branches = 0

    while len(results) < num_inputs:
        if corpus and gen._rng.random() < 0.4:
            seed_inp = gen._rng.choice(corpus)
            inp = gen.mutate(seed_inp, param_types)
        else:
            inp = tuple(gen.generate(t) for t in param_types)

        key = repr(inp)
        if key in seen_keys:
            continue
        seen_keys.add(key)

        output, error = tracker.run(
            fn, inp, timeout=per_call_timeout, filename=compile_filename
        )
        results.append({"input": inp, "output": output, "error": error})

        cur_lines = tracker.lines_covered_count
        cur_branches = tracker.branches_covered_count
        if cur_lines > prev_lines or cur_branches > prev_branches:
            corpus.append(inp)
            prev_lines = cur_lines
            prev_branches = cur_branches

    stats = {
        "lines_covered": tracker.lines_covered_count,
        "branches_covered": tracker.branches_covered_count,
        "corpus_size": len(corpus),
    }
    return results, stats


def fuzz_function(
    source: str,
    func_name: str,
    num_inputs: int = 100,
    seed: int | None = None,
    per_call_timeout: float = 5.0,
    coverage_guided: bool = False,
) -> list[dict]:
    """Fuzz *func_name* defined in *source* with random inputs.

    Parameters
    ----------
    source : Python source code containing the function to fuzz.
    func_name : name of the function to fuzz.
    num_inputs : number of unique inputs to generate.
    seed : optional random seed for reproducibility.
    per_call_timeout : per-call timeout in seconds.
    coverage_guided : when ``True``, use coverage tracking and AST-derived
        boundary-value hints to bias generation toward unexplored code paths.
        Requires the ``equivalence_benchmarks`` package on ``PYTHONPATH``.

    Returns a list of dicts, each containing:
      - ``input``: the input tuple
      - ``output``: the return value (or ``None`` on error)
      - ``error``: error string (or ``None`` on success)
    """
    if coverage_guided:
        results, _ = _fuzz_coverage_guided_with_stats(
            source, func_name, num_inputs, seed, per_call_timeout
        )
        return results
    sig = extract_function_signature(source, func_name)
    param_types = sig.param_types()

    gen = ValueGenerator(seed=seed)
    inputs = gen.generate_inputs(param_types, n=num_inputs)

    # Compile the source and extract the function object
    namespace: dict[str, Any] = {}
    exec(compile(source, "<fuzz_target>", "exec"), namespace)  # noqa: S102
    fn = namespace.get(func_name)
    if fn is None:
        raise RuntimeError(f"Function '{func_name}' not found after compilation")

    results: list[dict] = []
    for inp in inputs:
        output, error = _run_with_timeout(fn, inp, per_call_timeout)
        results.append({"input": inp, "output": output, "error": error})

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fuzz a Python function with random type-aware inputs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "file",
        help="Path to the Python source file containing the function",
    )
    parser.add_argument(
        "function",
        help="Name of the function to fuzz",
    )
    parser.add_argument(
        "--num-inputs",
        type=int,
        default=100,
        metavar="N",
        help="Number of random inputs to generate (default: 100)",
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
        default=5.0,
        metavar="SECS",
        help="Timeout per function call in seconds (default: 5)",
    )
    parser.add_argument(
        "--coverage-guided",
        action="store_true",
        default=False,
        help=(
            "Use coverage-guided generation: track line/branch coverage and "
            "bias inputs toward unexplored code paths using AST-derived hints. "
            "Requires the equivalence_benchmarks package on PYTHONPATH."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    """Entry point for the fuzz_function CLI."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    filepath = args.file
    if not os.path.isfile(filepath):
        parser.error(f"File not found: {filepath}")

    with open(filepath, encoding="utf-8") as fh:
        source = fh.read()

    # Validate the function exists
    available = list_functions(source)
    if args.function not in available:
        parser.error(
            f"Function '{args.function}' not found in {filepath}. "
            f"Available functions: {', '.join(available) or '(none)'}"
        )

    sig = extract_function_signature(source, args.function)
    param_str = ", ".join(f"{n}: {t}" for n, t in sig.params)
    ret_str = f" -> {sig.return_type}" if sig.return_type else ""

    mode = "coverage-guided" if args.coverage_guided else "random"
    print(f"Fuzzing: {sig.name}({param_str}){ret_str}")
    print(f"Mode: {mode}")
    print(f"Generating {args.num_inputs} inputs (seed={args.seed})\n")

    if args.coverage_guided:
        results, cov_stats = _fuzz_coverage_guided_with_stats(
            source=source,
            func_name=args.function,
            num_inputs=args.num_inputs,
            seed=args.seed,
            per_call_timeout=args.timeout,
        )
    else:
        results = fuzz_function(
            source=source,
            func_name=args.function,
            num_inputs=args.num_inputs,
            seed=args.seed,
            per_call_timeout=args.timeout,
        )
        cov_stats = None

    errors = 0
    for i, r in enumerate(results, 1):
        inp_str = ", ".join(repr(v) for v in r["input"])
        if r["error"] is not None:
            print(f"  [{i:>4}] ({inp_str})  =>  ERROR: {r['error']}")
            errors += 1
        else:
            print(f"  [{i:>4}] ({inp_str})  =>  {r['output']!r}")

    print(f"\nDone: {len(results)} inputs, {errors} errors.")
    if cov_stats is not None:
        print(
            f"Coverage: {cov_stats['lines_covered']} lines, "
            f"{cov_stats['branches_covered']} branches "
            f"({cov_stats['corpus_size']} coverage-increasing inputs found)."
        )


if __name__ == "__main__":
    main()
