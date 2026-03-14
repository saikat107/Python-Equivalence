"""Tests for equivalence_benchmarks.runner."""

import pytest
from equivalence_benchmarks.runner import SafeRunner


SIMPLE_SUM = """\
def simple_sum(xs: list) -> int:
    return sum(xs)
"""

ALWAYS_ZERO = """\
def simple_sum(xs: list) -> int:
    return 0
"""

RAISES_ON_EMPTY = """\
def simple_sum(xs: list) -> int:
    return xs[0]
"""

INFINITE_LOOP = """\
def simple_sum(xs: list) -> int:
    while True:
        pass
"""


class TestSafeRunner:
    def test_basic_execution(self):
        runner = SafeRunner(timeout=10.0)
        results = runner.run_batch(SIMPLE_SUM, "simple_sum", [([1, 2, 3],)])
        assert results[0] == (6, None)

    def test_empty_inputs(self):
        runner = SafeRunner(timeout=10.0)
        results = runner.run_batch(SIMPLE_SUM, "simple_sum", [])
        assert results == []

    def test_multiple_inputs(self):
        runner = SafeRunner(timeout=10.0)
        inputs = [([1, 2],), ([],), ([-1, 1],)]
        results = runner.run_batch(SIMPLE_SUM, "simple_sum", inputs)
        assert results[0] == (3, None)
        assert results[1] == (0, None)
        assert results[2] == (0, None)

    def test_runtime_error_captured(self):
        runner = SafeRunner(timeout=10.0)
        results = runner.run_batch(RAISES_ON_EMPTY, "simple_sum", [([],)])
        val, err = results[0]
        assert val is None
        assert err is not None

    def test_syntax_error_handled(self):
        bad_source = "def f(x: return x"
        runner = SafeRunner(timeout=10.0)
        results = runner.run_batch(bad_source, "f", [(1,)])
        val, err = results[0]
        assert val is None
        assert err is not None

    def test_timeout(self):
        runner = SafeRunner(timeout=2.0)
        results = runner.run_batch(INFINITE_LOOP, "simple_sum", [([1],)])
        val, err = results[0]
        assert val is None
        assert err is not None
        assert "Timeout" in err or "timeout" in err.lower()

    def test_run_pair(self):
        runner = SafeRunner(timeout=10.0)
        inputs = [([1, 2, 3],), ([0],), ([-1, -2],)]
        p1_res, p2_res = runner.run_pair(SIMPLE_SUM, ALWAYS_ZERO, "simple_sum", inputs)
        assert p1_res[0] == (6, None)
        assert p2_res[0] == (0, None)
        # They differ for non-zero sums
        assert p1_res[0][0] != p2_res[0][0]
        # They agree on [0] -> both return 0
        assert p1_res[1][0] == p2_res[1][0]
