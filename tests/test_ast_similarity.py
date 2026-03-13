"""Tests for benchmark_generator.ast_similarity."""

import pytest

from benchmark_generator.ast_similarity import (
    ast_similarity,
    _ast_to_sequence,
    _edit_distance,
)


class TestAstToSequence:
    def test_simple_function(self):
        import ast

        tree = ast.parse("def f(x): return x")
        seq = _ast_to_sequence(tree)
        assert len(seq) > 0
        assert seq[0] == "Module"
        assert "FunctionDef:->:(f)" in seq
        assert "Return" in seq

    def test_empty_module(self):
        import ast

        tree = ast.parse("")
        seq = _ast_to_sequence(tree)
        # An empty module still has the Module node
        assert seq == ["Module"]

    def test_identical_code_same_sequence(self):
        import ast

        code = "def f(x):\n    return x + 1"
        tree1 = ast.parse(code)
        tree2 = ast.parse(code)
        assert _ast_to_sequence(tree1) == _ast_to_sequence(tree2)


class TestEditDistance:
    def test_identical_sequences(self):
        assert _edit_distance(["a", "b", "c"], ["a", "b", "c"]) == 0

    def test_empty_sequences(self):
        assert _edit_distance([], []) == 0

    def test_one_empty(self):
        assert _edit_distance(["a", "b"], []) == 2
        assert _edit_distance([], ["a", "b"]) == 2

    def test_single_substitution(self):
        assert _edit_distance(["a", "b", "c"], ["a", "x", "c"]) == 1

    def test_single_insertion(self):
        assert _edit_distance(["a", "c"], ["a", "b", "c"]) == 1

    def test_single_deletion(self):
        assert _edit_distance(["a", "b", "c"], ["a", "c"]) == 1

    def test_completely_different(self):
        assert _edit_distance(["a", "b"], ["c", "d"]) == 2


class TestAstSimilarity:
    def test_identical_code_returns_one(self):
        code = "def f(x):\n    return x + 1"
        assert ast_similarity(code, code) == 1.0

    def test_completely_different_code(self):
        code1 = "x = 1"
        code2 = (
            "def f(a, b, c):\n"
            "    result = []\n"
            "    for i in range(a):\n"
            "        for j in range(b):\n"
            "            if i + j > c:\n"
            "                result.append((i, j))\n"
            "    return result"
        )
        sim = ast_similarity(code1, code2)
        assert sim < 0.3

    def test_similar_code_high_similarity(self):
        code1 = "def f(x): return x + 1"
        code2 = "def f(x): return x + 2"
        sim = ast_similarity(code1, code2)
        assert sim > 0.8

    def test_structurally_different_equivalent_code(self):
        # Iterative vs recursive — very different structure
        code1 = (
            "def f(n):\n"
            "    if n <= 1:\n"
            "        return 1\n"
            "    return n * f(n - 1)"
        )
        code2 = (
            "def f(n):\n"
            "    result = 1\n"
            "    for i in range(2, n + 1):\n"
            "        result *= i\n"
            "    return result"
        )
        sim = ast_similarity(code1, code2)
        assert sim < 0.9  # structurally different

    def test_syntax_error_returns_zero(self):
        assert ast_similarity("def f(: broken", "def f(x): return x") == 0.0
        assert ast_similarity("def f(x): return x", "def f(: broken") == 0.0

    def test_both_syntax_errors_returns_zero(self):
        assert ast_similarity("broken1 +++", "broken2 ---") == 0.0

    def test_symmetry(self):
        code1 = "def f(x): return x * 2"
        code2 = (
            "def f(x):\n"
            "    result = 0\n"
            "    for i in range(2):\n"
            "        result += x\n"
            "    return result"
        )
        assert ast_similarity(code1, code2) == ast_similarity(code2, code1)

    def test_returns_float_in_range(self):
        code1 = "def f(x): return x"
        code2 = "def g(x, y): return x + y"
        sim = ast_similarity(code1, code2)
        assert 0.0 <= sim <= 1.0

    def test_empty_sources(self):
        # Two empty strings parse to identical Module nodes
        assert ast_similarity("", "") == 1.0

