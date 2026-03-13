"""Tests for benchmark_generator.runner."""

import pytest
from benchmark_generator.runner import SafeRunner


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

    # ----------------------------------------------------------------
    # Additional tests for uncovered branches
    # ----------------------------------------------------------------

    def test_function_not_found(self):
        """Worker should return NameError when the function name is wrong."""
        runner = SafeRunner(timeout=10.0)
        results = runner.run_batch(SIMPLE_SUM, "nonexistent_func", [([1],)])
        val, err = results[0]
        assert val is None
        assert err is not None
        assert "NameError" in err or "not found" in err

    def test_empty_stdout_returns_worker_error(self):
        """When subprocess produces no stdout, a WorkerError is returned."""
        # Source that exits without printing (bypass the worker protocol)
        silent_src = "import sys; sys.exit(0)"
        runner = SafeRunner(timeout=10.0)
        results = runner.run_batch(silent_src, "f", [(1,)])
        val, err = results[0]
        assert val is None
        assert err is not None
        assert "WorkerError" in err or "no output" in err.lower()

    def test_invalid_json_stdout(self):
        """When subprocess outputs invalid JSON, a JSONDecodeError is returned."""
        from unittest.mock import patch, MagicMock
        runner = SafeRunner(timeout=10.0)
        # Mock subprocess.run to return invalid JSON
        mock_result = MagicMock()
        mock_result.stdout = "this is not valid json"
        mock_result.stderr = ""
        with patch("benchmark_generator.runner.subprocess.run", return_value=mock_result):
            results = runner.run_batch(SIMPLE_SUM, "simple_sum", [([1],)])
        val, err = results[0]
        assert val is None
        assert err is not None
        assert "JSONDecodeError" in err

    def test_subprocess_generic_error(self):
        """When subprocess.run raises a non-timeout exception."""
        from unittest.mock import patch
        runner = SafeRunner(timeout=10.0)
        with patch(
            "benchmark_generator.runner.subprocess.run",
            side_effect=OSError("mock error"),
        ):
            results = runner.run_batch(SIMPLE_SUM, "simple_sum", [([1],)])
        val, err = results[0]
        assert val is None
        assert err is not None
        assert "SubprocessError" in err

    def test_compile_error_in_worker(self):
        """Worker should handle source that raises during compilation."""
        bad_source = "def f(x):\n    return ("  # unclosed paren
        runner = SafeRunner(timeout=10.0)
        results = runner.run_batch(bad_source, "f", [(1,)])
        val, err = results[0]
        assert val is None
        assert err is not None
        assert "CompileError" in err or "SyntaxError" in err or "Error" in err

    def test_multiple_errors_same_count(self):
        """All inputs get the same error when function is not found."""
        runner = SafeRunner(timeout=10.0)
        inputs = [([1],), ([2],), ([3],)]
        results = runner.run_batch(SIMPLE_SUM, "wrong_name", inputs)
        assert len(results) == 3
        for val, err in results:
            assert val is None
            assert err is not None
