# API Reference

The library modules can be imported and used programmatically. Add `src/` to
your Python path (or install via editable mode) and import from the packages.

## Core Library (`equivalence_benchmarks`)

### BenchmarkEntry

Data model for a single benchmark entry.

```python
from equivalence_benchmarks.models import BenchmarkEntry

entry = BenchmarkEntry(
    entry_id="abc-123",
    func_name="sum_list",
    param_types=["list[int]"],
    return_type="int",
    p1_source="def sum_list(xs): ...",
    p2_source="def sum_list(xs): return sum(xs)",
    ptests=[([1, 2, 3],), ([],)],
    ntests=[],
    is_equivalent=True,
    metadata={"provenance": "catalog", "category": "aggregation"},
)

# Validity check
print(entry.is_valid)  # True if meets ptest/ntest thresholds

# Serialisation
d = entry.to_dict()
entry2 = BenchmarkEntry.from_dict(d)
```

**Key Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `entry_id` | str | UUID |
| `func_name` | str | Shared function name |
| `param_types` | list[str] | Parameter type annotations |
| `return_type` | str | Return type |
| `p1_source` | str | Source code of first function |
| `p2_source` | str | Source code of second function |
| `ptests` | list | Inputs where functions agree |
| `ntests` | list | Inputs where functions disagree |
| `is_equivalent` | bool | Ground-truth label |
| `metadata` | dict | Provenance, category, etc. |
| `is_valid` | bool (property) | Meets validity requirements |

---

### BenchmarkGenerator

Orchestrates the full generation pipeline.

```python
from equivalence_benchmarks.generator import BenchmarkGenerator

gen = BenchmarkGenerator(
    seed=42,
    min_ptests=1000,
    runner_timeout=60.0,
    min_loc=20,
    verbose=True,
)

# Generate from different sources
catalog_entries = gen.generate_from_catalog(categories=["aggregation"])
template_entries = gen.generate_from_templates(n=10)
ast_entries = gen.generate_from_random_ast(n=20, min_loc=50)

# Combine and save
all_entries = catalog_entries + template_entries + ast_entries
gen.save(all_entries, "output_dir/")
```

---

### InputGenerator

Type-directed test input generation.

```python
from equivalence_benchmarks.test_gen import InputGenerator

gen = InputGenerator(
    param_types=["list[int]", "int"],
    seed=42,
    input_filter=None,  # or a callable for domain constraints
)

inputs = gen.generate(n=100)
# inputs is a list of tuples, e.g. [([1, 2, 3], 5), ([], 0), ...]
```

**Supported types:** `int`, `float`, `bool`, `str`, `list[int]`, `list[str]`,
`list[float]`, `set[int]`, `dict[str,int]`, `tuple[int,...]`

---

### SafeRunner

Execute functions safely in a subprocess with timeouts.

```python
from equivalence_benchmarks.runner import SafeRunner

runner = SafeRunner(timeout=60.0, per_call_timeout=5.0)

# Run a single function on a batch of inputs
results = runner.run_batch(
    source='def add(x, y): return x + y',
    func_name='add',
    inputs=[(1, 2), (3, 4), (5, 6)],
)
# results: [3, 7, 11]

# Run a pair of functions
p1_results, p2_results = runner.run_pair(
    p1_source='def f(x): return x + 1',
    p2_source='def f(x): return x + 1',
    func_name='f',
    inputs=[(1,), (2,), (3,)],
)
```

---

### Catalog

Access the built-in seed functions.

```python
from equivalence_benchmarks.catalog import CATALOG

for entry in CATALOG:
    print(f"{entry['name']} ({entry['category']})")
    print(f"  Equivalents: {len(entry['equivalents'])}")
    print(f"  Mutations: {len(entry['mutations'])}")
```

Each catalog entry is a dictionary with:

| Key | Type | Description |
|-----|------|-------------|
| `name` | str | Function name |
| `source` | str | Canonical implementation |
| `param_types` | list[str] | Parameter types |
| `return_type` | str | Return type |
| `category` | str | Algorithmic category |
| `constraints` | str | Domain constraints |
| `equivalents` | list[str] | Semantically equivalent implementations |
| `mutations` | list[dict] | Mutations with `source` and `description` |

---

### RandomProgramGenerator

Template-based random function generation.

```python
from equivalence_benchmarks.program_gen import RandomProgramGenerator

gen = RandomProgramGenerator(seed=42)
specs = gen.generate(n=10)
# Each spec is a dict with name, source, equivalents, mutations, param_types, etc.
```

---

### RandomFunctionGenerator

AST blueprint-based generation for complex functions.

```python
from equivalence_benchmarks.random_func_gen import RandomFunctionGenerator

gen = RandomFunctionGenerator(seed=42, min_loc=50)
specs = gen.generate(n=20)
```

---

### AST Similarity

Measure structural similarity between two code snippets.

```python
from equivalence_benchmarks.ast_similarity import ast_similarity

score = ast_similarity(source1, source2)
# score ∈ [0.0, 1.0] where 1.0 = identical structure
```

---

### White-Box Analysis

Extract AST hints and track coverage.

```python
from equivalence_benchmarks.whitebox import analyse_source, ASTHints, CoverageTracker

# Extract hints from source code
hints = analyse_source("def f(x): return x + 1 if x > 0 else x - 1")
print(hints.int_constants)    # {0, 1}
print(hints.boundary_ints())  # {-1, 0, 1, 2}
print(hints.comparison_ops)   # {'>'}
print(hints.branch_count)     # 1

# Track coverage during execution
tracker = CoverageTracker()
tracker.start()
# ... execute function ...
tracker.stop()
print(tracker.current_coverage())  # set of line numbers
print(tracker.is_progress())       # True if new coverage achieved
```

---

## Standalone Fuzzer (`fuzzer`)

### Type Parser

Parse type annotations from Python source code.

```python
from fuzzer.type_parser import extract_function_signature, list_functions, TypeNode

# List all functions in a source file
source = open("my_module.py").read()
names = list_functions(source)

# Extract a specific function's signature
sig = extract_function_signature(source, "my_func")
print(sig.name)          # "my_func"
print(sig.param_types()) # [TypeNode('list', [TypeNode('int')]), TypeNode('int')]
print(sig.return_type)   # TypeNode('int')
```

`TypeNode` represents a type as a tree:

```python
# Simple type
TypeNode("int")                                    # int

# Parameterised type
TypeNode("list", [TypeNode("int")])                # list[int]

# Nested type
TypeNode("dict", [
    TypeNode("str"),
    TypeNode("list", [TypeNode("int")])
])                                                 # dict[str, list[int]]

# Variadic tuple
TypeNode("tuple", [TypeNode("int")], is_variadic=True)  # tuple[int, ...]
```

---

### Value Generator

Generate random values for any type annotation.

```python
from fuzzer.value_generator import ValueGenerator
from fuzzer.type_parser import TypeNode

gen = ValueGenerator(seed=42, max_collection_size=5, max_depth=4)

# Generate a single value
val = gen.generate(TypeNode("list", [TypeNode("int")]))
# e.g. [3, -1, 7, 0, 2]

# Generate multiple input tuples
type_nodes = [TypeNode("list", [TypeNode("int")]), TypeNode("int")]
inputs = gen.generate_inputs(type_nodes, n=50)
# e.g. [([1, 2], 3), ([], 0), ([-5, 2], 1), ...]
```

---

### Fuzz Function

Fuzz a single function programmatically.

```python
from fuzzer.fuzz_function import fuzz_function

source = '''
def sum_list(nums: list[int]) -> int:
    return sum(nums)
'''

results = fuzz_function(source, "sum_list", num_inputs=50, seed=42)
for inp, output, error in results:
    if error:
        print(f"  {inp} => ERROR: {error}")
    else:
        print(f"  {inp} => {output}")
```

Returns a list of `(input_tuple, output, error_string)` triples.

---

### Equivalence Checker

Check equivalence of two functions programmatically.

```python
from fuzzer.equivalence_checker import check_equivalence

src1 = "def sort_a(nums: list[int]) -> list[int]:\n    return sorted(nums)"
src2 = "def sort_b(nums: list[int]) -> list[int]:\n    r = list(nums); r.sort(); return r"

result = check_equivalence(
    src1, "sort_a",
    src2, "sort_b",
    time_limit=10,
    num_inputs=1000,
    seed=42,
)

print(result["equivalent"])      # True, False, or None (inconclusive)
print(result["counterexample"])  # (input, output1, output2) or None
print(result["inputs_tested"])   # number of unique inputs tested
print(result["elapsed_time"])    # seconds elapsed
```
