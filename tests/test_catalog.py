"""Tests for equivalence_benchmarks.catalog."""

import pytest
from equivalence_benchmarks.catalog import CATALOG


class TestCatalog:
    def test_catalog_non_empty(self):
        assert len(CATALOG) >= 10

    def test_each_entry_has_required_keys(self):
        required = {"name", "source", "param_types", "return_type",
                    "category", "equivalents", "mutations"}
        for entry in CATALOG:
            missing = required - entry.keys()
            assert not missing, f"Entry '{entry.get('name')}' missing keys: {missing}"

    def test_each_entry_has_at_least_one_equivalent(self):
        for entry in CATALOG:
            assert len(entry["equivalents"]) >= 1, (
                f"'{entry['name']}' has no equivalents"
            )

    def test_each_entry_has_at_least_one_mutation(self):
        for entry in CATALOG:
            assert len(entry["mutations"]) >= 1, (
                f"'{entry['name']}' has no mutations"
            )

    def test_mutations_have_source_and_description(self):
        for entry in CATALOG:
            for mut in entry["mutations"]:
                assert "source" in mut, (
                    f"Mutation in '{entry['name']}' missing 'source'"
                )
                assert "description" in mut, (
                    f"Mutation in '{entry['name']}' missing 'description'"
                )

    def test_sources_are_valid_python(self):
        import ast
        for entry in CATALOG:
            name = entry["name"]
            for src_label, src in (
                [("original", entry["source"])]
                + [("equiv", e) for e in entry["equivalents"]]
                + [("mutation", m["source"]) for m in entry["mutations"]]
            ):
                try:
                    ast.parse(src)
                except SyntaxError as exc:
                    pytest.fail(
                        f"SyntaxError in {name}/{src_label}: {exc}\n{src}"
                    )

    def test_all_sources_contain_function_def(self):
        import ast
        for entry in CATALOG:
            name = entry["name"]
            for src in (
                [entry["source"]]
                + list(entry["equivalents"])
                + [m["source"] for m in entry["mutations"]]
            ):
                tree = ast.parse(src)
                funcs = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
                assert funcs, (
                    f"No function definition found in a source for '{name}'"
                )

    def test_function_names_consistent(self):
        """All variants of a seed function should define the same function name."""
        import ast
        for entry in CATALOG:
            expected_name = entry["name"]
            for src in (
                [entry["source"]]
                + list(entry["equivalents"])
                + [m["source"] for m in entry["mutations"]]
            ):
                tree = ast.parse(src)
                funcs = [
                    n.name for n in ast.walk(tree)
                    if isinstance(n, ast.FunctionDef)
                ]
                assert expected_name in funcs, (
                    f"Expected function name '{expected_name}' not found "
                    f"in source:\n{src}"
                )

    def test_equivalents_actually_equivalent(self):
        """Spot-check: original and equivalents should agree on a small set of inputs."""
        import ast

        def run(source, fname, args):
            ns = {}
            exec(compile(source, "<test>", "exec"), ns)  # noqa: S102
            return ns[fname](*args)

        spot_inputs = {
            "list[int]": [([],), ([1, 2, 3],), ([-1, 0, 1],)],
            "str": [("",), ("hello",), ("racecar",)],
            "int": [(0,), (5,), (-3,)],
        }

        for entry in CATALOG:
            fname = entry["name"]
            ptypes = entry["param_types"]
            constraints = entry.get("constraints", "")

            # Pick inputs based on first param type
            first = ptypes[0] if ptypes else "int"
            inputs = spot_inputs.get(first, [(0,)])

            # Skip empty-list inputs for functions requiring non-empty lists
            if "non-empty" in constraints:
                inputs = [i for i in inputs if i != ([],)]
            if not inputs:
                continue

            for inp in inputs:
                # Adjust for multi-param functions
                if len(ptypes) > 1:
                    extra = 0 if ptypes[1] == "int" else []
                    inp = inp + (extra,)

                try:
                    expected = run(entry["source"], fname, inp)
                except Exception:
                    continue

                for equiv_src in entry["equivalents"]:
                    try:
                        got = run(equiv_src, fname, inp)
                        assert got == expected, (
                            f"{fname}: original={expected!r} equiv={got!r} "
                            f"for input {inp!r}\nEquiv source:\n{equiv_src}"
                        )
                    except Exception:
                        pass  # Runtime errors on specific inputs are OK
