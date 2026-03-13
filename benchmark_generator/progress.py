"""
Logging and progress-bar helpers shared by the CLI scripts.

* ``setup_file_logger`` creates a timestamped log file in a *logs/*
  directory and returns a :class:`logging.Logger` that writes to it.
* ``log_message`` writes a message to both the log file **and** the
  terminal (via :func:`tqdm.tqdm.write` so the progress bar stays
  visible).
"""

from __future__ import annotations

import logging
import os
import time

from tqdm import tqdm


def setup_file_logger(
    script_name: str,
    logs_dir: str = "logs",
) -> logging.Logger:
    """Return a :class:`~logging.Logger` that writes to *logs_dir*.

    The log file is named ``<script_name>_<YYYYMMDD_HHMMSS>.log``.
    """
    os.makedirs(logs_dir, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(logs_dir, f"{script_name}_{timestamp}.log")

    logger = logging.getLogger(script_name)
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers if called multiple times
    if not logger.handlers:
        handler = logging.FileHandler(log_file, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s — %(message)s"))
        logger.addHandler(handler)

    return logger


def log_message(logger: logging.Logger, msg: str) -> None:
    """Write *msg* to the log file and to the terminal above any tqdm bar."""
    logger.info(msg)
    tqdm.write(msg)
