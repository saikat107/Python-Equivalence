"""
benchmark_generator — tools to create a Python equivalence-checker benchmark.

Usage (from repo root):
    python generate_benchmark.py
"""

from .models import BenchmarkEntry
from .generator import BenchmarkGenerator, deduplicate_entries
from .random_func_gen import RandomFunctionGenerator

__all__ = [
    "BenchmarkEntry",
    "BenchmarkGenerator",
    "RandomFunctionGenerator",
    "deduplicate_entries",
]
