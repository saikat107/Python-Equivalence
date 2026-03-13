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
]
