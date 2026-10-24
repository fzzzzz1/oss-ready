"""oss-ready: check whether a project is ready to be open sourced."""

from .checks import ERROR, OK, WARN, Finding, run_all, score

__version__ = "0.1.0"
__all__ = ["Finding", "run_all", "score", "OK", "WARN", "ERROR", "__version__"]
