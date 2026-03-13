#!/usr/bin/env python3
"""
evaluate_benchmark.py — evaluate a benchmark on its generated ptests and ntests.

Given a benchmark JSON file (produced by ``generate_benchmark.py``), this script
loads every entry, compiles both ``p1`` and ``p2`` via ``exec``, runs them on the
stored ptests and ntests, and reports accuracy statistics.

Usage
-----
    python evaluate_benchmark.py benchmark_output/benchmark_20260101_120000.json

Options:
    --verbose          Print per-entry results
    --per-call-timeout Seconds per individual function call (default: 5)

The script uses ``exec`` to compile function source and then calls them directly
(no subprocess), making evaluation fast.

**Security note**: This script executes arbitrary Python code from the benchmark
file.  Only evaluate benchmarks from trusted sources.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading

# Make sure the package is importable when run from the repo root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate a Python equivalence benchmark on its ptests/ntests.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "benchmark",
        metavar="BENCHMARK_JSON",
        help="Path to the benchmark JSON file produced by generate_benchmark.py",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-entry evaluation details",
    )
    parser.add_argument(
        "--per-call-timeout",
        type=float,
        default=5.0,
        metavar="SECS",
        help="Timeout in seconds for each individual function call (default: 5)",
    )
    return parser.parse_args()


def _run_with_timeout(fn, args, timeout):
    """Run fn(*args) with a timeout using a daemon thread."""
    result = [None, None]  # [return_value, error_string]

    def target():
        try:
            result[0] = fn(*args)
        except Exception as exc:
            result[1] = str(exc)

    t = threading.Thread(target=target, daemon=True)
    t.start()
    t.join(timeout)
    if t.is_alive():
        return None, f"TimeoutError: exceeded {timeout}s"
    return result[0], result[1]


def _compile_function(source: str, func_name: str):
    """Compile source via exec and return the function object, or None on error."""
    namespace: dict = {}
    try:
        exec(compile(source, "<benchmark>", "exec"), namespace)  # noqa: S102
    except Exception as exc:
        return None, f"CompileError: {exc}"
    func = namespace.get(func_name)
    if func is None:
        return None, f"NameError: '{func_name}' not found"
    return func, None


def evaluate_entry(entry: dict, tests_data: dict, per_call_timeout: float) -> dict:
    """
    Evaluate a single benchmark entry against its ptests and ntests.

    Returns a dict with evaluation results.
    """
    func_name = entry["func_name"]
    p1_source = entry["p1_source"]
    p2_source = entry["p2_source"]
    is_equivalent = entry["is_equivalent"]

    ptests = tests_data.get("ptests", [])
    ntests = tests_data.get("ntests", [])

    # Compile both functions
    p1_fn, p1_err = _compile_function(p1_source, func_name)
    p2_fn, p2_err = _compile_function(p2_source, func_name)

    result = {
        "entry_id": entry["entry_id"],
        "func_name": func_name,
        "is_equivalent": is_equivalent,
        "num_ptests": len(ptests),
        "num_ntests": len(ntests),
        "p1_compile_error": p1_err,
        "p2_compile_error": p2_err,
    }

    if p1_err or p2_err:
        result["ptest_agree"] = 0
        result["ptest_disagree"] = 0
        result["ptest_errors"] = len(ptests)
        result["ntest_agree"] = 0
        result["ntest_disagree"] = 0
        result["ntest_errors"] = len(ntests)
        result["status"] = "compile_error"
        return result

    # Evaluate on ptests (expected: p1(*t) == p2(*t))
    ptest_agree = 0
    ptest_disagree = 0
    ptest_errors = 0
    for inp in ptests:
        r1, e1 = _run_with_timeout(p1_fn, inp, per_call_timeout)
        r2, e2 = _run_with_timeout(p2_fn, inp, per_call_timeout)
        if e1 is not None or e2 is not None:
            ptest_errors += 1
        elif r1 == r2:
            ptest_agree += 1
        else:
            ptest_disagree += 1

    # Evaluate on ntests (expected: p1(*t) != p2(*t))
    ntest_agree = 0
    ntest_disagree = 0
    ntest_errors = 0
    for inp in ntests:
        r1, e1 = _run_with_timeout(p1_fn, inp, per_call_timeout)
        r2, e2 = _run_with_timeout(p2_fn, inp, per_call_timeout)
        if e1 is not None or e2 is not None:
            ntest_errors += 1
        elif r1 == r2:
            ntest_agree += 1
        else:
            ntest_disagree += 1

    result.update({
        "ptest_agree": ptest_agree,
        "ptest_disagree": ptest_disagree,
        "ptest_errors": ptest_errors,
        "ntest_agree": ntest_agree,
        "ntest_disagree": ntest_disagree,
        "ntest_errors": ntest_errors,
    })

    # Determine status
    if is_equivalent:
        # For equivalent pairs: all ptests should agree, no ntests expected
        if ptest_disagree == 0 and ptest_errors == 0:
            result["status"] = "pass"
        else:
            result["status"] = "fail"
    else:
        # For non-equivalent pairs: at least one ntest should disagree
        if ntest_disagree >= 1:
            result["status"] = "pass"
        else:
            result["status"] = "fail"

    return result


def main() -> None:
    args = _parse_args()

    # Load the benchmark JSON
    benchmark_path = args.benchmark
    if not os.path.exists(benchmark_path):
        print(f"Error: benchmark file not found: {benchmark_path}", file=sys.stderr)
        sys.exit(1)

    with open(benchmark_path, encoding="utf-8") as fh:
        benchmark = json.load(fh)

    benchmark_dir = os.path.dirname(os.path.abspath(benchmark_path))
    entries = benchmark.get("entries", [])

    print("=" * 60)
    print("Python Equivalence Benchmark Evaluator")
    print("=" * 60)
    print(f"  Benchmark file   : {benchmark_path}")
    print(f"  Total entries    : {len(entries)}")
    print(f"  Per-call timeout : {args.per_call_timeout}s")
    print()

    results = []
    passed = 0
    failed = 0
    errors = 0

    for i, entry in enumerate(entries):
        # Load test data
        tests_file = entry.get("tests_file")
        if tests_file:
            tests_path = os.path.join(benchmark_dir, tests_file)
            if not os.path.exists(tests_path):
                print(f"  Warning: test file not found: {tests_path}")
                continue
            with open(tests_path, encoding="utf-8") as fh:
                tests_data = json.load(fh)
        else:
            # Tests are inline in the entry
            tests_data = {
                "ptests": entry.get("ptests", []),
                "ntests": entry.get("ntests", []),
            }

        result = evaluate_entry(entry, tests_data, args.per_call_timeout)
        results.append(result)

        if result["status"] == "pass":
            passed += 1
        elif result["status"] == "compile_error":
            errors += 1
        else:
            failed += 1

        if args.verbose:
            label = "EQ" if result["is_equivalent"] else "NE"
            status = result["status"].upper()
            print(
                f"  [{i + 1:>4}/{len(entries)}] {result['func_name']:<30} "
                f"[{label}] {status:>13}  "
                f"ptests: {result['ptest_agree']}/{result['num_ptests']} agree  "
                f"ntests: {result['ntest_disagree']}/{result['num_ntests']} disagree"
            )

    # Summary
    total = len(results)
    print()
    print("=" * 60)
    print("Evaluation Summary")
    print("=" * 60)
    print(f"  Total evaluated : {total}")
    print(f"  Passed          : {passed}")
    print(f"  Failed          : {failed}")
    print(f"  Compile errors  : {errors}")
    if total > 0:
        print(f"  Pass rate       : {passed / total * 100:.1f}%")

    # Breakdown by pair type
    eq_results = [r for r in results if r["is_equivalent"]]
    ne_results = [r for r in results if not r["is_equivalent"]]
    if eq_results:
        eq_pass = sum(1 for r in eq_results if r["status"] == "pass")
        print(f"\n  Equivalent pairs   : {eq_pass}/{len(eq_results)} passed")
    if ne_results:
        ne_pass = sum(1 for r in ne_results if r["status"] == "pass")
        print(f"  Non-equivalent pairs: {ne_pass}/{len(ne_results)} passed")

    print("=" * 60)


if __name__ == "__main__":
    main()
