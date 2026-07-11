"""
Handles upload constraints for the Code Submission Module: extension allow-list, size limit,
language inference from extension, and safe decoding.
"""
from __future__ import annotations

from app.config import get_settings
from app.models.schemas import Language

_EXTENSION_TO_LANGUAGE = {
    ".py": Language.PYTHON,
    ".java": Language.JAVA,
}


class UploadValidationError(Exception):
    """Raised for any upload that fails the submission module's intake rules."""


def infer_language_from_filename(filename: str) -> Language:
    settings = get_settings()
    suffix = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if suffix not in settings.allowed_extension_list:
        raise UploadValidationError(
            f"Unsupported file extension '{suffix or '(none)'}'. "
            f"Allowed: {', '.join(settings.allowed_extension_list)}"
        )
    return _EXTENSION_TO_LANGUAGE[suffix]


def enforce_size_limit(size_bytes: int) -> None:
    settings = get_settings()
    if size_bytes <= 0:
        raise UploadValidationError("Uploaded file is empty.")
    if size_bytes > settings.max_upload_size_bytes:
        limit_kb = settings.max_upload_size_bytes // 1024
        raise UploadValidationError(f"File exceeds the {limit_kb} KB upload limit.")


def decode_source(raw: bytes) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise UploadValidationError(
            "File is not valid UTF-8 text — binary files can't be reviewed."
        ) from exc
