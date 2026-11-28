# SPDX-License-Identifier: GPL-3.0-or-later
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import check_release
import check_wiki


class WikiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.wiki = Path(self.tmp.name) / "wiki"
        shutil.copytree(check_wiki.WIKI, self.wiki)

    def test_deterministic_complete_and_linked(self):
        count = len(check_wiki.entries(self.wiki))
        self.assertGreater(count, 0)
        self.assertEqual(check_wiki.run(self.wiki), count)
        expected = {p.name: p.read_bytes() for p in (self.wiki / "indexes").glob("*.md")}
        self.assertEqual(len(expected), 3)
        check_wiki.run(self.wiki, write=True)
        self.assertEqual(expected, {p.name: p.read_bytes() for p in (self.wiki / "indexes").glob("*.md")})

    def test_stale_index_and_broken_link(self):
        path = self.wiki / "indexes/make-assets.md"
        path.write_text("stale\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "stale index"):
            check_wiki.run(self.wiki)
        check_wiki.run(self.wiki, write=True)
        (self.wiki / "labs/images/mask-baseline.png").unlink()
        with self.assertRaisesRegex(ValueError, "broken local link"):
            check_wiki.run(self.wiki)

    def test_duplicate_id(self):
        path = self.wiki / "techniques/001-grip-roughness.md"
        shutil.copyfile(path, path.with_name("copy.md"))
        with self.assertRaisesRegex(ValueError, "duplicate technique ID"):
            check_wiki.run(self.wiki)

    def test_evidence_is_small_png_in_allowed_location(self):
        path = self.wiki / "labs/images/mask-baseline.png"
        self.assertTrue(check_release.validate_wiki_png(path))
        self.assertTrue(check_release.is_wiki_image(path, Path("docs/wiki/labs/images/mask-baseline.png")))
        self.assertFalse(check_release.is_wiki_image(path, Path("docs/wiki/mask-baseline.png")))
        path.write_bytes(b"fake")
        self.assertFalse(check_release.validate_wiki_png(path))
