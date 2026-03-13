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
