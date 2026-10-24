"""Preview first; write only a fully resolved new playlist on explicit --write."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import __version__
from .core import parse_mappings, plan_playlist

MAX_BYTES = 16 * 1024 * 1024


def positive(value: str) -> int:
    result = int(value)
    if result < 1:
        raise argparse.ArgumentTypeError("must be positive")
    return result


def write_new(path: Path, text: str) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        stream = os.fdopen(fd, "w", encoding="utf-8", newline="")
    except BaseException:
        os.close(fd)
        path.unlink(missing_ok=True)
        raise
    try:
        with stream:
            stream.write(text)
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Preview and verify an M3U root migration locally."
    )
    parser.add_argument("input", type=Path)
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="New playlist path (also needed to calculate relative paths in previews)",
    )
    parser.add_argument(
        "--map",
        dest="mappings",
        action="append",
        default=[],
        metavar="OLD=NEW",
        help="Repeat for multiple roots; longest component match wins",
    )
    parser.add_argument(
        "--base",
        type=Path,
        help="Base for existing relative references; default input playlist directory",
    )
    parser.add_argument(
        "--encoding",
        default="utf-8-sig",
        help="Explicit input codec; output is always UTF-8 without BOM",
    )
    parser.add_argument("--max-entries", type=positive, default=200_000)
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write only if every local entry resolves; default is a preview",
    )
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--version", action="version", version=__version__)
    args = parser.parse_args(argv)
    try:
        if os.path.lexists(args.output):
            raise FileExistsError("output already exists; choose a new name")
        with args.input.open("rb") as stream:
            data = stream.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ValueError("input exceeds 16 MiB")
        text = data.decode(args.encoding)
        mappings = parse_mappings(args.mappings)
        plan = plan_playlist(text, args.input, args.output, mappings, args.base, args.max_entries)
        written = False
        if args.write and not plan.errors:
            write_new(args.output, plan.render())
            written = True
        report = plan.to_dict()
        report["written"] = written
        if args.format == "json":
            print(json.dumps(report, ensure_ascii=True, indent=2))
        else:
            summary = report["summary"]
            print(
                f"{'Wrote playlist' if written else 'Preview'}: {summary['local']} local entries; {summary['remote_unchecked']} remote URLs left unchecked; {plan.errors} errors"
            )
            for entry in (e for e in plan.entries if e.error):
                print(f"line {entry.line}: {ascii(entry.error)}")
        return int(bool(plan.errors))
    except (OSError, ValueError, UnicodeError, LookupError) as exc:
        print(f"m3u-relocate: {ascii(str(exc))}", file=sys.stderr)
        return 2
