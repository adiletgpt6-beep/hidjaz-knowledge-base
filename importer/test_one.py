"""Archive and independently verify one Instagram video in private Cloudflare R2."""
import hashlib
import json
import os
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import boto3
import requests

PREFIX = "hidjaz/instagram/videos/"
MAX_BYTES = 250 * 1024 * 1024


def digest_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    posts = json.loads(Path("data/instagram/posts.json").read_text(encoding="utf-8"))
    post = next(p for p in posts if p.get("video", {}).get("url"))
    url = os.getenv("INSTAGRAM_MEDIA_URL") or post["video"]["url"]
    host = (urlparse(url).hostname or "").lower()
    if not (host.endswith(".cdninstagram.com") or host.endswith(".fbcdn.net")):
        raise ValueError("Untrusted Instagram CDN hostname")
    code = post["code"]
    if not code.isalnum():
        raise ValueError("Invalid post code")
    key = PREFIX + code + ".mp4"
    with tempfile.TemporaryDirectory() as folder:
        source = Path(folder) / "source.mp4"
        with requests.get(url, timeout=(15, 90), stream=True, allow_redirects=False) as response:
            if response.status_code != 200:
                raise RuntimeError(f"Instagram media HTTP {response.status_code}; refresh CDN URLs via Apify")
            content_type = response.headers.get("Content-Type", "").split(";")[0].lower()
            if content_type not in ("video/mp4", "application/octet-stream"):
                raise RuntimeError(f"Unexpected media content type: {content_type}")
            size = 0
            with source.open("wb") as f:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        size += len(chunk)
                        if size > MAX_BYTES:
                            raise RuntimeError("Video exceeds 250 MiB limit")
                        f.write(chunk)
        if size == 0 or source.open("rb").read(12)[4:8] != b"ftyp":
            raise RuntimeError("Empty or invalid MP4")
        expected = digest_file(source)
        s3 = boto3.client(
            "s3",
            endpoint_url=f'https://{os.environ["R2_ACCOUNT_ID"]}.r2.cloudflarestorage.com',
            region_name="auto",
        )
        bucket = os.environ["R2_BUCKET_NAME"]
        with source.open("rb") as f:
            s3.upload_fileobj(f, bucket, key, ExtraArgs={
                "ContentType": "video/mp4", "Metadata": {"sha256": expected}
            })
        head = s3.head_object(Bucket=bucket, Key=key)
        if head["ContentLength"] != size or head["Metadata"].get("sha256") != expected:
            raise RuntimeError("R2 HEAD metadata mismatch")
        downloaded = Path(folder) / "verified.mp4"
        s3.download_file(bucket, key, str(downloaded))
        if downloaded.stat().st_size != size or digest_file(downloaded) != expected:
            raise RuntimeError("R2 downloaded object integrity mismatch")
        print(json.dumps({"status": "verified", "post_code": code, "key": key,
                          "bytes": size, "sha256": expected}, ensure_ascii=False))


if __name__ == "__main__":
    main()
