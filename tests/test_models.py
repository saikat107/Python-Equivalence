"""Tests for benchmark_generator.models."""

import pytest
from benchmark_generator.models import BenchmarkEntry


def _make_entry(n_ptests: int, n_ntests: int, is_equivalent: bool) -> BenchmarkEntry:
    return BenchmarkEntry(
        entry_id="test-id",
        func_name="f",
        param_types=["int"],
        return_type="int",
        p1_source="def f(x): return x",
        p2_source="def f(x): return x",
        ptests=[[i] for i in range(n_ptests)],
        ntests=[[i] for i in range(n_ntests)],
        is_equivalent=is_equivalent,
    )


class TestBenchmarkEntry:
    def test_positive_valid_with_enough_ptests(self):
        e = _make_entry(1000, 0, is_equivalent=True)
        assert e.is_valid

    def test_positive_invalid_too_few_ptests(self):
        e = _make_entry(999, 0, is_equivalent=True)
        assert not e.is_valid

    def test_negative_valid_with_one_ntest(self):
        e = _make_entry(0, 1, is_equivalent=False)
        assert e.is_valid

    def test_negative_invalid_no_ntests(self):
        e = _make_entry(0, 0, is_equivalent=False)
        assert not e.is_valid

    def test_to_dict_round_trip(self):
        e = _make_entry(1000, 1, is_equivalent=True)
        d = e.to_dict()
        e2 = BenchmarkEntry.from_dict(d)
        assert e2.entry_id == e.entry_id
        assert e2.func_name == e.func_name
        assert e2.is_equivalent == e.is_equivalent
        assert e2.ptests == e.ptests
        assert e2.ntests == e.ntests

    def test_to_dict_contains_expected_keys(self):
        e = _make_entry(1000, 0, is_equivalent=True)
        d = e.to_dict()
        for key in ("entry_id", "func_name", "param_types", "return_type",
                    "p1_source", "p2_source", "ptests", "ntests",
                    "is_equivalent", "num_ptests", "num_ntests", "is_valid"):
            assert key in d, f"Missing key: {key}"

    def test_positive_invalid_with_duplicate_ptests(self):
        """1000 ptests that are not all distinct should be invalid."""
        e = BenchmarkEntry(
            entry_id="dup-test",
            func_name="f",
            param_types=["int"],
            return_type="int",
            p1_source="def f(x): return x",
            p2_source="def f(x): return x",
            ptests=[[0]] * 1000,  # 1000 copies of the same test
            ntests=[],
            is_equivalent=True,
        )
        assert not e.is_valid  # only 1 distinct ptest

    def test_negative_invalid_with_duplicate_ntests(self):
        """ntests with only duplicates should count as a single distinct ntest."""
        e = BenchmarkEntry(
            entry_id="dup-ntest",
            func_name="f",
            param_types=["int"],
            return_type="int",
            p1_source="def f(x): return x",
            p2_source="def f(x): return x + 1",
            ptests=[],
            ntests=[[1]] * 5,  # 5 copies of the same ntest — still 1 distinct
            is_equivalent=False,
        )
        assert e.is_valid  # 1 distinct ntest is enough
