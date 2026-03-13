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

    # ----------------------------------------------------------------
    # Additional tests for uncovered branches and edge cases
    # ----------------------------------------------------------------

    def test_from_dict_without_metadata(self):
        """from_dict should handle missing metadata key gracefully."""
        d = {
            "entry_id": "id1",
            "func_name": "f",
            "param_types": ["int"],
            "return_type": "int",
            "p1_source": "def f(x): return x",
            "p2_source": "def f(x): return x",
            "ptests": [[1]],
            "ntests": [],
            "is_equivalent": True,
        }
        e = BenchmarkEntry.from_dict(d)
        assert e.metadata == {}

    def test_from_dict_with_metadata(self):
        d = {
            "entry_id": "id1",
            "func_name": "f",
            "param_types": ["int"],
            "return_type": "int",
            "p1_source": "def f(x): return x",
            "p2_source": "def f(x): return x",
            "ptests": [[1]],
            "ntests": [],
            "is_equivalent": True,
            "metadata": {"provenance": "catalog"},
        }
        e = BenchmarkEntry.from_dict(d)
        assert e.metadata["provenance"] == "catalog"

    def test_to_dict_num_counts_match(self):
        e = _make_entry(50, 10, is_equivalent=False)
        d = e.to_dict()
        assert d["num_ptests"] == 50
        assert d["num_ntests"] == 10

    def test_to_dict_is_valid_field(self):
        valid_entry = _make_entry(1000, 0, is_equivalent=True)
        assert valid_entry.to_dict()["is_valid"] is True

        invalid_entry = _make_entry(5, 0, is_equivalent=True)
        assert invalid_entry.to_dict()["is_valid"] is False

    def test_negative_entry_valid_with_many_ptests(self):
        """A negative entry only needs ntests >= 1 to be valid."""
        e = _make_entry(5000, 1, is_equivalent=False)
        assert e.is_valid

    def test_positive_entry_boundary_exactly_1000(self):
        e = _make_entry(1000, 0, is_equivalent=True)
        assert e.is_valid

    def test_positive_entry_boundary_999(self):
        e = _make_entry(999, 0, is_equivalent=True)
        assert not e.is_valid

    def test_round_trip_preserves_all_fields(self):
        e = BenchmarkEntry(
            entry_id="test-uuid",
            func_name="my_func",
            param_types=["list[int]", "int"],
            return_type="bool",
            p1_source="def my_func(xs, n): return n in xs",
            p2_source="def my_func(xs, n): return any(x == n for x in xs)",
            ptests=[[[1, 2], 1], [[3], 3]],
            ntests=[[[1, 2], 5]],
            is_equivalent=True,
            metadata={"category": "search", "provenance": "catalog"},
        )
        d = e.to_dict()
        e2 = BenchmarkEntry.from_dict(d)
        assert e2.entry_id == e.entry_id
        assert e2.func_name == e.func_name
        assert e2.param_types == e.param_types
        assert e2.return_type == e.return_type
        assert e2.p1_source == e.p1_source
        assert e2.p2_source == e.p2_source
        assert e2.ptests == e.ptests
        assert e2.ntests == e.ntests
        assert e2.is_equivalent == e.is_equivalent
        assert e2.metadata == e.metadata
