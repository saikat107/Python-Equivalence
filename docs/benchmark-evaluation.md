# Benchmark Evaluation

The `evaluate_benchmark.py` script verifies a generated benchmark by executing
both functions on their test inputs and checking whether the results match the
ground-truth labels.

## Basic Usage

```bash
python src/evaluate_benchmark.py benchmark_output/benchmark_*.json
```

## How It Works

For each benchmark entry the evaluator:

1. **Compiles** both `p1` and `p2` via `exec()`.
2. **Runs ptests** — executes both functions on every positive test input.
   For **equivalent** pairs, every ptest must produce the same output from both
   functions. For **non-equivalent** pairs, ptests are inputs where the
   functions happen to agree.
3. **Runs ntests** — executes both functions on every negative test input.
   For **non-equivalent** pairs, at least one ntest must produce different
   outputs.
4. **Classifies** the entry as passed or failed based on the label:
   - **Equivalent pair passes** when all ptests agree and there are no ntests.
   - **Non-equivalent pair passes** when at least one ntest disagrees.

Each function call is guarded by a per-call timeout (daemon thread) so that
infinite loops or slow inputs don't stall the evaluator.

## CLI Reference

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `BENCHMARK_JSON` | str | *(required)* | Path to the benchmark JSON file |
| `--verbose` | flag | off | Print per-entry evaluation details |
| `--per-call-timeout SECS` | float | `5` | Timeout per individual function call |

## Output

The evaluator prints a summary to stdout:

```
============================================================
Evaluation Summary
============================================================
  Total evaluated : 100
  Passed          : 98
  Failed          : 2
  Compile errors  : 0
  Pass rate       : 98.0%

  Equivalent pairs   : 50/50 passed
  Non-equivalent pairs: 48/50 passed
============================================================
```

With `--verbose`, each entry also prints its individual result:

```
[PASS] entry abc123 (equivalent) — 1500 ptests OK
[FAIL] entry def456 (non-equivalent) — 0 ntests disagreed
```

## Examples

```bash
# Evaluate the pre-generated benchmark
python src/evaluate_benchmark.py data/benchmark_v1.json

# Verbose output
python src/evaluate_benchmark.py benchmark_output/benchmark_*.json --verbose

# Increase timeout for expensive functions
python src/evaluate_benchmark.py benchmark_output/benchmark_*.json --per-call-timeout 10
```

## Interpreting Results

| Metric | Meaning |
|--------|---------|
| **Pass rate** | Fraction of entries whose test results match the ground-truth label |
| **Compile errors** | Entries where `p1` or `p2` failed to compile (syntax errors) |
| **Equivalent pairs passed** | Equivalent pairs where all ptests agreed |
| **Non-equivalent pairs passed** | Non-equivalent pairs where ≥ 1 ntest disagreed |

A high pass rate (close to 100 %) confirms the benchmark labels are accurate.
Failed entries may indicate mutations that are too subtle to detect with the
generated tests, or edge cases in execution.
