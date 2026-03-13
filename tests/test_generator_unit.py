"""
Unit tests for benchmark_generator.generator internals.

Covers the helper functions and edge-case branches that the integration
tests do not exercise: _deduplicate, _log, _make_entry with input_filter /
error-producing inputs / invalid entries, _summary_text, and
generate_from_random_ast.
"""

import io
import json
import os
import tempfile
from contextlib import redirect_stdout
from unittest.mock import patch, MagicMock

import pytest

from benchmark_generator.generator import BenchmarkGenerator, _deduplicate
from benchmark_generator.models import BenchmarkEntry


# ------------------------------------------------------------------ #
# _deduplicate
# ------------------------------------------------------------------ #

class TestDeduplicate:
    def test_empty_list(self):
        assert _deduplicate([]) == []

    def test_no_duplicates(self):
        assert _deduplicate([1, 2, 3]) == [1, 2, 3]

    def test_removes_duplicates_preserves_order(self):
        assert _deduplicate([3, 1, 2, 1, 3, 4]) == [3, 1, 2, 4]

    def test_all_same(self):
        assert _deduplicate([5, 5, 5]) == [5]

    def test_uses_repr_for_keys(self):
        """Lists with equal content but different identity are deduped."""
        a = [1, 2]
        b = [1, 2]
        assert _deduplicate([a, b]) == [a]

    def test_mixed_types(self):
        result = _deduplicate(["a", 1, "a", 1, "b"])
        assert result == ["a", 1, "b"]


# ------------------------------------------------------------------ #
# BenchmarkGenerator._log (verbose / non-verbose)
# ------------------------------------------------------------------ #

class TestLog:
    def test_verbose_prints(self):
        gen = BenchmarkGenerator(verbose=True)
        buf = io.StringIO()
        with redirect_stdout(buf):
            gen._log("hello")
        assert "hello" in buf.getvalue()

    def test_non_verbose_silent(self):
        gen = BenchmarkGenerator(verbose=False)
        buf = io.StringIO()
        with redirect_stdout(buf):
            gen._log("hello")
        assert buf.getvalue() == ""


# ------------------------------------------------------------------ #
# BenchmarkGenerator._make_entry — edge-case branches
# ------------------------------------------------------------------ #

IDENTITY_SRC = "def f(x): return x"
ALWAYS_NONE_SRC = "def f(x): return None"
RAISE_SRC = "def f(x): raise ValueError('boom')"


class TestMakeEntry:
    """Exercise branches inside _make_entry that integration tests miss."""

    def _gen(self, **kw):
        defaults = dict(seed=42, min_ptests=5, runner_timeout=10.0, verbose=False)
        defaults.update(kw)
        return BenchmarkGenerator(**defaults)

    # -- input_filter branch (line 311) --

    def test_input_filter_applied(self):
        """When input_filter is provided, only matching inputs survive."""
        gen = self._gen(min_ptests=5)
        # Filter: keep only positive integers
        entry = gen._make_entry(
            func_name="f",
            p1_source=IDENTITY_SRC,
            p2_source=IDENTITY_SRC,
            param_types=["int"],
            return_type="int",
            is_equivalent=True,
            metadata={"category": "test", "provenance": "unit"},
            input_filter=lambda args: args[0] > 0,
        )
        # All ptests should have positive inputs
        if entry is not None:
            for pt in entry.ptests:
                assert pt[0] > 0

    # -- error-skipping branch (line 324-325) --

    def test_errored_inputs_are_skipped(self):
        """If one function raises, those inputs are excluded from ptests/ntests."""
        src_raises_on_neg = (
            "def f(x):\n"
            "    if x < 0:\n"
            "        raise ValueError('negative')\n"
            "    return x\n"
        )
        gen = self._gen(min_ptests=1)
        entry = gen._make_entry(
            func_name="f",
            p1_source=src_raises_on_neg,
            p2_source=src_raises_on_neg,
            param_types=["int"],
            return_type="int",
            is_equivalent=True,
            metadata={"category": "test", "provenance": "unit"},
        )
        # Negative inputs should not appear in ptests (they error)
        if entry is not None:
            for pt in entry.ptests:
                assert pt[0] >= 0

    # -- invalid entry returns None (lines 350-359) --

    def test_positive_pair_returns_none_when_too_few_ptests(self):
        """A positive pair where both functions always error yields no ptests → None."""
        gen = self._gen(min_ptests=5)
        entry = gen._make_entry(
            func_name="f",
            p1_source=RAISE_SRC,
            p2_source=RAISE_SRC,
            param_types=["int"],
            return_type="int",
            is_equivalent=True,
            metadata={"category": "test", "provenance": "unit"},
        )
        # Both functions always raise → no ptests → is_valid is False → returns None
        assert entry is None

    def test_negative_pair_returns_none_when_always_equal(self):
        """A negative pair where both functions always agree yields no ntests → None."""
        gen = self._gen(min_ptests=1)
        entry = gen._make_entry(
            func_name="f",
            p1_source=IDENTITY_SRC,
            p2_source=IDENTITY_SRC,  # same → no ntests
            param_types=["int"],
            return_type="int",
            is_equivalent=False,
            metadata={"category": "test", "provenance": "unit"},
        )
        assert entry is None

    def test_valid_negative_pair(self):
        gen = self._gen(min_ptests=1)
        entry = gen._make_entry(
            func_name="f",
            p1_source=IDENTITY_SRC,
            p2_source=ALWAYS_NONE_SRC,
            param_types=["int"],
            return_type="int",
            is_equivalent=False,
            metadata={"category": "test", "provenance": "unit"},
        )
        assert entry is not None
        assert len(entry.ntests) >= 1

    # -- verbose logging of invalid entry (lines 351-357) --

    def test_invalid_positive_logs_skip_reason(self):
        gen = self._gen(min_ptests=5, verbose=True)
        buf = io.StringIO()
        with redirect_stdout(buf):
            gen._make_entry(
                func_name="f",
                p1_source=RAISE_SRC,
                p2_source=RAISE_SRC,
                param_types=["int"],
                return_type="int",
                is_equivalent=True,
                metadata={"category": "test", "provenance": "unit"},
            )
        assert "skipped" in buf.getvalue().lower() or "✗" in buf.getvalue()

    def test_invalid_negative_logs_skip_reason(self):
        gen = self._gen(min_ptests=1, verbose=True)
        buf = io.StringIO()
        with redirect_stdout(buf):
            gen._make_entry(
                func_name="f",
                p1_source=IDENTITY_SRC,
                p2_source=IDENTITY_SRC,
                param_types=["int"],
                return_type="int",
                is_equivalent=False,
                metadata={"category": "test", "provenance": "unit"},
            )
        assert "skipped" in buf.getvalue().lower() or "✗" in buf.getvalue()


# ------------------------------------------------------------------ #
# BenchmarkGenerator.generate_from_random_ast
# ------------------------------------------------------------------ #

class TestGenerateFromRandomAst:
    def test_returns_list(self):
        gen = BenchmarkGenerator(seed=0, min_ptests=5, runner_timeout=30.0, verbose=False)
        entries = gen.generate_from_random_ast(n=2, min_loc=20)
        assert isinstance(entries, list)

    def test_entries_have_random_ast_provenance(self):
        gen = BenchmarkGenerator(seed=0, min_ptests=5, runner_timeout=30.0, verbose=False)
        entries = gen.generate_from_random_ast(n=2, min_loc=20)
        for e in entries:
            assert e.metadata["provenance"] == "random_ast"


# ------------------------------------------------------------------ #
# BenchmarkGenerator._summary_text
# ------------------------------------------------------------------ #

class TestSummaryText:
    @staticmethod
    def _make_entry(is_equiv, n_ptests, n_ntests, category="test"):
        return BenchmarkEntry(
            entry_id="id",
            func_name="f",
            param_types=["int"],
            return_type="int",
            p1_source="def f(x): return x",
            p2_source="def f(x): return x",
            ptests=[[i] for i in range(n_ptests)],
            ntests=[[i] for i in range(n_ntests)],
            is_equivalent=is_equiv,
            metadata={"category": category},
        )

    def test_summary_contains_counts(self):
        entries = [
            self._make_entry(True, 1000, 0, "cat_a"),
            self._make_entry(False, 0, 5, "cat_b"),
        ]
        text = BenchmarkGenerator._summary_text(entries, "/tmp/bench.json")
        assert "Total valid" in text
        assert "Positive" in text
        assert "Negative" in text
        assert "cat_a" in text
        assert "cat_b" in text

    def test_summary_with_only_positive(self):
        entries = [self._make_entry(True, 1000, 0)]
        text = BenchmarkGenerator._summary_text(entries, "/tmp/bench.json")
        assert "ptests" in text
        # No negative entries → ntests line should not appear
        assert "ntests" not in text

    def test_summary_with_only_negative(self):
        entries = [self._make_entry(False, 0, 3)]
        text = BenchmarkGenerator._summary_text(entries, "/tmp/bench.json")
        assert "ntests" in text

    def test_summary_empty(self):
        text = BenchmarkGenerator._summary_text([], "/tmp/bench.json")
        assert "Total valid" in text
        assert "0" in text

    def test_summary_with_invalid_entries(self):
        """Invalid entries should not be counted."""
        invalid = self._make_entry(True, 5, 0)  # < 1000 ptests → invalid
        assert not invalid.is_valid
        text = BenchmarkGenerator._summary_text([invalid], "/tmp/bench.json")
        assert "Total valid : 0" in text


# ------------------------------------------------------------------ #
# BenchmarkGenerator.save — supplementary checks
# ------------------------------------------------------------------ #

class TestSave:
    def test_save_creates_output_dir(self, tmp_path):
        gen = BenchmarkGenerator(seed=0, min_ptests=5, verbose=False)
        out_dir = str(tmp_path / "new_dir")
        entry = BenchmarkEntry(
            entry_id="e1", func_name="f", param_types=["int"],
            return_type="int", p1_source="def f(x): return x",
            p2_source="def f(x): return x",
            ptests=[[1]], ntests=[], is_equivalent=True,
            metadata={"category": "t"},
        )
        path = gen.save([entry], out_dir)
        assert os.path.exists(path)
        # tests subdirectory should exist
        assert os.path.isdir(os.path.join(out_dir, "tests"))

    def test_save_empty_entries(self, tmp_path):
        gen = BenchmarkGenerator(seed=0, min_ptests=5, verbose=False)
        path = gen.save([], str(tmp_path))
        with open(path) as fh:
            data = json.load(fh)
        assert data["total_entries"] == 0
        assert data["entries"] == []
