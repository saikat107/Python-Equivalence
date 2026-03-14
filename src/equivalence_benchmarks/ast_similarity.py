"""AST-based similarity measurement for Python source code.

Computes similarity between two Python code snippets by:
1. Parsing both into ASTs.
2. Linearizing each AST via depth-first traversal (node type labels).
3. Computing Levenshtein edit distance on the label sequences.
4. Normalizing to a similarity score in [0, 1].
"""

from __future__ import annotations

import ast
from typing import List


def _ast_to_sequence(node: ast.AST) -> List[str]:
    """Convert an AST to a sequence of node-type labels via DFS."""
    result: List[str] = []

    def _dfs(n: ast.AST) -> None:
        name = [str(type(n).__name__)]
        name_attr = getattr(n, "name", None)
        if isinstance(name_attr, str) and name_attr:
            name.append(f"({name_attr})")
        result.append(":->:".join(name))
        for child in ast.iter_child_nodes(n):
            _dfs(child)

    _dfs(node)
    return result


def _edit_distance(seq1: List[str], seq2: List[str]) -> int:
    """Levenshtein edit distance between two sequences (two-row DP)."""
    m, n = len(seq1), len(seq2)
    # Optimize so that n <= m (iterate over the shorter dimension).
    if m < n:
        seq1, seq2 = seq2, seq1
        m, n = n, m

    prev = list(range(n + 1))
    curr = [0] * (n + 1)

    for i in range(1, m + 1):
        curr[0] = i
        for j in range(1, n + 1):
            if seq1[i - 1] == seq2[j - 1]:
                curr[j] = prev[j - 1]
            else:
                curr[j] = 1 + min(prev[j], curr[j - 1], prev[j - 1])
        prev, curr = curr, prev

    return prev[n]


def ast_similarity(source1: str, source2: str) -> float:
    """Compute AST similarity between two Python source strings.

    Returns a float in ``[0, 1]`` where **1** means identical AST
    structure and **0** means completely different.  If either snippet
    cannot be parsed the function returns ``0.0``.
    """
    try:
        tree1 = ast.parse(source1)
        tree2 = ast.parse(source2)
    except SyntaxError:
        return 0.0

    seq1 = _ast_to_sequence(tree1)
    seq2 = _ast_to_sequence(tree2)

    if not seq1 and not seq2:
        return 1.0
    if not seq1 or not seq2:
        return 0.0

    dist = _edit_distance(seq1, seq2)
    max_len = max(len(seq1), len(seq2))
    return 1.0 - (dist / max_len)
