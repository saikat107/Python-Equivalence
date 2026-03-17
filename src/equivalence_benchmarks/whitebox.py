"""
whitebox.py — White-box analysis utilities for coverage-guided fuzzing.

This module provides two core capabilities:

1. **AST analysis** — Parse a function's source code to extract constants,
   comparison boundary values, and branch structure.  These "hints" let the
   fuzzer generate inputs that are more likely to trigger different code paths.

2. **Coverage tracking** — Lightweight line-level and branch-level coverage
   measurement using ``sys.settrace``.  The fuzzer can query coverage after
   each execution and prefer inputs that reach previously-uncovered code.
"""

from __future__ import annotations

import ast
import sys
import threading
from typing import Any, Optional


# ---------------------------------------------------------------------------
# 1. AST-based source analysis
# ---------------------------------------------------------------------------

class ASTHints:
    """
    Collected "hints" extracted from a function's AST.

    Attributes
    ----------
    int_constants : set[int]
        Integer literals found in the source (including boundary ±1 values
        derived from comparisons).
    float_constants : set[float]
        Float literals found in the source.
    str_constants : set[str]
        String literals found in the source.
    bool_constants : set[bool]
        Boolean literals found in the source.
    branch_count : int
        Number of ``if`` / ``elif`` / ``while`` / ``for`` branches.
    comparison_ops : list[str]
        Human-readable comparison operators (e.g. ``"<"``, ``"=="``) found.
    """

    def __init__(self) -> None:
        self.int_constants: set[int] = set()
        self.float_constants: set[float] = set()
        self.str_constants: set[str] = set()
        self.bool_constants: set[bool] = set()
        self.branch_count: int = 0
        self.comparison_ops: list[str] = []

    # Convenience helpers --------------------------------------------------

    def boundary_ints(self) -> list[int]:
        """Return int constants plus ±1 neighbours (useful as fuzzer seeds)."""
        result: set[int] = set()
        for c in self.int_constants:
            result.update([c - 1, c, c + 1])
        return sorted(result)

    def boundary_floats(self) -> list[float]:
        """Return float constants plus small deltas."""
        result: set[float] = set()
        for c in self.float_constants:
            result.update([c - 1.0, c - 0.5, c, c + 0.5, c + 1.0])
        return sorted(result)

    @classmethod
    def merge(cls, *hints: "ASTHints") -> "ASTHints":
        """Return a new :class:`ASTHints` combining all supplied *hints*.

        Useful for merging hints extracted from multiple source files so that
        the fuzzer can use constants from all functions under test.
        """
        merged = cls()
        for h in hints:
            merged.int_constants |= h.int_constants
            merged.float_constants |= h.float_constants
            merged.str_constants |= h.str_constants
            merged.bool_constants |= h.bool_constants
            merged.branch_count += h.branch_count
            merged.comparison_ops += h.comparison_ops
        return merged


def analyse_source(source: str) -> ASTHints:
    """
    Parse *source* and extract white-box hints.

    If the source cannot be parsed, return an empty ``ASTHints`` so that the
    caller can fall back to black-box behaviour.
    """
    hints = ASTHints()
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return hints

    _walk(tree, hints)
    return hints


# -- internal walkers ------------------------------------------------------

_CMP_OP_MAP = {
    ast.Eq: "==",
    ast.NotEq: "!=",
    ast.Lt: "<",
    ast.LtE: "<=",
    ast.Gt: ">",
    ast.GtE: ">=",
    ast.Is: "is",
    ast.IsNot: "is not",
    ast.In: "in",
    ast.NotIn: "not in",
}


def _walk(node: ast.AST, hints: ASTHints) -> None:  # noqa: C901 -- intentional
    """Recursively walk the AST and populate *hints*."""
    for child in ast.walk(node):
        # -- constants / literals ------------------------------------------
        if isinstance(child, ast.Constant):
            val = child.value
            if isinstance(val, bool):
                hints.bool_constants.add(val)
            elif isinstance(val, int):
                hints.int_constants.add(val)
            elif isinstance(val, float):
                hints.float_constants.add(val)
            elif isinstance(val, str):
                hints.str_constants.add(val)

        # -- branch-inducing nodes -----------------------------------------
        if isinstance(child, ast.If):
            hints.branch_count += 1
            # Count elif as separate branch
            for elif_node in child.orelse:
                if isinstance(elif_node, ast.If):
                    hints.branch_count += 1
        elif isinstance(child, ast.While):
            hints.branch_count += 1
        elif isinstance(child, ast.For):
            hints.branch_count += 1

        # -- comparisons ---------------------------------------------------
        if isinstance(child, ast.Compare):
            for op in child.ops:
                op_str = _CMP_OP_MAP.get(type(op))
                if op_str:
                    hints.comparison_ops.append(op_str)

            # Extract boundary values from ``x < N`` / ``x >= N`` patterns
            all_vals = [child.left] + list(child.comparators)
            for v in all_vals:
                if isinstance(v, ast.Constant):
                    val = v.value
                    if isinstance(val, int):
                        hints.int_constants.add(val)
                    elif isinstance(val, float):
                        hints.float_constants.add(val)
                    elif isinstance(val, str):
                        hints.str_constants.add(val)

        # -- UnaryOp with negative constants (e.g. -1, -10) ----------------
        if isinstance(child, ast.UnaryOp) and isinstance(child.op, ast.USub):
            operand = child.operand
            if isinstance(operand, ast.Constant):
                val = operand.value
                if isinstance(val, int):
                    hints.int_constants.add(-val)
                elif isinstance(val, float):
                    hints.float_constants.add(-val)

        # -- range() calls: extract start/stop/step literals ---------------
        if isinstance(child, ast.Call):
            func = child.func
            if isinstance(func, ast.Name) and func.id == "range":
                for arg in child.args:
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, int):
                        hints.int_constants.add(arg.value)

        # -- subscript constants (e.g. xs[0], xs[-1]) ----------------------
        if isinstance(child, ast.Subscript):
            sl = child.slice
            if isinstance(sl, ast.Constant) and isinstance(sl.value, int):
                hints.int_constants.add(sl.value)
            elif isinstance(sl, ast.UnaryOp) and isinstance(sl.op, ast.USub):
                if isinstance(sl.operand, ast.Constant) and isinstance(
                    sl.operand.value, int
                ):
                    hints.int_constants.add(-sl.operand.value)


# ---------------------------------------------------------------------------
# 2. Coverage tracking
# ---------------------------------------------------------------------------

class CoverageTracker:
    """
    Lightweight line-level and branch-level coverage tracker.

    Usage::

        tracker = CoverageTracker()
        tracker.run(fn, args)
        report = tracker.report()
        print(report.lines_covered)

    Uses ``sys.settrace`` in a daemon thread so that timed-out executions
    do not block subsequent runs.
    """

    def __init__(self) -> None:
        # lines_hit: set of (filename, lineno)
        self._lines_hit: set[tuple[str, int]] = set()
        # branches_hit: set of (filename, from_line, to_line)
        self._branches_hit: set[tuple[str, int, int]] = set()
        # Track the last line per filename for branch detection
        self._last_line: dict[str, int] = {}
        self._target_filename: Optional[str] = None

    # -- public API --------------------------------------------------------

    def run(
        self,
        fn: Any,
        args: tuple,
        *,
        timeout: float = 5.0,
        filename: str = "<benchmark>",
    ) -> tuple[Any, Optional[str]]:
        """
        Execute ``fn(*args)`` while tracing coverage.

        Uses a daemon thread with *timeout* to protect against infinite loops.
        Returns ``(return_value, error_string)``.  *error_string* is ``None``
        on success.
        """
        self._target_filename = filename
        result_box: list = [None, None]  # [return_value, error_string]
        lines_hit = self._lines_hit
        branches_hit = self._branches_hit
        last_line = self._last_line
        target = filename

        def _trace(frame, event, arg):  # noqa: ANN001, ANN201
            fname = frame.f_code.co_filename
            if fname != target:
                return _trace
            lineno = frame.f_lineno
            lines_hit.add((fname, lineno))
            prev = last_line.get(fname)
            if prev is not None and prev != lineno:
                branches_hit.add((fname, prev, lineno))
            last_line[fname] = lineno
            return _trace

        def _target():
            old = sys.gettrace()
            try:
                sys.settrace(_trace)
                result_box[0] = fn(*args)
            except Exception as exc:
                result_box[1] = f"{type(exc).__name__}: {exc}"
            finally:
                sys.settrace(old)

        t = threading.Thread(target=_target, daemon=True)
        t.start()
        t.join(timeout)
        if t.is_alive():
            return None, f"TimeoutError: exceeded {timeout}s"
        return result_box[0], result_box[1]

    def report(self) -> CoverageReport:
        """Return a snapshot of the coverage collected so far."""
        return CoverageReport(
            lines_covered=frozenset(self._lines_hit),
            branches_covered=frozenset(self._branches_hit),
        )

    def reset(self) -> None:
        """Clear all accumulated coverage data."""
        self._lines_hit.clear()
        self._branches_hit.clear()
        self._last_line.clear()

    @property
    def lines_covered_count(self) -> int:
        return len(self._lines_hit)

    @property
    def branches_covered_count(self) -> int:
        return len(self._branches_hit)


class CoverageReport:
    """Immutable snapshot of coverage data."""

    __slots__ = ("lines_covered", "branches_covered")

    def __init__(
        self,
        lines_covered: frozenset[tuple[str, int]],
        branches_covered: frozenset[tuple[str, int, int]],
    ) -> None:
        self.lines_covered = lines_covered
        self.branches_covered = branches_covered

    @property
    def lines_covered_count(self) -> int:
        return len(self.lines_covered)

    @property
    def branches_covered_count(self) -> int:
        return len(self.branches_covered)

    def __repr__(self) -> str:
        return (
            f"CoverageReport(lines={self.lines_covered_count}, "
            f"branches={self.branches_covered_count})"
        )
