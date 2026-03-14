"""
equivalence_benchmarks — tools to create a Python equivalence-checker benchmark.

Usage (from repo root):
    python src/generate_benchmark.py
"""

from .ast_similarity import ast_similarity
from .models import BenchmarkEntry
from .generator import BenchmarkGenerator, deduplicate_entries
from .random_func_gen import RandomFunctionGenerator

__all__ = [
    "BenchmarkEntry",
    "BenchmarkGenerator",
    "RandomFunctionGenerator",
    "ast_similarity",
    "deduplicate_entries",
]
