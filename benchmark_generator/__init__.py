"""
benchmark_generator — tools to create a Python equivalence-checker benchmark.

Usage (from repo root):
    python generate_benchmark.py
"""

from .models import BenchmarkEntry
from .generator import BenchmarkGenerator

__all__ = ["BenchmarkEntry", "BenchmarkGenerator"]
