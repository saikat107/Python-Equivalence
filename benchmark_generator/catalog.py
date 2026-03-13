"""
Catalog of seed functions used to build the benchmark.

Each entry describes:
  source          – the canonical "p1" implementation
  param_types     – list of type-annotation strings for parameters
  return_type     – return type annotation string
  category        – functional category tag
  constraints     – any preconditions on inputs (empty string = none)
  input_filter    – optional callable(args_tuple) -> bool; when present, only
                    input tuples satisfying the filter are kept.  Use this for
                    functions with domain preconditions (e.g. non-empty list,
                    n >= 0, lo <= hi).
  equivalents     – list of semantically equivalent alternative implementations
  mutations       – list of { source, description } dicts; each source is a
                    deliberate semantic mutation that should produce different
                    output for at least one valid input
"""

from __future__ import annotations
from typing import Any

# ---------------------------------------------------------------------------
# Helper – strip leading newline from triple-quoted strings so that repr()
# looks clean in the JSON output.
# ---------------------------------------------------------------------------
def _s(src: str) -> str:
    return src.lstrip("\n")


CATALOG: list[dict[str, Any]] = [

    # ===================================================================
    # AGGREGATION
    # ===================================================================

    {
        "name": "sum_list",
        "source": _s("""
def sum_list(xs: list) -> int:
    total = 0
    for x in xs:
        total += x
    return total
"""),
        "param_types": ["list[int]"],
        "return_type": "int",
        "category": "aggregation",
        "constraints": "",
        "equivalents": [
            _s("""
def sum_list(xs: list) -> int:
    return sum(xs)
"""),
            _s("""
def sum_list(xs: list) -> int:
    i = 0
    result = 0
    while i < len(xs):
        result = result + xs[i]
        i += 1
    return result
"""),
        ],
        "mutations": [
            {
                "source": _s("""
def sum_list(xs: list) -> int:
    total = 0
    for x in xs:
        if x > 0:
            total += x
    return total
"""),
                "description": "only sums positive elements — ignores non-positive values",
            },
            {
                "source": _s("""
def sum_list(xs: list) -> int:
    total = 0
    for x in xs[:-1]:
        total += x
    return total
"""),
                "description": "skips the last element of the list",
            },
        ],
    },

    {
        "name": "count_positives",
        "source": _s("""
def count_positives(xs: list) -> int:
    count = 0
    for x in xs:
        if x > 0:
            count += 1
    return count
"""),
        "param_types": ["list[int]"],
        "return_type": "int",
        "category": "aggregation",
        "constraints": "",
        "equivalents": [
            _s("""
def count_positives(xs: list) -> int:
    return sum(1 for x in xs if x > 0)
"""),
            _s("""
def count_positives(xs: list) -> int:
    return len([x for x in xs if x > 0])
"""),
        ],
        "mutations": [
            {
                "source": _s("""
def count_positives(xs: list) -> int:
    count = 0
    for x in xs:
        if x >= 0:
            count += 1
    return count
"""),
                "description": "uses >= 0 instead of > 0 — counts zero as positive",
            },
            {
                "source": _s("""
def count_positives(xs: list) -> int:
    count = 0
    for x in xs:
        if x < 0:
            count += 1
    return count
"""),
                "description": "counts negatives instead of positives",
            },
        ],
    },

    {
        "name": "sum_squares",
        "source": _s("""
def sum_squares(xs: list) -> int:
    total = 0
    for x in xs:
        total += x * x
    return total
"""),
        "param_types": ["list[int]"],
        "return_type": "int",
        "category": "aggregation",
        "constraints": "",
        "equivalents": [
            _s("""
def sum_squares(xs: list) -> int:
    return sum(x ** 2 for x in xs)
"""),
            _s("""
def sum_squares(xs: list) -> int:
    result = 0
    i = 0
    while i < len(xs):
        result += xs[i] * xs[i]
        i += 1
    return result
"""),
        ],
        "mutations": [
            {
                "source": _s("""
def sum_squares(xs: list) -> int:
    return sum(xs)
"""),
                "description": "returns plain sum instead of sum of squares",
            },
            {
                "source": _s("""
def sum_squares(xs: list) -> int:
    total = 0
    for x in xs:
        if x > 0:
            total += x * x
    return total
"""),
                "description": "only squares positive elements — skips non-positive",
            },
        ],
    },

    # ===================================================================
    # EXTREMA
    # ===================================================================

    {
        "name": "max_list",
        "source": _s("""
def max_list(xs: list) -> int:
    m = xs[0]
    for x in xs[1:]:
        if x > m:
            m = x
    return m
"""),
        "param_types": ["list[int]"],
        "return_type": "int",
        "category": "extrema",
        "constraints": "non-empty list",
        "input_filter": lambda args: len(args[0]) > 0,
        "equivalents": [
            _s("""
def max_list(xs: list) -> int:
    return max(xs)
"""),
            _s("""
def max_list(xs: list) -> int:
    return sorted(xs)[-1]
"""),
        ],
        "mutations": [
            {
                "source": _s("""
def max_list(xs: list) -> int:
    m = 0
    for x in xs:
        if x > m:
            m = x
    return m
"""),
                "description": "wrong initial value m=0 — fails when all elements are negative",
            },
            {
                "source": _s("""
def max_list(xs: list) -> int:
    m = xs[0]
    for x in xs[1:]:
        if x < m:
            m = x
    return m
"""),
                "description": "uses < instead of > — finds minimum instead of maximum",
            },
        ],
    },

    {
        "name": "min_list",
        "source": _s("""
def min_list(xs: list) -> int:
    m = xs[0]
    for x in xs[1:]:
        if x < m:
            m = x
    return m
"""),
        "param_types": ["list[int]"],
        "return_type": "int",
        "category": "extrema",
        "constraints": "non-empty list",
        "input_filter": lambda args: len(args[0]) > 0,
        "equivalents": [
            _s("""
def min_list(xs: list) -> int:
    return min(xs)
"""),
            _s("""
def min_list(xs: list) -> int:
    return sorted(xs)[0]
"""),
        ],
        "mutations": [
            {
                "source": _s("""
def min_list(xs: list) -> int:
    m = 0
    for x in xs:
        if x < m:
            m = x
    return m
"""),
                "description": "wrong initial value m=0 — fails when all elements are positive",
            },
            {
                "source": _s("""
def min_list(xs: list) -> int:
    m = xs[0]
    for x in xs[1:]:
        if x > m:
            m = x
    return m
"""),
                "description": "uses > instead of < — finds maximum instead of minimum",
            },
        ],
    },

    # ===================================================================
    # FILTERING
    # ===================================================================

    {
        "name": "filter_evens",
        "source": _s("""
def filter_evens(xs: list) -> list:
    result = []
    for x in xs:
        if x % 2 == 0:
            result.append(x)
    return result
"""),
        "param_types": ["list[int]"],
        "return_type": "list[int]",
        "category": "filtering",
        "constraints": "",
        "equivalents": [
            _s("""
def filter_evens(xs: list) -> list:
    return [x for x in xs if x % 2 == 0]
"""),
            _s("""
def filter_evens(xs: list) -> list:
    return list(filter(lambda x: x % 2 == 0, xs))
"""),
        ],
        "mutations": [
            {
                "source": _s("""
def filter_evens(xs: list) -> list:
    return [x for x in xs if x % 2 != 0]
"""),
                "description": "returns odd elements instead of even elements",
            },
            {
                "source": _s("""
def filter_evens(xs: list) -> list:
    return [x for x in xs if x % 3 == 0]
"""),
                "description": "returns multiples of 3 instead of even numbers",
            },
        ],
    },

    {
        "name": "filter_positives",
        "source": _s("""
def filter_positives(xs: list) -> list:
    result = []
    for x in xs:
        if x > 0:
            result.append(x)
    return result
"""),
        "param_types": ["list[int]"],
        "return_type": "list[int]",
        "category": "filtering",
        "constraints": "",
        "equivalents": [
            _s("""
def filter_positives(xs: list) -> list:
    return [x for x in xs if x > 0]
"""),
            _s("""
def filter_positives(xs: list) -> list:
    return list(filter(lambda x: x > 0, xs))
"""),
        ],
        "mutations": [
            {
                "source": _s("""
def filter_positives(xs: list) -> list:
    return [x for x in xs if x >= 0]
"""),
                "description": "uses >= 0 instead of > 0 — includes zero",
            },
            {
                "source": _s("""
def filter_positives(xs: list) -> list:
    return [x for x in xs if x < 0]
"""),
                "description": "returns negative elements instead of positive",
            },
        ],
    },

    # ===================================================================
    # SEARCHING
    # ===================================================================

    {
        "name": "linear_search",
        "source": _s("""
def linear_search(xs: list, target: int) -> int:
    for i, x in enumerate(xs):
        if x == target:
            return i
    return -1
"""),
        "param_types": ["list[int]", "int"],
        "return_type": "int",
        "category": "searching",
        "constraints": "",
        "equivalents": [
            _s("""
def linear_search(xs: list, target: int) -> int:
    try:
        return xs.index(target)
    except ValueError:
        return -1
"""),
            _s("""
def linear_search(xs: list, target: int) -> int:
    i = 0
    while i < len(xs):
        if xs[i] == target:
            return i
        i += 1
    return -1
"""),
        ],
        "mutations": [
            {
                "source": _s("""
def linear_search(xs: list, target: int) -> int:
    for i, x in enumerate(xs):
        if x == target:
            return i + 1
    return -1
"""),
                "description": "off-by-one: returns i+1 instead of i",
            },
            {
                "source": _s("""
def linear_search(xs: list, target: int) -> int:
    for i, x in enumerate(xs):
        if x >= target:
            return i
    return -1
"""),
                "description": "uses >= instead of == — finds first element >= target",
            },
        ],
    },

    {
        "name": "count_occurrences",
        "source": _s("""
def count_occurrences(xs: list, target: int) -> int:
    count = 0
    for x in xs:
        if x == target:
            count += 1
    return count
"""),
        "param_types": ["list[int]", "int"],
        "return_type": "int",
        "category": "searching",
        "constraints": "",
        "equivalents": [
            _s("""
def count_occurrences(xs: list, target: int) -> int:
    return xs.count(target)
"""),
            _s("""
def count_occurrences(xs: list, target: int) -> int:
    return sum(1 for x in xs if x == target)
"""),
        ],
        "mutations": [
            {
                "source": _s("""
def count_occurrences(xs: list, target: int) -> int:
    count = 0
    for x in xs:
        if x != target:
            count += 1
    return count
"""),
                "description": "counts elements != target instead of == target",
            },
            {
                "source": _s("""
def count_occurrences(xs: list, target: int) -> int:
    return len(xs)
"""),
                "description": "always returns total list length — ignores target",
            },
        ],
    },

    # ===================================================================
    # TRANSFORMATION
    # ===================================================================

    {
        "name": "reverse_list",
        "source": _s("""
def reverse_list(xs: list) -> list:
    result = []
    for x in xs:
        result.insert(0, x)
    return result
"""),
        "param_types": ["list[int]"],
        "return_type": "list[int]",
        "category": "transformation",
        "constraints": "",
        "equivalents": [
            _s("""
def reverse_list(xs: list) -> list:
    return xs[::-1]
"""),
            _s("""
def reverse_list(xs: list) -> list:
    return list(reversed(xs))
"""),
        ],
        "mutations": [
            {
                "source": _s("""
def reverse_list(xs: list) -> list:
    return xs[1:][::-1]
"""),
                "description": "drops first element before reversing — off-by-one at the front",
            },
            {
                "source": _s("""
def reverse_list(xs: list) -> list:
    return xs[:]
"""),
                "description": "returns a copy without reversing",
            },
        ],
    },

    {
        "name": "remove_duplicates",
        "source": _s("""
def remove_duplicates(xs: list) -> list:
    seen = set()
    result = []
    for x in xs:
        if x not in seen:
            seen.add(x)
            result.append(x)
    return result
"""),
        "param_types": ["list[int]"],
        "return_type": "list[int]",
        "category": "transformation",
        "constraints": "",
        "equivalents": [
            _s("""
def remove_duplicates(xs: list) -> list:
    result = []
    for x in xs:
        if x not in result:
            result.append(x)
    return result
"""),
            _s("""
def remove_duplicates(xs: list) -> list:
    return list(dict.fromkeys(xs))
"""),
        ],
        "mutations": [
            {
                "source": _s("""
def remove_duplicates(xs: list) -> list:
    return sorted(set(xs))
"""),
                "description": "returns sorted(set(xs)) — loses original order and sorts",
            },
            {
                "source": _s("""
def remove_duplicates(xs: list) -> list:
    return list(set(xs))
"""),
                "description": "returns list(set(xs)) — loses original order",
            },
        ],
    },

    {
        "name": "flatten_lists",
        "source": _s("""
def flatten_lists(xs: list, ys: list) -> list:
    result = []
    for x in xs:
        result.append(x)
    for y in ys:
        result.append(y)
    return result
"""),
        "param_types": ["list[int]", "list[int]"],
        "return_type": "list[int]",
        "category": "transformation",
        "constraints": "",
        "equivalents": [
            _s("""
def flatten_lists(xs: list, ys: list) -> list:
    return xs + ys
"""),
            _s("""
def flatten_lists(xs: list, ys: list) -> list:
    return [*xs, *ys]
"""),
        ],
        "mutations": [
            {
                "source": _s("""
def flatten_lists(xs: list, ys: list) -> list:
    return ys + xs
"""),
                "description": "swaps order — returns ys then xs instead of xs then ys",
            },
            {
                "source": _s("""
def flatten_lists(xs: list, ys: list) -> list:
    return xs + ys[1:]
"""),
                "description": "drops first element of ys",
            },
        ],
    },

    # ===================================================================
    # MATHEMATICAL / RECURSIVE
    # ===================================================================

    {
        "name": "factorial",
        "source": _s("""
def factorial(n: int) -> int:
    result = 1
    for i in range(1, n + 1):
        result *= i
    return result
"""),
        "param_types": ["int"],
        "return_type": "int",
        "category": "mathematical",
        "constraints": "n >= 0",
        # No input_filter needed: both iterative variants return 1 for n <= 0
        # (range(1, n+1) and while i > 1 both produce no iterations), so they
        # agree on the full integer domain.
        "equivalents": [
            _s("""
def factorial(n: int) -> int:
    result = 1
    i = n
    while i > 1:
        result *= i
        i -= 1
    return result
"""),
            _s("""
def factorial(n: int) -> int:
    product = 1
    for k in range(2, n + 1):
        product *= k
    return product
"""),
        ],
        "mutations": [
            {
                "source": _s("""
def factorial(n: int) -> int:
    result = 1
    for i in range(1, n):
        result *= i
    return result
"""),
                "description": "off-by-one: range(1, n) instead of range(1, n+1) — returns (n-1)! for n > 1",
            },
            {
                "source": _s("""
def factorial(n: int) -> int:
    if n == 0:
        return 0
    result = 1
    for i in range(1, n + 1):
        result *= i
    return result
"""),
                "description": "wrong base case: factorial(0) returns 0 instead of 1",
            },
        ],
    },

    {
        "name": "clamp",
        "source": _s("""
def clamp(x: int, lo: int, hi: int) -> int:
    if x < lo:
        return lo
    elif x > hi:
        return hi
    else:
        return x
"""),
        "param_types": ["int", "int", "int"],
        "return_type": "int",
        "category": "mathematical",
        "constraints": "lo <= hi",
        "input_filter": lambda args: args[1] <= args[2],  # lo <= hi
        "equivalents": [
            _s("""
def clamp(x: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, x))
"""),
            _s("""
def clamp(x: int, lo: int, hi: int) -> int:
    return min(hi, max(lo, x))
"""),
        ],
        "mutations": [
            {
                "source": _s("""
def clamp(x: int, lo: int, hi: int) -> int:
    return max(hi, min(lo, x))
"""),
                "description": "swaps lo and hi in max/min — returns wrong boundary",
            },
            {
                "source": _s("""
def clamp(x: int, lo: int, hi: int) -> int:
    if x < lo:
        return lo
    elif x > hi:
        return hi
    else:
        return x + 1
"""),
                "description": "off-by-one: returns x+1 instead of x when x is in [lo, hi]",
            },
        ],
    },

    # ===================================================================
    # BOOLEAN PREDICATES
    # ===================================================================

    {
        "name": "is_sorted",
        "source": _s("""
def is_sorted(xs: list) -> bool:
    for i in range(len(xs) - 1):
        if xs[i] > xs[i + 1]:
            return False
    return True
"""),
        "param_types": ["list[int]"],
        "return_type": "bool",
        "category": "predicate",
        "constraints": "",
        "equivalents": [
            _s("""
def is_sorted(xs: list) -> bool:
    return xs == sorted(xs)
"""),
            _s("""
def is_sorted(xs: list) -> bool:
    return all(xs[i] <= xs[i + 1] for i in range(len(xs) - 1))
"""),
        ],
        "mutations": [
            {
                "source": _s("""
def is_sorted(xs: list) -> bool:
    for i in range(len(xs) - 1):
        if xs[i] >= xs[i + 1]:
            return False
    return True
"""),
                "description": "uses >= instead of > — returns False for lists with equal adjacent elements",
            },
            {
                "source": _s("""
def is_sorted(xs: list) -> bool:
    for i in range(len(xs) - 1):
        if xs[i] < xs[i + 1]:
            return False
    return True
"""),
                "description": "checks descending order instead of ascending",
            },
        ],
    },

    # ===================================================================
    # STRING OPERATIONS
    # ===================================================================

    {
        "name": "is_palindrome",
        "source": _s("""
def is_palindrome(s: str) -> bool:
    n = len(s)
    for i in range(n // 2):
        if s[i] != s[n - 1 - i]:
            return False
    return True
"""),
        "param_types": ["str"],
        "return_type": "bool",
        "category": "string",
        "constraints": "",
        "equivalents": [
            _s("""
def is_palindrome(s: str) -> bool:
    return s == s[::-1]
"""),
            _s("""
def is_palindrome(s: str) -> bool:
    return all(s[i] == s[-(i + 1)] for i in range(len(s) // 2))
"""),
        ],
        "mutations": [
            {
                "source": _s("""
def is_palindrome(s: str) -> bool:
    return s.lower() == s[::-1].lower()
"""),
                "description": "case-insensitive check — returns True for 'Aa' but original returns False",
            },
            {
                "source": _s("""
def is_palindrome(s: str) -> bool:
    n = len(s)
    for i in range(n // 2):
        if s[i] != s[n - 2 - i]:
            return False
    return True
"""),
                "description": "off-by-one: uses n-2-i instead of n-1-i — wrong mirror index",
            },
        ],
    },

    {
        "name": "count_vowels",
        "source": _s("""
def count_vowels(s: str) -> int:
    count = 0
    for c in s:
        if c in 'aeiou':
            count += 1
    return count
"""),
        "param_types": ["str"],
        "return_type": "int",
        "category": "string",
        "constraints": "",
        "equivalents": [
            _s("""
def count_vowels(s: str) -> int:
    return sum(1 for c in s if c in 'aeiou')
"""),
            _s("""
def count_vowels(s: str) -> int:
    vowels = 'aeiou'
    return sum(s.count(v) for v in vowels)
"""),
        ],
        "mutations": [
            {
                "source": _s("""
def count_vowels(s: str) -> int:
    count = 0
    for c in s:
        if c in 'aeiouy':
            count += 1
    return count
"""),
                "description": "includes 'y' as a vowel",
            },
            {
                "source": _s("""
def count_vowels(s: str) -> int:
    count = 0
    for c in s:
        if c.lower() in 'aeiou':
            count += 1
    return count
"""),
                "description": "case-insensitive counting — counts uppercase vowels too",
            },
        ],
    },

    {
        "name": "reverse_string",
        "source": _s("""
def reverse_string(s: str) -> str:
    result = ''
    for c in s:
        result = c + result
    return result
"""),
        "param_types": ["str"],
        "return_type": "str",
        "category": "string",
        "constraints": "",
        "equivalents": [
            _s("""
def reverse_string(s: str) -> str:
    return s[::-1]
"""),
            _s("""
def reverse_string(s: str) -> str:
    return ''.join(reversed(s))
"""),
        ],
        "mutations": [
            {
                "source": _s("""
def reverse_string(s: str) -> str:
    return s[1:][::-1]
"""),
                "description": "drops first character before reversing",
            },
            {
                "source": _s("""
def reverse_string(s: str) -> str:
    return s
"""),
                "description": "returns original string unchanged",
            },
        ],
    },

    # ===================================================================
    # COMPLEX FUNCTIONS (15+ LOC bodies)
    # ===================================================================

    # ------ run_length_encode ------------------------------------------

    {
        "name": "run_length_encode",
        "source": _s("""
def run_length_encode(xs: list) -> list:
    if len(xs) == 0:
        return []
    result = []
    current_val = xs[0]
    current_count = 1
    idx = 1
    while idx < len(xs):
        if xs[idx] == current_val:
            current_count += 1
        else:
            pair = [current_val, current_count]
            result.append(pair)
            current_val = xs[idx]
            current_count = 1
        idx += 1
    result.append([current_val, current_count])
    return result
"""),
        "param_types": ["list[int]"],
        "return_type": "list",
        "category": "transformation",
        "constraints": "",
        "equivalents": [
            _s("""
def run_length_encode(xs: list) -> list:
    if not xs:
        return []
    groups = []
    start_idx = 0
    pos = 1
    n = len(xs)
    while pos <= n:
        if pos == n or xs[pos] != xs[start_idx]:
            run_val = xs[start_idx]
            run_len = pos - start_idx
            group = [run_val, run_len]
            groups.append(group)
            start_idx = pos
        pos = pos + 1
    return groups
"""),
            _s("""
def run_length_encode(xs: list) -> list:
    n = len(xs)
    if n == 0:
        return []
    encoded = []
    run_value = xs[0]
    run_length = 1
    for i in range(1, n):
        elem = xs[i]
        if elem == run_value:
            run_length = run_length + 1
        else:
            pair = [run_value, run_length]
            encoded.append(pair)
            run_value = elem
            run_length = 1
    last_pair = [run_value, run_length]
    encoded.append(last_pair)
    return encoded
"""),
        ],
        "mutations": [
            {
                "source": _s("""
def run_length_encode(xs: list) -> list:
    if len(xs) == 0:
        return []
    result = []
    current_val = xs[0]
    current_count = 0
    idx = 1
    while idx < len(xs):
        if xs[idx] == current_val:
            current_count += 1
        else:
            pair = [current_val, current_count]
            result.append(pair)
            current_val = xs[idx]
            current_count = 0
        idx += 1
    result.append([current_val, current_count])
    return result
"""),
                "description": "initializes run count to 0 instead of 1 — all counts off by one",
            },
            {
                "source": _s("""
def run_length_encode(xs: list) -> list:
    if len(xs) == 0:
        return []
    result = []
    current_val = xs[0]
    current_count = 1
    idx = 1
    while idx < len(xs):
        if xs[idx] == current_val:
            current_count += 1
        else:
            pair = [current_val, current_count]
            result.append(pair)
            current_val = xs[idx]
            current_count = 1
        idx += 1
    return result
"""),
                "description": "omits appending the final run group — last run is lost",
            },
        ],
    },

    # ------ compute_histogram ------------------------------------------

    {
        "name": "compute_histogram",
        "source": _s("""
def compute_histogram(xs: list) -> list:
    freq = {}
    for x in xs:
        if x in freq:
            freq[x] = freq[x] + 1
        else:
            freq[x] = 1
    keys = []
    for k in freq:
        keys.append(k)
    keys.sort()
    result = []
    for k in keys:
        pair = [k, freq[k]]
        result.append(pair)
    return result
"""),
        "param_types": ["list[int]"],
        "return_type": "list",
        "category": "aggregation",
        "constraints": "",
        "equivalents": [
            _s("""
def compute_histogram(xs: list) -> list:
    n = len(xs)
    if n == 0:
        return []
    counts = {}
    idx = 0
    while idx < n:
        val = xs[idx]
        if val not in counts:
            counts[val] = 0
        counts[val] = counts[val] + 1
        idx = idx + 1
    sorted_keys = sorted(counts.keys())
    pairs = []
    for key in sorted_keys:
        entry = [key, counts[key]]
        pairs.append(entry)
    return pairs
"""),
            _s("""
def compute_histogram(xs: list) -> list:
    freq = {}
    for x in xs:
        old_count = freq.get(x, 0)
        freq[x] = old_count + 1
    all_keys = list(freq.keys())
    all_keys.sort()
    result = []
    i = 0
    n = len(all_keys)
    while i < n:
        k = all_keys[i]
        c = freq[k]
        result.append([k, c])
        i = i + 1
    return result
"""),
        ],
        "mutations": [
            {
                "source": _s("""
def compute_histogram(xs: list) -> list:
    freq = {}
    for x in xs:
        if x in freq:
            freq[x] = freq[x] + 1
        else:
            freq[x] = 1
    keys = []
    for k in freq:
        keys.append(k)
    result = []
    for k in keys:
        pair = [k, freq[k]]
        result.append(pair)
    return result
"""),
                "description": "omits sorting the keys — output order follows insertion order",
            },
            {
                "source": _s("""
def compute_histogram(xs: list) -> list:
    freq = {}
    for x in xs:
        if x in freq:
            freq[x] = freq[x] + 1
        else:
            freq[x] = 0
    keys = []
    for k in freq:
        keys.append(k)
    keys.sort()
    result = []
    for k in keys:
        pair = [k, freq[k]]
        result.append(pair)
    return result
"""),
                "description": "initializes first occurrence count to 0 — all counts off by one",
            },
        ],
    },

    # ------ bubble_sort ------------------------------------------------

    {
        "name": "bubble_sort",
        "source": _s("""
def bubble_sort(xs: list) -> list:
    arr = []
    for x in xs:
        arr.append(x)
    n = len(arr)
    for i in range(n):
        swapped = False
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                temp = arr[j]
                arr[j] = arr[j + 1]
                arr[j + 1] = temp
                swapped = True
        if not swapped:
            break
    return arr
"""),
        "param_types": ["list[int]"],
        "return_type": "list[int]",
        "category": "transformation",
        "constraints": "",
        "equivalents": [
            _s("""
def bubble_sort(xs: list) -> list:
    arr = []
    for x in xs:
        arr.append(x)
    n = len(arr)
    for i in range(n):
        min_idx = i
        j = i + 1
        while j < n:
            if arr[j] < arr[min_idx]:
                min_idx = j
            j = j + 1
        if min_idx != i:
            temp = arr[i]
            arr[i] = arr[min_idx]
            arr[min_idx] = temp
    return arr
"""),
            _s("""
def bubble_sort(xs: list) -> list:
    n = len(xs)
    if n <= 1:
        return list(xs)
    arr = list(xs)
    changed = True
    while changed:
        changed = False
        i = 0
        while i < len(arr) - 1:
            left = arr[i]
            right = arr[i + 1]
            if left > right:
                arr[i] = right
                arr[i + 1] = left
                changed = True
            i = i + 1
    return arr
"""),
        ],
        "mutations": [
            {
                "source": _s("""
def bubble_sort(xs: list) -> list:
    arr = []
    for x in xs:
        arr.append(x)
    n = len(arr)
    for i in range(n):
        swapped = False
        for j in range(0, n - i - 1):
            if arr[j] < arr[j + 1]:
                temp = arr[j]
                arr[j] = arr[j + 1]
                arr[j + 1] = temp
                swapped = True
        if not swapped:
            break
    return arr
"""),
                "description": "uses < instead of > — sorts in descending order",
            },
            {
                "source": _s("""
def bubble_sort(xs: list) -> list:
    arr = []
    for x in xs:
        arr.append(x)
    n = len(arr)
    for i in range(n):
        swapped = False
        for j in range(0, n - i - 2):
            if arr[j] > arr[j + 1]:
                temp = arr[j]
                arr[j] = arr[j + 1]
                arr[j + 1] = temp
                swapped = True
        if not swapped:
            break
    return arr
"""),
                "description": "off-by-one in inner loop bound (n-i-2 vs n-i-1) — may leave array unsorted",
            },
        ],
    },

    # ------ longest_plateau -------------------------------------------

    {
        "name": "longest_plateau",
        "source": _s("""
def longest_plateau(xs: list) -> int:
    if len(xs) == 0:
        return 0
    max_len = 1
    current_len = 1
    i = 1
    while i < len(xs):
        if xs[i] == xs[i - 1]:
            current_len = current_len + 1
        else:
            if current_len > max_len:
                max_len = current_len
            current_len = 1
        i = i + 1
    if current_len > max_len:
        max_len = current_len
    return max_len
"""),
        "param_types": ["list[int]"],
        "return_type": "int",
        "category": "searching",
        "constraints": "",
        "equivalents": [
            _s("""
def longest_plateau(xs: list) -> int:
    n = len(xs)
    if n == 0:
        return 0
    best = 1
    run = 1
    for i in range(1, n):
        prev = xs[i - 1]
        curr = xs[i]
        if curr == prev:
            run = run + 1
        else:
            if run > best:
                best = run
            run = 1
    if run > best:
        best = run
    return best
"""),
            _s("""
def longest_plateau(xs: list) -> int:
    n = len(xs)
    if n == 0:
        return 0
    runs = []
    current_run = 1
    idx = 1
    while idx < n:
        if xs[idx] == xs[idx - 1]:
            current_run = current_run + 1
        else:
            runs.append(current_run)
            current_run = 1
        idx = idx + 1
    runs.append(current_run)
    max_run = runs[0]
    for r in runs[1:]:
        if r > max_run:
            max_run = r
    return max_run
"""),
        ],
        "mutations": [
            {
                "source": _s("""
def longest_plateau(xs: list) -> int:
    if len(xs) == 0:
        return 0
    max_len = 1
    current_len = 0
    i = 1
    while i < len(xs):
        if xs[i] == xs[i - 1]:
            current_len = current_len + 1
        else:
            if current_len > max_len:
                max_len = current_len
            current_len = 0
        i = i + 1
    if current_len > max_len:
        max_len = current_len
    return max_len
"""),
                "description": "initializes run length to 0 instead of 1 — all run lengths off by one",
            },
            {
                "source": _s("""
def longest_plateau(xs: list) -> int:
    if len(xs) == 0:
        return 0
    max_len = 1
    current_len = 1
    i = 1
    while i < len(xs):
        if xs[i] != xs[i - 1]:
            current_len = current_len + 1
        else:
            if current_len > max_len:
                max_len = current_len
            current_len = 1
        i = i + 1
    if current_len > max_len:
        max_len = current_len
    return max_len
"""),
                "description": "uses != instead of == — finds longest run of distinct consecutive elements",
            },
        ],
    },

    # ------ evaluate_polynomial ----------------------------------------

    {
        "name": "evaluate_polynomial",
        "source": _s("""
def evaluate_polynomial(coeffs: list, x: int) -> int:
    n = len(coeffs)
    if n == 0:
        return 0
    result = 0
    current_power = 1
    idx = 0
    while idx < n:
        coeff = coeffs[idx]
        contribution = coeff * current_power
        result = result + contribution
        next_power = current_power * x
        current_power = next_power
        idx = idx + 1
    return result
"""),
        "param_types": ["list[int]", "int"],
        "return_type": "int",
        "category": "mathematical",
        "constraints": "",
        "equivalents": [
            _s("""
def evaluate_polynomial(coeffs: list, x: int) -> int:
    n = len(coeffs)
    if n == 0:
        return 0
    reversed_coeffs = []
    for c in coeffs:
        reversed_coeffs.append(c)
    reversed_coeffs.reverse()
    result = reversed_coeffs[0]
    idx = 1
    while idx < n:
        multiplied = result * x
        coeff = reversed_coeffs[idx]
        result = multiplied + coeff
        idx = idx + 1
    return result
"""),
            _s("""
def evaluate_polynomial(coeffs: list, x: int) -> int:
    n = len(coeffs)
    if n == 0:
        return 0
    total = 0
    idx = 0
    for idx in range(n):
        coeff = coeffs[idx]
        power = 1
        j = 0
        while j < idx:
            power = power * x
            j = j + 1
        term = coeff * power
        total = total + term
    return total
"""),
        ],
        "mutations": [
            {
                "source": _s("""
def evaluate_polynomial(coeffs: list, x: int) -> int:
    n = len(coeffs)
    if n == 0:
        return 0
    result = 0
    current_power = x
    idx = 0
    while idx < n:
        coeff = coeffs[idx]
        contribution = coeff * current_power
        result = result + contribution
        next_power = current_power * x
        current_power = next_power
        idx = idx + 1
    return result
"""),
                "description": "starts current_power at x instead of 1 — all terms shifted by one power",
            },
            {
                "source": _s("""
def evaluate_polynomial(coeffs: list, x: int) -> int:
    n = len(coeffs)
    if n == 0:
        return 0
    result = 0
    current_power = 1
    idx = 1
    while idx < n:
        coeff = coeffs[idx]
        contribution = coeff * current_power
        result = result + contribution
        next_power = current_power * x
        current_power = next_power
        idx = idx + 1
    return result
"""),
                "description": "starts at index 1 — skips the constant coefficient term",
            },
        ],
    },

    # ------ insertion_sort ---------------------------------------------

    {
        "name": "insertion_sort",
        "source": _s("""
def insertion_sort(xs: list) -> list:
    arr = []
    for v in xs:
        arr.append(v)
    n = len(arr)
    i = 1
    while i < n:
        key = arr[i]
        j = i - 1
        while j >= 0:
            if arr[j] > key:
                arr[j + 1] = arr[j]
                j = j - 1
            else:
                break
        arr[j + 1] = key
        i = i + 1
    return arr
"""),
        "param_types": ["list[int]"],
        "return_type": "list[int]",
        "category": "transformation",
        "constraints": "",
        "equivalents": [
            _s("""
def insertion_sort(xs: list) -> list:
    n = len(xs)
    arr = []
    for x in xs:
        arr.append(x)
    if n <= 1:
        return arr
    for i in range(1, n):
        current = arr[i]
        position = i
        while position > 0:
            if arr[position - 1] > current:
                arr[position] = arr[position - 1]
                position = position - 1
            else:
                break
        arr[position] = current
    return arr
"""),
            _s("""
def insertion_sort(xs: list) -> list:
    arr = []
    for v in xs:
        arr.append(v)
    n = len(arr)
    i = 0
    while i < n:
        min_pos = i
        j = i + 1
        while j < n:
            if arr[j] < arr[min_pos]:
                min_pos = j
            j = j + 1
        if min_pos != i:
            temp = arr[i]
            arr[i] = arr[min_pos]
            arr[min_pos] = temp
        i = i + 1
    return arr
"""),
        ],
        "mutations": [
            {
                "source": _s("""
def insertion_sort(xs: list) -> list:
    arr = []
    for v in xs:
        arr.append(v)
    n = len(arr)
    i = 1
    while i < n:
        key = arr[i]
        j = i - 1
        while j >= 0:
            if arr[j] < key:
                arr[j + 1] = arr[j]
                j = j - 1
            else:
                break
        arr[j + 1] = key
        i = i + 1
    return arr
"""),
                "description": "uses < instead of > — sorts in descending order",
            },
            {
                "source": _s("""
def insertion_sort(xs: list) -> list:
    arr = []
    for v in xs:
        arr.append(v)
    n = len(arr)
    i = 2
    while i < n:
        key = arr[i]
        j = i - 1
        while j >= 0:
            if arr[j] > key:
                arr[j + 1] = arr[j]
                j = j - 1
            else:
                break
        arr[j + 1] = key
        i = i + 1
    return arr
"""),
                "description": "starts outer loop at index 2 — first two elements left unsorted",
            },
        ],
    },

    # ------ two_sum_count ----------------------------------------------

    {
        "name": "two_sum_count",
        "source": _s("""
def two_sum_count(xs: list, target: int) -> int:
    count = 0
    n = len(xs)
    if n < 2:
        return 0
    i = 0
    while i < n:
        j = i + 1
        while j < n:
            val_i = xs[i]
            val_j = xs[j]
            total = val_i + val_j
            if total == target:
                count = count + 1
            j = j + 1
        i = i + 1
    return count
"""),
        "param_types": ["list[int]", "int"],
        "return_type": "int",
        "category": "searching",
        "constraints": "",
        "equivalents": [
            _s("""
def two_sum_count(xs: list, target: int) -> int:
    n = len(xs)
    if n < 2:
        return 0
    pairs_found = 0
    for i in range(n):
        val_i = xs[i]
        remainder = target - val_i
        j = i + 1
        while j < n:
            val_j = xs[j]
            if val_j == remainder:
                pairs_found = pairs_found + 1
            j = j + 1
    return pairs_found
"""),
            _s("""
def two_sum_count(xs: list, target: int) -> int:
    n = len(xs)
    if n < 2:
        return 0
    total_pairs = 0
    for i in range(n):
        needed = target - xs[i]
        found = 0
        j = i + 1
        while j < n:
            if xs[j] == needed:
                found = found + 1
            j = j + 1
        total_pairs = total_pairs + found
    return total_pairs
"""),
        ],
        "mutations": [
            {
                "source": _s("""
def two_sum_count(xs: list, target: int) -> int:
    count = 0
    n = len(xs)
    if n < 2:
        return 0
    i = 0
    while i < n:
        j = i
        while j < n:
            val_i = xs[i]
            val_j = xs[j]
            total = val_i + val_j
            if total == target:
                count = count + 1
            j = j + 1
        i = i + 1
    return count
"""),
                "description": "inner loop starts at j=i instead of j=i+1 — includes self-pairs",
            },
            {
                "source": _s("""
def two_sum_count(xs: list, target: int) -> int:
    count = 0
    n = len(xs)
    if n < 2:
        return 0
    i = 0
    while i < n:
        j = i + 1
        while j < n:
            val_i = xs[i]
            val_j = xs[j]
            total = val_i + val_j
            if total != target:
                count = count + 1
            j = j + 1
        i = i + 1
    return count
"""),
                "description": "uses != instead of == — counts non-matching pairs",
            },
        ],
    },

    # ------ cumulative_max ---------------------------------------------

    {
        "name": "cumulative_max",
        "source": _s("""
def cumulative_max(xs: list) -> list:
    if len(xs) == 0:
        return []
    result = []
    n = len(xs)
    current_max = xs[0]
    result.append(current_max)
    idx = 1
    while idx < n:
        val = xs[idx]
        if val > current_max:
            new_max = val
        else:
            new_max = current_max
        current_max = new_max
        result.append(current_max)
        idx = idx + 1
    return result
"""),
        "param_types": ["list[int]"],
        "return_type": "list[int]",
        "category": "transformation",
        "constraints": "",
        "equivalents": [
            _s("""
def cumulative_max(xs: list) -> list:
    n = len(xs)
    if n == 0:
        return []
    output = [0] * n
    output[0] = xs[0]
    pos = 1
    while pos < n:
        prev_max = output[pos - 1]
        curr_val = xs[pos]
        if curr_val > prev_max:
            output[pos] = curr_val
        else:
            output[pos] = prev_max
        pos = pos + 1
    return output
"""),
            _s("""
def cumulative_max(xs: list) -> list:
    n = len(xs)
    if n == 0:
        return []
    result = []
    best = xs[0]
    idx = 0
    while idx < n:
        val = xs[idx]
        if idx == 0:
            best = val
        elif val > best:
            best = val
        result.append(best)
        idx = idx + 1
    return result
"""),
        ],
        "mutations": [
            {
                "source": _s("""
def cumulative_max(xs: list) -> list:
    if len(xs) == 0:
        return []
    result = []
    n = len(xs)
    current_max = xs[0]
    idx = 1
    while idx < n:
        val = xs[idx]
        if val > current_max:
            new_max = val
        else:
            new_max = current_max
        current_max = new_max
        result.append(current_max)
        idx = idx + 1
    return result
"""),
                "description": "omits appending the first element — result is one element shorter",
            },
            {
                "source": _s("""
def cumulative_max(xs: list) -> list:
    if len(xs) == 0:
        return []
    result = []
    n = len(xs)
    current_max = xs[0]
    result.append(current_max)
    idx = 1
    while idx < n:
        val = xs[idx]
        if val < current_max:
            new_max = val
        else:
            new_max = current_max
        current_max = new_max
        result.append(current_max)
        idx = idx + 1
    return result
"""),
                "description": "uses < instead of > — computes cumulative minimum instead of maximum",
            },
        ],
    },
]
