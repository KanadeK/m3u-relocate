"""Reproducible path-migration demo; marker files deliberately contain no audio."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "demo-output").resolve()
    if root.exists() and any(root.iterdir()):
        raise SystemExit("Use an empty or new demo directory")
    library = root / "Music" / "Artist"
    library.mkdir(parents=True, exist_ok=True)
    (library / "A song.flac").write_bytes(b"Path-verification marker, not an audio recording.\n")
    source = root / "old.m3u8"
    source.write_text(
        "#EXTM3U\n#EXTINF:123,Example track\nE:\\Old Music\\Artist\\A song.flac\nhttps://example.invalid/stream\n",
        encoding="utf-8",
    )
    output = root / "portable.m3u8"
    args = [
        sys.executable,
        "-m",
        "m3u_relocate",
        str(source),
        "--output",
        str(output),
        "--map",
        f"E:\\Old Music={root / 'Music'}",
        "--format",
        "json",
    ]
    preview = subprocess.run(args, capture_output=True, text=True, check=True)
    if output.exists() or json.loads(preview.stdout)["summary"]["errors"]:
        raise RuntimeError("preview did not remain read-only")
    result = subprocess.run([*args, "--write"], capture_output=True, text=True, check=True)
    if not json.loads(result.stdout)["written"]:
        raise RuntimeError("playlist was not written")
    if "Music/Artist/A song.flac" not in output.read_text(encoding="utf-8"):
        raise RuntimeError("relative path mismatch")
    print(
        "Preview and write verified. The marker tests paths only; replace it with real audio for playback."
    )
    print(output)


if __name__ == "__main__":
    main()
