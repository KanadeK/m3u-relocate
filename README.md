# m3u-relocate

Move a local music library without guessing where its playlists should point. **Preview explicit root mappings, verify every local file, then write a new relative M3U playlist.** The original playlist and media files are never modified or moved.

Python 3.10+, no runtime dependencies, no network requests. Works with foreign Windows drive/UNC paths on any supported OS. [中文说明](README.zh-CN.md).

## Install and try it

```sh
git clone https://github.com/KanadeK/m3u-relocate.git
cd m3u-relocate
python -m venv .venv
```

Activate using `source .venv/bin/activate` on Linux/macOS or `.venv\Scripts\Activate.ps1` in PowerShell:

```sh
python -m pip install .
m3u-relocate --version
python examples/demo.py demo-output
```

The demo creates a tiny library path fixture, previews a mapping from `E:\Old Music`, verifies that preview created no output, then writes `demo-output/portable.m3u8`. Its `.flac` file is explicitly a **non-audio marker** for path verification. Use a new or empty demo directory. No playable demo audio is fabricated or bundled.

Source installation and GitHub release archives are supported; no PyPI publication is claimed. `python -m m3u_relocate` is equivalent to the installed command.

## Migrate a real playlist

For a library moved from a Windows drive to `/srv/music`:

```sh
m3u-relocate old.m3u8 --map 'E:\Old Music=/srv/music' --output portable.m3u8 --format json
m3u-relocate old.m3u8 --map 'E:\Old Music=/srv/music' --output portable.m3u8 --write
```

The first command is a read-only preview. `--output` is required even for previews because relative references depend on the new playlist's directory. Fix any reported errors before running with `--write`. Existing output names, including dangling symlinks, are always refused; select another name or remove your own previous export.

On Windows, use a native destination, for example `--map 'E:\Old Music=D:\Music'`. New roots must be existing absolute native directories. Repeat `--map OLD=NEW` for several roots. Longest component-prefix match wins: `E:\Music` never matches `E:\MusicBackup`. Windows legacy roots compare case-insensitively, POSIX roots case-sensitively. Suffix spelling is preserved; this tool does not search for case variants or similar filenames.

Existing relative paths resolve against the input playlist's directory. Override this explicitly with `--base /path/to/library`. `--encoding cp1252` supports a known legacy input encoding; the default is UTF-8 with optional BOM. Output is UTF-8 without BOM, with LF line endings and forward-slash relative paths. New playlist and media must be on the same drive to express relative paths on Windows.

## What is verified

- Each local entry must resolve to an existing regular file. Directories, missing files, inaccessible paths and unmapped foreign roots produce per-entry errors.
- Source path, physical line, rendered relative path and resolved path are visible in `--format json`. Schema version 1 also includes entry/error counts and `written`.
- Comments (including `#EXTINF`), blank-line placement, entry order and remote HTTP(S)/RTSP/RTMP/MMS/FTP URLs are preserved as text. Remote URLs are explicitly **unchecked** and are never fetched.
- `file:` URIs are decoded as local references; Windows file URIs and UNC hosts can use explicit mappings. Unknown URI schemes are refused.
- Mapped symlinks cannot escape their new root. A native relative input can intentionally reference outside its base: this is not a filesystem sandbox.
- Writing occurs only when all local entries resolve. A read-only preview creates nothing, and a failed plan creates no output.

| Exit | Meaning |
|---|---|
| 0 | Every local entry resolves; preview or requested write succeeded |
| 1 | One or more entry errors; no output written |
| 2 | Input, format, mapping, argument or output error |

Inputs are limited to 16 MiB and 200,000 track entries by default; change the latter with `--max-entries N`. `--write` does not override either limit or existing output protection.

## Current limits and alternatives

Version 0.1.0 checks **paths**, not audio decoding, metadata accuracy or playback compatibility. It rejects HLS `#EXT-X-` playlists, Windows device/drive-relative paths, alternate streams, absolute paths containing parent segments, control characters and track paths with ambiguous edge whitespace. Backslashes are interpreted as separators; POSIX names containing literal backslashes are unsupported. Mapping source roots cannot contain `=`. Metadata tags are preserved, not interpreted or independently relocated.

The tool does not copy media, search by basename, repair unavailable streams, infer encodings or modify player databases. Filesystem changes after the check can invalidate the plan. Reports contain local paths and may include private URL tokens; inspect them before sharing. The input text is normalized to UTF-8/LF in output, so preservation is textual rather than byte-for-byte.

[Mopidy's M3U extension](https://docs.mopidy.com/latest/ext/m3u/) and media players can manage playlists inside their own libraries. Re-exporting from a functioning player is often convenient. This standalone tool instead makes cross-root migration explicit and verifiable without starting a media server or touching the source. The real path-portability problem is documented in [BluOS support](https://support.bluos.net/hc/en-us/articles/360000464567-Why-aren-t-all-my-Playlists-imported) and historical [Jellyfin issue 1874](https://github.com/jellyfin/jellyfin/issues/1874).

## Development and cleanup

See [contribution instructions](CONTRIBUTING.md), [acceptance/design](docs/DESIGN.md) and [security reporting](SECURITY.md). CI runs on Linux, Windows and macOS with Python 3.10/3.13 and read-only repository permissions. No automated code-committing bots are configured.

Uninstall with `python -m pip uninstall m3u-relocate`. After deactivating the environment, remove it and only the demo/export directories you created. Your real media and original playlists are unchanged.

MIT license; no third-party source/assets are bundled and there are no runtime dependencies. See [LICENSE](LICENSE).
