"""
Local execution of Python snippets via an isolated subprocess.

The executor writes the snippet to a temporary file, runs it with the same
Python interpreter as the application (``sys.executable``), captures its
stdout/stderr and return code, measures execution time, enforces a timeout,
and guarantees that the temporary file is always deleted.
"""

import logging
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from app.config.settings import settings
from app.schemas.execution_schema import ExecutionResult

logger = logging.getLogger(__name__)

_NO_WINDOW_FLAG = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def execute_python_code(
    code: str,
    timeout_seconds: float | None = None,
) -> ExecutionResult:
    """Execute a Python snippet in a subprocess and return its result.

    Args:
        code: Python source code to execute.
        timeout_seconds: Optional per-call override of the execution
            timeout. Falls back to ``settings.sandbox_timeout_seconds``
            when None or 0.

    Returns:
        An ExecutionResult describing the outcome. Code-level failures
        (syntax errors, runtime errors) never raise here; they are reported
        through ``return_code`` and ``stderr``. Only environment-level
        failures while writing the temp file are allowed to propagate.
    """
    timeout = timeout_seconds or settings.sandbox_timeout_seconds
    tmp_path: Path | None = None

    try:
        tmp_path = _write_temp_file(code)
    except OSError as exc:
        logger.error("Failed to create temporary file: %s", exc)
        return ExecutionResult(
            stderr=f"Failed to create temporary file: {exc}",
        )

    start = time.perf_counter()
    try:
        completed = subprocess.run(
            [sys.executable, str(tmp_path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=_NO_WINDOW_FLAG,
        )
    except subprocess.TimeoutExpired as exc:
        elapsed_ms = _elapsed_ms(start)
        logger.warning("Execution timed out after %.2fs", timeout)
        return ExecutionResult(
            stdout=exc.stdout or "",
            stderr=exc.stderr or "",
            timed_out=True,
            execution_time_ms=elapsed_ms,
        )
    except OSError as exc:
        elapsed_ms = _elapsed_ms(start)
        logger.error("Failed to launch Python interpreter: %s", exc)
        return ExecutionResult(
            stderr=f"Failed to launch Python interpreter: {exc}",
            execution_time_ms=elapsed_ms,
        )
    finally:
        _delete_temp_file(tmp_path)

    elapsed_ms = _elapsed_ms(start)
    logger.debug("Execution finished with return code %s", completed.returncode)
    return ExecutionResult(
        stdout=completed.stdout,
        stderr=completed.stderr,
        return_code=completed.returncode,
        execution_time_ms=elapsed_ms,
    )


def _write_temp_file(code: str) -> Path:
    """Write ``code`` to a temporary ``.py`` file and return its path.

    ``tempfile.mkstemp`` is used instead of ``NamedTemporaryFile`` because
    the subprocess must be able to read the file on Windows, where a still
    open ``NamedTemporaryFile`` would hold an exclusive lock.
    """
    fd, name = tempfile.mkstemp(prefix="coach_", suffix=".py", text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(code)
    return Path(name)


def _delete_temp_file(path: Path) -> None:
    """Best-effort removal of a temporary file; never raises."""
    if path is None:
        return
    try:
        path.unlink(missing_ok=True)
    except OSError as exc:
        logger.warning("Could not delete temporary file %s: %s", path, exc)


def _elapsed_ms(start: float) -> float:
    """Wall-clock time since ``start`` in milliseconds, rounded to 2 dp."""
    return round((time.perf_counter() - start) * 1000, 2)
