# Architecture

## Overview

Python-Equivalence generates benchmarks of the form **(p1, p2, ptests, ntests)**
for evaluating Python function equivalence checkers. It constructs function
pairs with known ground-truth labels through semantics-preserving rewrites
(equivalent pairs) and controlled semantic mutations (non-equivalent pairs).

## Pipeline

The benchmark generation pipeline, orchestrated by `generator.py`, proceeds in
seven stages:

```
┌──────────────────┐
│  Seed Functions   │  catalog.py / program_gen.py / random_func_gen.py
└────────┬─────────┘
         ▼
┌──────────────────┐
│ Pair Construction │  Seed × equivalents → positive pairs
│                   │  Seed × mutations   → negative pairs
└────────┬─────────┘
         ▼
┌──────────────────┐
│ Input Generation  │  test_gen.py — type-directed, edge-case aware
└────────┬─────────┘
         ▼
┌──────────────────┐
│    Execution      │  runner.py — subprocess sandbox, two-level timeouts
└────────┬─────────┘
         ▼
┌──────────────────┐
│   Partitioning    │  Classify inputs into ptests (agree) / ntests (disagree)
└────────┬─────────┘
         ▼
┌──────────────────┐
│    Validation     │  Positive: ≥ 1,000 ptests, 0 ntests
│                   │  Negative: ≥ 1 ntest
└────────┬─────────┘
         ▼
┌──────────────────┐
│  Serialisation    │  JSON metadata + separate test-data files
└──────────────────┘
```

### Stage 1 — Seed Instantiation

A seed function is drawn from one of three sources:

| Source | Module | Characteristics |
|--------|--------|-----------------|
| Catalog | `catalog.py` | 26 hand-curated functions across 8 categories |
| Templates | `program_gen.py` | 9 parameterized families, randomly instantiated |
| AST Blueprints | `random_func_gen.py` | 20 patterns producing complex functions (≥ 20 LOC) |

Each seed comes bundled with **equivalents** (semantics-preserving rewrites)
and **mutations** (semantics-breaking changes).

### Stage 2 — Pair Construction

- **Positive pairs**: seed paired with each of its equivalents.
- **Negative pairs**: seed paired with each of its mutations.

### Stage 3 — Input Generation

The `InputGenerator` (`test_gen.py`) produces ≥ 1,500 diverse inputs per
function signature:

| Type | Strategy |
|------|----------|
| `int` | Edge cases (0, ± 1, ± 10, ± 100) + dense range [-30, 30] + wide random [-200, 200] |
| `float` | Analogous strategy with floating-point ranges |
| `bool` | Both values |
| `str` | Empty, palindromes, mixed case, vowel-heavy, random lowercase |
| `list[int]` | Empty, singletons, sorted, reversed, duplicates, all-negative, all-positive, random |
| `list[str]`, `list[float]` | Similar container strategies with appropriate element types |
| `set[int]` | Various sizes with edge-case elements |
| `dict[str, int]` | Various sizes with string keys and integer values |
| `tuple[int, ...]` | Various lengths with integer elements |

For functions with domain preconditions (e.g. "non-empty list", "n ≥ 0"),
the generator oversamples by 3× and applies an `input_filter`.

### Stage 4 — Execution

Both functions are executed on all inputs inside a **sandboxed subprocess**
(`runner.py`) with two levels of timeout:

| Level | Flag | Default | Purpose |
|-------|------|---------|---------|
| Batch | `--runner-timeout` | 60 s | Kills entire subprocess if exceeded |
| Per-call | `--per-call-timeout` | 5 s | Guards each individual call via daemon thread |

The subprocess approach prevents infinite loops and memory leaks from
affecting the main generator process.

### Stage 5 — Partitioning

Inputs are classified into:

- **ptests**: both functions return the same result
- **ntests**: functions return different results
- Inputs causing runtime errors are discarded

### Stage 6 — Validation

| Pair Type | Requirement |
|-----------|-------------|
| Positive (equivalent) | ≥ 1,000 distinct ptests, 0 ntests |
| Negative (non-equivalent) | ≥ 1 ntest |

Entries that fail validation are discarded.

### Stage 7 — Serialisation

Valid entries are written to JSON with test data stored in separate files.
See [Output Format](output-format.md).

---

## Generation Strategies

### Hand-Curated Catalog

The catalog (`catalog.py`) contains 26 carefully designed seed functions
spanning 8 algorithmic categories. Each entry provides:

- A **canonical implementation** with complete type annotations
- **2 equivalent implementations** using different coding styles (e.g.
  for-loop vs. list comprehension vs. `filter()`)
- **2 semantic mutations** with descriptions of the introduced bug

This strategy produces the highest-quality pairs but is limited in scale.

### Template-Based Generation

The template generator (`program_gen.py`) defines 9 parameterized function
families. Each family has configurable parameters (operators, thresholds,
scales, window sizes) that are randomly sampled to produce unique instances.

Each template generates:

- A **canonical implementation** with the chosen parameters
- **2 equivalents** via alternative coding patterns
- **2 mutations** via operator flips, off-by-one errors, etc.

### AST Blueprint Generation

The AST generator (`random_func_gen.py`) defines 20 blueprint patterns that
produce complex functions with ≥ 20 lines of code. Blueprints feature:

- Nested loops and multi-branch conditionals
- State-tracking variables and accumulators
- Multiple intermediate computations
- Diverse algorithmic patterns (two-pointer, sliding window, state machines)

Functions are padded to meet the `--min-loc` requirement when necessary.

---

## Mutation Taxonomy

Negative pairs are produced by applying **semantic mutations** — small,
targeted changes that introduce a behavioural difference detectable by at
least one input. Mutations fall into seven categories:

### 1. Comparison Operator Mutations

Replace a comparison operator with a related but semantically different one.

| Original | Mutated | Effect |
|----------|---------|--------|
| `x > 0` | `x >= 0` | Zero counted as positive |
| `val > prev` | `val >= prev` | Equals treated as increasing |

### 2. Off-by-One Constant Mutations

Shift a numeric constant by ± 1.

| Original | Mutated | Effect |
|----------|---------|--------|
| `return i` | `return i + 1` | Index off by one |
| `xs[i - k]` | `xs[i - k + 1]` | Window slides to wrong position |

### 3. Wrong Initial Value Mutations

Change the initial value of an accumulator or tracker.

| Original | Mutated | Effect |
|----------|---------|--------|
| `m = xs[0]` | `m = 0` | Fails for all-negative lists |
| `acc = 0` | `acc = 1` | Result always off by 1 |

### 4. Wrong Arithmetic Operator Mutations

Replace an arithmetic operator with a different one.

| Original | Mutated | Effect |
|----------|---------|--------|
| `x * scale` | `x + scale` | Scaling becomes addition |
| `power *= x` | `power += x` | Exponential becomes linear |

### 5. Condition Removal or Replacement

Remove a conditional guard or replace the predicate.

| Original | Mutated | Effect |
|----------|---------|--------|
| Count matching `x OP t` | `return len(xs)` | Ignores condition |
| Keep `x % 2 == 0` | Keep `x % 2 != 0` | Odds instead of evens |

### 6. Data Structure and Ordering Mutations

Alter output structure, swap indices, or change iteration range.

| Original | Mutated | Effect |
|----------|---------|--------|
| `[low, mid, high]` | `[low, high, mid]` | Partitions swapped |
| Iterate over `xs` | Iterate over `xs[:-1]` | Last element skipped |

### 7. Wrong Aggregate Mutations

Compute a different aggregate function over the same data.

| Original | Mutated | Effect |
|----------|---------|--------|
| Find maximum | Find minimum | Returns smallest instead of largest |
| Weight `pos_w` | Weight `pos_w + 1` | Positive weight is wrong |

---

## AST Similarity

The `ast_similarity.py` module measures structural similarity between two
code snippets:

1. Parse both sources into ASTs
2. Linearise via depth-first traversal → sequence of node-type labels
3. Compute normalised Levenshtein edit distance
4. `similarity = 1.0 - (distance / max_len)`

This is used to filter generated pairs by structural similarity, ensuring
diverse and challenging benchmarks.

---

## Module Map

```
src/
├── generate_benchmark.py          # CLI: generate benchmarks
├── evaluate_benchmark.py          # CLI: evaluate benchmarks
├── fuzz_benchmark.py              # CLI: fuzz-test benchmarks
├── equivalence_benchmarks/
│   ├── __init__.py                # Public API exports
│   ├── models.py                  # BenchmarkEntry dataclass
│   ├── catalog.py                 # 26 hand-curated seed functions
│   ├── program_gen.py             # Template-based random generation (9 families)
│   ├── random_func_gen.py         # AST blueprint generation (20 patterns)
│   ├── test_gen.py                # Type-directed test input generator
│   ├── runner.py                  # Safe subprocess execution with timeouts
│   ├── generator.py               # Pipeline orchestration
│   ├── ast_similarity.py          # AST-based code similarity
│   ├── whitebox.py                # Coverage tracking & AST hint extraction
│   └── progress.py                # Logging & progress-bar helpers
└── fuzzer/
    ├── __init__.py
    ├── type_parser.py             # AST-based type annotation parser
    ├── value_generator.py         # Recursive random value generator
    ├── fuzz_function.py           # CLI: fuzz a single function
    └── equivalence_checker.py     # CLI: differential equivalence checking
```
