"""
Safe function runner.

Executes a batch of inputs against a Python function defined by its source
code.  Uses ``subprocess.run`` so that infinite loops, crashes, or other
runtime errors cannot affect the calling process.

The entire batch is serialised as JSON, sent to a fresh Python subprocess,
and the results are deserialised back from the subprocess stdout.  This
approach avoids the process-pool teardown issues that can occur with
``concurrent.futures.ProcessPoolExecutor`` inside test runners.

Supported input/output types: int, bool, str, list[int], list[str], None.
These all round-trip cleanly through JSON.
"""

from __future__ import annotations

import json
import subprocess
import sys
from typing import Any, Optional


# ---------------------------------------------------------------------------
# The script that runs inside the subprocess
# ---------------------------------------------------------------------------

_WORKER_SCRIPT = """\
import json, sys

payload = json.loads(sys.stdin.read())
source    = payload["source"]
func_name = payload["func_name"]
inputs    = payload["inputs"]

namespace: dict = {}
try:
    exec(compile(source, "<benchmark>", "exec"), namespace)
except Exception as exc:
    print(json.dumps([(None, f"CompileError: {exc}")] * len(inputs)))
    sys.exit(0)

func = namespace.get(func_name)
if func is None:
    print(json.dumps([(None, f"NameError: '{func_name}' not found")] * len(inputs)))
    sys.exit(0)

results = []
for inp in inputs:
    try:
        r = func(*inp)
        results.append([r, None])
    except Exception as exc:
        results.append([None, f"{type(exc).__name__}: {exc}"])

print(json.dumps(results))
"""


# ---------------------------------------------------------------------------
# SafeRunner
# ---------------------------------------------------------------------------

class SafeRunner:
    """
    Run a function source on a batch of inputs inside a separate process.

    Parameters
    ----------
    timeout : seconds to allow for the *entire* batch
    """

    def __init__(self, timeout: float = 60.0) -> None:
        self.timeout = timeout

    def run_batch(
        self,
        source: str,
        func_name: str,
        inputs: list[tuple],
    ) -> list[tuple[Any, Optional[str]]]:
        """
        Execute *func_name* on every input tuple.

        Returns
        -------
        List of (return_value, error_string) pairs, one per input.
        ``error_string`` is ``None`` on success.
        If the subprocess times out, all entries are filled with a
        timeout error string.
        """
        if not inputs:
            return []

        payload = json.dumps(
            {
                "source": source,
                "func_name": func_name,
                # Convert tuples to lists for JSON serialisation
                "inputs": [list(inp) for inp in inputs],
            }
        )

        try:
            proc = subprocess.run(
                [sys.executable, "-c", _WORKER_SCRIPT],
                input=payload,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired:
            return [
                (None, "TimeoutError: batch exceeded time limit")
            ] * len(inputs)
        except Exception as exc:
            return [(None, f"SubprocessError: {exc}")] * len(inputs)

        if not proc.stdout.strip():
            stderr = proc.stderr.strip()
            return [(None, f"WorkerError: no output. stderr={stderr!r}")] * len(inputs)

        try:
            raw = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            return [(None, f"JSONDecodeError: {exc}")] * len(inputs)

        return [(r, e) for r, e in raw]

    def run_pair(
        self,
        p1_source: str,
        p2_source: str,
        func_name: str,
        inputs: list[tuple],
    ) -> tuple[list[tuple[Any, Optional[str]]], list[tuple[Any, Optional[str]]]]:
        """
        Convenience wrapper: run both p1 and p2 on the same inputs.

        Returns
        -------
        (p1_results, p2_results) — each is a list of (value, error) pairs.
        """
        p1_results = self.run_batch(p1_source, func_name, inputs)
        p2_results = self.run_batch(p2_source, func_name, inputs)
        return p1_results, p2_results
