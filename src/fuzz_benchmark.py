#!/usr/bin/env python3
"""
fuzz_benchmark.py — fuzz-test a benchmark and evaluate with new test cases.

Given a benchmark JSON file (produced by ``generate_benchmark.py``), this
script loads every entry, fuzzes ``p1_source`` to generate additional test
inputs that are **not** already present in the original test suite, then
evaluates both ``p1_source`` and ``p2_source`` on the newly generated tests.

The evaluation logic mirrors ``evaluate_benchmark.py``: for each new test
input, both functions are executed and compared.

Fuzzing strategy
----------------
1. Load existing ptests/ntests as seeds.
2. Mutate seeds (type-aware mutations for int, str, bool, list[int], list[str]).
3. Run ``p1_source`` on each candidate to confirm it does not crash.
4. Discard candidates that duplicate any existing test input.
5. Collect up to ``--max-tests`` new unique inputs per entry, or stop after
   ``--max-time`` seconds per entry.

Multiple entries are fuzzed in parallel using ``multiprocessing.Pool``.

Usage
-----
    python src/fuzz_benchmark.py benchmark_output/benchmark_20260101_120000.json

Options::

    --max-tests N        Max new tests per entry (default: 20)
    --max-time  SECS     Max wall-clock seconds per entry (default: 3600)
    --workers   N        Number of parallel workers (default: CPU count)
    --per-call-timeout S Timeout per individual function call (default: 5)
    --output    FILE     Write JSON results to FILE (default: stdout summary)
    --verbose            Print per-entry details

**Security note**: This script executes arbitrary Python code from the
benchmark file.  Only evaluate benchmarks from trusted sources.
"""

from __future__ import annotations

import argparse
import json
import multiprocessing
import os
import random
import string
import sys
import threading
import time
from typing import Any, Optional

from tqdm import tqdm

# Make sure the package is importable when run from the repo root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from equivalence_benchmarks.progress import setup_file_logger, log_message


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fuzz a Python equivalence benchmark and evaluate with new tests.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "benchmark",
        metavar="BENCHMARK_JSON",
        help="Path to the benchmark JSON file produced by generate_benchmark.py",
    )
    parser.add_argument(
        "--max-tests",
        type=int,
        default=20,
        metavar="N",
        help="Maximum number of new test cases to generate per entry (default: 20)",
    )
    parser.add_argument(
        "--max-time",
        type=float,
        default=3600.0,
        metavar="SECS",
        help="Maximum wall-clock seconds to spend fuzzing each entry (default: 3600)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        metavar="N",
        help="Number of parallel worker processes (default: CPU count)",
    )
    parser.add_argument(
        "--per-call-timeout",
        type=float,
        default=5.0,
        metavar="SECS",
        help="Timeout in seconds for each individual function call (default: 5)",
    )
    parser.add_argument(
        "--output",
        default=None,
        metavar="FILE",
        help="Write JSON evaluation results to FILE",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-entry evaluation details",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        metavar="N",
        help="Random seed for reproducibility",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Timeout helper (same approach as evaluate_benchmark.py)
# ---------------------------------------------------------------------------

def _run_with_timeout(fn, args, timeout):
    """Run *fn(*args)* with a timeout using a daemon thread."""
    result = [None, None]  # [return_value, error_string]

    def target():
        try:
            result[0] = fn(*args)
        except Exception as exc:
            result[1] = f"{type(exc).__name__}: {exc}"

    t = threading.Thread(target=target, daemon=True)
    t.start()
    t.join(timeout)
    if t.is_alive():
        return None, f"TimeoutError: exceeded {timeout}s"
    return result[0], result[1]


# ---------------------------------------------------------------------------
# Compile helper
# ---------------------------------------------------------------------------

def _compile_function(source: str, func_name: str):
    """Compile *source* via exec and return the function object, or None."""
    namespace: dict = {}
    try:
        exec(compile(source, "<benchmark>", "exec"), namespace)  # noqa: S102
    except Exception as exc:
        return None, f"CompileError: {exc}"
    func = namespace.get(func_name)
    if func is None:
        return None, f"NameError: '{func_name}' not found"
    return func, None


# ---------------------------------------------------------------------------
# Type-aware input mutation
# ---------------------------------------------------------------------------

class InputFuzzer:
    """
    Generate new test inputs by mutating existing seeds.

    Parameters
    ----------
    param_types : list of type-annotation strings, e.g. ["list[int]", "int"]
    seed        : random seed for reproducibility
    """

    def __init__(
        self,
        param_types: list[str],
        seed: Optional[int] = None,
    ) -> None:
        self.param_types = param_types
        self._rng = random.Random(seed)

    def mutate(self, inp: tuple) -> tuple:
        """
        Return a mutated copy of *inp* (a tuple of arguments).

        Each argument is mutated independently according to its type.
        """
        mutated = []
        for value, type_str in zip(inp, self.param_types):
            t = type_str.strip()
            if t == "int":
                mutated.append(self._mutate_int(value))
            elif t == "bool":
                mutated.append(self._mutate_bool(value))
            elif t == "str":
                mutated.append(self._mutate_str(value))
            elif t in ("list[int]", "list"):
                mutated.append(self._mutate_list_int(value))
            elif t == "list[str]":
                mutated.append(self._mutate_list_str(value))
            else:
                # Fallback: treat as int
                mutated.append(self._mutate_int(value))
        return tuple(mutated)

    def random_input(self) -> tuple:
        """Generate a completely random input tuple (no seed needed)."""
        return tuple(self._random_value(t) for t in self.param_types)

    # ------------------------------------------------------------------
    # Int mutations
    # ------------------------------------------------------------------

    def _mutate_int(self, value: int) -> int:
        strategy = self._rng.randint(0, 7)
        if strategy == 0:
            # Add small delta
            return value + self._rng.randint(-10, 10)
        elif strategy == 1:
            # Negate
            return -value
        elif strategy == 2:
            # Boundary values
            return self._rng.choice([0, 1, -1, 2, -2, 10, -10, 100, -100])
        elif strategy == 3:
            # Large random
            return self._rng.randint(-1000, 1000)
        elif strategy == 4:
            # Multiply by small factor
            return value * self._rng.choice([2, 3, -1, -2, 0])
        elif strategy == 5:
            # Bit flip
            bit = self._rng.randint(0, 7)
            return value ^ (1 << bit)
        elif strategy == 6:
            # Add/subtract 1
            return value + self._rng.choice([-1, 1])
        else:
            # Completely random
            return self._rng.randint(-500, 500)

    # ------------------------------------------------------------------
    # Bool mutations
    # ------------------------------------------------------------------

    def _mutate_bool(self, value: bool) -> bool:
        return not value

    # ------------------------------------------------------------------
    # String mutations
    # ------------------------------------------------------------------

    def _mutate_str(self, value: str) -> str:
        if not value:
            # Generate a short random string from empty
            length = self._rng.randint(1, 5)
            return "".join(self._rng.choice(string.ascii_lowercase) for _ in range(length))

        strategy = self._rng.randint(0, 7)
        if strategy == 0:
            # Insert a random char
            pos = self._rng.randint(0, len(value))
            ch = self._rng.choice(string.ascii_lowercase)
            return value[:pos] + ch + value[pos:]
        elif strategy == 1:
            # Delete a random char
            if len(value) <= 1:
                return ""
            pos = self._rng.randint(0, len(value) - 1)
            return value[:pos] + value[pos + 1:]
        elif strategy == 2:
            # Replace a random char
            pos = self._rng.randint(0, len(value) - 1)
            ch = self._rng.choice(string.ascii_lowercase)
            return value[:pos] + ch + value[pos + 1:]
        elif strategy == 3:
            # Reverse
            return value[::-1]
        elif strategy == 4:
            # Duplicate a char
            pos = self._rng.randint(0, len(value) - 1)
            return value[:pos] + value[pos] + value[pos:]
        elif strategy == 5:
            # Swap two adjacent chars
            if len(value) < 2:
                return value
            pos = self._rng.randint(0, len(value) - 2)
            lst = list(value)
            lst[pos], lst[pos + 1] = lst[pos + 1], lst[pos]
            return "".join(lst)
        elif strategy == 6:
            # Change case
            return value.swapcase()
        else:
            # Random string of similar length
            length = max(1, len(value) + self._rng.randint(-2, 2))
            return "".join(self._rng.choice(string.ascii_lowercase) for _ in range(length))

    # ------------------------------------------------------------------
    # List[int] mutations
    # ------------------------------------------------------------------

    def _mutate_list_int(self, value: list) -> list:
        if not isinstance(value, list):
            value = list(value)
        result = list(value)

        strategy = self._rng.randint(0, 8)
        if strategy == 0:
            # Insert a random element
            pos = self._rng.randint(0, len(result))
            result.insert(pos, self._rng.randint(-10, 10))
        elif strategy == 1:
            # Delete a random element
            if result:
                pos = self._rng.randint(0, len(result) - 1)
                result.pop(pos)
        elif strategy == 2:
            # Modify a random element
            if result:
                pos = self._rng.randint(0, len(result) - 1)
                result[pos] = self._mutate_int(result[pos])
        elif strategy == 3:
            # Reverse
            result.reverse()
        elif strategy == 4:
            # Sort
            result.sort()
        elif strategy == 5:
            # Duplicate an element
            if result:
                pos = self._rng.randint(0, len(result) - 1)
                result.insert(pos, result[pos])
        elif strategy == 6:
            # Swap two elements
            if len(result) >= 2:
                i = self._rng.randint(0, len(result) - 1)
                j = self._rng.randint(0, len(result) - 1)
                result[i], result[j] = result[j], result[i]
        elif strategy == 7:
            # Replace with random list of similar size
            length = max(0, len(result) + self._rng.randint(-2, 2))
            result = [self._rng.randint(-10, 10) for _ in range(length)]
        else:
            # Append boundary value
            result.append(self._rng.choice([0, 1, -1, 10, -10]))
        return result

    # ------------------------------------------------------------------
    # List[str] mutations
    # ------------------------------------------------------------------

    def _mutate_list_str(self, value: list) -> list:
        if not isinstance(value, list):
            value = list(value)
        result = list(value)

        strategy = self._rng.randint(0, 5)
        if strategy == 0:
            # Insert a random string
            pos = self._rng.randint(0, len(result))
            length = self._rng.randint(1, 4)
            s = "".join(self._rng.choice(string.ascii_lowercase[:8]) for _ in range(length))
            result.insert(pos, s)
        elif strategy == 1:
            # Delete a random element
            if result:
                pos = self._rng.randint(0, len(result) - 1)
                result.pop(pos)
        elif strategy == 2:
            # Modify a random element
            if result:
                pos = self._rng.randint(0, len(result) - 1)
                result[pos] = self._mutate_str(result[pos])
        elif strategy == 3:
            # Reverse
            result.reverse()
        elif strategy == 4:
            # Swap two elements
            if len(result) >= 2:
                i = self._rng.randint(0, len(result) - 1)
                j = self._rng.randint(0, len(result) - 1)
                result[i], result[j] = result[j], result[i]
        else:
            # Replace with random list
            length = max(0, len(result) + self._rng.randint(-1, 2))
            chars = list(string.ascii_lowercase[:8])
            result = [self._rng.choice(chars) for _ in range(length)]
        return result

    # ------------------------------------------------------------------
    # Random value generation (for fully random inputs)
    # ------------------------------------------------------------------

    def _random_value(self, type_str: str) -> Any:
        t = type_str.strip()
        if t == "int":
            return self._rng.randint(-500, 500)
        if t == "bool":
            return self._rng.choice([True, False])
        if t == "str":
            length = self._rng.randint(0, 8)
            return "".join(self._rng.choice(string.ascii_lowercase) for _ in range(length))
        if t in ("list[int]", "list"):
            length = self._rng.randint(0, 8)
            return [self._rng.randint(-10, 10) for _ in range(length)]
        if t == "list[str]":
            length = self._rng.randint(0, 5)
            chars = list(string.ascii_lowercase[:8])
            return [self._rng.choice(chars) for _ in range(length)]
        # Fallback
        return self._rng.randint(-10, 10)


# ---------------------------------------------------------------------------
# Core fuzzing logic for a single entry
# ---------------------------------------------------------------------------

def fuzz_entry(
    entry: dict,
    tests_data: dict,
    max_tests: int,
    max_time: float,
    per_call_timeout: float,
    rng_seed: Optional[int] = None,
) -> dict:
    """
    Fuzz a single benchmark entry and evaluate with newly generated tests.

    Parameters
    ----------
    entry          : benchmark entry dict (with p1_source, p2_source, etc.)
    tests_data     : dict with "ptests" and "ntests" lists
    max_tests      : max number of new tests to generate
    max_time       : max wall-clock seconds for fuzzing this entry
    per_call_timeout : timeout per function call
    rng_seed       : random seed

    Returns
    -------
    dict with fuzzing and evaluation results
    """
    func_name = entry["func_name"]
    p1_source = entry["p1_source"]
    p2_source = entry["p2_source"]
    is_equivalent = entry["is_equivalent"]
    param_types = entry["param_types"]

    existing_ptests = tests_data.get("ptests", [])
    existing_ntests = tests_data.get("ntests", [])

    # Build set of existing test repr keys for deduplication
    existing_keys: set = set()
    for t in existing_ptests:
        existing_keys.add(repr(t))
    for t in existing_ntests:
        existing_keys.add(repr(t))

    # Compile p1 for validation during fuzzing
    p1_fn, p1_err = _compile_function(p1_source, func_name)
    p2_fn, p2_err = _compile_function(p2_source, func_name)

    result = {
        "entry_id": entry["entry_id"],
        "func_name": func_name,
        "is_equivalent": is_equivalent,
        "num_original_ptests": len(existing_ptests),
        "num_original_ntests": len(existing_ntests),
        "p1_compile_error": p1_err,
        "p2_compile_error": p2_err,
    }

    if p1_err or p2_err:
        result.update({
            "new_tests_generated": 0,
            "ptest_agree": 0,
            "ptest_disagree": 0,
            "ptest_errors": 0,
            "ntest_agree": 0,
            "ntest_disagree": 0,
            "ntest_errors": 0,
            "status": "compile_error",
            "fuzz_time": 0.0,
        })
        return result

    # Collect seeds from existing tests for mutation
    all_seeds = []
    for t in existing_ptests:
        all_seeds.append(tuple(t))
    for t in existing_ntests:
        all_seeds.append(tuple(t))

    fuzzer = InputFuzzer(param_types, seed=rng_seed)

    new_tests: list[tuple] = []
    new_keys: set = set()
    start_time = time.monotonic()

    attempts = 0
    max_attempts = max_tests * 200  # avoid infinite loops

    while (
        len(new_tests) < max_tests
        and (time.monotonic() - start_time) < max_time
        and attempts < max_attempts
    ):
        attempts += 1

        # Alternate between mutation of existing seeds and random generation
        if all_seeds and fuzzer._rng.random() < 0.7:
            seed_inp = fuzzer._rng.choice(all_seeds)
            candidate = fuzzer.mutate(seed_inp)
        else:
            candidate = fuzzer.random_input()

        # Convert to the canonical list form for repr comparison
        candidate_as_list = [
            list(v) if isinstance(v, (list, tuple)) and not isinstance(v, str)
            else v
            for v in candidate
        ]
        key = repr(candidate_as_list)

        # Must not duplicate existing or already-generated tests
        if key in existing_keys or key in new_keys:
            continue

        # Validate: p1 must not crash on this input
        _, err = _run_with_timeout(p1_fn, candidate, per_call_timeout)
        if err is not None:
            continue

        new_keys.add(key)
        new_tests.append(candidate)

    fuzz_time = time.monotonic() - start_time

    # Evaluate both functions on the new tests
    ptest_agree = 0
    ptest_disagree = 0
    ptest_errors = 0
    ntest_agree = 0
    ntest_disagree = 0
    ntest_errors = 0

    new_ptests: list[list] = []
    new_ntests: list[list] = []

    for inp in new_tests:
        r1, e1 = _run_with_timeout(p1_fn, inp, per_call_timeout)
        r2, e2 = _run_with_timeout(p2_fn, inp, per_call_timeout)

        if e1 is not None or e2 is not None:
            ptest_errors += 1
        elif r1 == r2:
            ptest_agree += 1
            new_ptests.append(list(inp))
        else:
            ptest_disagree += 1
            new_ntests.append(list(inp))

    # For the reporting, treat new_ptests as "agree" tests and
    # new_ntests as "disagree" tests.  Then determine status the same
    # way as evaluate_benchmark.py.
    if not new_tests:
        # No new tests were generated — cannot validate
        status = "no_new_tests"
    elif is_equivalent:
        # Equivalent pairs: all new tests should agree
        if ptest_disagree == 0 and ptest_errors == 0:
            status = "pass"
        else:
            status = "fail"
    else:
        # Non-equivalent pairs: at least one new test should disagree
        if ptest_disagree >= 1:
            status = "pass"
        else:
            status = "fail"

    result.update({
        "new_tests_generated": len(new_tests),
        "new_ptests": len(new_ptests),
        "new_ntests": len(new_ntests),
        "ptest_agree": ptest_agree,
        "ptest_disagree": ptest_disagree,
        "ptest_errors": ptest_errors,
        "status": status,
        "fuzz_time": round(fuzz_time, 2),
        "fuzz_attempts": attempts,
    })

    return result


# ---------------------------------------------------------------------------
# Multiprocessing wrapper
# ---------------------------------------------------------------------------

def _fuzz_entry_worker(args: tuple) -> dict:
    """Top-level function for multiprocessing (must be picklable)."""
    entry, tests_data, max_tests, max_time, per_call_timeout, rng_seed = args
    return fuzz_entry(
        entry=entry,
        tests_data=tests_data,
        max_tests=max_tests,
        max_time=max_time,
        per_call_timeout=per_call_timeout,
        rng_seed=rng_seed,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args = _parse_args()
    logger = setup_file_logger("fuzz_benchmark")

    def _log(msg: str) -> None:
        log_message(logger, msg)

    # Load the benchmark JSON
    benchmark_path = args.benchmark
    if not os.path.exists(benchmark_path):
        _log(f"Error: benchmark file not found: {benchmark_path}")
        sys.exit(1)

    with open(benchmark_path, encoding="utf-8") as fh:
        benchmark = json.load(fh)

    benchmark_dir = os.path.dirname(os.path.abspath(benchmark_path))
    entries = benchmark.get("entries", [])

    num_workers = args.workers or multiprocessing.cpu_count()

    _log("=" * 60)
    _log("Python Equivalence Benchmark Fuzzer")
    _log("=" * 60)
    _log(f"  Benchmark file   : {benchmark_path}")
    _log(f"  Total entries    : {len(entries)}")
    _log(f"  Max tests/entry  : {args.max_tests}")
    _log(f"  Max time/entry   : {args.max_time}s")
    _log(f"  Workers          : {num_workers}")
    _log(f"  Per-call timeout : {args.per_call_timeout}s")
    if args.seed is not None:
        _log(f"  Random seed      : {args.seed}")
    _log("")

    # Prepare work items
    work_items = []
    for i, entry in enumerate(entries):
        # Load test data
        tests_file = entry.get("tests_file")
        if tests_file:
            tests_path = os.path.join(benchmark_dir, tests_file)
            if not os.path.exists(tests_path):
                _log(f"  Warning: test file not found: {tests_path}")
                continue
            with open(tests_path, encoding="utf-8") as fh:
                tests_data = json.load(fh)
        else:
            tests_data = {
                "ptests": entry.get("ptests", []),
                "ntests": entry.get("ntests", []),
            }

        # Per-entry seed derived from base seed + entry index
        rng_seed = (args.seed + i) if args.seed is not None else None

        work_items.append((
            entry,
            tests_data,
            args.max_tests,
            args.max_time,
            args.per_call_timeout,
            rng_seed,
        ))

    # Run fuzzing in parallel
    _log(f"Fuzzing {len(work_items)} entries with {num_workers} workers…\n")
    start_time = time.monotonic()

    if num_workers == 1:
        # Single-process mode for easier debugging
        results = []
        for item in tqdm(work_items, desc="Fuzzing", unit="entry"):
            results.append(_fuzz_entry_worker(item))
    else:
        with multiprocessing.Pool(processes=num_workers) as pool:
            results = list(tqdm(
                pool.imap(_fuzz_entry_worker, work_items),
                total=len(work_items),
                desc="Fuzzing",
                unit="entry",
            ))

    total_time = time.monotonic() - start_time

    # Print per-entry results
    passed = 0
    failed = 0
    errors = 0
    no_new_tests = 0
    total_new_tests = 0

    for i, result in enumerate(results):
        if result["status"] == "pass":
            passed += 1
        elif result["status"] == "compile_error":
            errors += 1
        elif result["status"] == "no_new_tests":
            no_new_tests += 1
        else:
            failed += 1

        total_new_tests += result.get("new_tests_generated", 0)

        if args.verbose:
            label = "EQ" if result["is_equivalent"] else "NE"
            status = result["status"].upper()
            new_tests = result.get("new_tests_generated", 0)
            _log(
                f"  [{i + 1:>4}/{len(results)}] {result['func_name']:<30} "
                f"[{label}] {status:>13}  "
                f"new_tests: {new_tests:>3}  "
                f"agree: {result['ptest_agree']:>3}  "
                f"disagree: {result['ptest_disagree']:>3}  "
                f"errors: {result['ptest_errors']:>3}  "
                f"({result.get('fuzz_time', 0):.1f}s)"
            )

    # Summary
    total = len(results)
    _log("")
    _log("=" * 60)
    _log("Fuzz Evaluation Summary")
    _log("=" * 60)
    _log(f"  Total evaluated     : {total}")
    _log(f"  Passed              : {passed}")
    _log(f"  Failed              : {failed}")
    _log(f"  No new tests        : {no_new_tests}")
    _log(f"  Compile errors      : {errors}")
    _log(f"  Total new tests     : {total_new_tests}")
    _log(f"  Total fuzz time     : {total_time:.1f}s")
    if total > 0:
        _log(f"  Pass rate           : {passed / total * 100:.1f}%")

    # Breakdown by pair type
    eq_results = [r for r in results if r["is_equivalent"]]
    ne_results = [r for r in results if not r["is_equivalent"]]
    if eq_results:
        eq_pass = sum(1 for r in eq_results if r["status"] == "pass")
        _log(f"\n  Equivalent pairs    : {eq_pass}/{len(eq_results)} passed")
    if ne_results:
        ne_pass = sum(1 for r in ne_results if r["status"] == "pass")
        _log(f"  Non-equivalent pairs: {ne_pass}/{len(ne_results)} passed")

    _log("=" * 60)

    # Optionally write JSON output
    if args.output:
        output_payload = {
            "benchmark_file": benchmark_path,
            "max_tests_per_entry": args.max_tests,
            "max_time_per_entry": args.max_time,
            "workers": num_workers,
            "total_fuzz_time": round(total_time, 2),
            "summary": {
                "total": total,
                "passed": passed,
                "failed": failed,
                "no_new_tests": no_new_tests,
                "compile_errors": errors,
                "total_new_tests": total_new_tests,
                "pass_rate": round(passed / total * 100, 1) if total else 0,
            },
            "results": results,
        }
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as fh:
            json.dump(output_payload, fh, indent=2, ensure_ascii=False)
        _log(f"\nResults written to: {args.output}")


if __name__ == "__main__":
    main()
