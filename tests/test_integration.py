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
        json_files = [f for f in os.listdir(output_dir) if f.endswith(".json")]
        assert len(json_files) == 1

    def test_json_is_parseable(self, small_benchmark):
        entries, output_dir = small_benchmark
        json_files = [f for f in os.listdir(output_dir) if f.endswith(".json")]
        path = os.path.join(output_dir, json_files[0])
        with open(path) as fh:
            data = json.load(fh)
        assert "entries" in data
        assert data["total_entries"] == len(entries)

    def test_tests_stored_separately(self, small_benchmark):
        """Test data (ptests/ntests) should be in separate files, not inline."""
        entries, output_dir = small_benchmark
        # tests/ subdirectory must exist
        tests_dir = os.path.join(output_dir, "tests")
        assert os.path.isdir(tests_dir)
        # One test file per entry
        test_files = [f for f in os.listdir(tests_dir) if f.endswith("_tests.json")]
        assert len(test_files) == len(entries)
        # Each entry in the main JSON should reference tests_file, not embed ptests/ntests
        json_files = [f for f in os.listdir(output_dir) if f.endswith(".json")]
        path = os.path.join(output_dir, json_files[0])
        with open(path) as fh:
            data = json.load(fh)
        for ed in data["entries"]:
            assert "tests_file" in ed
            assert "ptests" not in ed
            assert "ntests" not in ed
        # Each test file is loadable and has ptests/ntests
        for tf in test_files:
            with open(os.path.join(tests_dir, tf)) as fh:
                td = json.load(fh)
            assert "ptests" in td
            assert "ntests" in td

    def test_summary_written(self, small_benchmark):
        _, output_dir = small_benchmark
        assert os.path.exists(os.path.join(output_dir, "summary.txt"))

    def test_metadata_provenance(self, small_benchmark):
        entries, _ = small_benchmark
        for e in entries:
            assert "provenance" in e.metadata
            assert e.metadata["provenance"] == "catalog"

    def test_ptests_are_distinct(self, small_benchmark):
        """Every ptest in each entry must be unique."""
        entries, _ = small_benchmark
        for e in entries:
            reprs = [repr(t) for t in e.ptests]
            assert len(reprs) == len(set(reprs)), (
                f"Duplicate ptests in entry {e.entry_id} ({e.func_name})"
            )

    def test_ntests_are_distinct(self, small_benchmark):
        """Every ntest in each entry must be unique."""
        entries, _ = small_benchmark
        for e in entries:
            reprs = [repr(t) for t in e.ntests]
            assert len(reprs) == len(set(reprs)), (
                f"Duplicate ntests in entry {e.entry_id} ({e.func_name})"
            )

    def test_no_identical_p1_p2(self, small_benchmark):
        """No entry should have p1 and p2 that are identical."""
        from benchmark_generator.generator import _normalize_source

        entries, _ = small_benchmark
        for e in entries:
            p1_norm = _normalize_source(e.p1_source, e.func_name)
            p2_norm = _normalize_source(e.p2_source, e.func_name)
            assert p1_norm != p2_norm, (
                f"Entry {e.entry_id} ({e.func_name}) has identical p1 and p2"
            )

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
