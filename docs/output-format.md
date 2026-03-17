# Output Format

## Directory Structure

Running `generate_benchmark.py` produces the following output:

```
benchmark_output/                   # (configurable via --output)
├── benchmark_<timestamp>.json      # Main benchmark file
├── summary.txt                     # Human-readable statistics
└── tests/
    ├── <entry_id_1>_tests.json     # Test data for entry 1
    ├── <entry_id_2>_tests.json     # Test data for entry 2
    └── ...
```

Test data (ptests and ntests) is stored in **separate files** to keep the
main JSON manageable and reduce I/O when reading entry metadata.

---

## Main Benchmark File

`benchmark_<timestamp>.json` contains metadata for all entries:

```json
{
  "generated_at": "2026-01-01T12:00:00",
  "total_entries": 100,
  "valid_entries": 100,
  "positive_pairs": 50,
  "negative_pairs": 50,
  "entries": [
    {
      "entry_id": "a1b2c3d4-...",
      "func_name": "sum_list",
      "param_types": ["list[int]"],
      "return_type": "int",
      "p1_source": "def sum_list(xs: list) -> int:\n    total = 0\n    for x in xs:\n        total += x\n    return total",
      "p2_source": "def sum_list(xs: list) -> int:\n    return sum(xs)",
      "is_equivalent": true,
      "num_ptests": 1500,
      "num_ntests": 0,
      "is_valid": true,
      "tests_file": "tests/a1b2c3d4-..._tests.json",
      "metadata": {
        "category": "aggregation",
        "provenance": "catalog",
        "pair_type": "equivalent",
        "seed_name": "sum_list",
        "constraints": ""
      }
    }
  ]
}
```

### Entry Fields

| Field | Type | Description |
|-------|------|-------------|
| `entry_id` | string | UUID uniquely identifying this entry |
| `func_name` | string | Shared function name for `p1` and `p2` |
| `param_types` | string[] | Parameter type annotations (e.g. `["list[int]"]`) |
| `return_type` | string | Return type annotation (e.g. `"int"`) |
| `p1_source` | string | Complete source code of the first function |
| `p2_source` | string | Complete source code of the second function |
| `is_equivalent` | boolean | Ground-truth label: `true` for equivalent pairs, `false` for non-equivalent |
| `num_ptests` | integer | Count of positive tests (both functions agree) |
| `num_ntests` | integer | Count of negative tests (functions disagree) |
| `is_valid` | boolean | Whether this entry meets validity requirements |
| `tests_file` | string | Relative path to the test data file |
| `metadata` | object | Provenance and categorisation information |

### Metadata Fields

| Field | Values | Description |
|-------|--------|-------------|
| `category` | `aggregation`, `extrema`, `filtering`, `searching`, `transformation`, `mathematical`, `predicate`, `string` | Algorithmic category of the seed function |
| `provenance` | `catalog`, `template`, `random_ast` | Which generation strategy produced this entry |
| `pair_type` | `equivalent`, `non_equivalent` | Whether this is a positive or negative pair |
| `seed_name` | string | Name of the original seed function |
| `constraints` | string | Input domain constraints (e.g. `"non-empty"`, `"n >= 0"`) |

---

## Test Data Files

Each `tests/<entry_id>_tests.json` file contains the actual test inputs:

```json
{
  "entry_id": "a1b2c3d4-...",
  "ptests": [
    [[1, 2, 3]],
    [[]],
    [[-1, 0, 1]]
  ],
  "ntests": []
}
```

### Test Data Fields

| Field | Type | Description |
|-------|------|-------------|
| `entry_id` | string | UUID matching the main benchmark entry |
| `ptests` | array of arrays | Input tuples where `p1(*t) == p2(*t)` |
| `ntests` | array of arrays | Input tuples where `p1(*t) != p2(*t)` |

Each element in `ptests` or `ntests` is a **tuple of arguments** represented
as a JSON array. For a function `f(xs: list[int])`, each test is a
single-element array like `[[1, 2, 3]]`. For `f(x: int, y: int)`, each test
is a two-element array like `[3, 5]`.

---

## Validity Requirements

| Pair Type | Requirement |
|-----------|-------------|
| Equivalent (`is_equivalent: true`) | ≥ 1,000 distinct ptests, 0 ntests |
| Non-equivalent (`is_equivalent: false`) | ≥ 1 ntest |

Entries that fail these requirements have `is_valid: false` and are typically
excluded from downstream analysis.

---

## Summary File

`summary.txt` contains human-readable statistics:

```
Benchmark Summary
=================
Generated at: 2026-01-01 12:00:00
Total entries: 100
Valid entries: 100
Positive (equivalent) pairs: 50
Negative (non-equivalent) pairs: 50
```

---

## Pre-Generated Benchmark

The repository includes a ready-to-use benchmark at `data/benchmark_v1.json`.
This file follows the same schema described above and can be evaluated
directly:

```bash
python src/evaluate_benchmark.py data/benchmark_v1.json
```
