# Release validation — 0.1.0

Local checks on Windows/Python 3.13.16, 2026-10-24:

- 27 unittest cases: 24 passed, three platform/privilege skips (two symlink creation tests need Windows privilege; a literal colon filename is POSIX-only). The same cases run on Linux/macOS in CI, where these boundaries can be exercised without Windows symlink privilege. Consult the actual workflow for results.
- 95% measured combined statement/branch coverage before final release checks. Coverage does not include subprocess code in the parent's data. Tests exercise foreign Windows and UNC roots, component boundaries, overlapping roots, file URIs, Unicode, metadata, remote URL preservation, explicit encodings, missing files, preview, write and overwrite refusal.
- Ruff lint/security rules and formatting, wheel/sdist builds and clean source installation are required release gates. Runtime third-party dependencies: none. The separate tooling audit found no known dependency vulnerabilities when checked; it does not audit the Python runtime or prove absence of vulnerabilities.
- The reproducible demo creates a non-audio path marker, verifies the read-only preview and then verifies the generated relative playlist. It makes no claim of audio playback.

Review checked path containment for mapped symlinks, nonclobbering output, foreign lexical path handling and the distinction between input-relative and output-relative bases. A test initially compared Windows input CRLF bytes with the intentionally normalized LF output; its expectation was corrected while retaining a separate exact byte check that the source was untouched.

Version boundaries remain deliberate: no filename guessing, media copying, stream fetching, HLS processing or playback validation. A plan describes the filesystem at validation time; it cannot reserve media files against future changes.
