"""Idempotent Instagram media archiver. Never deletes R2 objects."""
import argparse
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import boto3
import requests

ROOT = "hidjaz/instagram/"
MAX_BYTES = 250 * 1024 * 1024


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sources(posts):
    for p in posts:
        code = p.get("code", "")
        if not re.fullmatch(r"[A-Za-z0-9_-]{5,40}", code):
            continue
        video = p.get("video") or {}
        if video.get("url"):
            yield code, "videos", 0, video["url"], "video/mp4", ".mp4"
        if p.get("image"):
            yield code, "images", 0, p["image"], "image/jpeg", ".jpg"
        for i, item in enumerate(p.get("carousel") or []):
            if not isinstance(item, dict):
                continue
            v = item.get("video") or {}
            if isinstance(v, dict) and v.get("url"):
                yield code, "carousel", i + 1, v["url"], "video/mp4", ".mp4"
            elif item.get("image") or item.get("url"):
                yield code, "carousel", i + 1, item.get("image") or item["url"], "image/jpeg", ".jpg"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=5)
    args = ap.parse_args()
    if args.limit < 1 or args.limit > 200:
        ap.error("limit must be 1..200")
    posts = json.loads(Path("data/instagram/posts.json").read_text(encoding="utf-8"))
    client = boto3.client("s3", endpoint_url="https://" + os.environ["R2_ACCOUNT_ID"] + ".r2.cloudflarestorage.com", region_name="auto")
    bucket = os.environ["R2_BUCKET_NAME"]
    report = {"verified": [], "already_present": [], "failed": [], "skipped": []}
    processed = 0
    for code, kind, index, url, mime, ext in sources(posts):
        key = ROOT + kind + "/" + code + (("_" + str(index)) if index else "") + ext
        if processed >= args.limit:
            report["skipped"].append(key)
            continue
        processed += 1
        try:
            try:
                head = client.head_object(Bucket=bucket, Key=key)
            except client.exceptions.ClientError as exc:
                if exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode") != 404:
                    raise
            else:
                known = head.get("Metadata", {}).get("sha256", "")
                if re.fullmatch("[a-f0-9]{64}", known) and head["ContentLength"] > 0:
                    with tempfile.TemporaryDirectory() as td:
                        local = Path(td) / "existing"
                        client.download_file(bucket, key, str(local))
                        if local.stat().st_size == head["ContentLength"] and sha(local) == known:
                            report["already_present"].append({"key": key, "bytes": head["ContentLength"], "sha256": known})
                            continue
                raise RuntimeError("Existing object not independently verified; refusing overwrite")
            host = (urlparse(url).hostname or "").lower()
            if not (host.endswith(".cdninstagram.com") or host.endswith(".fbcdn.net")):
                raise RuntimeError("Unsupported media hostname")
            with tempfile.TemporaryDirectory() as td:
                path = Path(td) / "source"
                with requests.get(url, stream=True, allow_redirects=False, timeout=(15, 90)) as resp:
                    if resp.status_code != 200:
                        raise RuntimeError("Instagram CDN HTTP " + str(resp.status_code) + "; refresh URL")
                    ctype = resp.headers.get("Content-Type", "").lower().split(";")[0]
                    if ctype not in (mime, "application/octet-stream"):
                        raise RuntimeError("Unexpected content type " + ctype)
                    size = 0
                    with path.open("wb") as f:
                        for chunk in resp.iter_content(1024 * 1024):
                            if chunk:
                                size += len(chunk)
                                if size > MAX_BYTES:
                                    raise RuntimeError("File too large")
                                f.write(chunk)
                if size == 0:
                    raise RuntimeError("Empty download")
                header = path.open("rb").read(16)
                if (ext == ".mp4" and header[4:8] != b"ftyp") or (ext == ".jpg" and not header.startswith(bytes.fromhex("ffd8ff"))):
                    raise RuntimeError("Invalid media signature")
                digest = sha(path)
                with path.open("rb") as f:
                    client.upload_fileobj(f, bucket, key, ExtraArgs={"ContentType": mime, "Metadata": {"sha256": digest}})
                head = client.head_object(Bucket=bucket, Key=key)
                downloaded = Path(td) / "readback"
                client.download_file(bucket, key, str(downloaded))
                if head["ContentLength"] != size or head.get("Metadata", {}).get("sha256") != digest or downloaded.stat().st_size != size or sha(downloaded) != digest:
                    raise RuntimeError("R2 readback integrity check failed")
                report["verified"].append({"key": key, "bytes": size, "sha256": digest})
        except Exception as exc:
            report["failed"].append({"key": key, "error": str(exc)[:180]})
    Path("import-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: len(v) for k, v in report.items()}))
    if report["failed"]:
        raise SystemExit("Some media failed; inspect import-report.json artifact")


if __name__ == "__main__":
    main()
