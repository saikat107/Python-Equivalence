# Standalone Fuzzer

The `src/fuzzer/` package provides two standalone tools for testing arbitrary
Python functions — independent of the benchmark pipeline.

## Fuzz a Single Function

Generate random inputs for any type-annotated Python function and display the
results:

```bash
python src/fuzzer/fuzz_function.py <file.py> <function_name> [options]
```

### Example

Create `example.py`:

```python
def sum_list(nums: list[int]) -> int:
    return sum(nums)
```

Fuzz it:

```bash
python src/fuzzer/fuzz_function.py example.py sum_list --num-inputs 20
```

Output:

```
Fuzzing: sum_list(nums: list[int]) -> int
Mode: random
Generating 20 inputs (seed=None)

  [   1] ([3, -1, 7],)  =>  9
  [   2] ([],)  =>  0
  [   3] ([-5, 2],)  =>  -3
  ...

Done: 20 inputs, 0 errors.
```

### CLI Reference

| Option | Default | Description |
|--------|---------|-------------|
| `FILE` | *(required)* | Python source file containing the function |
| `FUNCTION` | *(required)* | Name of the function to fuzz |
| `--num-inputs N` | `100` | Number of random inputs to generate |
| `--seed S` | `None` | Random seed for reproducibility |
| `--timeout SECS` | `5` | Per-call timeout in seconds |
| `--coverage-guided` | off | Use coverage-guided generation with AST-derived boundary-value hints (requires `equivalence_benchmarks` on `PYTHONPATH`) |

---

## Check Equivalence of Two Functions

Perform differential fuzzing to determine whether two functions are equivalent:

```bash
# Both functions in the same file
python src/fuzzer/equivalence_checker.py <file.py> <func1> <func2> [options]

# Functions in different files
python src/fuzzer/equivalence_checker.py <file1.py> <func1> <func2> --file2 <file2.py>
```

### Example — Equivalent Functions

Create `pair.py`:

```python
def sort_a(nums: list[int]) -> list[int]:
    return sorted(nums)

def sort_b(nums: list[int]) -> list[int]:
    result = list(nums)
    result.sort()
    return result
```

Check equivalence:

```bash
python src/fuzzer/equivalence_checker.py pair.py sort_a sort_b --time-limit 10 --num-inputs 1000
```

Output:

```
Function 1: sort_a(nums: list[int]) -> list[int]
Function 2: sort_b(nums: list[int]) -> list[int]

✓ Signatures are compatible
Mode: random | Up to 1000 inputs (time limit: 10.0s, seed: None)

Tested 1000 unique inputs in 2.3s

✓ Functions appear EQUIVALENT
  No counterexample found after 1000 unique inputs in 2.3s
```

### Example — Non-Equivalent Functions

Create `pair2.py`:

```python
def add(x: int, y: int) -> int:
    return x + y

def multiply(x: int, y: int) -> int:
    return x * y
```

```bash
python src/fuzzer/equivalence_checker.py pair2.py add multiply
```

```
✗ Functions are NOT EQUIVALENT
  Counterexample input: (3, 5)
  add returned: 8
  multiply returned: 15
```

### CLI Reference

| Option | Default | Description |
|--------|---------|-------------|
| `FILE` | *(required)* | Python source file for the first function |
| `FUNC1` | *(required)* | Name of the first function |
| `FUNC2` | *(required)* | Name of the second function |
| `--file2 FILE` | *(same as file1)* | Source file for the second function |
| `--time-limit SECS` | `3600` | Maximum fuzzing time |
| `--num-inputs N` | `100000` | Maximum number of unique inputs |
| `--seed S` | `None` | Random seed for reproducibility |
| `--timeout SECS` | `120` | Per-call timeout in seconds |
| `--coverage-guided` | off | Use coverage-guided generation: track line/branch coverage of both functions and bias inputs toward unexplored paths using AST-derived hints (requires `equivalence_benchmarks` on `PYTHONPATH`) |

---

## Supported Types

The fuzzer generates random values for any type annotation that can be
expressed as a combination of:

| Category | Types |
|----------|-------|
| **Primitives** | `int`, `float`, `str`, `bool`, `bytes`, `None` |
| **Containers** | `list[T]`, `dict[K, V]`, `set[T]`, `frozenset[T]` |
| **Tuples** | `tuple[T1, T2, ...]` (fixed-length), `tuple[T, ...]` (variadic) |
| **Optional** | `Optional[T]`, `T \| None` |
| **Union** | `Union[T1, T2]`, `T1 \| T2` |

Types can be **arbitrarily nested**:

- `dict[str, list[tuple[str, str, bool]]]`
- `list[dict[int, set[str]]]`
- `tuple[list[int], dict[str, float], bool]`
- `Optional[list[tuple[int, str]]]`

Both Python 3.9+ builtin syntax (`list[int]`) and `typing` module aliases
(`List[int]`) are supported. `from __future__ import annotations` is also
handled correctly.

---

## How It Works

1. **AST Parsing** (`type_parser.py`): The function source is parsed via
   `ast.parse()`. Each parameter annotation is recursively converted into a
   `TypeNode` tree that captures the full structure of the type.

2. **Value Generation** (`value_generator.py`): A `ValueGenerator` walks the
   `TypeNode` tree recursively. For each type, it produces random values
   using a mix of edge cases (e.g. `0`, `""`, empty lists) and uniformly
   random data.

3. **Execution & Comparison**: Functions are compiled with `exec()` and
   called via daemon threads with a configurable per-call timeout. Outputs
   are compared with `==`.

4. **Coverage-Guided Mode** (`--coverage-guided`): When enabled, the fuzzer
   uses `sys.settrace`-based line and branch coverage tracking
   (`whitebox.CoverageTracker`) and AST-derived boundary values
   (`whitebox.analyse_source`) to bias generation toward unexplored code
   paths. Inputs that increase coverage are added to a mutation corpus;
   subsequent inputs are generated either as mutations of corpus entries
   (40%) or as fresh random values (60%).

---

## Programmatic Use

Both tools can be imported and used as a library:

```python
from fuzzer.type_parser import extract_function_signature, list_functions
from fuzzer.value_generator import ValueGenerator
from fuzzer.fuzz_function import fuzz_function
from fuzzer.equivalence_checker import check_equivalence

# Parse a function signature
sig = extract_function_signature(source_code, "my_func")
print(sig.param_types())  # [TypeNode('list', [TypeNode('int')])]

# Generate random values for a type
gen = ValueGenerator(seed=42)
value = gen.generate(sig.param_types()[0])  # e.g. [3, -1, 7]

# Fuzz a single function (returns list[dict])
results = fuzz_function(source_code, "my_func", num_inputs=50, seed=42)
for r in results:
    if r["error"] is None:
        print(f"  {r['input']} => {r['output']}")
    else:
        print(f"  {r['input']} => ERROR: {r['error']}")

# Check equivalence of two functions
result = check_equivalence(src1, "func_a", src2, "func_b", time_limit=10)
print(result["equivalent"])       # True / False / None
print(result["inputs_tested"])    # number of inputs tested
if result["counterexample"] is not None:
    cx = result["counterexample"]
    print(cx["input"], cx["output1"], cx["output2"])
```
