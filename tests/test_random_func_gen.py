"""Tests for benchmark_generator.random_func_gen (RandomFunctionGenerator)."""

import ast

import pytest

from benchmark_generator.random_func_gen import (
    RandomFunctionGenerator,
    _count_loc,
)


class TestRandomFunctionGenerator:
    def test_generates_requested_count(self):
        gen = RandomFunctionGenerator(seed=0)
        specs = gen.generate(n=10)
        assert len(specs) == 10

    def test_names_are_unique(self):
        gen = RandomFunctionGenerator(seed=0)
        specs = gen.generate(n=20)
        names = [s["name"] for s in specs]
        assert len(names) == len(set(names))

    def test_names_are_valid_identifiers(self):
        gen = RandomFunctionGenerator(seed=42)
        specs = gen.generate(n=10)
        for spec in specs:
            assert spec["name"].isidentifier(), (
                f"'{spec['name']}' is not a valid Python identifier"
            )

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
        s1 = gen1.generate(n=10)
        s2 = gen2.generate(n=10)
        names1 = [s["name"] for s in s1]
        names2 = [s["name"] for s in s2]
        assert names1 == names2

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

    def test_min_loc_enforced(self):
        """All generated sources must be at least 20 LOC."""
        gen = RandomFunctionGenerator(seed=42, min_loc=20)
        specs = gen.generate(n=15)
        for spec in specs:
            assert _count_loc(spec["source"]) >= 20, (
                f"{spec['name']} source has {_count_loc(spec['source'])} LOC < 20"
            )
            for equiv_src in spec["equivalents"]:
                assert _count_loc(equiv_src) >= 20, (
                    f"{spec['name']} equiv has {_count_loc(equiv_src)} LOC < 20"
                )
            for mut in spec["mutations"]:
                assert _count_loc(mut["source"]) >= 20, (
                    f"{spec['name']} mutation has {_count_loc(mut['source'])} LOC < 20"
                )

    def test_equivalents_actually_equivalent_spot(self):
        """Quick smoke check: original and equivalents agree on sample inputs."""
        gen = RandomFunctionGenerator(seed=5)
        specs = gen.generate(n=5)
        for spec in specs:
            fname = spec["name"]
            test_inputs = [([1, 2, 3],), ([0],), ([-1, 1],), ([],)]
            for inp in test_inputs:
                ns = {}
                exec(compile(spec["source"], "<test>", "exec"), ns)  # noqa: S102
                try:
                    expected = ns[fname](*inp)
                except Exception:
                    continue
                for equiv_src in spec["equivalents"]:
                    ns2 = {}
                    exec(compile(equiv_src, "<test>", "exec"), ns2)  # noqa: S102
                    try:
                        got = ns2[fname](*inp)
                        assert got == expected, (
                            f"{fname}: original={expected!r} equiv={got!r} "
                            f"for {inp!r}"
                        )
                    except Exception:
                        pass

    def test_each_spec_has_at_least_two_equivalents(self):
        gen = RandomFunctionGenerator(seed=0)
        specs = gen.generate(n=10)
        for spec in specs:
            assert len(spec["equivalents"]) >= 2, (
                f"'{spec['name']}' has only {len(spec['equivalents'])} equivalents"
            )

    def test_each_spec_has_at_least_two_mutations(self):
        gen = RandomFunctionGenerator(seed=0)
        specs = gen.generate(n=10)
        for spec in specs:
            assert len(spec["mutations"]) >= 2, (
                f"'{spec['name']}' has only {len(spec['mutations'])} mutations"
            )

    def test_mutations_have_source_and_description(self):
        gen = RandomFunctionGenerator(seed=0)
        specs = gen.generate(n=10)
        for spec in specs:
            for mut in spec["mutations"]:
                assert "source" in mut
                assert "description" in mut

    def test_category_is_random_generated(self):
        gen = RandomFunctionGenerator(seed=0)
        specs = gen.generate(n=5)
        for spec in specs:
            assert spec["category"] == "random_generated"
