import io
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from prepare_release import normalize_sdist  # noqa: E402


class ReleaseTests(unittest.TestCase):
    def test_archive_owner_removed_content_preserved_and_repeatable(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "source.tar.gz"
            with tarfile.open(path, "w:gz", format=tarfile.PAX_FORMAT) as archive:
                entry = tarfile.TarInfo("example/readme.txt")
                content = b"public example"
                entry.size = len(content)
                entry.uid = 1234
                entry.gid = 5678
                entry.uname = "build-user"
                entry.gname = "build-group"
                entry.pax_headers = {"uname": "build-user", "mtime": "1234.123", "atime": "4567"}
                archive.addfile(entry, io.BytesIO(content))
            normalize_sdist(path, 1234)
            with tarfile.open(path) as archive:
                entry = archive.getmember("example/readme.txt")
                self.assertEqual((entry.uid, entry.gid, entry.uname, entry.gname), (0, 0, "", ""))
                self.assertEqual(entry.mtime, 1234)
                self.assertNotIn("atime", entry.pax_headers)
                self.assertEqual(archive.extractfile(entry).read(), content)
            first = path.read_bytes()
            normalize_sdist(path, 1234)
            self.assertEqual(first, path.read_bytes())

    def test_unsafe_archive_members_rejected_without_overwriting(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "source.tar.gz"
            with tarfile.open(path, "w:gz") as archive:
                entry = tarfile.TarInfo("../outside")
                archive.addfile(entry, io.BytesIO())
            original = path.read_bytes()
            with self.assertRaises(ValueError):
                normalize_sdist(path, 1234)
            self.assertEqual(original, path.read_bytes())
