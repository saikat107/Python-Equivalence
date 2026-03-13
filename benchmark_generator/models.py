"""Data models for the benchmark generator."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class BenchmarkEntry:
    """
    A single benchmark entry: (p1, p2, ptests, ntests).

    Fields
    ------
    entry_id        : unique identifier
    func_name       : shared function name used by both p1 and p2
    param_types     : list of parameter-type annotation strings
    return_type     : return-type annotation string
    p1_source       : full source code of the first implementation
    p2_source       : full source code of the second implementation
    ptests          : list of input tuples where p1(*t) == p2(*t)
    ntests          : list of input tuples where p1(*t) != p2(*t)
    is_equivalent   : ground-truth label (set at construction time)
    metadata        : provenance and other bookkeeping information
    """

    entry_id: str
    func_name: str
    param_types: list[str]
    return_type: str
    p1_source: str
    p2_source: str
    ptests: list[list]
    ntests: list[list]
    is_equivalent: bool
    metadata: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Validity check
    # ------------------------------------------------------------------
    @property
    def is_valid(self) -> bool:
        """
        An entry is valid when:
          * positive pair  → at least 1 000 distinct ptests
          * negative pair  → at least 1 ntest
        """
        if self.is_equivalent:
            return len(self.ptests) >= 1000
        else:
            return len(self.ntests) >= 1

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "func_name": self.func_name,
            "param_types": self.param_types,
            "return_type": self.return_type,
            "p1_source": self.p1_source,
            "p2_source": self.p2_source,
            "ptests": self.ptests,
            "ntests": self.ntests,
            "is_equivalent": self.is_equivalent,
            "num_ptests": len(self.ptests),
            "num_ntests": len(self.ntests),
            "is_valid": self.is_valid,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "BenchmarkEntry":
        return cls(
            entry_id=d["entry_id"],
            func_name=d["func_name"],
            param_types=d["param_types"],
            return_type=d["return_type"],
            p1_source=d["p1_source"],
            p2_source=d["p2_source"],
            ptests=d["ptests"],
            ntests=d["ntests"],
            is_equivalent=d["is_equivalent"],
            metadata=d.get("metadata", {}),
        )
