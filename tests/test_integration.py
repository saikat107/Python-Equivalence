"""
Integration tests for the full benchmark generator pipeline.

These tests use a small min_ptests threshold to keep run time manageable.
"""

import json
import os
import tempfile
import pytest

from benchmark_generator.generator import BenchmarkGenerator


class TestBenchmarkGeneratorIntegration:
    """End-to-end tests for BenchmarkGenerator."""

    @pytest.fixture(scope="class")
    def small_benchmark(self, tmp_path_factory):
        """Generate a small benchmark (only 'aggregation' category, 50 ptests)."""
        tmp = tmp_path_factory.mktemp("bench")
        gen = BenchmarkGenerator(
            seed=42,
            min_ptests=50,
            runner_timeout=30.0,
            verbose=False,
        )
        entries = gen.generate_from_catalog(categories=["aggregation"])
        gen.save(entries, str(tmp))
        return entries, str(tmp)

    def test_generates_entries(self, small_benchmark):
        entries, _ = small_benchmark
        assert len(entries) > 0

    def test_all_entries_valid(self, small_benchmark):
        entries, _ = small_benchmark
        for e in entries:
            assert e.is_valid, (
                f"Entry {e.entry_id} ({e.func_name}) is not valid: "
                f"equivalent={e.is_equivalent}, ptests={len(e.ptests)}, ntests={len(e.ntests)}"
            )

    def test_positive_entries_have_enough_ptests(self, small_benchmark):
        entries, _ = small_benchmark
        for e in entries:
            if e.is_equivalent:
                assert len(e.ptests) >= 50

    def test_negative_entries_have_ntests(self, small_benchmark):
        entries, _ = small_benchmark
        for e in entries:
            if not e.is_equivalent:
                assert len(e.ntests) >= 1

    def test_json_output_written(self, small_benchmark):
        _, output_dir = small_benchmark
        # Main benchmark JSON is at the top level (not inside tests/)
        top_json = [
            f for f in os.listdir(output_dir)
            if f.endswith(".json") and os.path.isfile(os.path.join(output_dir, f))
        ]
        assert len(top_json) == 1

    def test_json_is_parseable(self, small_benchmark):
        entries, output_dir = small_benchmark
        top_json = [
            f for f in os.listdir(output_dir)
            if f.endswith(".json") and os.path.isfile(os.path.join(output_dir, f))
        ]
        path = os.path.join(output_dir, top_json[0])
        with open(path) as fh:
            data = json.load(fh)
        assert "entries" in data
        assert data["total_entries"] == len(entries)
        # Tests should NOT be inlined in the JSON
        for entry_dict in data["entries"]:
            assert "ptests" not in entry_dict
            assert "ntests" not in entry_dict
            assert "tests_file" in entry_dict

    def test_tests_stored_separately(self, small_benchmark):
        """Each entry's ptests/ntests should be saved in a separate file."""
        entries, output_dir = small_benchmark
        tests_dir = os.path.join(output_dir, "tests")
        assert os.path.isdir(tests_dir)
        for e in entries:
            test_file = os.path.join(tests_dir, f"{e.entry_id}.json")
            assert os.path.exists(test_file), f"Missing test file for {e.entry_id}"
            with open(test_file) as fh:
                data = json.load(fh)
            assert "ptests" in data
            assert "ntests" in data

    def test_summary_written(self, small_benchmark):
        _, output_dir = small_benchmark
        assert os.path.exists(os.path.join(output_dir, "summary.txt"))

    def test_metadata_provenance(self, small_benchmark):
        entries, _ = small_benchmark
        for e in entries:
            assert "provenance" in e.metadata
            assert e.metadata["provenance"] == "catalog"

    def test_random_template_entries(self, tmp_path):
        """Template-generated entries should also pass validity."""
        gen = BenchmarkGenerator(
            seed=7,
            min_ptests=50,
            runner_timeout=30.0,
            verbose=False,
        )
        entries = gen.generate_from_templates(n=5)
        for e in entries:
            if e.is_equivalent:
                assert len(e.ptests) >= 50
            else:
                assert len(e.ntests) >= 1
