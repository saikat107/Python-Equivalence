"""Tests for equivalence_benchmarks.whitebox — AST analysis & coverage tracking."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from equivalence_benchmarks.whitebox import (
    ASTHints,
    CoverageTracker,
    CoverageReport,
    analyse_source,
)


# ---------------------------------------------------------------------------
# AST analysis tests
# ---------------------------------------------------------------------------

class TestAnalyseSource(unittest.TestCase):
    """Tests for analyse_source() and ASTHints."""

    def test_extracts_int_constants(self):
        src = """\
def f(x):
    if x > 5:
        return 10
    return 0
"""
        hints = analyse_source(src)
        self.assertIn(5, hints.int_constants)
        self.assertIn(10, hints.int_constants)
        self.assertIn(0, hints.int_constants)

    def test_extracts_float_constants(self):
        src = """\
def f(x):
    if x > 3.14:
        return 2.71
    return 0.0
"""
        hints = analyse_source(src)
        self.assertIn(3.14, hints.float_constants)
        self.assertIn(2.71, hints.float_constants)
        self.assertIn(0.0, hints.float_constants)

    def test_extracts_str_constants(self):
        src = """\
def f(s):
    if s == "hello":
        return "world"
    return ""
"""
        hints = analyse_source(src)
        self.assertIn("hello", hints.str_constants)
        self.assertIn("world", hints.str_constants)
        self.assertIn("", hints.str_constants)

    def test_extracts_bool_constants(self):
        src = """\
def f(x):
    flag = True
    if not flag:
        return False
    return True
"""
        hints = analyse_source(src)
        self.assertIn(True, hints.bool_constants)
        self.assertIn(False, hints.bool_constants)

    def test_counts_branches(self):
        src = """\
def f(x):
    if x > 0:
        pass
    elif x == 0:
        pass
    else:
        pass
    while x > 10:
        x -= 1
    for i in range(5):
        pass
"""
        hints = analyse_source(src)
        # if + elif + while + for = 4
        self.assertGreaterEqual(hints.branch_count, 4)

    def test_extracts_comparison_ops(self):
        src = """\
def f(x, y):
    if x < y:
        return -1
    elif x == y:
        return 0
    else:
        return 1
"""
        hints = analyse_source(src)
        self.assertIn("<", hints.comparison_ops)
        self.assertIn("==", hints.comparison_ops)

    def test_extracts_negative_constants(self):
        src = """\
def f(x):
    if x < -10:
        return -1
    return 0
"""
        hints = analyse_source(src)
        self.assertIn(-10, hints.int_constants)
        self.assertIn(-1, hints.int_constants)

    def test_extracts_range_args(self):
        src = """\
def f(xs):
    for i in range(1, 100):
        pass
    for j in range(5):
        pass
"""
        hints = analyse_source(src)
        self.assertIn(1, hints.int_constants)
        self.assertIn(100, hints.int_constants)
        self.assertIn(5, hints.int_constants)

    def test_extracts_subscript_constants(self):
        src = """\
def f(xs):
    a = xs[0]
    b = xs[-1]
    return a + b
"""
        hints = analyse_source(src)
        self.assertIn(0, hints.int_constants)
        self.assertIn(-1, hints.int_constants)

    def test_syntax_error_returns_empty_hints(self):
        hints = analyse_source("def bad(:\n  pass")
        self.assertEqual(len(hints.int_constants), 0)
        self.assertEqual(hints.branch_count, 0)

    def test_empty_source(self):
        hints = analyse_source("")
        self.assertEqual(len(hints.int_constants), 0)
        self.assertEqual(len(hints.comparison_ops), 0)

    def test_boundary_ints(self):
        src = """\
def f(x):
    if x == 5:
        return 1
    return 0
"""
        hints = analyse_source(src)
        boundaries = hints.boundary_ints()
        # Should include 4, 5, 6 (±1 around 5) plus neighbours of 0, 1
        self.assertIn(4, boundaries)
        self.assertIn(5, boundaries)
        self.assertIn(6, boundaries)

    def test_boundary_floats(self):
        src = """\
def f(x):
    if x > 3.0:
        return 1.0
"""
        hints = analyse_source(src)
        boundaries = hints.boundary_floats()
        # Should include 2.0, 2.5, 3.0, 3.5, 4.0 etc.
        self.assertIn(3.0, boundaries)
        self.assertIn(2.5, boundaries)
        self.assertIn(3.5, boundaries)

    def test_complex_function(self):
        """Test with a realistic function from the benchmark."""
        src = """\
def func(xs):
    n = len(xs)
    if n == 0:
        return 0
    cur_min = xs[0]
    cur_max = xs[0]
    for i in range(1, n):
        val = xs[i]
        if val < cur_min:
            cur_min = val
        if val > cur_max:
            cur_max = val
    return cur_max - cur_min
"""
        hints = analyse_source(src)
        self.assertIn(0, hints.int_constants)
        self.assertIn(1, hints.int_constants)
        self.assertIn("==", hints.comparison_ops)
        self.assertIn("<", hints.comparison_ops)
        self.assertIn(">", hints.comparison_ops)
        self.assertGreaterEqual(hints.branch_count, 3)  # if + for + 2 inner ifs

    def test_partition_function_extracts_pivot_comparisons(self):
        """Partition-style function should yield comparison-related hints."""
        src = """\
def partition(xs, pivot):
    below = []
    equal = []
    above = []
    for val in xs:
        if val < pivot:
            below.append(val)
        elif val == pivot:
            equal.append(val)
        else:
            above.append(val)
    return below + equal + above
"""
        hints = analyse_source(src)
        self.assertIn("<", hints.comparison_ops)
        self.assertIn("==", hints.comparison_ops)
        self.assertGreaterEqual(hints.branch_count, 3)

    def test_no_constants_function(self):
        """Function with no numeric constants should still work."""
        src = """\
def f(a, b):
    return a + b
"""
        hints = analyse_source(src)
        self.assertEqual(len(hints.int_constants), 0)
        self.assertEqual(len(hints.float_constants), 0)
        self.assertEqual(hints.branch_count, 0)


# ---------------------------------------------------------------------------
# ASTHints unit tests
# ---------------------------------------------------------------------------

class TestASTHints(unittest.TestCase):

    def test_boundary_ints_empty(self):
        h = ASTHints()
        self.assertEqual(h.boundary_ints(), [])

    def test_boundary_ints_single(self):
        h = ASTHints()
        h.int_constants.add(10)
        self.assertEqual(h.boundary_ints(), [9, 10, 11])

    def test_boundary_floats_empty(self):
        h = ASTHints()
        self.assertEqual(h.boundary_floats(), [])

    def test_boundary_floats_single(self):
        h = ASTHints()
        h.float_constants.add(5.0)
        result = h.boundary_floats()
        self.assertIn(4.0, result)
        self.assertIn(4.5, result)
        self.assertIn(5.0, result)
        self.assertIn(5.5, result)
        self.assertIn(6.0, result)


# ---------------------------------------------------------------------------
# Coverage tracker tests
# ---------------------------------------------------------------------------

class TestCoverageTracker(unittest.TestCase):
    """Tests for CoverageTracker."""

    def _compile(self, source, name):
        ns = {}
        code = compile(source, "<test>", "exec")
        exec(code, ns)  # noqa: S102
        return ns[name]

    def test_basic_coverage(self):
        src = """\
def add(a, b):
    return a + b
"""
        fn = self._compile(src, "add")
        tracker = CoverageTracker()
        val, err = tracker.run(fn, (2, 3), filename="<test>")
        self.assertEqual(val, 5)
        self.assertIsNone(err)
        self.assertGreater(tracker.lines_covered_count, 0)

    def test_branch_coverage_increases(self):
        src = """\
def classify(x):
    if x > 0:
        return "positive"
    elif x < 0:
        return "negative"
    else:
        return "zero"
"""
        fn = self._compile(src, "classify")
        tracker = CoverageTracker()

        # Run with positive input
        tracker.run(fn, (5,), filename="<test>")
        cov_after_pos = tracker.lines_covered_count
        branches_after_pos = tracker.branches_covered_count

        # Run with negative input — should increase coverage
        tracker.run(fn, (-3,), filename="<test>")
        cov_after_neg = tracker.lines_covered_count
        branches_after_neg = tracker.branches_covered_count
        self.assertGreater(cov_after_neg, cov_after_pos)
        self.assertGreater(branches_after_neg, branches_after_pos)

        # Run with zero — should further increase
        tracker.run(fn, (0,), filename="<test>")
        cov_after_zero = tracker.lines_covered_count
        self.assertGreater(cov_after_zero, cov_after_neg)

    def test_error_captured(self):
        src = """\
def divide(a, b):
    return a / b
"""
        fn = self._compile(src, "divide")
        tracker = CoverageTracker()
        val, err = tracker.run(fn, (1, 0), filename="<test>")
        self.assertIsNotNone(err)
        self.assertIn("ZeroDivisionError", err)

    def test_timeout_captured(self):
        src = """\
def infinite(x):
    while True:
        pass
"""
        fn = self._compile(src, "infinite")
        tracker = CoverageTracker()
        val, err = tracker.run(fn, (1,), timeout=0.5, filename="<test>")
        self.assertIn("TimeoutError", err)

    def test_report_snapshot(self):
        src = """\
def inc(x):
    return x + 1
"""
        fn = self._compile(src, "inc")
        tracker = CoverageTracker()
        tracker.run(fn, (1,), filename="<test>")
        report = tracker.report()
        self.assertIsInstance(report, CoverageReport)
        self.assertGreater(report.lines_covered_count, 0)

    def test_reset_clears_coverage(self):
        src = """\
def inc(x):
    return x + 1
"""
        fn = self._compile(src, "inc")
        tracker = CoverageTracker()
        tracker.run(fn, (1,), filename="<test>")
        self.assertGreater(tracker.lines_covered_count, 0)
        tracker.reset()
        self.assertEqual(tracker.lines_covered_count, 0)
        self.assertEqual(tracker.branches_covered_count, 0)

    def test_coverage_accumulates(self):
        src = """\
def process(xs):
    if len(xs) == 0:
        return []
    result = []
    for x in xs:
        if x > 0:
            result.append(x * 2)
        else:
            result.append(0)
    return result
"""
        fn = self._compile(src, "process")
        tracker = CoverageTracker()

        # Empty list — covers early return
        tracker.run(fn, ([],), filename="<test>")
        cov1 = tracker.lines_covered_count

        # List with positives — covers the x > 0 branch
        tracker.run(fn, ([1, 2],), filename="<test>")
        cov2 = tracker.lines_covered_count
        self.assertGreater(cov2, cov1)

        # List with negatives — covers the else branch
        tracker.run(fn, ([-1, -2],), filename="<test>")
        cov3 = tracker.lines_covered_count
        self.assertGreater(cov3, cov2)

    def test_coverage_report_repr(self):
        report = CoverageReport(
            lines_covered=frozenset({("<test>", 1), ("<test>", 2)}),
            branches_covered=frozenset({("<test>", 1, 2)}),
        )
        self.assertIn("lines=2", repr(report))
        self.assertIn("branches=1", repr(report))


# ---------------------------------------------------------------------------
# Integration: white-box hints + fuzzer
# ---------------------------------------------------------------------------

class TestWhiteboxIntegration(unittest.TestCase):
    """Verify that ASTHints integrate with InputFuzzer from fuzz_benchmark."""

    def test_fuzzer_with_hints(self):
        from fuzz_benchmark import InputFuzzer
        hints = analyse_source("""\
def f(x):
    if x == 42:
        return True
    return False
""")
        fuzzer = InputFuzzer(["int"], seed=0, hints=hints)
        # Boundary ints should include 41, 42, 43 from the constant 42
        self.assertIn(42, fuzzer._hint_ints)
        self.assertIn(41, fuzzer._hint_ints)
        self.assertIn(43, fuzzer._hint_ints)
        # Generate many inputs — some should be hint-derived
        values = set()
        for _ in range(200):
            values.add(fuzzer.random_input()[0])
        # At least one hint value should appear
        self.assertTrue(
            values & {41, 42, 43},
            "Expected at least one hint-derived boundary value in random inputs",
        )

    def test_fuzzer_with_str_hints(self):
        from fuzz_benchmark import InputFuzzer
        hints = analyse_source("""\
def f(s):
    if s == "abc":
        return 1
    return 0
""")
        fuzzer = InputFuzzer(["str"], seed=0, hints=hints)
        self.assertIn("abc", fuzzer._hint_strs)
        values = set()
        for _ in range(200):
            values.add(fuzzer.random_input()[0])
        self.assertIn("abc", values)

    def test_fuzzer_without_hints(self):
        """Fuzzer still works correctly without hints (backward compat)."""
        from fuzz_benchmark import InputFuzzer
        fuzzer = InputFuzzer(["int", "str"], seed=42)
        self.assertEqual(fuzzer._hint_ints, [])
        self.assertEqual(fuzzer._hint_strs, [])
        result = fuzzer.random_input()
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], int)
        self.assertIsInstance(result[1], str)

    def test_fuzz_entry_returns_coverage_stats(self):
        """fuzz_entry should now return coverage metrics."""
        from fuzz_benchmark import fuzz_entry

        src_p1 = """\
def add(a, b):
    if a > 0 and b > 0:
        return a + b
    elif a < 0 and b < 0:
        return a + b
    else:
        return a + b
"""
        src_p2 = """\
def add(a, b):
    return a + b
"""
        entry = {
            "entry_id": "wb-test-1",
            "func_name": "add",
            "param_types": ["int", "int"],
            "return_type": "int",
            "p1_source": src_p1,
            "p2_source": src_p2,
            "is_equivalent": True,
        }
        tests_data = {"ptests": [[1, 2]], "ntests": []}
        result = fuzz_entry(
            entry, tests_data,
            max_tests=10, max_time=30, per_call_timeout=5, rng_seed=42,
        )
        self.assertIn("coverage_lines", result)
        self.assertIn("coverage_branches", result)
        self.assertIn("coverage_seeds_found", result)
        self.assertIn("hint_int_count", result)
        self.assertGreater(result["coverage_lines"], 0)
        self.assertGreater(result["new_tests_generated"], 0)

    def test_fuzz_entry_hints_extract_source_constants(self):
        """Hints should extract constants from both p1 and p2 source."""
        from fuzz_benchmark import fuzz_entry

        src_p1 = """\
def check(x):
    if x == 99:
        return True
    return False
"""
        src_p2 = """\
def check(x):
    return x == 99
"""
        entry = {
            "entry_id": "wb-test-2",
            "func_name": "check",
            "param_types": ["int"],
            "return_type": "bool",
            "p1_source": src_p1,
            "p2_source": src_p2,
            "is_equivalent": True,
        }
        tests_data = {"ptests": [[0]], "ntests": []}
        result = fuzz_entry(
            entry, tests_data,
            max_tests=10, max_time=30, per_call_timeout=5, rng_seed=42,
        )
        # 99 should be extracted → hint_int_count >= 1
        self.assertGreater(result["hint_int_count"], 0)
        self.assertEqual(result["status"], "pass")


if __name__ == "__main__":
    unittest.main()
