#!/usr/bin/env python3
"""
generate_benchmark.py — single entry point for the benchmark generator.

Run with no arguments to generate the full benchmark:

    python generate_benchmark.py

Common options:

    python generate_benchmark.py --output my_benchmark/
    python generate_benchmark.py --include-random --random-count 30
    python generate_benchmark.py --categories aggregation filtering
    python generate_benchmark.py --seed 123 --min-ptests 500

The output directory will contain:
    benchmark_<timestamp>.json   — all benchmark entries in JSON
    summary.txt                  — human-readable statistics
"""

from __future__ import annotations

import argparse
import sys
import os

# Make sure the package is importable when run from the repo root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from benchmark_generator.generator import BenchmarkGenerator


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a Python equivalence-checker benchmark.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--output",
        default="benchmark_output",
        metavar="DIR",
        help="Directory to write benchmark files (default: benchmark_output/)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)",
    )
    parser.add_argument(
        "--min-ptests",
        type=int,
        default=1000,
        metavar="N",
        help="Minimum distinct ptests required for positive pairs (default: 1000)",
    )
    parser.add_argument(
        "--runner-timeout",
        type=float,
        default=60.0,
        metavar="SECS",
        help="Wall-clock timeout in seconds per function batch (default: 60)",
    )
    parser.add_argument(
        "--categories",
        nargs="+",
        metavar="CAT",
        help=(
            "Restrict catalog seeds to these categories. "
            "Available: aggregation, extrema, filtering, searching, "
            "transformation, mathematical, predicate, string"
        ),
    )
    parser.add_argument(
        "--include-random",
        action="store_true",
        help="Also generate entries from randomly instantiated templates",
    )
    parser.add_argument(
        "--random-count",
        type=int,
        default=20,
        metavar="N",
        help="Number of random seed functions to generate (default: 20)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress output",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    print("=" * 60)
    print("Python Equivalence Benchmark Generator")
    print("=" * 60)
    print(f"  seed          : {args.seed}")
    print(f"  min-ptests    : {args.min_ptests}")
    print(f"  output dir    : {args.output}")
    print(f"  include-random: {args.include_random}")
    if args.categories:
        print(f"  categories    : {', '.join(args.categories)}")
    print()

    gen = BenchmarkGenerator(
        seed=args.seed,
        min_ptests=args.min_ptests,
        runner_timeout=args.runner_timeout,
        verbose=not args.quiet,
    )

    entries = []

    # --- Catalog-based entries ---
    print("Generating entries from built-in catalog…")
    entries.extend(gen.generate_from_catalog(categories=args.categories))

    # --- Template-based random entries ---
    if args.include_random:
        print(f"\nGenerating {args.random_count} random template functions…")
        entries.extend(gen.generate_from_templates(n=args.random_count))

    # --- Save ---
    print("\nSaving benchmark…")
    path = gen.save(entries, args.output)

    # --- Final summary ---
    valid = [e for e in entries if e.is_valid]
    positive = [e for e in valid if e.is_equivalent]
    negative = [e for e in valid if not e.is_equivalent]

    print()
    print("=" * 60)
    print("Done!")
    print(f"  Total valid entries : {len(valid)}")
    print(f"  Positive pairs      : {len(positive)}")
    print(f"  Negative pairs      : {len(negative)}")
    print(f"  JSON output         : {path}")
    print(f"  Summary             : {os.path.join(args.output, 'summary.txt')}")
    print("=" * 60)


if __name__ == "__main__":
    main()
