import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from m3u_relocate.cli import main


class CLITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root / "song.flac").write_bytes(b"marker")
        self.input = self.root / "in.m3u"
        self.input.write_text("#EXTM3U\nsong.flac\n", encoding="utf-8")
        self.output = self.root / "out.m3u8"

    def invoke(self, *args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main([str(self.input), "--output", str(self.output), *map(str, args)])
        return code, stdout.getvalue(), stderr.getvalue()

    def test_preview_then_write_does_not_change_input(self):
        before = self.input.read_bytes()
        code, text, error = self.invoke("--format", "json")
        self.assertEqual((code, error), (0, ""))
        self.assertFalse(json.loads(text)["written"])
        self.assertFalse(self.output.exists())
        self.assertEqual(self.invoke("--write")[0], 0)
        self.assertEqual(before, self.input.read_bytes())
        self.assertEqual(self.output.read_bytes(), before.replace(b"\r\n", b"\n"))

    def test_unresolved_entries_never_create_partial_output(self):
        self.input.write_text("song.flac\nmissing.flac\n")
        code, text, error = self.invoke("--write")
        self.assertEqual((code, error), (1, ""))
        self.assertIn("line 2", text)
        self.assertFalse(self.output.exists())

    def test_existing_output_is_refused(self):
        self.output.write_text("keep")
        self.assertEqual(self.invoke("--write")[0], 2)
        self.assertEqual(self.output.read_text(), "keep")

    def test_existing_output_symlink_is_refused(self):
        try:
            self.output.symlink_to(self.root / "missing-target")
        except OSError as exc:
            self.skipTest(f"symlink privilege unavailable: {exc}")
        self.assertEqual(self.invoke("--write")[0], 2)
        self.assertFalse((self.root / "missing-target").exists())

    def test_byte_limit_bad_encoding_unknown_codec_and_missing_input(self):
        with patch("m3u_relocate.cli.MAX_BYTES", 2):
            self.assertEqual(self.invoke()[0], 2)
        self.input.write_bytes(b"\xff")
        self.assertEqual(self.invoke()[0], 2)
        self.assertEqual(self.invoke("--encoding", "not-a-codec")[0], 2)
        self.input.unlink()
        self.assertEqual(self.invoke()[0], 2)

    def test_explicit_legacy_codec_writes_utf8(self):
        (self.root / "café.flac").write_bytes(b"marker")
        self.input.write_bytes("#EXTM3U\ncafé.flac\n".encode("cp1252"))
        self.assertEqual(self.invoke("--encoding", "cp1252", "--write")[0], 0)
        self.assertIn("café.flac", self.output.read_text(encoding="utf-8"))

    def test_invalid_mapping_and_entry_limit(self):
        self.assertEqual(self.invoke("--map", "bad")[0], 2)
        self.input.write_text("song.flac\nsong.flac")
        self.assertEqual(self.invoke("--max-entries", "1")[0], 2)
        with self.assertRaises(SystemExit) as caught:
            self.invoke("--max-entries", "0")
        self.assertEqual(caught.exception.code, 2)

    def test_real_installed_module(self):
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "m3u_relocate",
                str(self.input),
                "--output",
                str(self.output),
                "--write",
                "--format",
                "json",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(json.loads(proc.stdout)["written"])

    def test_version(self):
        with (
            contextlib.redirect_stdout(io.StringIO()) as stdout,
            self.assertRaises(SystemExit) as caught,
        ):
            main(["--version"])
        self.assertEqual((caught.exception.code, stdout.getvalue().strip()), (0, "0.1.0"))
