"""
Main orchestration for benchmark generation.

Workflow
--------
1. Iterate over catalog seeds  (+ optional random template seeds).
2. For each seed, create *positive pairs*  (original vs. each equivalent).
3. For each seed, create *negative pairs* (original vs. each mutation).
4. For every pair, generate a large pool of inputs from the parameter types.
5. Run both functions on all inputs, partition into ptests / ntests.
6. Keep only entries that pass the validity criteria:
     * positive: >= min_ptests distinct ptests
     * negative: >= 1 ntest
7. Save the benchmark to a JSON file.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from typing import Any, Optional, Sequence

from .catalog import CATALOG
from .models import BenchmarkEntry
from .program_gen import RandomProgramGenerator
from .random_func_gen import RandomFunctionGenerator
from .runner import SafeRunner
from .test_gen import InputGenerator


def _deduplicate(items: list[Any]) -> list[Any]:
    """Deduplicate a list while preserving order, using repr as the key."""
    seen: set = set()
    result = []
    for x in items:
        k = repr(x)
        if k not in seen:
            seen.add(k)
            result.append(x)
    return result


class BenchmarkGenerator:
    """
    Generate a benchmark of (p1, p2, ptests, ntests) tuples.

    Parameters
    ----------
    seed          : random seed for the input generator and program generator
    min_ptests    : minimum number of distinct ptests required for positive pairs
    runner_timeout: wall-clock timeout (seconds) per function batch execution
    verbose       : if True print progress to stdout
    """

    def __init__(
        self,
        seed: int = 42,
        min_ptests: int = 1000,
        runner_timeout: float = 60.0,
        verbose: bool = True,
    ) -> None:
        self._seed = seed
        self._min_ptests = min_ptests
        self._runner = SafeRunner(timeout=runner_timeout)
        self._verbose = verbose

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_from_catalog(
        self,
        categories: Optional[Sequence[str]] = None,
    ) -> list[BenchmarkEntry]:
        """
        Build benchmark entries from the built-in function catalog.

        Parameters
        ----------
        categories : if given, only include seeds in these categories
        """
        seeds = CATALOG
        if categories:
            seeds = [s for s in seeds if s["category"] in categories]

        entries: list[BenchmarkEntry] = []
        for seed_spec in seeds:
            entries.extend(self._entries_from_spec(seed_spec, provenance="catalog"))
        return entries

    def generate_from_templates(self, n: int = 20) -> list[BenchmarkEntry]:
        """
        Build benchmark entries from randomly generated template functions.

        Parameters
        ----------
        n : number of random seed functions to generate
        """
        gen = RandomProgramGenerator(seed=self._seed)
        specs = gen.generate(n=n)
        entries: list[BenchmarkEntry] = []
        for spec in specs:
            entries.extend(self._entries_from_spec(spec, provenance="template"))
        return entries

    def generate_from_random_ast(
        self,
        n: int = 10,
        min_loc: int = 20,
    ) -> list[BenchmarkEntry]:
        """
        Build benchmark entries from AST-based random function generation.

        Unlike template-based generation, this uses blueprint patterns to
        create complex functions with diverse control flow (loops, nested
        conditionals, multiple variables) that are at least *min_loc* lines
        of code.

        Parameters
        ----------
        n       : number of random seed functions to generate
        min_loc : minimum lines of code per function (default 20)
        """
        gen = RandomFunctionGenerator(seed=self._seed, min_loc=min_loc)
        specs = gen.generate(n=n)
        entries: list[BenchmarkEntry] = []
        for spec in specs:
            entries.extend(self._entries_from_spec(spec, provenance="random_ast"))
        return entries

    def save(
        self,
        entries: list[BenchmarkEntry],
        output_dir: str = "benchmark_output",
    ) -> str:
        """
        Serialise *entries* to a timestamped JSON file in *output_dir*.

        Test data (ptests / ntests) is written to individual JSON files
        inside a ``tests/`` subdirectory rather than being embedded in the
        main benchmark JSON.  Each entry in the main file references its
        test-data file via ``"tests_file"``.

        Returns the path of the written JSON file.
        """
        os.makedirs(output_dir, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        path = os.path.join(output_dir, f"benchmark_{timestamp}.json")

        # Create tests subdirectory for test data
        tests_dir = os.path.join(output_dir, "tests")
        os.makedirs(tests_dir, exist_ok=True)

        entry_dicts = []
        for entry in entries:
            d = entry.to_dict()

            # Write ptests and ntests to a separate file
            tests_filename = f"{entry.entry_id}_tests.json"
            tests_path = os.path.join(tests_dir, tests_filename)
            tests_payload = {
                "entry_id": entry.entry_id,
                "ptests": d.pop("ptests"),
                "ntests": d.pop("ntests"),
            }
            with open(tests_path, "w", encoding="utf-8") as fh:
                json.dump(tests_payload, fh, indent=2, ensure_ascii=False)

            # Replace inline tests with a reference to the file
            d["tests_file"] = f"tests/{tests_filename}"
            entry_dicts.append(d)

        payload = {
            "generated_at": timestamp,
            "total_entries": len(entries),
            "valid_entries": sum(1 for e in entries if e.is_valid),
            "positive_pairs": sum(1 for e in entries if e.is_equivalent and e.is_valid),
            "negative_pairs": sum(1 for e in entries if not e.is_equivalent and e.is_valid),
            "entries": entry_dicts,
        }

        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)

        # Also write a short summary
        summary_path = os.path.join(output_dir, "summary.txt")
        with open(summary_path, "w", encoding="utf-8") as fh:
            fh.write(self._summary_text(entries, path))

        return path

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _log(self, msg: str) -> None:
        if self._verbose:
            print(msg)

    def _entries_from_spec(
        self,
        spec: dict[str, Any],
        provenance: str,
    ) -> list[BenchmarkEntry]:
        """
        Create all positive and negative BenchmarkEntry objects from one seed
        specification dict (as in CATALOG or from RandomProgramGenerator).
        """
        entries: list[BenchmarkEntry] = []
        fname = spec["name"]
        p1_source = spec["source"]
        param_types = spec["param_types"]
        return_type = spec["return_type"]
        category = spec["category"]
        constraints = spec.get("constraints", "")
        min_list_length = 1 if "non-empty" in constraints else 0
        input_filter = spec.get("input_filter")  # optional callable(args) -> bool

        self._log(f"  Processing seed: {fname} [{category}]")

        # --- positive pairs ---
        for idx, equiv_source in enumerate(spec.get("equivalents", [])):
            entry = self._make_entry(
                func_name=fname,
                p1_source=p1_source,
                p2_source=equiv_source,
                param_types=param_types,
                return_type=return_type,
                is_equivalent=True,
                metadata={
                    "category": category,
                    "provenance": provenance,
                    "pair_type": "equivalent",
                    "equiv_index": idx,
                    "seed_name": fname,
                    "constraints": constraints,
                    **({
                        "template_id": spec.get("template_id"),
                        "template_params": spec.get("template_params"),
                    } if provenance == "template" else {}),
                },
                min_list_length=min_list_length,
                input_filter=input_filter,
            )
            if entry is not None:
                entries.append(entry)

        # --- negative pairs ---
        for mut in spec.get("mutations", []):
            mut_source = mut["source"]
            mut_desc = mut["description"]
            entry = self._make_entry(
                func_name=fname,
                p1_source=p1_source,
                p2_source=mut_source,
                param_types=param_types,
                return_type=return_type,
                is_equivalent=False,
                metadata={
                    "category": category,
                    "provenance": provenance,
                    "pair_type": "mutation",
                    "mutation_description": mut_desc,
                    "seed_name": fname,
                    "constraints": constraints,
                    **({
                        "template_id": spec.get("template_id"),
                        "template_params": spec.get("template_params"),
                    } if provenance == "template" else {}),
                },
                min_list_length=min_list_length,
                input_filter=input_filter,
            )
            if entry is not None:
                entries.append(entry)

        return entries

    def _make_entry(
        self,
        func_name: str,
        p1_source: str,
        p2_source: str,
        param_types: list[str],
        return_type: str,
        is_equivalent: bool,
        metadata: dict[str, Any],
        min_list_length: int = 0,
        input_filter=None,
    ) -> Optional[BenchmarkEntry]:
        """
        Generate inputs, run both functions, partition ptests/ntests, and
        return a BenchmarkEntry — or None if validity criteria are not met.
        """
        # Generate inputs.  When a domain constraint filter is provided we
        # generate extra candidates so that, after filtering, we still have a
        # sufficient pool.
        n_inputs = max(self._min_ptests + 200, 1500)
        oversample = 3 if input_filter is not None else 1
        gen = InputGenerator(
            param_types=param_types,
            seed=self._seed,
            min_list_length=min_list_length,
        )
        inputs = gen.generate(n=n_inputs * oversample)

        # Apply domain constraint filter if provided
        if input_filter is not None:
            inputs = [inp for inp in inputs if input_filter(inp)]

        # Run both functions
        p1_results, p2_results = self._runner.run_pair(
            p1_source, p2_source, func_name, inputs
        )

        # Partition
        ptests: list[list] = []
        ntests: list[list] = []

        for inp, (r1, e1), (r2, e2) in zip(inputs, p1_results, p2_results):
            # Skip inputs where either function errored
            if e1 is not None or e2 is not None:
                continue
            inp_list = list(inp)
            if r1 == r2:
                ptests.append(inp_list)
            else:
                ntests.append(inp_list)

        entry = BenchmarkEntry(
            entry_id=str(uuid.uuid4()),
            func_name=func_name,
            param_types=param_types,
            return_type=return_type,
            p1_source=p1_source,
            p2_source=p2_source,
            ptests=ptests,
            ntests=ntests,
            is_equivalent=is_equivalent,
            metadata=metadata,
        )

        if entry.is_valid:
            label = "positive" if is_equivalent else "negative"
            self._log(
                f"    ✓ {label} pair: {len(ptests)} ptests, {len(ntests)} ntests"
            )
        else:
            label = "positive" if is_equivalent else "negative"
            reason = (
                f"need {self._min_ptests} ptests, got {len(ptests)}"
                if is_equivalent
                else f"need ≥1 ntest, got {len(ntests)}"
            )
            self._log(f"    ✗ {label} pair skipped — {reason}")

        return entry if entry.is_valid else None

    @staticmethod
    def _summary_text(entries: List[BenchmarkEntry], json_path: str) -> str:
        valid = [e for e in entries if e.is_valid]
        positive = [e for e in valid if e.is_equivalent]
        negative = [e for e in valid if not e.is_equivalent]

        cats: dict[str, int] = {}
        for e in valid:
            c = e.metadata.get("category", "unknown")
            cats[c] = cats.get(c, 0) + 1

        lines = [
            "=" * 60,
            "Python Equivalence Benchmark — Summary",
            "=" * 60,
            f"JSON output : {json_path}",
            f"Total valid : {len(valid)}",
            f"  Positive (equivalent)     : {len(positive)}",
            f"  Negative (non-equivalent) : {len(negative)}",
            "",
            "By category:",
        ]
        for cat, count in sorted(cats.items()):
            lines.append(f"  {cat:<25} {count:>4}")

        if positive:
            ptests_counts = [len(e.ptests) for e in positive]
            lines += [
                "",
                f"ptests — min: {min(ptests_counts)}  "
                f"max: {max(ptests_counts)}  "
                f"avg: {sum(ptests_counts) // len(ptests_counts)}",
            ]
        if negative:
            ntests_counts = [len(e.ntests) for e in negative]
            lines += [
                f"ntests — min: {min(ntests_counts)}  "
                f"max: {max(ntests_counts)}  "
                f"avg: {sum(ntests_counts) // len(ntests_counts)}",
            ]
        lines.append("=" * 60)
        return "\n".join(lines) + "\n"
