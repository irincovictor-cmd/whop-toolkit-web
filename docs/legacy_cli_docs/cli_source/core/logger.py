"""
Shared logging setup.

Every module should use `from core.logger import get_logger` instead
of print() for anything that isn't meant to be direct CLI output.
Keeps errors friendly on screen but detailed in the log file.
"""

import logging
import config

_configured = False


def _configure_root_logger():
    global _configured
    if _configured:
        return

    log_file = config.LOGS_FOLDER / "whop.log"

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)

    root = logging.getLogger("whop")
    root.setLevel(logging.DEBUG)
    root.addHandler(file_handler)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """
    Returns a logger that writes to logs/whop.log.
    Console output is left to the CLI (print statements),
    this is for the persistent debug trail.
    """
    _configure_root_logger()
    return logging.getLogger(f"whop.{name}")
