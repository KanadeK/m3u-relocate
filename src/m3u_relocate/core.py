"""Plan local playlist migrations using explicit roots, never filename guesses."""

from __future__ import annotations

import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path, PurePath, PurePosixPath, PureWindowsPath
from urllib.parse import unquote, urlsplit

REMOTE_SCHEMES = frozenset({"http", "https", "rtsp", "rtmp", "mms", "ftp"})


def lexical_path(value: str) -> PurePath:
    """Interpret foreign drive/UNC paths without accessing their filesystem."""
    if not value or any(not char.isprintable() for char in value):
        raise ValueError("empty path or control character")
    if value.startswith(("\\\\?\\", "\\\\.\\", "//?/", "//./")):
        raise ValueError("Windows device namespaces are unsupported")
    if re.match(r"^[A-Za-z]:", value) or value.startswith(("\\\\", "//")):
        path = PureWindowsPath(value)
        if not path.is_absolute():
            raise ValueError("drive-relative or incomplete UNC path")
        if any(":" in part for part in path.parts[1:]):
            raise ValueError("Windows alternate stream syntax is unsupported")
    elif value.startswith("\\"):
        raise ValueError("rooted Windows path has no drive")
    else:
        if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", value):
            raise ValueError("unsupported URI scheme")
        path = PurePosixPath(value.replace("\\", "/"))
    if path.is_absolute() and ".." in path.parts:
        raise ValueError("absolute paths with parent segments are unsupported")
    return path


def file_uri(value: str) -> str:
    parts = urlsplit(value)
    if (
        parts.scheme.lower() != "file"
        or parts.query
        or parts.fragment
        or re.search(r"%(?![A-Fa-f0-9]{2})", value)
    ):
        raise ValueError("invalid file URI; queries/fragments are unsupported")
    if any(c in parts.netloc for c in "@:[]\\"):
        raise ValueError("invalid file URI host")
    path = unquote(parts.path, errors="strict")
    if parts.netloc and parts.netloc.lower() != "localhost":
        path = f"//{parts.netloc}{path}"
    elif re.match(r"^/[A-Za-z]:/", path):
        path = path[1:]
    if not path.startswith(("/", "\\")) and not re.match(r"^[A-Za-z]:/", path):
        raise ValueError("file URI must be absolute")
    return path


@dataclass(frozen=True)
class Mapping:
    old: PurePath
    new: Path

    @classmethod
    def parse(cls, specification: str) -> Mapping:
        old_text, separator, new_text = specification.partition("=")
        if not separator or not new_text:
            raise ValueError("mapping must be OLD_ABSOLUTE_ROOT=NEW_NATIVE_ROOT")
        old = lexical_path(old_text)
        if not old.is_absolute():
            raise ValueError("old mapping root must be absolute")
        new = Path(new_text).expanduser()
        if not new.is_absolute():
            raise ValueError("new mapping root must be an absolute native path")
        new = new.resolve(strict=True)
        if not new.is_dir():
            raise ValueError("new mapping root must be a directory")
        return cls(old, new)


def parse_mappings(specifications: list[str]) -> list[Mapping]:
    mappings = [Mapping.parse(spec) for spec in specifications]
    seen = set()
    for mapping in mappings:
        key = (
            type(mapping.old),
            str(mapping.old).casefold()
            if isinstance(mapping.old, PureWindowsPath)
            else str(mapping.old),
        )
        if key in seen:
            raise ValueError("duplicate mapping roots")
        seen.add(key)
    return sorted(mappings, key=lambda mapping: len(mapping.old.parts), reverse=True)


@dataclass
class Entry:
    line: int
    original: str
    kind: str
    output: str | None = None
    resolved: str | None = None
    mapped_root: str | None = None
    error: str | None = None


@dataclass
class Plan:
    lines: list[str]
    entries: list[Entry]

    @property
    def errors(self) -> int:
        return sum(entry.error is not None for entry in self.entries)

    def to_dict(self) -> dict:
        return {
            "schema_version": 1,
            "summary": {
                "entries": len(self.entries),
                "local": sum(entry.kind == "local" for entry in self.entries),
                "remote_unchecked": sum(entry.kind == "remote" for entry in self.entries),
                "errors": self.errors,
            },
            "entries": [asdict(entry) for entry in self.entries],
        }

    def render(self) -> str:
        if self.errors:
            raise ValueError("cannot render a playlist with unresolved entries")
        lines = self.lines.copy()
        for entry in self.entries:
            lines[entry.line - 1] = entry.output
        return "\n".join(lines)


def resolve_local(value: str, mappings: list[Mapping], base: Path) -> tuple[Path, str | None]:
    lexical = lexical_path(value)
    for mapping in mappings:
        if type(mapping.old) is not type(lexical):
            continue
        try:
            suffix = lexical.relative_to(mapping.old)
        except ValueError:
            continue
        candidate = mapping.new.joinpath(*suffix.parts).resolve(strict=True)
        if not candidate.is_relative_to(mapping.new):
            raise ValueError("mapped entry escapes its new root through a symlink")
        return candidate, str(mapping.old)
    if lexical.is_absolute():
        windows = isinstance(lexical, PureWindowsPath)
        if windows != (os.name == "nt"):
            raise ValueError("foreign absolute path needs an explicit root mapping")
        return Path(str(lexical)).resolve(strict=True), None
    return base.joinpath(*lexical.parts).resolve(strict=True), None


def plan_playlist(
    text: str,
    input_path: Path,
    output_path: Path,
    mappings: list[Mapping],
    base: Path | None = None,
    max_entries: int = 200_000,
) -> Plan:
    if max_entries < 1:
        raise ValueError("max_entries must be positive")
    if any(ord(char) < 32 and char not in "\r\n\t" for char in text):
        raise ValueError("playlist contains a control character")
    base = (base if base is not None else input_path.parent).resolve(strict=True)
    parent = output_path.parent.resolve(strict=True)
    if not base.is_dir() or not parent.is_dir():
        raise ValueError("input base and output parent must be directories")
    lines = text.removeprefix("\ufeff").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    entries = []
    for number, line in enumerate(lines, 1):
        if line.lstrip().startswith("#EXT-X-"):
            raise ValueError(f"line {number}: HLS playlists are unsupported")
        if not line.strip() or line.startswith("#"):
            continue
        if len(entries) >= max_entries:
            raise ValueError("playlist entry limit exceeded")
        entry = Entry(number, line, "local")
        entries.append(entry)
        try:
            if line != line.strip():
                raise ValueError("leading/trailing whitespace in a track path")
            scheme = urlsplit(line).scheme.lower() if "://" in line else ""
            if scheme in REMOTE_SCHEMES:
                parts = urlsplit(line)
                if not parts.netloc or any(
                    char.isspace() or not char.isprintable() for char in line
                ):
                    raise ValueError("invalid remote URL")
                entry.kind, entry.output = "remote", line
                continue
            value = file_uri(line) if scheme == "file" else line
            candidate, root = resolve_local(value, mappings, base)
            if not candidate.is_file():
                raise ValueError("entry does not resolve to a regular file")
            relative = os.path.relpath(candidate, parent).replace(os.sep, "/")
            if relative != relative.strip():
                raise ValueError("output path has ambiguous leading/trailing whitespace")
            if relative.startswith("#") or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", relative):
                relative = "./" + relative
            if any(not char.isprintable() for char in relative):
                raise ValueError("output path contains a control character")
            entry.output, entry.resolved, entry.mapped_root = relative, str(candidate), root
        except (OSError, ValueError, RuntimeError) as exc:
            # Path.resolve reports symlink loops as RuntimeError on older Python versions.
            entry.error = f"{type(exc).__name__}: {exc}"
    return Plan(lines, entries)
