"""File-system storage for uploaded images (student avatars, school logos).

Files are persisted under ``<static_root>/uploads/<subdir>/`` (i.e.
``app/static/uploads/`` in production) and served back at
``/static/uploads/<subdir>/<filename>`` via the ``StaticFiles`` mount.

Security posture:

* stored names are generated (``<prefix>_<16 hex>.<ext>``) — the client's
  filename is never used on disk, so path traversal is structurally impossible;
* bytes are validated by magic-number sniffing, not by trusting the
  client-declared ``Content-Type`` or extension;
* deletions are double-checked against the uploads root before unlinking.
"""

from __future__ import annotations

import contextlib
import os
import re
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

from app.core.errors import PayloadTooLargeError, ServiceError, StorageError

_SAFE_SUBDIR = re.compile(r"\A[a-z0-9_]{1,32}\Z")
_UNSAFE_PREFIX_CHARS = re.compile(r"[^A-Za-z0-9._-]+")

#: Content types we treat as "client didn't really tell us" and accept the
#: sniffed type instead.
_LENIENT_DECLARED_TYPES = frozenset({"", "application/octet-stream", "application/unknown"})

#: image_format -> (extension, canonical MIME type)
_IMAGE_FORMATS: dict[str, tuple[str, str]] = {
    "png": (".png", "image/png"),
    "jpeg": (".jpg", "image/jpeg"),
    "gif": (".gif", "image/gif"),
    "webp": (".webp", "image/webp"),
}


def _detect_image_format(data: bytes) -> str | None:
    """Identify an image by its file signature (magic bytes)."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "gif"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


@dataclass(frozen=True, slots=True)
class StoredImage:
    """Metadata about a successfully persisted upload."""

    subdir: str
    filename: str
    content_type: str
    size_bytes: int


class FileStorageService:
    """Writes and removes image files inside the uploads root.

    The service is framework-agnostic: routers decode ``UploadFile`` content
    and hand raw ``bytes`` to :meth:`save_image`.
    """

    def __init__(
        self,
        uploads_root: Path,
        *,
        max_bytes: int,
        allowed_subdirs: tuple[str, ...] = ("avatars", "logos"),
    ) -> None:
        for subdir in allowed_subdirs:
            if not _SAFE_SUBDIR.match(subdir):
                raise ValueError(f"unsafe upload sub-directory name: {subdir!r}")
        if max_bytes <= 0:
            raise ValueError("max_bytes must be positive")
        self._root = Path(uploads_root)
        self._max_bytes = max_bytes
        self._allowed_subdirs = tuple(allowed_subdirs)

    # -- introspection -----------------------------------------------------

    @property
    def root(self) -> Path:
        return self._root

    @property
    def max_bytes(self) -> int:
        return self._max_bytes

    # -- lifecycle -----------------------------------------------------------

    def ensure_dirs(self) -> None:
        """Create the uploads root and every allowed sub-directory."""
        for subdir in self._allowed_subdirs:
            (self._root / subdir).mkdir(parents=True, exist_ok=True)

    # -- writes ------------------------------------------------------------

    def save_image(
        self,
        *,
        subdir: str,
        data: bytes,
        declared_content_type: str | None,
        prefix: str,
    ) -> StoredImage:
        """Validate *data* as a supported image and persist it atomically.

        Raises :class:`ServiceError` (400) for empty/unsupported/mismatched
        payloads and :class:`PayloadTooLargeError` (413) when *data* exceeds
        the configured size limit.
        """
        directory = self._directory_for(subdir)

        if not data:
            raise ServiceError("uploaded file is empty")
        if len(data) > self._max_bytes:
            raise PayloadTooLargeError(
                f"uploaded file is {len(data)} bytes, exceeding the "
                f"{self._max_bytes}-byte limit"
            )

        image_format = _detect_image_format(data)
        if image_format is None:
            raise ServiceError(
                "unsupported file type: expected PNG, JPEG, WebP or GIF image data"
            )
        extension, content_type = _IMAGE_FORMATS[image_format]

        declared = (declared_content_type or "").split(";")[0].strip().lower()
        if declared and declared not in _LENIENT_DECLARED_TYPES and declared != content_type:
            raise ServiceError(
                f"declared content type {declared!r} does not match the file "
                f"contents ({content_type})"
            )

        safe_prefix = _UNSAFE_PREFIX_CHARS.sub("-", prefix.strip()).strip("-._")[:48]
        if not safe_prefix:
            safe_prefix = "upload"
        filename = f"{safe_prefix}_{uuid.uuid4().hex[:16]}{extension}"
        destination = directory / filename

        handle_fd, temp_path = tempfile.mkstemp(
            dir=str(directory), prefix=".tmp_", suffix=extension
        )
        try:
            with os.fdopen(handle_fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temp_path, 0o644)
            os.replace(temp_path, destination)  # atomic on POSIX file systems
        except OSError as exc:
            with contextlib.suppress(OSError):
                os.unlink(temp_path)
            raise StorageError(f"could not persist upload: {exc}") from exc

        return StoredImage(
            subdir=subdir,
            filename=filename,
            content_type=content_type,
            size_bytes=len(data),
        )

    # -- deletes -----------------------------------------------------------

    def delete(self, *, subdir: str, filename: str) -> bool:
        """Remove one stored file. Returns ``True`` only if a file was deleted."""
        directory = self._directory_for(subdir).resolve()
        target = (directory / filename).resolve()
        if not target.is_relative_to(directory):  # defensive; names are generated
            raise ServiceError("refusing to delete a path outside the uploads directory")
        if not target.is_file():
            return False
        try:
            target.unlink(missing_ok=True)
        except OSError as exc:
            raise StorageError(f"could not delete {filename!r}: {exc}") from exc
        return True

    # -- helpers -------------------------------------------------------------

    def _directory_for(self, subdir: str) -> Path:
        if subdir not in self._allowed_subdirs:
            raise ValueError(f"{subdir!r} is not an allowed upload sub-directory")
        return self._root / subdir
