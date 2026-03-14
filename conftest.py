import os
import sys

# Make the src/ directory importable so that tests can find
# equivalence_benchmarks and the top-level scripts.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
