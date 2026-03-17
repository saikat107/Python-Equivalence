# Getting Started

## Prerequisites

- **Python 3.9+** (tested on 3.9–3.12)
- No external dependencies for the core library and fuzzer tools
- [`tqdm`](https://pypi.org/project/tqdm/) for progress bars in CLI scripts

## Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/saikat107/Python-Equivalence.git
cd Python-Equivalence
pip install -r requirements.txt
```

The `requirements.txt` installs `tqdm` for progress-bar support. All other
functionality uses the Python standard library.

## Quick Start

### 1. Generate a benchmark

```bash
# Generate 1000 benchmark entries (default: AST-random generation)
python src/generate_benchmark.py --num-examples 1000
```

Output is written to `benchmark_output/` by default:

| File | Contents |
|------|----------|
| `benchmark_<timestamp>.json` | Entry metadata (function sources, labels, test-file paths) |
| `tests/<entry_id>_tests.json` | Per-entry test data (ptests and ntests) |
| `summary.txt` | Human-readable statistics |

### 2. Evaluate the benchmark

```bash
python src/evaluate_benchmark.py benchmark_output/benchmark_*.json
```

The evaluator compiles both functions, runs them on the stored tests, and
prints a pass/fail summary.

### 3. Fuzz-test the benchmark

```bash
python src/fuzz_benchmark.py benchmark_output/benchmark_*.json --max-tests 20 --workers 4
```

The fuzzer generates new test inputs via type-aware, coverage-guided mutations
and checks whether the new inputs reveal any previously undetected
disagreements.

### 4. Fuzz a single function

```bash
python src/fuzzer/fuzz_function.py my_module.py my_function --num-inputs 50
```

### 5. Check equivalence of two functions

```bash
python src/fuzzer/equivalence_checker.py funcs.py func_a func_b --time-limit 30
```

## Pre-Generated Benchmark

A ready-to-use benchmark is included at `data/benchmark_v1.json`. You can
evaluate it immediately without running the generator:

```bash
python src/evaluate_benchmark.py data/benchmark_v1.json
```

## Running Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

The test suite contains ~237 tests covering all modules.

## Next Steps

| Guide | Description |
|-------|-------------|
| [Benchmark Generation](benchmark-generation.md) | Full CLI reference and generation strategies |
| [Benchmark Evaluation](benchmark-evaluation.md) | Evaluating and interpreting results |
| [Fuzz-Testing](fuzz-testing.md) | Coverage-guided fuzzing of benchmark entries |
| [Standalone Fuzzer](standalone-fuzzer.md) | Fuzz individual functions or check equivalence |
| [Architecture](architecture.md) | Pipeline design, generation strategies, mutation taxonomy |
| [Output Format](output-format.md) | JSON schema for benchmark files |
| [API Reference](api-reference.md) | Using the library programmatically |
