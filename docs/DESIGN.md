# MVP and acceptance criteria

Audience: local-library owners with obsolete M3U roots after a move between machines or a NAS migration. A complete workflow is explicit mapping → preview → fix unresolved paths → write a separate UTF-8 relative playlist. The tool verifies path existence/regular-file type; it never asserts that a file decodes or plays.

Foreign Windows drive and UNC paths are parsed lexically on every OS. Windows legacy roots compare case-insensitively; POSIX roots compare case-sensitively. Component boundaries prevent `Music` from matching `MusicBackup`. Longest matching explicit root wins; duplicate roots fail. Relative references resolve from `--base` or the original playlist directory. New paths are relative to the output playlist's directory, not the process working directory.

Absolute paths containing `..`, Windows device/drive-relative forms and alternate streams are rejected. A mapped symlink resolving outside the new root is refused. A native relative input may intentionally reference outside its base; this is a path-migration tool, not a filesystem sandbox. Only metadata/stat checks are performed. Filesystem contents must remain stable between planning and later playback.

Preserve comments, blank-line placement, entry ordering and remote HTTP(S)/RTSP/RTMP/MMS/FTP URLs. Normalize CR/LF to LF and output UTF-8 without BOM. File URIs become local references. Reject HLS `#EXT-X-` tags, unknown URI schemes, malformed encodings and ambiguous whitespace. Do not search for similarly named files, modify media, follow network URLs or update an existing playlist in place. Remote URLs are explicitly reported as unchecked.

Acceptance: cross-root and foreign-drive mappings; Unicode/space filenames; literal `#` track names; missing/directory entries; false-prefix mismatches; two overlapping roots; map escape through symlinks where supported; read-only preview; complete refusal of output on any unresolved entry; existing output/symlink protection; alternate input codec; installed CLI and a reproducible demo from a clean source install. Resource caps are 16 MiB and 200,000 tracks by default.
