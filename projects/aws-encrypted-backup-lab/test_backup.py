import hashlib
from pathlib import Path
import tempfile
import unittest
from backup import restore, upload


class FakeS3:
    def upload_file(self, path, bucket, key, ExtraArgs):
        self.payload = Path(path).read_bytes()
        self.metadata = ExtraArgs["Metadata"]
        self.encryption = ExtraArgs

    def head_object(self, **kwargs):
        return {"VersionId": "version-1", "Metadata": self.metadata}

    def download_file(self, bucket, key, path, ExtraArgs):
        if ExtraArgs != {"VersionId": "version-1"}:
            raise AssertionError("Missing immutable version selection")
        Path(path).write_bytes(self.payload)


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source.txt"
        self.source.write_bytes(b"restore rehearsal\n")
        self.s3 = FakeS3()
        self.receipt = upload(self.s3, self.source, "lab-bucket", "key-arn")

    def test_round_trip(self):
        target = self.root / "restored.txt"
        restore(self.s3, "lab-bucket", self.receipt["key"], "version-1", self.receipt["sha256"], target)
        self.assertEqual(target.read_bytes(), self.source.read_bytes())
        self.assertEqual(self.s3.encryption["SSEKMSKeyId"], "key-arn")

    def test_corruption_does_not_publish(self):
        self.s3.payload = b"corrupted"
        target = self.root / "restored.txt"
        with self.assertRaises(RuntimeError):
            restore(self.s3, "lab-bucket", self.receipt["key"], "version-1", self.receipt["sha256"], target)
        self.assertFalse(target.exists())
        self.assertEqual(list(self.root.glob(".restore-*")), [])

    def test_no_overwrite(self):
        with self.assertRaises(ValueError):
            restore(self.s3, "lab-bucket", self.receipt["key"], "version-1", self.receipt["sha256"], self.source)
        self.assertEqual(self.source.read_bytes(), b"restore rehearsal\n")

    def test_sha256_record(self):
        self.assertEqual(self.receipt["sha256"], hashlib.sha256(self.source.read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
