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
    python generate_benchmark.py --num-examples 500

The output directory will contain:
    benchmark_<timestamp>.json   — all benchmark entries in JSON
    summary.txt                  — human-readable statistics
"""

from __future__ import annotations

import argparse
import sys
import os

from tqdm import tqdm

# Make sure the package is importable when run from the repo root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from benchmark_generator.generator import BenchmarkGenerator, deduplicate_entries
from benchmark_generator.progress import setup_file_logger, log_message


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
        default=10000,
        metavar="N",
        help="Minimum distinct ptests required for positive pairs (default: 10000)",
    )
    parser.add_argument(
        "--runner-timeout",
        type=float,
        default=60.0,
        metavar="SECS",
        help="Wall-clock timeout in seconds per function batch (default: 60)",
    )
    parser.add_argument(
        "--per-call-timeout",
        type=float,
        default=5.0,
        metavar="SECS",
        help="Timeout in seconds per individual function call (default: 5)",
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
        "--include-catalog",
        action="store_true",
        help="Also generate entries from the built-in catalog of functions",
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
        "--include-ast-random",
        action="store_true",
        help="Also generate entries from AST-based random function generation",
    )
    parser.add_argument(
        "--ast-random-count",
        type=int,
        default=10,
        metavar="N",
        help="Number of AST-random seed functions to generate (default: 10)",
    )
    parser.add_argument(
        "--min-loc",
        type=int,
        default=50,
        metavar="N",
        help="Minimum lines of code per function, applied to all sources (default: 50)",
    )
    parser.add_argument(
        "--num-examples",
        type=int,
        default=None,
        metavar="N",
        help=(
            "Target total number of benchmark entries to generate. "
            "When set, the generator defaults to AST-random generation "
            "and continues producing entries until N are reached. "
            "Overrides --ast-random-count."
        ),
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress output",
    )
    parser.add_argument(
        "--equiv-sim-min",
        type=float,
        default=0,
        metavar="F",
        help="Minimum AST similarity for equivalent pairs (default: 0)",
    )
    parser.add_argument(
        "--equiv-sim-max",
        type=float,
        default=1.0,
        metavar="F",
        help="Maximum AST similarity for equivalent pairs (default: 1.0)",
    )
    parser.add_argument(
        "--non-equiv-sim-min",
        type=float,
        default=0,
        metavar="F",
        help="Minimum AST similarity for non-equivalent pairs (default: 0)",
    )
    parser.add_argument(
        "--non-equiv-sim-max",
        type=float,
        default=1.0,
        metavar="F",
        help="Maximum AST similarity for non-equivalent pairs (default: 1.0)",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    logger = setup_file_logger("generate_benchmark")

    def _log(msg: str) -> None:
        log_message(logger, msg)

    # Clamp similarity ranges to [0.0, 1.0] and ensure min <= max.
    args.equiv_sim_min = max(0.0, min(1.0, args.equiv_sim_min))
    args.equiv_sim_max = max(0.0, min(1.0, args.equiv_sim_max))
    if args.equiv_sim_max < args.equiv_sim_min:
        args.equiv_sim_max = args.equiv_sim_min

    args.non_equiv_sim_min = max(0.0, min(1.0, args.non_equiv_sim_min))
    args.non_equiv_sim_max = max(0.0, min(1.0, args.non_equiv_sim_max))
    if args.non_equiv_sim_max < args.non_equiv_sim_min:
        args.non_equiv_sim_max = args.non_equiv_sim_min

    # If --num-examples is set and no explicit source is enabled, default to
    # AST-random generation.
    use_num_examples = args.num_examples is not None
    if use_num_examples and not (
        args.include_catalog or args.include_random or args.include_ast_random
    ):
        args.include_ast_random = True

    _log("=" * 60)
    _log("Python Equivalence Benchmark Generator")
    _log("=" * 60)
    _log(f"  seed            : {args.seed}")
    _log(f"  min-ptests      : {args.min_ptests}")
    _log(f"  min-loc         : {args.min_loc}")
    _log(f"  output dir      : {args.output}")
    _log(f"  include-catalog : {args.include_catalog}")
    _log(f"  include-random  : {args.include_random}")
    _log(f"  include-ast     : {args.include_ast_random}")
    _log(
        f"  equiv sim range : [{args.equiv_sim_min}, {args.equiv_sim_max}]"
    )
    _log(
        f"  non-eq sim range: [{args.non_equiv_sim_min}, {args.non_equiv_sim_max}]"
    )
    if use_num_examples:
        _log(f"  num-examples    : {args.num_examples}")
    if args.categories:
        _log(f"  categories      : {', '.join(args.categories)}")
    _log("")

    gen = BenchmarkGenerator(
        seed=args.seed,
        min_ptests=args.min_ptests,
        runner_timeout=args.runner_timeout,
        min_loc=args.min_loc,
        equiv_sim_range=(args.equiv_sim_min, args.equiv_sim_max),
        non_equiv_sim_range=(args.non_equiv_sim_min, args.non_equiv_sim_max),
        verbose=not args.quiet,
        log_fn=_log,
    )

    entries = []

    target_n = args.num_examples  # None if not set

    # --- Catalog-based entries ---
    if args.include_catalog:
        _log("Generating entries from built-in catalog…")
        with tqdm(desc="Catalog seeds", unit="seed") as pbar:
            entries.extend(gen.generate_from_catalog(
                categories=args.categories,
                progress_bar=pbar,
            ))
        if target_n is not None and len(entries) >= target_n:
            entries = entries[:target_n]

    # --- Template-based random entries ---
    if args.include_random and (target_n is None or len(entries) < target_n):
        count = args.random_count
        if target_n is not None:
            # Request enough templates to fill remaining quota
            count = max(count, target_n - len(entries))
        _log(f"\nGenerating {count} random template functions…")
        with tqdm(desc="Template seeds", unit="seed") as pbar:
            new_entries = gen.generate_from_templates(
                n=count,
                progress_bar=pbar,
            )
        entries.extend(new_entries)
        if target_n is not None and len(entries) >= target_n:
            entries = entries[:target_n]

    # --- AST-based random entries ---
    ESTIMATED_ENTRIES_PER_SEED = 4  # each seed typically yields ~4 entries
    if args.include_ast_random and (target_n is None or len(entries) < target_n):
        if target_n is not None:
            # Keep generating AST-random entries until we reach the target.
            remaining = target_n - len(entries)
            # Ceiling division to request enough seeds
            ast_count = max(
                args.ast_random_count,
                (remaining + ESTIMATED_ENTRIES_PER_SEED - 1)
                // ESTIMATED_ENTRIES_PER_SEED
                + 5,
            )
        else:
            ast_count = args.ast_random_count

        _log(
            f"\nGenerating {ast_count} AST-random functions "
            f"(min {args.min_loc} LOC)…"
        )
        with tqdm(desc="AST-random seeds", unit="seed") as pbar:
            new_entries = gen.generate_from_random_ast(
                n=ast_count,
                min_loc=args.min_loc,
                progress_bar=pbar,
            )
        entries.extend(new_entries)
        if target_n is not None and len(entries) >= target_n:
            entries = entries[:target_n]

    # --- Deduplicate (p1, p2) pairs ---
    before = len(entries)
    entries = deduplicate_entries(entries)
    if before != len(entries):
        _log(f"\nDeduplicated: {before} → {len(entries)} entries")

    # --- Save ---
    _log("\nSaving benchmark…")
    path = gen.save(entries, args.output)

    # --- Final summary ---
    valid = [e for e in entries if e.is_valid]
    positive = [e for e in valid if e.is_equivalent]
    negative = [e for e in valid if not e.is_equivalent]

    _log("")
    _log("=" * 60)
    _log("Done!")
    _log(f"  Total valid entries : {len(valid)}")
    _log(f"  Positive pairs      : {len(positive)}")
    _log(f"  Negative pairs      : {len(negative)}")
    _log(f"  JSON output         : {path}")
    _log(f"  Summary             : {os.path.join(args.output, 'summary.txt')}")
    _log("=" * 60)


if __name__ == "__main__":
    main()
