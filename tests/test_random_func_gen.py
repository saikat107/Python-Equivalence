"""Tests for equivalence_benchmarks.random_func_gen (RandomFunctionGenerator)."""

import ast
import pytest
from equivalence_benchmarks.random_func_gen import RandomFunctionGenerator


class TestRandomFunctionGenerator:
    """Unit tests for the AST-based random function generator."""

    def test_generates_requested_count(self):
        gen = RandomFunctionGenerator(seed=0)
        specs = gen.generate(n=8)
        assert len(specs) == 8

    def test_names_are_unique(self):
        gen = RandomFunctionGenerator(seed=0)
        specs = gen.generate(n=15)
        names = [s["name"] for s in specs]
        assert len(names) == len(set(names))

    def test_all_sources_valid_python(self):
        gen = RandomFunctionGenerator(seed=42)
        specs = gen.generate(n=10)
        for spec in specs:
            for src in (
                [spec["source"]]
                + list(spec["equivalents"])
                + [m["source"] for m in spec["mutations"]]
            ):
                try:
                    ast.parse(src)
                except SyntaxError as exc:
                    pytest.fail(f"SyntaxError in {spec['name']}: {exc}\n{src}")

    def test_required_fields_present(self):
        gen = RandomFunctionGenerator(seed=7)
        specs = gen.generate(n=5)
        required = {
            "name", "source", "equivalents", "mutations",
            "param_types", "return_type", "category",
        }
        for spec in specs:
            missing = required - spec.keys()
            assert not missing, f"Missing fields in spec: {missing}"

    def test_deterministic_with_same_seed(self):
        gen1 = RandomFunctionGenerator(seed=123)
        gen2 = RandomFunctionGenerator(seed=123)
        s1 = gen1.generate(n=8)
        s2 = gen2.generate(n=8)
        names1 = [s["name"] for s in s1]
        names2 = [s["name"] for s in s2]
        assert names1 == names2

    def test_different_seeds_differ(self):
        gen1 = RandomFunctionGenerator(seed=1)
        gen2 = RandomFunctionGenerator(seed=99)
        s1 = gen1.generate(n=5)
        s2 = gen2.generate(n=5)
        names1 = {s["name"] for s in s1}
        names2 = {s["name"] for s in s2}
        # Very unlikely the same random names appear with different seeds
        assert names1 != names2

    def test_function_name_in_all_sources(self):
        gen = RandomFunctionGenerator(seed=1)
        specs = gen.generate(n=5)
        for spec in specs:
            expected = spec["name"]
            for src in (
                [spec["source"]]
                + list(spec["equivalents"])
                + [m["source"] for m in spec["mutations"]]
            ):
                tree = ast.parse(src)
                funcs = [
                    n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
                ]
                assert expected in funcs, (
                    f"Function '{expected}' not defined in:\n{src}"
                )

    def test_minimum_loc_enforced(self):
        gen = RandomFunctionGenerator(seed=42, min_loc=20)
        specs = gen.generate(n=10)
        for spec in specs:
            for label, src in [("source", spec["source"])] + [
                (f"equiv_{i}", e) for i, e in enumerate(spec["equivalents"])
            ] + [
                (f"mut_{i}", m["source"]) for i, m in enumerate(spec["mutations"])
            ]:
                lines = [ln for ln in src.strip().split("\n") if ln.strip()]
                assert len(lines) >= 20, (
                    f"{spec['name']} {label} has only {len(lines)} LOC:\n{src}"
                )

    def test_at_least_two_equivalents(self):
        gen = RandomFunctionGenerator(seed=5)
        specs = gen.generate(n=10)
        for spec in specs:
            assert len(spec["equivalents"]) >= 2, (
                f"{spec['name']} has only {len(spec['equivalents'])} equivalents"
            )

    def test_at_least_two_mutations(self):
        gen = RandomFunctionGenerator(seed=5)
        specs = gen.generate(n=10)
        for spec in specs:
            assert len(spec["mutations"]) >= 2, (
                f"{spec['name']} has only {len(spec['mutations'])} mutations"
            )

    def test_mutations_have_description(self):
        gen = RandomFunctionGenerator(seed=3)
        specs = gen.generate(n=5)
        for spec in specs:
            for mut in spec["mutations"]:
                assert "source" in mut
                assert "description" in mut
                assert len(mut["description"]) > 0

    def test_category_starts_with_random_ast(self):
        gen = RandomFunctionGenerator(seed=10)
        specs = gen.generate(n=5)
        for spec in specs:
            assert spec["category"].startswith("random_ast_"), (
                f"Unexpected category: {spec['category']}"
            )

    def test_equivalents_match_on_sample_inputs(self):
        """Equivalents should agree with the original on diverse inputs."""
        gen = RandomFunctionGenerator(seed=42)
        specs = gen.generate(n=8)
        mismatches = 0
        total = 0

        for spec in specs:
            fname = spec["name"]
            ptypes = spec["param_types"]

            # Build test inputs based on parameter types
            inputs = _make_test_inputs(ptypes)

            ns_orig = {}
            exec(compile(spec["source"], "<test>", "exec"), ns_orig)  # noqa: S102

            for equiv_src in spec["equivalents"]:
                ns_eq = {}
                exec(compile(equiv_src, "<test>", "exec"), ns_eq)  # noqa: S102
                for inp in inputs:
                    total += 1
                    try:
                        r1 = ns_orig[fname](*inp)
                        r2 = ns_eq[fname](*inp)
                        if r1 != r2:
                            mismatches += 1
                    except Exception:
                        pass  # skip inputs that trigger errors

        assert mismatches == 0, (
            f"{mismatches}/{total} equivalence mismatches"
        )

    def test_generate_function_returns_ast(self):
        gen = RandomFunctionGenerator(seed=7)
        func_node = gen.generate_function("test_fn", ["list[int]"], "int")
        assert isinstance(func_node, ast.FunctionDef)
        assert func_node.name == "test_fn"


# ------------------------------------------------------------------
# Helper for building test inputs
# ------------------------------------------------------------------

def _make_test_inputs(param_types: list[str]) -> list[tuple]:
    """Build a small set of test inputs for the given parameter types."""
    type_values = {
        "list[int]": [
            [1, 2, 3], [], [-1, 0, 1], [5, -5, 5, -5], [0],
            [1, 1, 1], [-10, 10], [3, 1, 4, 1, 5],
        ],
        "int": [0, 1, -1, 3, 5, -5, 10],
        "str": ["hello", "", "aeiou", "abc", "xyz", "racecar"],
        "bool": [True, False],
    }

    per_param = []
    for t in param_types:
        per_param.append(type_values.get(t, [[1, 2, 3]]))

    # Build small cartesian product (limited)
    from itertools import product as iproduct

    results = []
    for combo in iproduct(*per_param):
        results.append(combo)
        if len(results) >= 20:
            break
    return results
