"""Tests for deduplicate_entries and _normalize_source."""

import pytest

from benchmark_generator.generator import deduplicate_entries, _normalize_source
from benchmark_generator.models import BenchmarkEntry


def _entry(
    func_name: str = "f",
    p1: str = "def f(x): return x",
    p2: str = "def f(x): return x",
    entry_id: str = "1",
    is_equivalent: bool = True,
) -> BenchmarkEntry:
    return BenchmarkEntry(
        entry_id=entry_id,
        func_name=func_name,
        param_types=["int"],
        return_type="int",
        p1_source=p1,
        p2_source=p2,
        ptests=[[i] for i in range(1000)],
        ntests=[],
        is_equivalent=is_equivalent,
    )


class TestNormalizeSource:
    def test_replaces_func_name_in_def(self):
        src = "def foo(x):\n    return x"
        assert _normalize_source(src, "foo") == "def _F_(x):\n    return x"

    def test_replaces_recursive_call(self):
        src = "def bar(n):\n    return bar(n - 1)"
        assert _normalize_source(src, "bar") == "def _F_(n):\n    return _F_(n - 1)"

    def test_does_not_replace_substring(self):
        src = "def sum_list(xs):\n    return sum(xs)"
        result = _normalize_source(src, "sum_list")
        # "sum_list" replaced, but "sum" left intact
        assert "def _F_(xs)" in result
        assert "sum(xs)" in result

    def test_strips_leading_trailing_whitespace(self):
        src = "  \ndef foo(x):\n    return foo(x)\n  "
        assert _normalize_source(src, "foo") == "def _F_(x):\n    return _F_(x)"

    def test_identity_when_name_absent(self):
        src = "def f(x): return x"
        assert _normalize_source(src, "zzz_missing") == src


class TestDeduplicateEntries:
    def test_empty_list(self):
        assert deduplicate_entries([]) == []

    def test_no_duplicates_unchanged(self):
        entries = [
            _entry(p1="def f(x): return x", p2="def f(x): return x + 1", entry_id="1"),
            _entry(p1="def f(x): return x * 2", p2="def f(x): return x + x", entry_id="2"),
        ]
        result = deduplicate_entries(entries)
        assert len(result) == 2

    def test_exact_duplicates_removed(self):
        e1 = _entry(p1="def f(x): return x", p2="def f(x): return x + 1", entry_id="1")
        e2 = _entry(p1="def f(x): return x", p2="def f(x): return x + 1", entry_id="2")
        result = deduplicate_entries([e1, e2])
        assert len(result) == 1
        assert result[0].entry_id == "1"  # first occurrence kept

    def test_same_body_different_name_are_duplicates(self):
        e1 = _entry(
            func_name="alpha",
            p1="def alpha(x):\n    return x",
            p2="def alpha(x):\n    return x + 1",
            entry_id="1",
        )
        e2 = _entry(
            func_name="beta",
            p1="def beta(x):\n    return x",
            p2="def beta(x):\n    return x + 1",
            entry_id="2",
        )
        result = deduplicate_entries([e1, e2])
        assert len(result) == 1
        assert result[0].entry_id == "1"

    def test_different_bodies_kept(self):
        e1 = _entry(
            func_name="f",
            p1="def f(x): return x",
            p2="def f(x): return x + 1",
            entry_id="1",
        )
        e2 = _entry(
            func_name="f",
            p1="def f(x): return x",
            p2="def f(x): return x * 2",
            entry_id="2",
        )
        result = deduplicate_entries([e1, e2])
        assert len(result) == 2

    def test_preserves_order(self):
        entries = [
            _entry(func_name="a", p1="def a(x): return 1", p2="def a(x): return 2", entry_id="1"),
            _entry(func_name="b", p1="def b(x): return 3", p2="def b(x): return 4", entry_id="2"),
            _entry(func_name="c", p1="def c(x): return 1", p2="def c(x): return 2", entry_id="3"),  # dup of 1
        ]
        result = deduplicate_entries(entries)
        assert [e.entry_id for e in result] == ["1", "2"]

    def test_recursive_calls_normalized(self):
        """Functions with recursive calls to their own name should still match."""
        e1 = _entry(
            func_name="fact",
            p1="def fact(n):\n    if n <= 1: return 1\n    return n * fact(n - 1)",
            p2="def fact(n):\n    r = 1\n    for i in range(1, n+1): r *= i\n    return r",
            entry_id="1",
        )
        e2 = _entry(
            func_name="factorial",
            p1="def factorial(n):\n    if n <= 1: return 1\n    return n * factorial(n - 1)",
            p2="def factorial(n):\n    r = 1\n    for i in range(1, n+1): r *= i\n    return r",
            entry_id="2",
        )
        result = deduplicate_entries([e1, e2])
        assert len(result) == 1

    def test_p1_p2_order_matters(self):
        """(p1, p2) and (p2, p1) should NOT be considered duplicates."""
        e1 = _entry(
            func_name="f",
            p1="def f(x): return x",
            p2="def f(x): return x + 1",
            entry_id="1",
        )
        e2 = _entry(
            func_name="f",
            p1="def f(x): return x + 1",
            p2="def f(x): return x",
            entry_id="2",
        )
        result = deduplicate_entries([e1, e2])
        assert len(result) == 2

    def test_mixed_equivalent_and_mutation(self):
        """Entries with same sources but different labels are still duplicates."""
        e1 = _entry(
            func_name="f",
            p1="def f(x): return x",
            p2="def f(x): return x + 1",
            entry_id="1",
            is_equivalent=True,
        )
        e2 = _entry(
            func_name="f",
            p1="def f(x): return x",
            p2="def f(x): return x + 1",
            entry_id="2",
            is_equivalent=False,
        )
        result = deduplicate_entries([e1, e2])
        assert len(result) == 1

    def test_identical_p1_p2_removed(self):
        """Entries where p1 and p2 are the same should be removed."""
        e = _entry(
            func_name="f",
            p1="def f(x): return x",
            p2="def f(x): return x",
            entry_id="1",
        )
        result = deduplicate_entries([e])
        assert len(result) == 0

    def test_identical_p1_p2_after_normalization_removed(self):
        """p1==p2 after normalization (different func name) should be removed."""
        e = _entry(
            func_name="foo",
            p1="def foo(x): return x",
            p2="  def foo(x): return x  ",
            entry_id="1",
        )
        result = deduplicate_entries([e])
        assert len(result) == 0

    def test_identical_p1_p2_mixed_with_valid(self):
        """Only identical-source entries are removed; valid ones are kept."""
        e1 = _entry(
            func_name="f",
            p1="def f(x): return x",
            p2="def f(x): return x",
            entry_id="1",
        )
        e2 = _entry(
            func_name="f",
            p1="def f(x): return x",
            p2="def f(x): return x + 1",
            entry_id="2",
        )
        result = deduplicate_entries([e1, e2])
        assert len(result) == 1
        assert result[0].entry_id == "2"
