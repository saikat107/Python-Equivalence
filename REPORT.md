# Mutation-Based Benchmark Generation for Python Function Equivalence Checking

## Abstract

This report describes the design and implementation of a benchmark generator for evaluating Python function equivalence checkers. The system produces labeled pairs of Python functions—some semantically equivalent, others semantically distinct—together with test suites that witness their equivalence or non-equivalence. Central to the approach is a taxonomy of *semantic mutations*: controlled, small modifications to a correct reference implementation that alter its observable behavior on at least one input. We catalog the mutation operators used, explain why each constitutes a genuine semantic change, and describe the overall generation pipeline that produces benchmark entries of the form *(p1, p2, ptests, ntests)*.

---

## 1. Introduction

Automated equivalence checking for programs is a fundamental problem in software engineering, with applications in compiler validation, refactoring verification, and plagiarism detection. Evaluating the accuracy of equivalence checkers requires benchmarks with *known ground truth*—pairs of programs whose semantic relationship (equivalent or non-equivalent) is established by construction rather than by testing alone.

This project addresses that need by generating benchmark datasets where:

- **Positive pairs** (equivalent) are produced by applying semantics-preserving rewrites to a reference function, such as replacing a `for` loop with a list comprehension or substituting a library call for a hand-written loop.
- **Negative pairs** (non-equivalent) are produced by applying *semantic mutations*—small, targeted changes to the reference function that introduce a behavioral difference detectable by at least one input.

Ground truth is derived from *construction provenance*: positive pairs are equivalent because the rewrite is known to preserve semantics, and negative pairs are non-equivalent because the mutation is designed to break at least one input-output relationship. The generator then validates each pair empirically: positive pairs must yield identical outputs on ≥1,000 distinct inputs, and negative pairs must exhibit at least one differing output.

---

## 2. System Overview

The benchmark generator is organized into three complementary function-generation strategies, each contributing seed functions along with their equivalents and mutations:

| Strategy | Module | Description |
|----------|--------|-------------|
| **Hand-Curated Catalog** | `catalog.py` | 26 carefully designed seed functions spanning 8 categories, each with 2 equivalents and 2 mutations. |
| **Template-Based Generation** | `program_gen.py` | 9 parameterized template families instantiated with random operators and constants, each producing 2 equivalents and 2 mutations. |
| **AST-Based Blueprint Generation** | `random_func_gen.py` | 20 blueprint patterns generating complex functions (≥20 LOC) with diverse control flow, each with 2 equivalents and 2 mutations. |

### 2.1 Pipeline Architecture

The generation pipeline, orchestrated by `generator.py`, proceeds as follows for each seed function:

1. **Seed Instantiation**: A seed function is drawn from the catalog, generated from a parameterized template, or synthesized from an AST blueprint.
2. **Pair Construction**: Positive pairs are formed by pairing the seed with each of its equivalents; negative pairs by pairing it with each of its mutations.
3. **Input Generation**: A type-directed input generator (`test_gen.py`) produces ≥1,500 diverse inputs covering edge cases (e.g., empty lists, zero, negative numbers, boundary values) and random values.
4. **Execution**: Both functions in a pair are executed on all inputs inside a sandboxed subprocess with per-call and batch-level timeouts (`runner.py`).
5. **Partitioning**: Inputs are classified into *ptests* (where both functions agree) and *ntests* (where they disagree). Inputs that cause runtime errors in either function are discarded.
6. **Validation**: Positive pairs require ≥1,000 distinct ptests and 0 ntests. Negative pairs require ≥1 ntest.
7. **Serialization**: Valid entries are saved as JSON with test data in separate files for scalability.

---

## 3. Mutation Taxonomy

We classify the mutations used in this system into seven categories based on the nature of the semantic change they introduce. Each mutation is designed to be *small* (typically a single-token or single-line change) yet *semantically significant* (producing different output for at least one valid input).

### 3.1 Comparison Operator Mutations

**Definition**: Replace a comparison operator with a related but semantically different one (e.g., `>` with `>=`, `<` with `<=`, `==` with `!=`).

**Why it is a mutation**: Comparison operators define the boundary conditions of branching logic. Changing `>` to `>=` includes the boundary value, which alters the set of elements that satisfy the condition. For inputs at exactly the boundary, the two programs produce different results.

**Examples**:

| Seed Function | Original Condition | Mutated Condition | Effect |
|---------------|-------------------|-------------------|--------|
| `count_positives` | `x > 0` | `x >= 0` | Zero is counted as positive |
| `filter_positives` | `x > 0` | `x >= 0` | Zero is included in output |
| `filter_threshold` | `x > t` | `x >= t` | Elements equal to threshold are included |
| `nested_pair_find` | `xs[i] + xs[j] > target` | `xs[i] + xs[j] >= target` | Pairs summing to exactly the target are included |
| `state_machine` | `val > prev` | `val >= prev` | Equal consecutive elements treated as increasing |
| `two_pointer` | `left < right` | `left <= right` | Loop processes one extra iteration (potential out-of-bounds or double-count) |

This is the most frequently used mutation class, appearing in all three generation strategies. It is especially effective because boundary cases are a common source of real-world bugs.

### 3.2 Off-by-One Constant Mutations

**Definition**: Shift a numeric constant by ±1, or use an adjacent value in place of the correct one.

**Why it is a mutation**: Off-by-one errors change the threshold at which a condition activates, the size of a window, or the index at which a value is read. These are among the most common programming errors and are difficult for static analysis tools to detect.

**Examples**:

| Seed Function | Original | Mutated | Effect |
|---------------|----------|---------|--------|
| `filter_threshold` | `x > t` | `x > t+1` | Threshold shifted by 1 |
| `find_first` | `return i` | `return i+1` | Returned index is off by one |
| `sliding_window_sum` | `ws` elements in initial window | `ws-1` elements | First window computation is wrong |
| `sliding_window` | `xs[i - k]` | `xs[i - k + 1]` | Window slides to wrong position |
| `map_scale` | `x * scale` | `x * (scale+1)` | Every element scaled by wrong factor |
| `multi_pass_transform` | `v * scale` | `v * (scale+1)` | Scale factor off by one in transformation pass |

### 3.3 Wrong Initial Value Mutations

**Definition**: Change the initial value of an accumulator, counter, or extremum tracker.

**Why it is a mutation**: The initial value of an accumulator determines the base case of a computation. Setting `max_value = 0` instead of `max_value = xs[0]` fails when all elements are negative. Setting an accumulator to `1` instead of `0` introduces a constant offset in all results.

**Examples**:

| Seed Function | Original Init | Mutated Init | Effect |
|---------------|---------------|--------------|--------|
| `max_list` | `m = xs[0]` | `m = 0` | Fails for all-negative lists |
| `min_list` | `m = xs[0]` | `m = 0` | Fails for all-positive lists |
| `aggregate_filter` | `acc = 0` | `acc = 1` | Result always off by 1 |
| `sliding_window` | `best = 0` | `best = 1` | Minimum window sum is wrong |
| `state_machine` | `run_count = 1` | `run_count = 0` | Run count always off by 1 |
| `polynomial_eval` | `result = 0` | `result = 1` | Polynomial value has constant offset |

### 3.4 Wrong Operator Mutations (Arithmetic)

**Definition**: Replace an arithmetic operator with a different one (e.g., `*` with `+`, `+` with `-`, `*` with `//`).

**Why it is a mutation**: Arithmetic operators define the fundamental computation. Replacing multiplication with addition changes a scaling operation into a shifting operation, producing drastically different results for most inputs.

**Examples**:

| Seed Function | Original | Mutated | Effect |
|---------------|----------|---------|--------|
| `map_scale` | `x * scale` | `x + scale` | Elements shifted instead of scaled |
| `polynomial_eval` | `power *= x` | `power += x` | Exponential growth becomes linear |
| `index_processing` | `(even_sum - odd_sum) * factor` | `(even_sum - odd_sum) + factor` | Multiplication replaced with addition |
| `list_transform` | `val * scale` | `val + scale` (or `val - scale`) | Transformation semantics changed |

### 3.5 Condition Removal or Replacement Mutations

**Definition**: Remove a conditional guard entirely, or replace it with a trivially different condition (e.g., filtering by a different predicate, returning the total count instead of the filtered count).

**Why it is a mutation**: Removing a condition causes the function to process all elements uniformly rather than selectively, fundamentally changing which elements contribute to the result.

**Examples**:

| Seed Function | Original Behavior | Mutated Behavior | Effect |
|---------------|-------------------|------------------|--------|
| `count_threshold` | Count elements matching `x OP t` | `return len(xs)` | Returns total count, ignores condition |
| `sum_threshold` | Sum elements matching `x OP t` | `return sum(xs)` | Sums all elements, ignores condition |
| `filter_evens` | Keep `x % 2 == 0` | Keep `x % 2 != 0` | Returns odd elements instead of even |
| `filter_evens` | Keep `x % 2 == 0` | Keep `x % 3 == 0` | Returns multiples of 3 instead of even |
| `count_positives` | Count `x > 0` | Count `x < 0` | Counts negatives instead of positives |
| `string_count` | Count `upper + digit` | Count `upper + lower` | Wrong character categories combined |

### 3.6 Data Structure and Ordering Mutations

**Definition**: Alter the structure of the output—swap indices, reorder partitions, skip elements, or change the iteration range.

**Why it is a mutation**: Even when the same values are computed, returning them in the wrong order or omitting elements changes the observable output.

**Examples**:

| Seed Function | Original | Mutated | Effect |
|---------------|----------|---------|--------|
| `partition_count` | Returns `[low, mid, high]` | Returns `[low, high, mid]` | Middle and high partitions are swapped |
| `sum_list` | Iterates over `xs` | Iterates over `xs[:-1]` | Last element is skipped |
| `index_processing` | Even indices: `i % 2 == 0` | Even indices: `i % 2 == 1` | Even and odd index processing is swapped |
| `nested_pair_find` | Inner loop starts at `i+1` | Inner loop starts at `i` | Self-pairs are counted |
| `sliding_window_sum` | Subtract `xs[pos - ws]` | Subtract `xs[pos - ws + 1]` | Window drifts by one position |

### 3.7 Wrong Aggregate Mutations

**Definition**: Compute a different aggregate function over the same data (e.g., `min` instead of `max`, `sum` instead of `count`).

**Why it is a mutation**: Aggregate functions collapse a collection into a single value. Using the wrong aggregate produces a fundamentally different result, though both are valid computations over the same input.

**Examples**:

| Seed Function | Original Aggregate | Mutated Aggregate | Effect |
|---------------|-------------------|-------------------|--------|
| `max_list` | Find maximum (`x > m`) | Find minimum (`x < m`) | Returns smallest instead of largest |
| `min_list` | Find minimum (`x < m`) | Find maximum (`x > m`) | Returns largest instead of smallest |
| `weighted_sum` | Weight `pos_w` for positive | Weight `pos_w + 1` | Positive weight is wrong |
| `weighted_sum` | Weight `neg_w` for negative | Weight `1` for negative | Negative values unweighted |
| `multi_condition_acc` | Medium-range weight `w2` | Medium-range weight `w2 + 1` | One partition has wrong weight |

---

## 4. Generation Strategies in Detail

### 4.1 Hand-Curated Catalog (`catalog.py`)

The catalog contains 26 seed functions organized into 8 categories:

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

Each catalog entry provides:
- A **canonical implementation** (the reference `p1`)
- **Two equivalent implementations** using different coding styles (list comprehensions, built-in functions, while loops, etc.)
- **Two semantic mutations** with natural-language descriptions

For example, `sum_list` has:
- **Canonical**: Manual loop accumulating `total += x`
- **Equivalent 1**: `return sum(xs)` (built-in function)
- **Equivalent 2**: While-loop with explicit index
- **Mutation 1**: Only sums positive elements (`if x > 0: total += x`)
- **Mutation 2**: Skips the last element (`for x in xs[:-1]`)

### 4.2 Template-Based Generation (`program_gen.py`)

Nine parameterized template families are instantiated with random parameter values (operators, thresholds, scales) to produce diverse function instances:

| Template | Parameters | Equivalents | Mutation Types |
|----------|-----------|-------------|----------------|
| `filter_threshold` | op ∈ {`>`,`<`,`>=`,`<=`}, threshold ∈ [-3, 5] | List comprehension, `filter()` with lambda | Operator flip, threshold off-by-one |
| `count_threshold` | op, threshold | Generator expression, `len()` of comprehension | Operator flip, condition removal |
| `sum_threshold` | op, threshold | Generator sum, two-pass filter-then-sum | Operator flip, condition removal |
| `map_scale` | scale ∈ {2, 3, 4, 5, 10} | List comprehension, `map()` with lambda | Wrong scale (+1), wrong operator (+ instead of ×) |
| `find_first` | op, threshold | While-loop, comprehension with indexing | Off-by-one index, operator flip |
| `sliding_window_sum` | window_size ∈ {2, 3, 4, 5} | Nested-loop recompute, slice-based | Wrong initial window size, off-by-one in subtraction |
| `partition_count` | lo ∈ [-3, 2], hi ∈ [3, 7] | Alternative counting, derived middle count | Boundary inclusion change, swapped result indices |
| `weighted_sum` | threshold ∈ [1, 5], weights ∈ [2, 3, 4] | Alternative accumulation, split-then-combine | Wrong positive weight, wrong negative weight |
| `multi_pass_transform` | op, threshold, scale | Single-pass variant, comprehension chain | Wrong scale, operator flip in filter |

Each template instantiation produces a unique function name (e.g., `filter_threshold_gt_3`) and is validated syntactically before inclusion.

### 4.3 AST-Based Blueprint Generation (`random_func_gen.py`)

Twenty blueprint patterns generate complex functions with ≥20 lines of code, diverse control flow (nested loops, multi-branch conditionals, state tracking), and multiple intermediate variables. Blueprints cover:

| Blueprint | Algorithmic Pattern | Mutation Types |
|-----------|-------------------|----------------|
| `aggregate_filter` | Sum/count/max with filtering | Comparison flip, wrong initial accumulator |
| `list_transform` | Map + filter with conditional logic | Wrong arithmetic operator, wrong filter condition |
| `nested_pair_find` | O(n²) pair search | Comparison flip, self-pair inclusion |
| `string_count` | Character classification by `ord()` ranges | Boundary off-by-one, wrong category combination |
| `polynomial_eval` | Iterative polynomial evaluation | Wrong initial value, operator change (× → +) |
| `classify` | Three-way partitioning | Boundary shift (`<` to `>=`, `<=` to `<`) |
| `state_machine` | Increasing/decreasing run tracking | Comparison change (`>` to `>=`), wrong initial count |
| `two_pointer` | Sorted array pair finding | Loop condition change, equality relaxation |
| `sliding_window` | Maximum window sum | Off-by-one removal index, wrong initial sum |
| `multi_condition_acc` | Multi-threshold weighted accumulation | Wrong weight, boundary shift |
| `conditional_list_build` | Conditional element transformation | Wrong multiplier, boundary shift |
| `index_processing` | Even/odd index separation | Wrong operator in computation, swapped parity |
| `early_termination` | First-match search with break | Opposite comparison, off-by-one index |
| `prefix_sum` | Cumulative sum array | Wrong accumulation, off-by-one boundary |
| `histogram` | Frequency counting in buckets | Wrong bucket boundaries, off-by-one classification |
| `running_extrema` | Running min/max tracking | Wrong initial value, wrong comparison |
| `list_partition` | Predicate-based partitioning | Wrong condition, wrong grouping |

Each blueprint function includes padding variables and bookkeeping logic to ensure the ≥20 LOC requirement is met while maintaining realistic code structure.

---

## 5. Why These Are Mutations

A mutation, in the context of mutation testing and benchmark generation, is a *small syntactic change* to a program that *alters its semantics*. The mutations in this system satisfy both criteria:

1. **Syntactic minimality**: Each mutation differs from the original by at most one or two tokens—a comparison operator, a constant, an initial value, or a single expression. This makes the mutated program structurally similar to the original, forcing equivalence checkers to reason about semantic rather than syntactic differences.

2. **Semantic significance**: Each mutation is designed to change the output for at least one valid input. The system empirically validates this by executing both the original and mutated functions on ≥1,500 inputs and requiring at least one *ntest* (input where outputs differ) for the pair to be included in the benchmark.

3. **Realism**: The mutation categories correspond to common programming errors:
   - **Off-by-one errors** are the most frequent bug category in numerical and array-processing code.
   - **Wrong operator** bugs arise from copy-paste errors or logical mistakes.
   - **Wrong initial values** occur when programmers forget edge cases (e.g., all-negative input to a max function).
   - **Missing conditions** result from incomplete implementations or incorrect simplifications.

4. **Diversity**: By combining three generation strategies (catalog, templates, blueprints) and seven mutation categories, the benchmark exercises a wide range of equivalence-checking capabilities, from simple constant comparisons to complex control-flow reasoning.

---

## 6. What Is Being Generated

The benchmark generator produces a dataset of **benchmark entries**, each a 4-tuple *(p1, p2, ptests, ntests)*:

| Field | Type | Description |
|-------|------|-------------|
| `p1` | `str` | Source code of the first Python function |
| `p2` | `str` | Source code of the second Python function (equivalent or mutated) |
| `ptests` | `list[list]` | Input tuples where `p1(*t) == p2(*t)` |
| `ntests` | `list[list]` | Input tuples where `p1(*t) != p2(*t)` |

Each entry also carries metadata including the function category, provenance (catalog, template, or AST-random), pair type (equivalent or mutation), and a natural-language description of the mutation (for negative pairs).

### 6.1 Output Structure

The generator writes three artifacts:

1. **`benchmark_<timestamp>.json`** — The main benchmark file containing all entry metadata (source code, equivalence label, test counts, metadata). Test data is referenced by file path rather than embedded inline.

2. **`tests/<entry_id>_tests.json`** — Individual test data files containing the `ptests` and `ntests` arrays for each entry.

3. **`summary.txt`** — Human-readable statistics (total entries, valid entries, positive/negative counts, per-category breakdown).

### 6.2 Validity Criteria

An entry is considered valid when:
- **Positive pairs**: ≥1,000 distinct ptests, 0 ntests (confirming empirical equivalence)
- **Negative pairs**: ≥1 distinct ntest (confirming empirical non-equivalence)

### 6.3 Scale

A single generation run can produce:
- From the catalog alone: up to 26 seeds × 4 pairs = 104 entries
- From templates: configurable, e.g., 20 seeds × 4 pairs = 80 entries
- From AST blueprints: configurable, e.g., 50 seeds × 4 pairs = 200 entries
- Combined: hundreds to thousands of entries with diverse function families

---

## 7. Evaluation

The companion script `evaluate_benchmark.py` independently verifies the generated benchmark by:

1. Loading each entry and compiling both `p1` and `p2` via `exec`
2. Running both functions on all stored ptests and ntests
3. Verifying that ptests produce identical outputs and ntests produce differing outputs
4. Reporting accuracy statistics (pass rate, per-category breakdown)

This provides a confidence check that the ground-truth labels are consistent with the stored test data.

---

## 8. Conclusion

This benchmark generator provides a systematic, scalable approach to producing labeled Python function pairs for equivalence checking evaluation. The mutation taxonomy—spanning comparison operator flips, off-by-one constants, wrong initial values, arithmetic operator changes, condition removal, structural reordering, and aggregate function changes—covers the most common classes of semantic-altering program modifications. By combining hand-curated seeds with parameterized templates and AST-based blueprints, the system generates diverse, realistic benchmark entries whose ground truth is established by construction and validated by execution.
