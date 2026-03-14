"""
AST-based type annotation parser.

Extracts parameter types and return types from Python function source code
by parsing the AST.  Supports arbitrarily complex nested type annotations
such as ``dict[str, list[tuple[str, str, bool]]]``.

Works with both:
- Native Python 3.9+ syntax: ``dict[str, list[int]]``
- ``typing`` module aliases: ``Dict[str, List[int]]``
- ``from __future__ import annotations`` (string annotations)
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# ------------------------------------------------------------------
# Type tree representation
# ------------------------------------------------------------------

@dataclass
class TypeNode:
    """A node in the parsed type-annotation tree.

    Examples
    --------
    ``int``                          → ``TypeNode('int')``
    ``list[int]``                    → ``TypeNode('list', [TypeNode('int')])``
    ``tuple[int, ...]``              → ``TypeNode('tuple', [TypeNode('int')], is_variadic=True)``
    ``dict[str, list[tuple[str,…]]]``→ nested ``TypeNode`` tree
    """

    name: str
    args: List[TypeNode] = field(default_factory=list)
    is_variadic: bool = False  # True for ``tuple[T, ...]``

    # Allow equality checks for signature compatibility
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TypeNode):
            return NotImplemented
        return (
            self.name == other.name
            and self.args == other.args
            and self.is_variadic == other.is_variadic
        )

    def __hash__(self) -> int:
        return hash((self.name, tuple(self.args), self.is_variadic))

    def __repr__(self) -> str:
        if not self.args:
            return self.name
        inner = ", ".join(repr(a) for a in self.args)
        suffix = ", ..." if self.is_variadic else ""
        return f"{self.name}[{inner}{suffix}]"


# ------------------------------------------------------------------
# Parsed function signature
# ------------------------------------------------------------------

@dataclass
class FunctionSignature:
    """Parsed function signature with typed parameters and return type."""

    name: str
    params: List[Tuple[str, TypeNode]]
    return_type: Optional[TypeNode]

    def param_types(self) -> List[TypeNode]:
        """Return just the parameter types (without names)."""
        return [t for _, t in self.params]


# ------------------------------------------------------------------
# Typing → builtin name normalisation
# ------------------------------------------------------------------

_TYPING_TO_BUILTIN: dict[str, str] = {
    "List": "list",
    "Dict": "dict",
    "Tuple": "tuple",
    "Set": "set",
    "FrozenSet": "frozenset",
    "Sequence": "list",
}


# ------------------------------------------------------------------
# Recursive annotation-node parser
# ------------------------------------------------------------------

def _parse_annotation_node(node: ast.expr) -> TypeNode:
    """Recursively convert an AST expression into a :class:`TypeNode`."""

    # --- constant values (None, Ellipsis, or string annotations) ---
    if isinstance(node, ast.Constant):
        if node.value is None:
            return TypeNode("None")
        if node.value is ...:
            return TypeNode("...")
        # String annotation (``from __future__ import annotations``)
        if isinstance(node.value, str):
            try:
                inner = ast.parse(node.value, mode="eval").body
                return _parse_annotation_node(inner)
            except SyntaxError:
                return TypeNode("Any")
        return TypeNode(str(type(node.value).__name__))

    # --- bare name like ``int``, ``str``, ``List``, … ---
    if isinstance(node, ast.Name):
        name = _TYPING_TO_BUILTIN.get(node.id, node.id)
        return TypeNode(name)

    # --- qualified name like ``typing.List`` ---
    if isinstance(node, ast.Attribute):
        name = _TYPING_TO_BUILTIN.get(node.attr, node.attr)
        return TypeNode(name)

    # --- parameterised type like ``list[int]``, ``Dict[str, int]`` ---
    if isinstance(node, ast.Subscript):
        base = _parse_annotation_node(node.value)

        # Unpack slice (single arg vs tuple of args)
        slice_node = node.slice
        if isinstance(slice_node, ast.Tuple):
            args = [_parse_annotation_node(elt) for elt in slice_node.elts]
        else:
            args = [_parse_annotation_node(slice_node)]

        # ``tuple[int, ...]`` → variadic tuple
        if base.name == "tuple" and len(args) >= 2 and args[-1].name == "...":
            return TypeNode("tuple", args[:-1], is_variadic=True)

        # ``Optional[T]``
        if base.name == "Optional" and len(args) == 1:
            return TypeNode("Optional", args)

        # ``Union[T, None]`` → ``Optional[T]``
        if base.name == "Union":
            non_none = [a for a in args if a.name != "None"]
            has_none = any(a.name == "None" for a in args)
            if has_none and len(non_none) == 1:
                return TypeNode("Optional", non_none)
            return TypeNode("Union", args)

        base.args = args
        return base

    # --- ``T | None`` union syntax (Python 3.10+) ---
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        left = _parse_annotation_node(node.left)
        right = _parse_annotation_node(node.right)
        if right.name == "None":
            return TypeNode("Optional", [left])
        if left.name == "None":
            return TypeNode("Optional", [right])
        return TypeNode("Union", [left, right])

    # --- fallback ---
    return TypeNode("Any")


# ------------------------------------------------------------------
# Public helpers
# ------------------------------------------------------------------

def extract_function_signature(
    source: str, func_name: str
) -> FunctionSignature:
    """Extract the signature of *func_name* from Python *source* code.

    Raises ``ValueError`` if the function is not found.
    """
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == func_name:
                params: list[tuple[str, TypeNode]] = []
                for arg in node.args.args:
                    if arg.arg == "self":
                        continue
                    type_node = (
                        _parse_annotation_node(arg.annotation)
                        if arg.annotation is not None
                        else TypeNode("Any")
                    )
                    params.append((arg.arg, type_node))

                return_type = (
                    _parse_annotation_node(node.returns)
                    if node.returns is not None
                    else None
                )

                return FunctionSignature(
                    name=func_name,
                    params=params,
                    return_type=return_type,
                )

    raise ValueError(f"Function '{func_name}' not found in source")


def list_functions(source: str) -> list[str]:
    """Return names of all top-level function definitions in *source*."""
    tree = ast.parse(source)
    return [
        node.name
        for node in ast.iter_child_nodes(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
