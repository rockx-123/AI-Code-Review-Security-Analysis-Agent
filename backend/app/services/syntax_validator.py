"""
Syntax validation for the Code Submission Module.

Design note: this is intentionally an interface (`SyntaxValidator`) with one implementation per
language, so adding a third language later (per docs/architecture.md §5) means writing one new
class, not touching the API route or the orchestration layer.
"""
from __future__ import annotations

import ast
import re
import shutil
import subprocess
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path

from app.models.schemas import SyntaxValidationResult, ValidationError


class SyntaxValidator(ABC):
    @abstractmethod
    def validate(self, code: str) -> SyntaxValidationResult:
        raise NotImplementedError


class PythonSyntaxValidator(SyntaxValidator):
    """Uses Python's built-in `ast` module — exact, no external tooling required."""

    def validate(self, code: str) -> SyntaxValidationResult:
        try:
            ast.parse(code)
            return SyntaxValidationResult(is_valid=True, errors=[])
        except SyntaxError as exc:
            return SyntaxValidationResult(
                is_valid=False,
                errors=[
                    ValidationError(
                        line=exc.lineno,
                        column=exc.offset,
                        message=exc.msg or "Invalid Python syntax",
                    )
                ],
            )
        except (ValueError, TypeError) as exc:  # e.g. null bytes in source
            return SyntaxValidationResult(
                is_valid=False,
                errors=[ValidationError(line=None, column=None, message=str(exc))],
            )


class JavaSyntaxValidator(SyntaxValidator):
    """
    Validates Java source.

    Prefers `javac -Xstdout` for an exact compiler-grade check when a JDK is available on the
    host. Falls back to a structural heuristic check (balanced braces/parens/brackets, balanced
    quotes, presence of a class/interface/enum declaration) when `javac` isn't installed, so the
    Code Submission Module still works in environments without a JDK — at reduced precision,
    which is surfaced to the caller.
    """

    _JAVAC = shutil.which("javac")

    def validate(self, code: str) -> SyntaxValidationResult:
        if self._JAVAC:
            return self._validate_with_javac(code)
        return self._validate_heuristically(code)

    # -- exact path -----------------------------------------------------

    def _validate_with_javac(self, code: str) -> SyntaxValidationResult:
        class_name = self._guess_public_class_name(code) or "Submission"
        with tempfile.TemporaryDirectory() as tmp:
            src_path = Path(tmp) / f"{class_name}.java"
            src_path.write_text(code, encoding="utf-8")
            result = subprocess.run(
                [self._JAVAC, "-d", tmp, str(src_path)],
                capture_output=True,
                text=True,
                timeout=15,
            )
        if result.returncode == 0:
            return SyntaxValidationResult(is_valid=True, errors=[])

        errors = self._parse_javac_errors(result.stderr, src_path.name if 'src_path' in locals() else "")
        if not errors:
            errors = [ValidationError(line=None, column=None, message=result.stderr.strip()[:500] or "Compilation failed")]
        return SyntaxValidationResult(is_valid=False, errors=errors)

    @staticmethod
    def _guess_public_class_name(code: str) -> str | None:
        match = re.search(r"public\s+(?:final\s+|abstract\s+)?class\s+([A-Za-z_][A-Za-z0-9_]*)", code)
        return match.group(1) if match else None

    @staticmethod
    def _parse_javac_errors(stderr: str, filename: str) -> list[ValidationError]:
        errors: list[ValidationError] = []
        # javac format: "Submission.java:3: error: ';' expected"
        pattern = re.compile(r":(\d+):\s*(?:error|warning):\s*(.+)")
        for line in stderr.splitlines():
            m = pattern.search(line)
            if m:
                errors.append(
                    ValidationError(line=int(m.group(1)), column=None, message=m.group(2).strip())
                )
        return errors

    # -- fallback path ----------------------------------------------------

    def _validate_heuristically(self, code: str) -> SyntaxValidationResult:
        errors: list[ValidationError] = []

        if not re.search(r"\b(class|interface|enum|record)\s+[A-Za-z_][A-Za-z0-9_]*", code):
            errors.append(
                ValidationError(
                    line=None,
                    column=None,
                    message="No class, interface, enum, or record declaration found.",
                )
            )

        brace_error = self._check_balanced(code, "{", "}")
        if brace_error:
            errors.append(brace_error)
        paren_error = self._check_balanced(code, "(", ")")
        if paren_error:
            errors.append(paren_error)
        bracket_error = self._check_balanced(code, "[", "]")
        if bracket_error:
            errors.append(bracket_error)

        is_valid = not errors
        if is_valid:
            # Note the reduced-precision mode so the caller/UI can be honest about it.
            errors = [
                ValidationError(
                    line=None,
                    column=None,
                    message=(
                        "javac not found on this host — validated structurally "
                        "(balanced braces/parens, class declaration present) rather than "
                        "compiled. Install a JDK for exact compiler diagnostics."
                    ),
                )
            ]
            return SyntaxValidationResult(is_valid=True, errors=errors)

        return SyntaxValidationResult(is_valid=False, errors=errors)

    @staticmethod
    def _check_balanced(code: str, open_ch: str, close_ch: str) -> ValidationError | None:
        depth = 0
        in_string = False
        in_char = False
        in_line_comment = False
        in_block_comment = False
        line = 1
        escape = False

        i = 0
        length = len(code)
        while i < length:
            ch = code[i]
            nxt = code[i + 1] if i + 1 < length else ""

            if ch == "\n":
                line += 1
                in_line_comment = False

            if in_line_comment:
                i += 1
                continue
            if in_block_comment:
                if ch == "*" and nxt == "/":
                    in_block_comment = False
                    i += 2
                    continue
                i += 1
                continue
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
                i += 1
                continue
            if in_char:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == "'":
                    in_char = False
                i += 1
                continue

            if ch == "/" and nxt == "/":
                in_line_comment = True
                i += 2
                continue
            if ch == "/" and nxt == "*":
                in_block_comment = True
                i += 2
                continue
            if ch == '"':
                in_string = True
                i += 1
                continue
            if ch == "'":
                in_char = True
                i += 1
                continue

            if ch == open_ch:
                depth += 1
            elif ch == close_ch:
                depth -= 1
                if depth < 0:
                    return ValidationError(
                        line=line, column=None, message=f"Unmatched closing '{close_ch}'."
                    )
            i += 1

        if depth != 0:
            return ValidationError(
                line=None,
                column=None,
                message=f"Unbalanced '{open_ch}{close_ch}' — {abs(depth)} unclosed.",
            )
        return None


_VALIDATORS: dict[str, SyntaxValidator] = {
    "python": PythonSyntaxValidator(),
    "java": JavaSyntaxValidator(),
}


def get_validator(language: str) -> SyntaxValidator:
    try:
        return _VALIDATORS[language]
    except KeyError as exc:
        raise ValueError(f"Unsupported language: {language}") from exc
