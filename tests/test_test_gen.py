"""Tests for benchmark_generator.test_gen."""

import pytest
from benchmark_generator.test_gen import InputGenerator


class TestInputGenerator:
    def test_int_param_returns_enough_distinct_inputs(self):
        gen = InputGenerator(["int"], seed=0)
        inputs = gen.generate(n=1100)
        assert len(inputs) >= 1000
        # All values should be ints
        for (v,) in inputs:
            assert isinstance(v, int)

    def test_list_int_param(self):
        gen = InputGenerator(["list[int]"], seed=0)
        inputs = gen.generate(n=1100)
        assert len(inputs) >= 1000
        for (lst,) in inputs:
            assert isinstance(lst, list)
            assert all(isinstance(x, int) for x in lst)

    def test_two_params(self):
        gen = InputGenerator(["list[int]", "int"], seed=0)
        inputs = gen.generate(n=1200)
        assert len(inputs) >= 1000
        for lst, v in inputs:
            assert isinstance(lst, list)
            assert isinstance(v, int)

    def test_str_param(self):
        gen = InputGenerator(["str"], seed=0)
        inputs = gen.generate(n=500)
        assert len(inputs) > 0
        for (s,) in inputs:
            assert isinstance(s, str)

    def test_min_list_length_respected(self):
        gen = InputGenerator(["list[int]"], seed=0, min_list_length=1)
        inputs = gen.generate(n=200)
        for (lst,) in inputs:
            assert len(lst) >= 1

    def test_deterministic_with_same_seed(self):
        gen1 = InputGenerator(["list[int]"], seed=99)
        gen2 = InputGenerator(["list[int]"], seed=99)
        assert gen1.generate(n=50) == gen2.generate(n=50)

    def test_different_seeds_differ(self):
        gen1 = InputGenerator(["list[int]"], seed=1)
        gen2 = InputGenerator(["list[int]"], seed=2)
        # They may occasionally overlap but should not be identical for large n
        assert gen1.generate(n=200) != gen2.generate(n=200)

    def test_three_int_params(self):
        gen = InputGenerator(["int", "int", "int"], seed=0)
        inputs = gen.generate(n=300)
        assert len(inputs) > 100
        for a, b, c in inputs:
            assert isinstance(a, int)
            assert isinstance(b, int)
            assert isinstance(c, int)

    # ----------------------------------------------------------------
    # Additional tests for uncovered branches
    # ----------------------------------------------------------------

    def test_bool_param(self):
        """Cover _bool_values and bool branch in _random_value."""
        gen = InputGenerator(["bool"], seed=0)
        inputs = gen.generate(n=50)
        assert len(inputs) >= 2  # At least True and False
        values = {inp[0] for inp in inputs}
        assert True in values
        assert False in values
        for (v,) in inputs:
            assert isinstance(v, bool)

    def test_bool_with_int(self):
        """Bool combined with int param."""
        gen = InputGenerator(["bool", "int"], seed=0)
        inputs = gen.generate(n=100)
        assert len(inputs) > 10
        for b, i in inputs:
            assert isinstance(b, bool)
            assert isinstance(i, int)

    def test_list_str_param(self):
        """Cover _list_str_values and list[str] branches in _values_for/_random_value."""
        gen = InputGenerator(["list[str]"], seed=0)
        inputs = gen.generate(n=200)
        assert len(inputs) > 10
        for (lst,) in inputs:
            assert isinstance(lst, list)
            for item in lst:
                assert isinstance(item, str)

    def test_list_str_includes_empty_list(self):
        """list[str] values should include an empty list."""
        gen = InputGenerator(["list[str]"], seed=0)
        inputs = gen.generate(n=200)
        has_empty = any(lst == [] for (lst,) in inputs)
        assert has_empty

    def test_list_str_two_params(self):
        gen = InputGenerator(["list[str]", "int"], seed=0)
        inputs = gen.generate(n=200)
        assert len(inputs) > 10
        for lst, v in inputs:
            assert isinstance(lst, list)
            assert isinstance(v, int)

    def test_unknown_type_falls_back_to_int(self):
        """An unrecognized type string should fall back to generating ints."""
        gen = InputGenerator(["float"], seed=0)
        inputs = gen.generate(n=100)
        assert len(inputs) > 0
        for (v,) in inputs:
            assert isinstance(v, int)  # fallback generates ints

    def test_list_type_alias(self):
        """'list' (without qualifier) should behave like 'list[int]'."""
        gen = InputGenerator(["list"], seed=0)
        inputs = gen.generate(n=200)
        assert len(inputs) > 10
        for (lst,) in inputs:
            assert isinstance(lst, list)
            for item in lst:
                assert isinstance(item, int)

    def test_large_n_for_int_covers_random_range(self):
        """When n is large enough, _int_values should use rng.randint fallback."""
        gen = InputGenerator(["int"], seed=42)
        inputs = gen.generate(n=2000)
        # Should have many distinct values including some large ones
        values = {inp[0] for inp in inputs}
        assert len(values) > 100
        # Some values should be outside the [-30, 30] edge-case range
        assert any(abs(v) > 30 for v in values)
