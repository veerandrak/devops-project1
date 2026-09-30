"""Version-specific S3 backup and integrity-checked restore. No credentials in code."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
import uuid


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def upload(s3, source, bucket, kms_key):
    source = Path(source)
    if not source.is_file():
        raise ValueError("Source must be an existing regular file")
    # Freeze the bytes before hashing/uploading, even if the caller changes source.
    with tempfile.TemporaryDirectory() as directory:
        snapshot = Path(directory) / "snapshot"
        with source.open("rb") as src, snapshot.open("wb") as dst:
            for chunk in iter(lambda: src.read(1024 * 1024), b""):
                dst.write(chunk)
        checksum = sha256(snapshot)
        key = f"backups/{uuid.uuid4().hex}/{source.name}"
        s3.upload_file(str(snapshot), bucket, key, ExtraArgs={
            "ServerSideEncryption": "aws:kms", "SSEKMSKeyId": kms_key,
            "Metadata": {"sha256": checksum},
        })
    head = s3.head_object(Bucket=bucket, Key=key)
    version = head.get("VersionId")
    if not version or version == "null":
        raise RuntimeError("Bucket versioning must be enabled; uploaded object has no version ID")
    if head.get("Metadata", {}).get("sha256") != checksum:
        raise RuntimeError("Uploaded metadata does not match the local checksum")
    return {"bucket": bucket, "key": key, "version_id": version, "sha256": checksum}


def restore(s3, bucket, key, version, checksum, destination):
    if not key.startswith("backups/"):
        raise ValueError("Only keys beneath backups/ are accepted")
    if not version or version == "null":
        raise ValueError("Specify an immutable object version")
    destination = Path(destination)
    if destination.exists():
        raise ValueError("Refusing to overwrite an existing destination")
    fd, temporary = tempfile.mkstemp(prefix=".restore-", dir=destination.parent)
    os.close(fd)
    try:
        s3.download_file(bucket, key, temporary, ExtraArgs={"VersionId": version})
        if sha256(temporary) != checksum:
            raise RuntimeError("Restore checksum mismatch; destination was not written")
        # Hard-link publication is atomic and refuses to overwrite an existing file.
        os.link(temporary, destination)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return {"restored": str(destination), "sha256": checksum}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    put = sub.add_parser("backup")
    put.add_argument("source")
    put.add_argument("--bucket", required=True)
    put.add_argument("--kms-key", required=True)
    get = sub.add_parser("restore")
    get.add_argument("destination")
    for field in ("bucket", "key", "version", "sha256"):
        get.add_argument("--" + field, required=True)
    args = parser.parse_args()
    import boto3
    s3 = boto3.client("s3")
    if args.command == "backup":
        result = upload(s3, args.source, args.bucket, args.kms_key)
    else:
        result = restore(s3, args.bucket, args.key, args.version, args.sha256, args.destination)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
