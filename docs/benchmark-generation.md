# Benchmark Generation

The `generate_benchmark.py` script produces a dataset of Python function pairs
labelled as semantically equivalent or non-equivalent, together with test inputs
that confirm the label.

## Basic Usage

```bash
python src/generate_benchmark.py --num-examples 1000
```

This generates approximately 1,000 benchmark entries using AST-random
generation and writes them to `benchmark_output/`.

## Generation Sources

Three complementary strategies produce seed functions, each with its own
equivalents and mutations:

| Flag | Strategy | Module | Description |
|------|----------|--------|-------------|
| `--include-catalog` | Hand-Curated Catalog | `catalog.py` | 26 seed functions across 8 categories, each with 2 equivalents and 2 mutations |
| `--include-random` | Template-Based | `program_gen.py` | 9 parameterized template families instantiated with random operators and constants |
| `--include-ast-random` | AST Blueprint | `random_func_gen.py` | 20 blueprint patterns generating complex functions with ≥ 20 LOC |
| `--num-examples N` | Auto (AST-random) | — | Automatically uses AST-random generation to reach *N* total entries |

You can combine multiple sources in a single run:

```bash
python src/generate_benchmark.py \
  --include-catalog \
  --include-random --random-count 30 \
  --include-ast-random --ast-random-count 50
```

### Catalog Categories

When using `--include-catalog`, you can restrict to specific categories:

```bash
python src/generate_benchmark.py --include-catalog --categories aggregation filtering searching
```

Available categories:

| Category | Seed Functions |
|----------|---------------|
| **Aggregation** | `sum_list`, `count_positives`, `sum_squares`, `compute_histogram`, `cumulative_max` |
| **Extrema** | `max_list`, `min_list` |
| **Filtering** | `filter_evens`, `filter_positives` |
| **Searching** | `linear_search`, `count_occurrences`, `bubble_sort`, `two_sum_count` |
| **Transformation** | `reverse_list`, `remove_duplicates`, `flatten_lists`, `longest_plateau`, `insertion_sort` |
| **Mathematical** | `factorial`, `clamp`, `evaluate_polynomial` |
| **Predicate** | `is_sorted`, `is_palindrome` |
| **String** | `count_vowels`, `reverse_string`, `run_length_encode` |

### Template-Based Functions

Nine template families generate parameterized functions:

| Template | Parameters | Example Name |
|----------|-----------|--------------|
| `filter_threshold` | op ∈ {`>`,`<`,`>=`,`<=`}, threshold ∈ [-3, 5] | `filter_threshold_gt_3` |
| `count_threshold` | op, threshold | `count_threshold_le_0` |
| `sum_threshold` | op, threshold | `sum_threshold_gte_5` |
| `map_scale` | scale ∈ {2, 3, 4, 5, 10} | `map_scale_3` |
| `find_first` | op, threshold | `find_first_lt_neg2` |
| `sliding_window_sum` | window_size ∈ {2, 3, 4, 5} | `sliding_window_sum_4` |
| `partition_count` | lo ∈ [-3, 2], hi ∈ [3, 7] | `partition_count_0_5` |
| `weighted_sum` | threshold, weights | `weighted_sum_2_3` |
| `multi_pass_transform` | op, threshold, scale | `multi_pass_gt_3_scale_2` |

### AST Blueprint Functions

Twenty blueprints produce complex functions with diverse control flow:

| Blueprint | Pattern |
|-----------|---------|
| `aggregate_filter` | Sum/count/max with filtering |
| `list_transform` | Map + filter with conditional logic |
| `nested_pair_find` | O(n²) pair search |
| `string_count` | Character classification by `ord()` ranges |
| `polynomial_eval` | Iterative polynomial evaluation |
| `classify` | Three-way partitioning |
| `state_machine` | Increasing/decreasing run tracking |
| `two_pointer` | Sorted array pair finding |
| `sliding_window` | Maximum window sum |
| `multi_condition_acc` | Multi-threshold weighted accumulation |
| `conditional_list_build` | Conditional element transformation |
| `index_processing` | Even/odd index separation |
| `early_termination` | First-match search with break |
| `prefix_sum` | Cumulative sum array |
| `histogram` | Frequency counting in buckets |
| `running_extrema` | Running min/max tracking |
| `list_partition` | Predicate-based partitioning |

## CLI Reference

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--output DIR` | str | `benchmark_output/` | Directory to write benchmark files |
| `--seed N` | int | `42` | Random seed for reproducibility |
| `--min-ptests N` | int | `10000` | Minimum distinct ptests for positive pairs |
| `--runner-timeout SECS` | float | `60` | Subprocess-level batch timeout |
| `--per-call-timeout SECS` | float | `5` | Per-individual function call timeout |
| `--min-loc N` | int | `50` | Minimum lines of code per function |
| `--num-examples N` | int | — | Target total entries (auto AST-random) |
| `--include-catalog` | flag | off | Generate from the built-in catalog |
| `--include-random` | flag | off | Generate from random templates |
| `--random-count N` | int | `20` | Number of random template seeds |
| `--include-ast-random` | flag | off | Generate from AST-based blueprints |
| `--ast-random-count N` | int | `10` | Number of AST-random seeds |
| `--categories CAT ...` | str[] | all | Restrict catalog to listed categories |
| `--quiet` | flag | off | Suppress progress output |
| `--equiv-sim-min` | float | `0.0` | Min AST similarity for equivalent pairs |
| `--equiv-sim-max` | float | `1.0` | Max AST similarity for equivalent pairs |
| `--non-equiv-sim-min` | float | `0.0` | Min AST similarity for non-equivalent pairs |
| `--non-equiv-sim-max` | float | `1.0` | Max AST similarity for non-equivalent pairs |

## Examples

```bash
# Quick: 100 entries from AST-random
python src/generate_benchmark.py --num-examples 100

# Large benchmark from all sources
python src/generate_benchmark.py \
  --include-catalog \
  --include-random --random-count 50 \
  --include-ast-random --ast-random-count 100 \
  --output large_benchmark/

# Catalog only, specific categories, custom seed
python src/generate_benchmark.py \
  --include-catalog \
  --categories aggregation extrema mathematical \
  --seed 123

# Control code complexity
python src/generate_benchmark.py --num-examples 500 --min-loc 30

# Filter by AST similarity (e.g. only structurally different equivalents)
python src/generate_benchmark.py --num-examples 200 \
  --equiv-sim-min 0.1 --equiv-sim-max 0.5

# Custom timeouts for expensive functions
python src/generate_benchmark.py --num-examples 500 \
  --runner-timeout 120 --per-call-timeout 10
```

## Minimum Lines of Code

The `--min-loc` flag applies to **all generation sources**:

- **Catalog**: seeds with fewer lines than the minimum are skipped.
- **Templates**: generated functions below the threshold are skipped.
- **AST-random**: functions are padded with helper code to meet the minimum.

## AST Similarity Filtering

The `--equiv-sim-min/max` and `--non-equiv-sim-min/max` flags control AST
similarity ranges. Similarity is measured by linearising both ASTs and
computing the normalised Levenshtein distance (1.0 = identical structure,
0.0 = completely different).

This is useful for creating benchmarks where equivalent pairs look
syntactically different, or where non-equivalent pairs look syntactically
similar — making the task harder for automated checkers.

## Output

See [Output Format](output-format.md) for the full JSON schema.
