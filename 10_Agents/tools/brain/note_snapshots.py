"""Immutable normalized note content and its provenance, independent of the CLI.

Callers own file access and environment confinement. Parsing, search, and
embedding must use the same captured value instead of reopening the source.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib


def content_hash(text: str) -> str:
    """SHA-256 of text already normalized according to the note text model."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class NoteSnapshot:
    text: str | None
    size_bytes: int
    digest: str | None

    @classmethod
    def from_bytes(cls, raw: bytes) -> NoteSnapshot:
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            normalized = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
            return cls(None, len(normalized), None)
        text = text.removeprefix("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
        encoded = text.encode("utf-8")
        return cls(text, len(encoded), hashlib.sha256(encoded).hexdigest())
