# Python-Equivalence

A comprehensive toolkit for generating, evaluating, and fuzz-testing benchmarks
of Python function equivalence.

## Overview

This project creates benchmark datasets of the form **(p1, p2, ptests, ntests)**
for evaluating Python function equivalence checkers:

| Field    | Description |
|----------|-------------|
| `p1`     | Source code of the first Python function |
| `p2`     | Source code of the second Python function |
| `ptests` | Input tuples where `p1(*t) == p2(*t)` (functions agree) |
| `ntests` | Input tuples where `p1(*t) != p2(*t)` (functions disagree) |

Ground truth comes from *construction provenance* — positive pairs are built
by semantics-preserving rewrites and negative pairs by controlled semantic
mutations.

---

## Capabilities

### 1. Benchmark Generation

Generate large-scale benchmark datasets with configurable generation
strategies, code complexity, and AST similarity filtering.

```bash
python src/generate_benchmark.py --num-examples 1000
```

Three complementary generation strategies are supported:

| Strategy | Seeds | Description |
|----------|-------|-------------|
| **Hand-Curated Catalog** | 26 functions, 8 categories | Expert-designed seeds with carefully crafted equivalents and mutations |
| **Template-Based** | 9 parameterized families | Randomly instantiated templates with diverse operators and constants |
| **AST Blueprint** | 20 complex patterns | Functions with ≥ 20 LOC, nested loops, state machines, and multi-branch logic |

📖 [Full generation guide →](docs/benchmark-generation.md)

### 2. Benchmark Evaluation

Verify benchmark correctness by executing both functions on their test inputs
and comparing results against ground-truth labels.

```bash
python src/evaluate_benchmark.py benchmark_output/benchmark_*.json
```

```
Evaluation Summary
  Total evaluated : 100     Pass rate : 98.0%
  Equivalent pairs   : 50/50 passed
  Non-equivalent pairs: 48/50 passed
```

📖 [Evaluation guide →](docs/benchmark-evaluation.md)

### 3. Coverage-Guided Fuzz-Testing

Apply white-box, coverage-guided fuzzing to benchmark entries to discover
additional test inputs beyond the original ptests and ntests.

```bash
python src/fuzz_benchmark.py benchmark_output/benchmark_*.json --max-tests 20 --workers 4
```

The fuzzer combines AST analysis (extracting constants and boundary values),
type-aware mutations, `sys.settrace`-based coverage tracking, and
multiprocessing parallelism.

📖 [Fuzz-testing guide →](docs/fuzz-testing.md)

### 4. Standalone Function Fuzzing

Fuzz any type-annotated Python function with random inputs — no benchmark
needed.

```bash
python src/fuzzer/fuzz_function.py example.py sum_list --num-inputs 50
```

```
Fuzzing: sum_list(nums: list[int]) -> int
  [   1] ([3, -1, 7],)  =>  9
  [   2] ([],)           =>  0
Done: 50 inputs, 0 errors.
```

📖 [Standalone fuzzer guide →](docs/standalone-fuzzer.md)

### 5. Equivalence Checking

Check whether two functions are equivalent via differential fuzzing with
automatic counterexample discovery.

```bash
python src/fuzzer/equivalence_checker.py funcs.py sort_a sort_b --time-limit 30
```

```
✓ Functions appear EQUIVALENT
  No counterexample found after 1000 unique inputs in 2.3s
```

📖 [Equivalence checking guide →](docs/standalone-fuzzer.md#check-equivalence-of-two-functions)

### 6. Programmatic API

All modules can be imported and used as a library for custom workflows:

```python
from equivalence_benchmarks.generator import BenchmarkGenerator
from fuzzer.equivalence_checker import check_equivalence
from fuzzer.fuzz_function import fuzz_function
```

📖 [API reference →](docs/api-reference.md)

---

## Quick Start

```bash
# Install
git clone https://github.com/saikat107/Python-Equivalence.git
cd Python-Equivalence
pip install -r requirements.txt    # installs tqdm for progress bars

# Generate a benchmark
python src/generate_benchmark.py --num-examples 1000

# Evaluate it
python src/evaluate_benchmark.py benchmark_output/benchmark_*.json

# Fuzz-test it
python src/fuzz_benchmark.py benchmark_output/benchmark_*.json --workers 4

# Or evaluate the pre-generated benchmark
python src/evaluate_benchmark.py data/benchmark_v1.json
```

📖 [Full getting started guide →](docs/getting-started.md)

---

## Repository Structure

```
src/
├── generate_benchmark.py          # CLI: generate benchmarks
├── evaluate_benchmark.py          # CLI: evaluate benchmarks
├── fuzz_benchmark.py              # CLI: fuzz-test benchmarks
├── equivalence_benchmarks/        # Core library
│   ├── models.py                  #   BenchmarkEntry dataclass
│   ├── catalog.py                 #   26 hand-curated seed functions
│   ├── program_gen.py             #   Template-based generation (9 families)
│   ├── random_func_gen.py         #   AST blueprint generation (20 patterns)
│   ├── test_gen.py                #   Type-directed test input generator
│   ├── runner.py                  #   Safe subprocess execution with timeouts
│   ├── generator.py               #   Pipeline orchestration
│   ├── ast_similarity.py          #   AST-based code similarity measurement
│   ├── whitebox.py                #   Coverage tracking & AST hint extraction
│   └── progress.py                #   Logging & progress-bar helpers
└── fuzzer/                        # Standalone fuzzer tools
    ├── type_parser.py             #   AST-based type annotation parser
    ├── value_generator.py         #   Recursive random value generator
    ├── fuzz_function.py           #   CLI: fuzz a single function
    └── equivalence_checker.py     #   CLI: differential equivalence checker
data/
└── benchmark_v1.json              # Pre-generated benchmark dataset
docs/                              # Detailed documentation
tests/                             # Test suite (~237 tests)
```

---

## Documentation

| Guide | Description |
|-------|-------------|
| [Getting Started](docs/getting-started.md) | Installation, prerequisites, and quick start |
| [Benchmark Generation](docs/benchmark-generation.md) | Generation strategies, CLI options, and examples |
| [Benchmark Evaluation](docs/benchmark-evaluation.md) | Evaluating and interpreting benchmark results |
| [Fuzz-Testing](docs/fuzz-testing.md) | Coverage-guided fuzzing of benchmark entries |
| [Standalone Fuzzer](docs/standalone-fuzzer.md) | Fuzz individual functions or check equivalence |
| [Architecture](docs/architecture.md) | Pipeline design, generation strategies, mutation taxonomy |
| [Output Format](docs/output-format.md) | JSON schema for benchmark files |
| [API Reference](docs/api-reference.md) | Using the library programmatically |

---

## Running Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

---

## License

MIT — see [LICENSE](LICENSE) for details.
