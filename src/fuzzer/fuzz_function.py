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

def fuzz_function(
    source: str,
    func_name: str,
    num_inputs: int = 100,
    seed: int | None = None,
    per_call_timeout: float = 5.0,
) -> list[dict]:
    """Fuzz *func_name* defined in *source* with random inputs.

    Returns a list of dicts, each containing:
      - ``input``: the input tuple
      - ``output``: the return value (or ``None`` on error)
      - ``error``: error string (or ``None`` on success)
    """
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

    print(f"Fuzzing: {sig.name}({param_str}){ret_str}")
    print(f"Generating {args.num_inputs} random inputs (seed={args.seed})\n")

    results = fuzz_function(
        source=source,
        func_name=args.function,
        num_inputs=args.num_inputs,
        seed=args.seed,
        per_call_timeout=args.timeout,
    )

    errors = 0
    for i, r in enumerate(results, 1):
        inp_str = ", ".join(repr(v) for v in r["input"])
        if r["error"] is not None:
            print(f"  [{i:>4}] ({inp_str})  =>  ERROR: {r['error']}")
            errors += 1
        else:
            print(f"  [{i:>4}] ({inp_str})  =>  {r['output']!r}")

    print(f"\nDone: {len(results)} inputs, {errors} errors.")


if __name__ == "__main__":
    main()
