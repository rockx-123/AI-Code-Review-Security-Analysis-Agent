"""
Executes validated Python/Java code and captures its output.

READ docs/code-execution-safety.md BEFORE ENABLING THIS IN ANY PUBLIC-FACING DEPLOYMENT.

This is a best-effort safety layer around subprocess execution, NOT a full sandbox:
  - Enforced: wall-clock timeout, output size cap, a stripped environment (no host env vars
    leaked to the executed process), best-effort CPU/memory rlimits on POSIX systems.
  - NOT enforced: network isolation, filesystem isolation, or protection against a
    sufficiently determined malicious payload. A real sandbox needs a container/VM boundary
    (e.g. Docker, gVisor, Firecracker) — this module does not provide that.

Gated behind `settings.enable_code_execution`, which defaults to False. The API route checks
this flag before ever calling into this module.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from app.config import get_settings
from app.models.schemas import ExecutionResult

try:
    import resource  # POSIX only
    _HAS_RESOURCE = True
except ImportError:  # Windows dev environments
    _HAS_RESOURCE = False

_MAX_MEMORY_BYTES = 256 * 1024 * 1024  # 256 MB
_MAX_CPU_SECONDS = 5


def _limit_resources() -> None:
    """Best-effort rlimits applied in the child process before exec. POSIX only; silently
    skipped on platforms without the `resource` module (e.g. Windows)."""
    if not _HAS_RESOURCE:
        return
    try:
        resource.setrlimit(resource.RLIMIT_AS, (_MAX_MEMORY_BYTES, _MAX_MEMORY_BYTES))
        resource.setrlimit(resource.RLIMIT_CPU, (_MAX_CPU_SECONDS, _MAX_CPU_SECONDS))
        resource.setrlimit(resource.RLIMIT_NPROC, (32, 32))
    except (ValueError, OSError):
        # Some hosts (containers with restrictive parent limits) reject certain rlimits —
        # fail open on the limit itself rather than crashing the whole execution feature.
        pass


def _stripped_env() -> dict:
    """A minimal environment for the child process — deliberately excludes the host's real
    environment variables (which may contain secrets like LLM_API_KEY) from being readable
    by executed code via os.environ / System.getenv."""
    return {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": "/tmp"}


def _truncate(text: str, limit: int) -> tuple[str, bool]:
    if len(text) <= limit:
        return text, False
    return text[:limit] + "\n… (output truncated)", True


def _run_subprocess(cmd: list[str], cwd: str, timeout: int) -> tuple[str, str, int | None, bool]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=_stripped_env(),
            preexec_fn=_limit_resources if _HAS_RESOURCE else None,
        )
        return proc.stdout, proc.stderr, proc.returncode, False
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or "" if isinstance(exc.stdout, str) else (exc.stdout or b"").decode("utf-8", "replace")
        stderr = exc.stderr or "" if isinstance(exc.stderr, str) else (exc.stderr or b"").decode("utf-8", "replace")
        return stdout, stderr, None, True


def run_python(code: str) -> ExecutionResult:
    settings = get_settings()
    start = time.monotonic()
    with tempfile.TemporaryDirectory() as tmp:
        script_path = Path(tmp) / "submission.py"
        script_path.write_text(code, encoding="utf-8")
        stdout, stderr, exit_code, timed_out = _run_subprocess(
            [sys.executable, "-I", str(script_path)],  # -I: isolated mode, ignores env/site config
            cwd=tmp,
            timeout=settings.execution_timeout_seconds,
        )
    duration_ms = int((time.monotonic() - start) * 1000)
    stdout, out_trunc = _truncate(stdout, settings.execution_max_output_chars)
    stderr, err_trunc = _truncate(stderr, settings.execution_max_output_chars)
    return ExecutionResult(
        ran=True,
        stdout=stdout,
        stderr=stderr,
        exit_code=exit_code,
        timed_out=timed_out,
        truncated=out_trunc or err_trunc,
        duration_ms=duration_ms,
    )


def run_java(code: str) -> ExecutionResult:
    settings = get_settings()
    start = time.monotonic()

    import re
    match = re.search(r"public\s+(?:final\s+|abstract\s+)?class\s+([A-Za-z_][A-Za-z0-9_]*)", code)
    class_name = match.group(1) if match else "Main"

    with tempfile.TemporaryDirectory() as tmp:
        src_path = Path(tmp) / f"{class_name}.java"
        src_path.write_text(code, encoding="utf-8")

        compile_stdout, compile_stderr, compile_code, compile_timeout = _run_subprocess(
            ["javac", str(src_path)],
            cwd=tmp,
            timeout=settings.execution_timeout_seconds,
        )
        if compile_code != 0 or compile_timeout:
            duration_ms = int((time.monotonic() - start) * 1000)
            stderr, trunc = _truncate(compile_stderr or "Compilation failed.", settings.execution_max_output_chars)
            return ExecutionResult(
                ran=False,
                stderr=stderr,
                exit_code=compile_code,
                timed_out=compile_timeout,
                truncated=trunc,
                duration_ms=duration_ms,
                error="Compilation failed — see stderr.",
            )

        stdout, stderr, exit_code, timed_out = _run_subprocess(
            ["java", "-cp", tmp, class_name],
            cwd=tmp,
            timeout=settings.execution_timeout_seconds,
        )

    duration_ms = int((time.monotonic() - start) * 1000)
    stdout, out_trunc = _truncate(stdout, settings.execution_max_output_chars)
    stderr, err_trunc = _truncate(stderr, settings.execution_max_output_chars)
    return ExecutionResult(
        ran=True,
        stdout=stdout,
        stderr=stderr,
        exit_code=exit_code,
        timed_out=timed_out,
        truncated=out_trunc or err_trunc,
        duration_ms=duration_ms,
    )


def run_code(language: str, code: str) -> ExecutionResult:
    if language == "python":
        return run_python(code)
    if language == "java":
        import shutil
        if not shutil.which("javac") or not shutil.which("java"):
            return ExecutionResult(
                ran=False,
                error="No JDK found on this server (javac/java not on PATH) — Java execution unavailable here.",
            )
        return run_java(code)
    return ExecutionResult(ran=False, error=f"Execution not supported for language: {language}")
