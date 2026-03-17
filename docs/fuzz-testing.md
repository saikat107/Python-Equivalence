# Fuzz-Testing Benchmarks

The `fuzz_benchmark.py` script applies **coverage-guided, type-aware fuzzing**
to benchmark entries. It generates new test inputs beyond the original ptests
and ntests, then checks whether the new inputs reveal any previously undetected
behavioural differences between `p1` and `p2`.

## Basic Usage

```bash
python src/fuzz_benchmark.py benchmark_output/benchmark_*.json
```

## How It Works

The fuzzer combines several techniques for effective test generation:

### 1. White-Box AST Analysis

Before fuzzing, the tool analyses the source code of `p1` to extract
**hints** (`whitebox.py`):

- **Constants** used in comparisons and assignments (int, float, str, bool)
- **Boundary values** — each integer/float constant ± 1
- **Branch structure** — number of `if`/`elif`/`for`/`while` statements
- **Comparison operators** used in conditions

These hints bias mutations toward values that are likely to trigger different
code paths.

### 2. Seed-Based Mutation

Existing ptests and ntests serve as **mutation seeds**. The `InputFuzzer`
applies type-aware mutations to each seed:

| Type | Mutation Strategies |
|------|-------------------|
| `int` | Boundary ± 1, negate, multiply, bit flip, random range, hint-derived values |
| `float` | Similar to int with floating-point deltas |
| `bool` | Toggle |
| `str` | Character substitution, truncation, repetition, case change |
| `list[int]` | Element insertion, deletion, modification, sort, reverse, shuffle |
| `list[str]` | Element-level string mutations |
| `list[float]` | Element-level float mutations |
| `set[int]` | Add/remove elements |
| `dict[str, int]` | Add/remove/modify key-value pairs |

When AST hints are available, 25 % of int/float mutations use hint-derived
boundary values instead of purely random values.

### 3. Coverage-Guided Selection

Each mutated input is executed under a `sys.settrace`-based
**coverage tracker** that records which lines and branches of `p1` are hit.
Inputs that increase coverage are promoted as seeds for further mutation,
steering the fuzzer toward unexplored code paths.

### 4. Parallel Execution

Multiple entries are fuzzed in parallel using `multiprocessing.Pool`. The
`--workers` flag controls concurrency (defaults to CPU count).

### 5. Deduplication

Candidate inputs that duplicate existing ptests/ntests or previously generated
inputs are discarded to avoid wasting execution budget.

## CLI Reference

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `BENCHMARK_JSON` | str | *(required)* | Path to the benchmark JSON file |
| `--max-tests N` | int | `20` | Maximum new tests to generate per entry |
| `--max-time SECS` | float | `3600` | Maximum fuzzing time per entry |
| `--workers N` | int | CPU count | Number of parallel worker processes |
| `--per-call-timeout SECS` | float | `5` | Timeout per individual function call |
| `--output FILE` | str | — | Write JSON results to file |
| `--verbose` | flag | off | Print per-entry details |
| `--seed N` | int | — | Random seed for reproducibility |

## Examples

```bash
# Basic fuzzing with defaults
python src/fuzz_benchmark.py benchmark_output/benchmark_*.json

# Aggressive fuzzing: more tests, more time, all cores
python src/fuzz_benchmark.py benchmark_output/benchmark_*.json \
  --max-tests 100 --max-time 7200 --workers 8

# Quick smoke test: 5 new tests per entry, 60 s limit
python src/fuzz_benchmark.py benchmark_output/benchmark_*.json \
  --max-tests 5 --max-time 60

# Save results to JSON
python src/fuzz_benchmark.py benchmark_output/benchmark_*.json \
  --output fuzz_results.json --verbose

# Reproducible fuzzing
python src/fuzz_benchmark.py benchmark_output/benchmark_*.json --seed 42
```

## Output

The fuzzer prints per-entry results to stdout and an overall summary:

```
Entry abc123 (equivalent): 20 new tests, 0 disagreements
Entry def456 (non-equivalent): 15 new tests, 3 new disagreements found
...
```

With `--output`, a JSON file is produced containing new test inputs and their
results for each entry.

## When to Use Fuzz-Testing

- **Validating benchmark quality** — check that equivalent pairs truly agree
  on a wider range of inputs than the original ptests.
- **Finding subtle bugs** — coverage-guided mutations can trigger code paths
  missed by the initial type-directed input generator.
- **Hardening benchmarks** — add the newly discovered disagreeing inputs to
  the ntests of non-equivalent pairs.
