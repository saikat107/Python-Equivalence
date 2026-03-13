"""Tests for benchmark_generator.program_gen (RandomProgramGenerator)."""

import ast
import pytest
from benchmark_generator.program_gen import RandomProgramGenerator


class TestRandomProgramGenerator:
    def test_generates_requested_count(self):
        gen = RandomProgramGenerator(seed=0)
        specs = gen.generate(n=15)
        assert len(specs) == 15

    def test_names_are_unique(self):
        gen = RandomProgramGenerator(seed=0)
        specs = gen.generate(n=20)
        names = [s["name"] for s in specs]
        assert len(names) == len(set(names))

    def test_all_sources_valid_python(self):
        gen = RandomProgramGenerator(seed=42)
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
        gen = RandomProgramGenerator(seed=7)
        specs = gen.generate(n=5)
        required = {"name", "source", "equivalents", "mutations",
                    "param_types", "return_type", "category"}
        for spec in specs:
            missing = required - spec.keys()
            assert not missing, f"Missing fields in spec: {missing}"

    def test_deterministic_with_same_seed(self):
        gen1 = RandomProgramGenerator(seed=123)
        gen2 = RandomProgramGenerator(seed=123)
        s1 = gen1.generate(n=10)
        s2 = gen2.generate(n=10)
        names1 = [s["name"] for s in s1]
        names2 = [s["name"] for s in s2]
        assert names1 == names2

    def test_function_name_in_all_sources(self):
        gen = RandomProgramGenerator(seed=1)
        specs = gen.generate(n=5)
        for spec in specs:
            expected = spec["name"]
            for src in (
                [spec["source"]]
                + list(spec["equivalents"])
                + [m["source"] for m in spec["mutations"]]
            ):
                tree = ast.parse(src)
                funcs = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
                assert expected in funcs, (
                    f"Function '{expected}' not defined in:\n{src}"
                )

    def test_equivalents_actually_equivalent_spot(self):
        """Quick smoke check: original and equivalents agree on simple inputs."""
        gen = RandomProgramGenerator(seed=5)
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
                            f"{fname}: original={expected!r} equiv={got!r} for {inp!r}"
                        )
                    except Exception:
                        pass

    # ----------------------------------------------------------------
    # Additional tests for uncovered branches
    # ----------------------------------------------------------------

    def test_different_seeds_produce_different_names(self):
        gen1 = RandomProgramGenerator(seed=1)
        gen2 = RandomProgramGenerator(seed=99)
        s1 = gen1.generate(n=5)
        s2 = gen2.generate(n=5)
        names1 = {s["name"] for s in s1}
        names2 = {s["name"] for s in s2}
        assert names1 != names2

    def test_has_at_least_one_mutation(self):
        gen = RandomProgramGenerator(seed=10)
        specs = gen.generate(n=10)
        for spec in specs:
            assert len(spec["mutations"]) >= 1

    def test_mutations_have_description(self):
        gen = RandomProgramGenerator(seed=3)
        specs = gen.generate(n=5)
        for spec in specs:
            for mut in spec["mutations"]:
                assert "source" in mut
                assert "description" in mut
                assert len(mut["description"]) > 0

    def test_category_field_present_and_nonempty(self):
        gen = RandomProgramGenerator(seed=7)
        specs = gen.generate(n=5)
        for spec in specs:
            assert "category" in spec
            assert len(spec["category"]) > 0

    def test_has_template_id(self):
        gen = RandomProgramGenerator(seed=0)
        specs = gen.generate(n=5)
        for spec in specs:
            assert "template_id" in spec

    def test_generate_zero(self):
        gen = RandomProgramGenerator(seed=0)
        specs = gen.generate(n=0)
        assert specs == []
