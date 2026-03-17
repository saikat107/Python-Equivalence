"""Tests for the src/fuzzer package."""

from __future__ import annotations

import textwrap

import pytest

from fuzzer.type_parser import (
    FunctionSignature,
    TypeNode,
    extract_function_signature,
    list_functions,
    _parse_annotation_node,
)
from fuzzer.value_generator import ValueGenerator
from fuzzer.fuzz_function import fuzz_function
from fuzzer.equivalence_checker import check_equivalence, signatures_compatible


# ===================================================================
# type_parser tests
# ===================================================================


class TestTypeNode:
    def test_simple_equality(self):
        assert TypeNode("int") == TypeNode("int")
        assert TypeNode("int") != TypeNode("str")

    def test_nested_equality(self):
        t1 = TypeNode("list", [TypeNode("int")])
        t2 = TypeNode("list", [TypeNode("int")])
        assert t1 == t2

    def test_variadic_tuple(self):
        t = TypeNode("tuple", [TypeNode("int")], is_variadic=True)
        assert t.is_variadic
        assert repr(t) == "tuple[int, ...]"

    def test_repr_simple(self):
        assert repr(TypeNode("int")) == "int"
        assert repr(TypeNode("str")) == "str"

    def test_repr_parameterised(self):
        t = TypeNode("dict", [TypeNode("str"), TypeNode("int")])
        assert repr(t) == "dict[str, int]"

    def test_hash(self):
        t1 = TypeNode("int")
        t2 = TypeNode("int")
        assert hash(t1) == hash(t2)
        s = {t1, t2}
        assert len(s) == 1


class TestParseAnnotation:
    """Test _parse_annotation_node via extract_function_signature."""

    def _parse(self, annotation_str: str) -> TypeNode:
        src = f"def f(x: {annotation_str}) -> None: pass"
        sig = extract_function_signature(src, "f")
        return sig.params[0][1]

    def test_int(self):
        assert self._parse("int") == TypeNode("int")

    def test_float(self):
        assert self._parse("float") == TypeNode("float")

    def test_str(self):
        assert self._parse("str") == TypeNode("str")

    def test_bool(self):
        assert self._parse("bool") == TypeNode("bool")

    def test_list_int(self):
        assert self._parse("list[int]") == TypeNode("list", [TypeNode("int")])

    def test_dict_str_int(self):
        expected = TypeNode("dict", [TypeNode("str"), TypeNode("int")])
        assert self._parse("dict[str, int]") == expected

    def test_tuple_fixed(self):
        expected = TypeNode(
            "tuple", [TypeNode("str"), TypeNode("str"), TypeNode("bool")]
        )
        assert self._parse("tuple[str, str, bool]") == expected

    def test_tuple_variadic(self):
        expected = TypeNode("tuple", [TypeNode("int")], is_variadic=True)
        assert self._parse("tuple[int, ...]") == expected

    def test_set_int(self):
        assert self._parse("set[int]") == TypeNode("set", [TypeNode("int")])

    def test_complex_nested(self):
        """dict[str, list[tuple[str, str, bool]]]"""
        expected = TypeNode(
            "dict",
            [
                TypeNode("str"),
                TypeNode(
                    "list",
                    [
                        TypeNode(
                            "tuple",
                            [TypeNode("str"), TypeNode("str"), TypeNode("bool")],
                        )
                    ],
                ),
            ],
        )
        assert self._parse("dict[str, list[tuple[str, str, bool]]]") == expected

    def test_optional(self):
        expected = TypeNode("Optional", [TypeNode("int")])
        assert self._parse("Optional[int]") == expected

    def test_typing_list(self):
        """Typing module alias List should normalise to list."""
        assert self._parse("List[int]") == TypeNode("list", [TypeNode("int")])

    def test_typing_dict(self):
        expected = TypeNode("dict", [TypeNode("str"), TypeNode("int")])
        assert self._parse("Dict[str, int]") == expected


class TestExtractSignature:
    def test_basic(self):
        src = "def add(x: int, y: int) -> int: return x + y"
        sig = extract_function_signature(src, "add")
        assert sig.name == "add"
        assert len(sig.params) == 2
        assert sig.params[0] == ("x", TypeNode("int"))
        assert sig.params[1] == ("y", TypeNode("int"))
        assert sig.return_type == TypeNode("int")

    def test_no_return(self):
        src = "def greet(name: str): print(name)"
        sig = extract_function_signature(src, "greet")
        assert sig.return_type is None

    def test_complex(self):
        src = textwrap.dedent("""\
            def process(data: dict[str, list[tuple[str, str, bool]]]) -> int:
                return 0
        """)
        sig = extract_function_signature(src, "process")
        assert len(sig.params) == 1
        param_type = sig.params[0][1]
        assert param_type.name == "dict"
        assert len(param_type.args) == 2
        assert param_type.args[0] == TypeNode("str")
        inner_list = param_type.args[1]
        assert inner_list.name == "list"
        inner_tuple = inner_list.args[0]
        assert inner_tuple.name == "tuple"
        assert len(inner_tuple.args) == 3

    def test_function_not_found(self):
        with pytest.raises(ValueError, match="not found"):
            extract_function_signature("def foo(): pass", "bar")

    def test_skips_self(self):
        src = textwrap.dedent("""\
            class Foo:
                def method(self, x: int) -> int:
                    return x
        """)
        sig = extract_function_signature(src, "method")
        assert len(sig.params) == 1
        assert sig.params[0] == ("x", TypeNode("int"))

    def test_future_annotations(self):
        src = textwrap.dedent("""\
            from __future__ import annotations

            def add(x: int, y: int) -> int:
                return x + y
        """)
        sig = extract_function_signature(src, "add")
        assert sig.params[0][1] == TypeNode("int")
        assert sig.return_type == TypeNode("int")


class TestListFunctions:
    def test_basic(self):
        src = "def foo(): pass\ndef bar(): pass\nx = 1"
        assert list_functions(src) == ["foo", "bar"]

    def test_empty(self):
        assert list_functions("x = 1") == []


# ===================================================================
# value_generator tests
# ===================================================================


class TestValueGenerator:
    def test_int(self):
        gen = ValueGenerator(seed=42)
        val = gen.generate(TypeNode("int"))
        assert isinstance(val, int)

    def test_float(self):
        gen = ValueGenerator(seed=42)
        val = gen.generate(TypeNode("float"))
        assert isinstance(val, float)

    def test_str(self):
        gen = ValueGenerator(seed=42)
        val = gen.generate(TypeNode("str"))
        assert isinstance(val, str)

    def test_bool(self):
        gen = ValueGenerator(seed=42)
        val = gen.generate(TypeNode("bool"))
        assert isinstance(val, bool)

    def test_none(self):
        gen = ValueGenerator(seed=42)
        val = gen.generate(TypeNode("None"))
        assert val is None

    def test_list_int(self):
        gen = ValueGenerator(seed=42)
        val = gen.generate(TypeNode("list", [TypeNode("int")]))
        assert isinstance(val, list)
        for item in val:
            assert isinstance(item, int)

    def test_dict_str_int(self):
        gen = ValueGenerator(seed=42)
        val = gen.generate(TypeNode("dict", [TypeNode("str"), TypeNode("int")]))
        assert isinstance(val, dict)
        for k, v in val.items():
            assert isinstance(k, str)
            assert isinstance(v, int)

    def test_tuple_fixed(self):
        gen = ValueGenerator(seed=42)
        t = TypeNode("tuple", [TypeNode("str"), TypeNode("int"), TypeNode("bool")])
        val = gen.generate(t)
        assert isinstance(val, tuple)
        assert len(val) == 3
        assert isinstance(val[0], str)
        assert isinstance(val[1], int)
        assert isinstance(val[2], bool)

    def test_tuple_variadic(self):
        gen = ValueGenerator(seed=42)
        t = TypeNode("tuple", [TypeNode("int")], is_variadic=True)
        val = gen.generate(t)
        assert isinstance(val, tuple)
        for item in val:
            assert isinstance(item, int)

    def test_set_int(self):
        gen = ValueGenerator(seed=42)
        val = gen.generate(TypeNode("set", [TypeNode("int")]))
        assert isinstance(val, set)
        for item in val:
            assert isinstance(item, int)

    def test_optional_int(self):
        gen = ValueGenerator(seed=42)
        t = TypeNode("Optional", [TypeNode("int")])
        vals = [gen.generate(t) for _ in range(100)]
        # Should produce both None and int values
        assert any(v is None for v in vals)
        assert any(isinstance(v, int) for v in vals)

    def test_complex_nested(self):
        """dict[str, list[tuple[str, str, bool]]]"""
        gen = ValueGenerator(seed=42)
        t = TypeNode(
            "dict",
            [
                TypeNode("str"),
                TypeNode(
                    "list",
                    [
                        TypeNode(
                            "tuple",
                            [TypeNode("str"), TypeNode("str"), TypeNode("bool")],
                        )
                    ],
                ),
            ],
        )
        val = gen.generate(t)
        assert isinstance(val, dict)
        for k, v in val.items():
            assert isinstance(k, str)
            assert isinstance(v, list)
            for item in v:
                assert isinstance(item, tuple)
                assert len(item) == 3
                assert isinstance(item[0], str)
                assert isinstance(item[1], str)
                assert isinstance(item[2], bool)

    def test_generate_inputs_deduplication(self):
        gen = ValueGenerator(seed=42)
        inputs = gen.generate_inputs([TypeNode("bool")], n=10)
        # bool has only 2 values, so we should get at most 2 unique
        assert len(inputs) == 2

    def test_generate_inputs_count(self):
        gen = ValueGenerator(seed=42)
        inputs = gen.generate_inputs([TypeNode("int")], n=50)
        assert len(inputs) == 50


# ===================================================================
# fuzz_function tests
# ===================================================================


class TestFuzzFunction:
    def test_basic(self):
        src = textwrap.dedent("""\
            def double(x: int) -> int:
                return x * 2
        """)
        results = fuzz_function(src, "double", num_inputs=10, seed=42)
        assert len(results) == 10
        for r in results:
            assert r["error"] is None
            assert r["output"] == r["input"][0] * 2

    def test_error_handling(self):
        src = textwrap.dedent("""\
            def divide(x: int, y: int) -> float:
                return x / y
        """)
        results = fuzz_function(src, "divide", num_inputs=50, seed=42)
        # Some inputs will have y=0 causing ZeroDivisionError
        errors = [r for r in results if r["error"] is not None]
        successes = [r for r in results if r["error"] is None]
        assert len(successes) > 0  # most should work
        # At least check structure
        for r in results:
            assert "input" in r
            assert "output" in r
            assert "error" in r

    def test_complex_type(self):
        src = textwrap.dedent("""\
            def count_keys(d: dict[str, list[int]]) -> int:
                return len(d)
        """)
        results = fuzz_function(src, "count_keys", num_inputs=10, seed=42)
        assert len(results) == 10
        for r in results:
            assert r["error"] is None
            assert isinstance(r["output"], int)


# ===================================================================
# equivalence_checker tests
# ===================================================================


class TestSignaturesCompatible:
    def test_compatible(self):
        sig1 = FunctionSignature(
            "f", [("x", TypeNode("int"))], TypeNode("int")
        )
        sig2 = FunctionSignature(
            "g", [("y", TypeNode("int"))], TypeNode("int")
        )
        ok, _ = signatures_compatible(sig1, sig2)
        assert ok

    def test_param_count_mismatch(self):
        sig1 = FunctionSignature(
            "f", [("x", TypeNode("int"))], TypeNode("int")
        )
        sig2 = FunctionSignature(
            "g",
            [("x", TypeNode("int")), ("y", TypeNode("int"))],
            TypeNode("int"),
        )
        ok, reason = signatures_compatible(sig1, sig2)
        assert not ok
        assert "count" in reason.lower()

    def test_param_type_mismatch(self):
        sig1 = FunctionSignature(
            "f", [("x", TypeNode("int"))], TypeNode("int")
        )
        sig2 = FunctionSignature(
            "g", [("x", TypeNode("str"))], TypeNode("int")
        )
        ok, reason = signatures_compatible(sig1, sig2)
        assert not ok
        assert "mismatch" in reason.lower()

    def test_return_type_mismatch(self):
        sig1 = FunctionSignature(
            "f", [("x", TypeNode("int"))], TypeNode("int")
        )
        sig2 = FunctionSignature(
            "g", [("x", TypeNode("int"))], TypeNode("str")
        )
        ok, reason = signatures_compatible(sig1, sig2)
        assert not ok
        assert "return" in reason.lower()


class TestCheckEquivalence:
    def test_equivalent_functions(self):
        src = textwrap.dedent("""\
            def sort_a(nums: list[int]) -> list[int]:
                return sorted(nums)

            def sort_b(nums: list[int]) -> list[int]:
                result = list(nums)
                result.sort()
                return result
        """)
        result = check_equivalence(
            src, "sort_a", src, "sort_b",
            num_inputs=200, time_limit=10, seed=42,
        )
        assert result["equivalent"] is True
        assert result["compatible"] is True
        assert result["inputs_tested"] > 0
        assert result["counterexample"] is None

    def test_non_equivalent_functions(self):
        src = textwrap.dedent("""\
            def add(x: int, y: int) -> int:
                return x + y

            def multiply(x: int, y: int) -> int:
                return x * y
        """)
        result = check_equivalence(
            src, "add", src, "multiply",
            num_inputs=200, time_limit=10, seed=42,
        )
        assert result["equivalent"] is False
        assert result["counterexample"] is not None
        cx = result["counterexample"]
        assert cx["output1"] != cx["output2"]

    def test_incompatible_signatures(self):
        src1 = "def f(x: int) -> int: return x"
        src2 = "def g(x: str) -> str: return x"
        result = check_equivalence(src1, "f", src2, "g")
        assert result["equivalent"] is None
        assert result["compatible"] is False

    def test_complex_equivalent(self):
        """Test with complex types."""
        src = textwrap.dedent("""\
            def keys_a(d: dict[str, int]) -> list[str]:
                return sorted(d.keys())

            def keys_b(d: dict[str, int]) -> list[str]:
                result = list(d.keys())
                result.sort()
                return result
        """)
        result = check_equivalence(
            src, "keys_a", src, "keys_b",
            num_inputs=100, time_limit=10, seed=42,
        )
        assert result["equivalent"] is True


# ===================================================================
# ValueGenerator hints + mutate tests
# ===================================================================


class TestValueGeneratorHints:
    """Test hint-aware generation and the mutate() method."""

    def _make_hints(self, int_vals=(), float_vals=(), str_vals=()):
        """Build a minimal duck-typed hints object."""
        class FakeHints:
            def boundary_ints(self):
                return list(int_vals)
            def boundary_floats(self):
                return list(float_vals)
            @property
            def str_constants(self):
                return set(str_vals)
        return FakeHints()

    def test_int_hint_used(self):
        hints = self._make_hints(int_vals=[999])
        gen = ValueGenerator(seed=0, hints=hints)
        # Generate many ints; with 30% probability each will be 999
        vals = [gen._gen_int() for _ in range(300)]
        assert 999 in vals, "hint int value should appear in generated ints"

    def test_float_hint_used(self):
        hints = self._make_hints(float_vals=[3.14])
        gen = ValueGenerator(seed=0, hints=hints)
        vals = [gen._gen_float() for _ in range(300)]
        assert 3.14 in vals, "hint float value should appear in generated floats"

    def test_str_hint_used(self):
        hints = self._make_hints(str_vals=["sentinel"])
        gen = ValueGenerator(seed=0, hints=hints)
        vals = [gen._gen_str() for _ in range(300)]
        assert "sentinel" in vals, "hint string value should appear in generated strs"

    def test_no_hints_unchanged_types(self):
        gen = ValueGenerator(seed=42, hints=None)
        assert isinstance(gen._gen_int(), int)
        assert isinstance(gen._gen_float(), float)
        assert isinstance(gen._gen_str(), str)

    def test_mutate_returns_tuple(self):
        gen = ValueGenerator(seed=42)
        param_types = [TypeNode("int"), TypeNode("str")]
        inp = (7, "hello")
        mutated = gen.mutate(inp, param_types)
        assert isinstance(mutated, tuple)
        assert len(mutated) == 2
        assert isinstance(mutated[0], int)
        assert isinstance(mutated[1], str)

    def test_mutate_bool_flips(self):
        gen = ValueGenerator(seed=0)
        param_types = [TypeNode("bool")]
        # Force the mutation branch: run many times and expect both values
        results = set()
        for _ in range(200):
            results.add(gen.mutate((True,), param_types)[0])
        assert True in results
        assert False in results

    def test_mutate_int_stays_int(self):
        gen = ValueGenerator(seed=42)
        pt = [TypeNode("int")]
        for _ in range(50):
            val = gen.mutate((10,), pt)[0]
            assert isinstance(val, int)

    def test_mutate_list_changes_length(self):
        gen = ValueGenerator(seed=42)
        pt = [TypeNode("list", [TypeNode("int")])]
        original = [1, 2, 3]
        lengths = set()
        for _ in range(100):
            result = gen.mutate((original,), pt)[0]
            assert isinstance(result, list)
            lengths.add(len(result))
        # Expect at least two distinct lengths
        assert len(lengths) > 1, "mutate should sometimes add/remove list elements"


# ===================================================================
# Coverage-guided fuzz_function tests
# ===================================================================


class TestFuzzFunctionCoverageGuided:
    def test_returns_correct_count(self):
        src = textwrap.dedent("""\
            def classify(x: int) -> str:
                if x < 0:
                    return "negative"
                elif x == 0:
                    return "zero"
                else:
                    return "positive"
        """)
        results = fuzz_function(
            src, "classify", num_inputs=20, seed=42, coverage_guided=True
        )
        assert len(results) == 20

    def test_result_structure(self):
        src = textwrap.dedent("""\
            def double(x: int) -> int:
                return x * 2
        """)
        results = fuzz_function(
            src, "double", num_inputs=10, seed=1, coverage_guided=True
        )
        for r in results:
            assert "input" in r
            assert "output" in r
            assert "error" in r

    def test_correct_outputs(self):
        src = textwrap.dedent("""\
            def double(x: int) -> int:
                return x * 2
        """)
        results = fuzz_function(
            src, "double", num_inputs=15, seed=7, coverage_guided=True
        )
        for r in results:
            if r["error"] is None:
                assert r["output"] == r["input"][0] * 2

    def test_random_mode_structure_matches_coverage_guided(self):
        """Results from random mode should have the same structure as coverage mode."""
        src = textwrap.dedent("""\
            def inc(x: int) -> int:
                return x + 1
        """)
        r_random = fuzz_function(src, "inc", num_inputs=10, seed=42, coverage_guided=False)
        r_guided = fuzz_function(src, "inc", num_inputs=10, seed=42, coverage_guided=True)
        assert len(r_random) == len(r_guided)
        for r in r_guided:
            assert set(r.keys()) == {"input", "output", "error"}


# ===================================================================
# Coverage-guided check_equivalence tests
# ===================================================================


class TestCheckEquivalenceCoverageGuided:
    def test_equivalent_functions(self):
        src = textwrap.dedent("""\
            def sort_a(nums: list[int]) -> list[int]:
                return sorted(nums)

            def sort_b(nums: list[int]) -> list[int]:
                result = list(nums)
                result.sort()
                return result
        """)
        result = check_equivalence(
            src, "sort_a", src, "sort_b",
            num_inputs=100, time_limit=10, seed=42,
            coverage_guided=True,
        )
        assert result["equivalent"] is True
        assert result["compatible"] is True
        assert result["counterexample"] is None
        assert "coverage_lines" in result
        assert "coverage_branches" in result
        assert result["coverage_lines"] >= 0
        assert result["coverage_branches"] >= 0

    def test_non_equivalent_functions(self):
        src = textwrap.dedent("""\
            def add(x: int, y: int) -> int:
                return x + y

            def multiply(x: int, y: int) -> int:
                return x * y
        """)
        result = check_equivalence(
            src, "add", src, "multiply",
            num_inputs=500, time_limit=10, seed=42,
            coverage_guided=True,
        )
        assert result["equivalent"] is False
        assert result["counterexample"] is not None
        assert "coverage_lines" in result

    def test_incompatible_signatures_unaffected(self):
        src1 = "def f(x: int) -> int: return x"
        src2 = "def g(x: str) -> str: return x"
        result = check_equivalence(
            src1, "f", src2, "g", coverage_guided=True
        )
        assert result["equivalent"] is None
        assert result["compatible"] is False
        # No coverage stats when signatures are incompatible
        assert "coverage_lines" not in result

    def test_coverage_stats_present_on_success(self):
        src = textwrap.dedent("""\
            def identity(x: int) -> int:
                return x
        """)
        result = check_equivalence(
            src, "identity", src, "identity",
            num_inputs=20, time_limit=5, seed=0,
            coverage_guided=True,
        )
        assert result["equivalent"] is True
        assert isinstance(result["coverage_lines"], int)
        assert isinstance(result["coverage_branches"], int)
