import os
import tempfile
import unittest
from pathlib import Path

from m3u_relocate.core import file_uri, lexical_path, parse_mappings, plan_playlist


class PlanningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.library = self.root / "Music"
        self.library.mkdir()
        self.input = self.root / "old.m3u8"
        self.output = self.root / "new.m3u8"
        self.track = self.library / "Artist" / "雪 song.flac"
        self.track.parent.mkdir()
        self.track.write_bytes(b"path fixture, deliberately not an audio file")

    def plan(self, text, mappings=None, **kwargs):
        return plan_playlist(
            text, self.input, self.output, parse_mappings(mappings or []), **kwargs
        )

    def test_foreign_windows_root_with_unicode_and_case_insensitive_prefix(self):
        plan = self.plan("E:\\old MUSIC\\Artist\\雪 song.flac\n", [f"E:\\Old Music={self.library}"])
        self.assertEqual(plan.errors, 0)
        self.assertEqual(plan.render(), "Music/Artist/雪 song.flac\n")
        self.assertEqual(plan.entries[0].resolved, str(self.track))

    def test_component_boundary_does_not_match_similar_prefix(self):
        plan = self.plan(
            "E:\\Old MusicBackup\\Artist\\雪 song.flac", [f"E:\\Old Music={self.library}"]
        )
        self.assertEqual(plan.errors, 1)
        with self.assertRaisesRegex(ValueError, "unresolved"):
            plan.render()

    def test_longest_root_wins(self):
        special = self.root / "Special"
        special.mkdir()
        (special / "song.mp3").write_bytes(b"marker")
        plan = self.plan(
            "C:\\Music\\Special\\song.mp3",
            [f"C:\\Music={self.library}", f"C:\\Music\\Special={special}"],
        )
        self.assertEqual(plan.errors, 0)
        self.assertEqual(plan.render(), "Special/song.mp3")

    def test_unc_path_and_file_uri(self):
        for reference in (
            r"\\nas\share\Music\Artist\雪 song.flac",
            "file://nas/share/Music/Artist/%E9%9B%AA%20song.flac",
        ):
            plan = self.plan(reference, [f"\\\\nas\\share\\Music={self.library}"])
            self.assertEqual(plan.errors, 0, plan.to_dict())
            self.assertEqual(plan.render(), "Music/Artist/雪 song.flac")

    def test_posix_root_is_case_sensitive(self):
        plan = self.plan("/legacy/Music/Artist/雪 song.flac", [f"/legacy/Music={self.library}"])
        self.assertEqual(plan.errors, 0)
        other = self.plan("/legacy/music/Artist/雪 song.flac", [f"/legacy/Music={self.library}"])
        self.assertEqual(other.errors, 1)

    def test_relative_base_and_output_directory_are_independent(self):
        playlist_dir = self.root / "lists"
        playlist_dir.mkdir()
        output_dir = self.root / "exports"
        output_dir.mkdir()
        plan = plan_playlist(
            "../Music/Artist/雪 song.flac", playlist_dir / "in.m3u", output_dir / "out.m3u", []
        )
        self.assertEqual(plan.errors, 0)
        self.assertEqual(plan.render(), "../Music/Artist/雪 song.flac")
        override = self.plan("Artist/雪 song.flac", base=self.library)
        self.assertEqual(override.errors, 0)

    def test_native_absolute_and_file_uri_without_mapping(self):
        for value in (str(self.track), self.track.as_uri()):
            plan = self.plan(value)
            self.assertEqual(plan.errors, 0, plan.to_dict())

    def test_metadata_order_newline_normalization_and_remote_urls(self):
        text = "\ufeff#EXTM3U\r\n#EXTINF:5,Title\r\nMusic/Artist/雪 song.flac\r\n\r\nhttps://example.invalid/stream?q=1\r\n"
        plan = self.plan(text)
        self.assertEqual(plan.render(), text.removeprefix("\ufeff").replace("\r\n", "\n"))
        summary = plan.to_dict()["summary"]
        self.assertEqual(
            (summary["local"], summary["remote_unchecked"], summary["errors"]), (1, 1, 0)
        )
        for scheme in ("rtsp", "rtmp", "mms", "ftp", "HTTP"):
            self.assertEqual(self.plan(f"{scheme}://example.invalid/a").errors, 0)

    def test_literal_comment_filename_is_prefixed(self):
        (self.root / "#track.flac").write_bytes(b"marker")
        plan = self.plan("./#track.flac")
        self.assertEqual(plan.render(), "./#track.flac")

    def test_missing_file_and_directory_are_reported(self):
        plan = self.plan("missing.flac\nMusic\nMusic/Artist/雪 song.flac")
        self.assertEqual(plan.errors, 2)
        self.assertEqual([e.line for e in plan.entries if e.error], [1, 2])

    def test_unsupported_track_syntax_reports_each_error(self):
        text = "C:relative.flac\n\\rooted.flac\ndata:text/plain,abc\n music.flac\nhttp:///missing-host\nfile:///a?query=1\nfile:///a#fragment\nfile:///bad%xx"
        plan = self.plan(text)
        self.assertEqual(plan.errors, 8)

    def test_global_syntax_and_resource_errors(self):
        for text in ("#EXTM3U\n#EXT-X-TARGETDURATION:6", "  #EXT-X-STREAM-INF:test", "\x00"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.plan(text)
        with self.assertRaisesRegex(ValueError, "limit"):
            self.plan("a\nb", max_entries=1)
        with self.assertRaises(ValueError):
            self.plan("", max_entries=0)
        with self.assertRaises(ValueError):
            self.plan("", base=self.track)

    def test_empty_and_comment_only_playlist(self):
        self.assertEqual(self.plan("").render(), "")
        self.assertEqual(self.plan("#EXTM3U\n\n").render(), "#EXTM3U\n\n")

    def test_duplicate_or_invalid_mapping_options(self):
        for specifications in (
            ["no-separator"],
            ["C:\\Music="],
            [f"relative={self.library}"],
            ["C:\\Music=relative"],
            [f"C:\\Music={self.track}"],
            [f"C:\\Music={self.library}", f"c:\\music={self.library}"],
        ):
            with self.subTest(specifications=specifications), self.assertRaises(ValueError):
                parse_mappings(specifications)

    def test_lexical_rejects_ambiguous_absolute_paths(self):
        for value in (
            "",
            "a\tb",
            "C:relative",
            "\\rooted",
            "C:\\Music\\..\\outside",
            "/a/../b",
            "\\\\?\\C:\\Music",
            "C:\\Music\\file:stream",
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                lexical_path(value)

    def test_file_uri_validation(self):
        self.assertEqual(file_uri("file:///C:/Music/a%20b"), "C:/Music/a b")
        self.assertEqual(file_uri("file://localhost/a%20b"), "/a b")
        for value in (
            "https://host/a",
            "file:relative",
            "file://user@host/a",
            "file://host:22/a",
            "file:///a?b",
            "file:///%ff",
        ):
            with self.subTest(value=value), self.assertRaises((ValueError, UnicodeError)):
                file_uri(value)

    def test_mapped_symlink_escape_is_blocked(self):
        outside = self.root / "outside.flac"
        outside.write_bytes(b"marker")
        link = self.library / "link.flac"
        try:
            link.symlink_to(outside)
        except OSError as exc:
            self.skipTest(f"symlink privilege unavailable: {exc}")
        plan = self.plan("C:\\Music\\link.flac", [f"C:\\Music={self.library}"])
        self.assertEqual(plan.errors, 1)
        self.assertIn("escapes", plan.entries[0].error)

    @unittest.skipUnless(os.name != "nt", "colon filenames are POSIX-only")
    def test_colon_filename_is_unambiguous_after_rendering(self):
        (self.root / "track:part.flac").write_bytes(b"marker")
        plan = self.plan("./track:part.flac")
        self.assertEqual(plan.render(), "./track:part.flac")
