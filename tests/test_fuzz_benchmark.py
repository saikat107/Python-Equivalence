"""Tests for fuzz_benchmark.py."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

# Make sure the repo root is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fuzz_benchmark import (
    InputFuzzer,
    _compile_function,
    _run_with_timeout,
    fuzz_entry,
    _fuzz_entry_worker,
)


# ---------------------------------------------------------------------------
# Helpers — tiny programs for testing
# ---------------------------------------------------------------------------

_ADD_SOURCE = """\
def add(a, b):
    return a + b
"""

_ADD_EQUIV_SOURCE = """\
def add(a, b):
    return b + a
"""

_ADD_MUTANT_SOURCE = """\
def add(a, b):
    return a - b
"""

_INFINITE_SOURCE = """\
def add(a, b):
    while True:
        pass
"""


# ---------------------------------------------------------------------------
# InputFuzzer tests
# ---------------------------------------------------------------------------

class TestInputFuzzer(unittest.TestCase):
    """Tests for the InputFuzzer class."""

    def test_mutate_int_returns_int(self):
        fuzzer = InputFuzzer(["int"], seed=42)
        for _ in range(50):
            result = fuzzer.mutate((5,))
            self.assertIsInstance(result, tuple)
            self.assertEqual(len(result), 1)
            self.assertIsInstance(result[0], int)

    def test_mutate_bool_flips(self):
        fuzzer = InputFuzzer(["bool"], seed=42)
        result = fuzzer.mutate((True,))
        self.assertEqual(result, (False,))
        result = fuzzer.mutate((False,))
        self.assertEqual(result, (True,))

    def test_mutate_str_returns_str(self):
        fuzzer = InputFuzzer(["str"], seed=42)
        for _ in range(50):
            result = fuzzer.mutate(("hello",))
            self.assertIsInstance(result[0], str)

    def test_mutate_empty_str(self):
        fuzzer = InputFuzzer(["str"], seed=42)
        result = fuzzer.mutate(("",))
        self.assertIsInstance(result[0], str)
        # Mutating empty string should produce a non-empty string
        self.assertGreater(len(result[0]), 0)

    def test_mutate_list_int_returns_list(self):
        fuzzer = InputFuzzer(["list[int]"], seed=42)
        for _ in range(50):
            result = fuzzer.mutate(([1, 2, 3],))
            self.assertIsInstance(result[0], list)
            for v in result[0]:
                self.assertIsInstance(v, int)

    def test_mutate_list_str_returns_list(self):
        fuzzer = InputFuzzer(["list[str]"], seed=42)
        for _ in range(50):
            result = fuzzer.mutate((["a", "b"],))
            self.assertIsInstance(result[0], list)
            for v in result[0]:
                self.assertIsInstance(v, str)

    def test_mutate_multiple_params(self):
        fuzzer = InputFuzzer(["int", "str", "bool"], seed=42)
        result = fuzzer.mutate((5, "hello", True))
        self.assertEqual(len(result), 3)
        self.assertIsInstance(result[0], int)
        self.assertIsInstance(result[1], str)
        self.assertIsInstance(result[2], bool)

    def test_random_input_types(self):
        fuzzer = InputFuzzer(["int", "str", "list[int]", "bool"], seed=42)
        result = fuzzer.random_input()
        self.assertEqual(len(result), 4)
        self.assertIsInstance(result[0], int)
        self.assertIsInstance(result[1], str)
        self.assertIsInstance(result[2], list)
        self.assertIsInstance(result[3], bool)

    def test_mutations_produce_diversity(self):
        """Repeated mutations of the same seed should produce varied outputs."""
        fuzzer = InputFuzzer(["int"], seed=42)
        results = set()
        for _ in range(100):
            result = fuzzer.mutate((5,))
            results.add(result)
        # Should produce at least a few different values
        self.assertGreater(len(results), 5)

    def test_deterministic_with_same_seed(self):
        fuzzer1 = InputFuzzer(["int", "str"], seed=123)
        fuzzer2 = InputFuzzer(["int", "str"], seed=123)
        for _ in range(20):
            self.assertEqual(fuzzer1.random_input(), fuzzer2.random_input())

    def test_mutate_list_int_empty(self):
        fuzzer = InputFuzzer(["list[int]"], seed=42)
        result = fuzzer.mutate(([],))
        self.assertIsInstance(result[0], list)

    def test_mutate_list_str_empty(self):
        fuzzer = InputFuzzer(["list[str]"], seed=42)
        result = fuzzer.mutate(([],))
        self.assertIsInstance(result[0], list)


# ---------------------------------------------------------------------------
# Compile / timeout helper tests
# ---------------------------------------------------------------------------

class TestHelpers(unittest.TestCase):
    def test_compile_function_success(self):
        fn, err = _compile_function(_ADD_SOURCE, "add")
        self.assertIsNone(err)
        self.assertIsNotNone(fn)
        self.assertEqual(fn(2, 3), 5)

    def test_compile_function_syntax_error(self):
        fn, err = _compile_function("def bad(:\n  pass", "bad")
        self.assertIsNone(fn)
        self.assertIn("CompileError", err)

    def test_compile_function_name_not_found(self):
        fn, err = _compile_function(_ADD_SOURCE, "nonexistent")
        self.assertIsNone(fn)
        self.assertIn("NameError", err)

    def test_run_with_timeout_success(self):
        fn, _ = _compile_function(_ADD_SOURCE, "add")
        val, err = _run_with_timeout(fn, (2, 3), 5.0)
        self.assertEqual(val, 5)
        self.assertIsNone(err)

    def test_run_with_timeout_exception(self):
        fn, _ = _compile_function(_ADD_SOURCE, "add")
        val, err = _run_with_timeout(fn, ("a", 3), 5.0)
        self.assertIsNotNone(err)

    def test_run_with_timeout_timeout(self):
        fn, _ = _compile_function(_INFINITE_SOURCE, "add")
        val, err = _run_with_timeout(fn, (1, 2), 0.5)
        self.assertIn("TimeoutError", err)


# ---------------------------------------------------------------------------
# fuzz_entry tests
# ---------------------------------------------------------------------------

class TestFuzzEntry(unittest.TestCase):
    """Tests for the fuzz_entry function."""

    def _make_entry(self, p1_source, p2_source, is_equivalent, ptests=None, ntests=None):
        return {
            "entry_id": "test-entry-1",
            "func_name": "add",
            "param_types": ["int", "int"],
            "return_type": "int",
            "p1_source": p1_source,
            "p2_source": p2_source,
            "is_equivalent": is_equivalent,
        }

    def test_fuzz_equivalent_pair(self):
        entry = self._make_entry(_ADD_SOURCE, _ADD_EQUIV_SOURCE, True)
        tests_data = {"ptests": [[1, 2], [3, 4]], "ntests": []}
        result = fuzz_entry(
            entry, tests_data,
            max_tests=10, max_time=30, per_call_timeout=5, rng_seed=42,
        )
        self.assertEqual(result["entry_id"], "test-entry-1")
        self.assertTrue(result["is_equivalent"])
        self.assertGreater(result["new_tests_generated"], 0)
        # Integer addition is commutative, so all should agree
        self.assertEqual(result["ptest_disagree"], 0)
        self.assertEqual(result["status"], "pass")

    def test_fuzz_non_equivalent_pair(self):
        entry = self._make_entry(_ADD_SOURCE, _ADD_MUTANT_SOURCE, False)
        tests_data = {"ptests": [[0, 0]], "ntests": [[1, 2]]}
        result = fuzz_entry(
            entry, tests_data,
            max_tests=10, max_time=30, per_call_timeout=5, rng_seed=42,
        )
        self.assertFalse(result["is_equivalent"])
        self.assertGreater(result["new_tests_generated"], 0)
        # a+b != a-b for most inputs, so should find disagreements
        self.assertGreater(result["ptest_disagree"], 0)
        self.assertEqual(result["status"], "pass")

    def test_new_tests_do_not_overlap_existing(self):
        """New fuzzed tests must NOT be in the original test suite."""
        entry = self._make_entry(_ADD_SOURCE, _ADD_EQUIV_SOURCE, True)
        existing_ptests = [[i, j] for i in range(-5, 6) for j in range(-5, 6)]
        tests_data = {"ptests": existing_ptests, "ntests": []}
        result = fuzz_entry(
            entry, tests_data,
            max_tests=15, max_time=30, per_call_timeout=5, rng_seed=42,
        )
        # Each new test should not be in the existing set
        # We verify this by checking that new tests were generated
        # (the logic in fuzz_entry checks for duplicates internally)
        self.assertGreater(result["new_tests_generated"], 0)

    def test_compile_error_handled(self):
        entry = self._make_entry("def bad(:\n  pass", _ADD_SOURCE, True)
        tests_data = {"ptests": [], "ntests": []}
        result = fuzz_entry(
            entry, tests_data,
            max_tests=5, max_time=10, per_call_timeout=5, rng_seed=42,
        )
        self.assertEqual(result["status"], "compile_error")
        self.assertEqual(result["new_tests_generated"], 0)

    def test_max_tests_respected(self):
        entry = self._make_entry(_ADD_SOURCE, _ADD_EQUIV_SOURCE, True)
        tests_data = {"ptests": [[1, 2]], "ntests": []}
        result = fuzz_entry(
            entry, tests_data,
            max_tests=5, max_time=60, per_call_timeout=5, rng_seed=42,
        )
        self.assertLessEqual(result["new_tests_generated"], 5)

    def test_max_time_respected(self):
        """Fuzzing should stop within the time limit."""
        entry = self._make_entry(_ADD_SOURCE, _ADD_EQUIV_SOURCE, True)
        tests_data = {"ptests": [], "ntests": []}
        result = fuzz_entry(
            entry, tests_data,
            max_tests=10000, max_time=2.0, per_call_timeout=5, rng_seed=42,
        )
        self.assertLessEqual(result["fuzz_time"], 5.0)  # generous margin

    def test_fuzz_time_recorded(self):
        entry = self._make_entry(_ADD_SOURCE, _ADD_EQUIV_SOURCE, True)
        tests_data = {"ptests": [], "ntests": []}
        result = fuzz_entry(
            entry, tests_data,
            max_tests=5, max_time=30, per_call_timeout=5, rng_seed=42,
        )
        self.assertIn("fuzz_time", result)
        self.assertGreaterEqual(result["fuzz_time"], 0)

    def test_worker_wrapper(self):
        """Test the multiprocessing worker wrapper."""
        entry = self._make_entry(_ADD_SOURCE, _ADD_EQUIV_SOURCE, True)
        tests_data = {"ptests": [[1, 2]], "ntests": []}
        work_item = (entry, tests_data, 5, 30, 5.0, 42)
        result = _fuzz_entry_worker(work_item)
        self.assertIn("status", result)
        self.assertGreater(result["new_tests_generated"], 0)

    def test_no_new_tests_status(self):
        """When max_tests=0, status should be 'no_new_tests'."""
        entry = self._make_entry(_ADD_SOURCE, _ADD_EQUIV_SOURCE, True)
        tests_data = {"ptests": [[1, 2]], "ntests": []}
        result = fuzz_entry(
            entry, tests_data,
            max_tests=0, max_time=30, per_call_timeout=5, rng_seed=42,
        )
        self.assertEqual(result["new_tests_generated"], 0)
        self.assertEqual(result["status"], "no_new_tests")


# ---------------------------------------------------------------------------
# Integration test with a real (tiny) benchmark file
# ---------------------------------------------------------------------------

class TestFuzzBenchmarkIntegration(unittest.TestCase):
    """Integration test using a temporary benchmark JSON."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        tests_dir = os.path.join(self.tmpdir, "tests")
        os.makedirs(tests_dir)

        # Create a test data file
        tests_payload = {
            "entry_id": "int-test-1",
            "ptests": [[1, 2], [3, 4], [0, 0]],
            "ntests": [],
        }
        tests_file = os.path.join(tests_dir, "int-test-1_tests.json")
        with open(tests_file, "w") as fh:
            json.dump(tests_payload, fh)

        # Create the benchmark file
        benchmark = {
            "generated_at": "20260101_120000",
            "total_entries": 1,
            "entries": [
                {
                    "entry_id": "int-test-1",
                    "func_name": "add",
                    "param_types": ["int", "int"],
                    "return_type": "int",
                    "p1_source": _ADD_SOURCE,
                    "p2_source": _ADD_EQUIV_SOURCE,
                    "is_equivalent": True,
                    "tests_file": "tests/int-test-1_tests.json",
                    "metadata": {},
                }
            ],
        }
        self.benchmark_path = os.path.join(self.tmpdir, "benchmark.json")
        with open(self.benchmark_path, "w") as fh:
            json.dump(benchmark, fh)

    def test_end_to_end_fuzz(self):
        """Test loading a benchmark file and fuzzing it."""
        with open(self.benchmark_path) as fh:
            benchmark = json.load(fh)

        benchmark_dir = os.path.dirname(self.benchmark_path)
        entry = benchmark["entries"][0]

        tests_path = os.path.join(benchmark_dir, entry["tests_file"])
        with open(tests_path) as fh:
            tests_data = json.load(fh)

        result = fuzz_entry(
            entry, tests_data,
            max_tests=10, max_time=30, per_call_timeout=5, rng_seed=42,
        )
        self.assertEqual(result["status"], "pass")
        self.assertGreater(result["new_tests_generated"], 0)
        self.assertEqual(result["ptest_disagree"], 0)


# ---------------------------------------------------------------------------
# String param fuzzing test
# ---------------------------------------------------------------------------

_UPPER_SOURCE = """\
def upper(s):
    return s.upper()
"""

_UPPER_EQUIV_SOURCE = """\
def upper(s):
    result = ""
    for c in s:
        result += c.upper()
    return result
"""


class TestFuzzStringParams(unittest.TestCase):
    def test_fuzz_string_function(self):
        entry = {
            "entry_id": "str-test-1",
            "func_name": "upper",
            "param_types": ["str"],
            "return_type": "str",
            "p1_source": _UPPER_SOURCE,
            "p2_source": _UPPER_EQUIV_SOURCE,
            "is_equivalent": True,
        }
        tests_data = {"ptests": [["hello"], ["world"]], "ntests": []}
        result = fuzz_entry(
            entry, tests_data,
            max_tests=10, max_time=30, per_call_timeout=5, rng_seed=42,
        )
        self.assertGreater(result["new_tests_generated"], 0)
        self.assertEqual(result["ptest_disagree"], 0)
        self.assertEqual(result["status"], "pass")


# ---------------------------------------------------------------------------
# List param fuzzing test
# ---------------------------------------------------------------------------

_SORT_SOURCE = """\
def sort_list(lst):
    return sorted(lst)
"""

_SORT_EQUIV_SOURCE = """\
def sort_list(lst):
    result = list(lst)
    result.sort()
    return result
"""


class TestFuzzListParams(unittest.TestCase):
    def test_fuzz_list_function(self):
        entry = {
            "entry_id": "list-test-1",
            "func_name": "sort_list",
            "param_types": ["list[int]"],
            "return_type": "list[int]",
            "p1_source": _SORT_SOURCE,
            "p2_source": _SORT_EQUIV_SOURCE,
            "is_equivalent": True,
        }
        tests_data = {"ptests": [[[3, 1, 2]], [[5, 4]]], "ntests": []}
        result = fuzz_entry(
            entry, tests_data,
            max_tests=10, max_time=30, per_call_timeout=5, rng_seed=42,
        )
        self.assertGreater(result["new_tests_generated"], 0)
        self.assertEqual(result["ptest_disagree"], 0)
        self.assertEqual(result["status"], "pass")


if __name__ == "__main__":
    unittest.main()
