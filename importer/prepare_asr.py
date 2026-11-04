"""Download one verified R2 video and extract mono 16 kHz WAV for Kyrgyz ASR."""
import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

import boto3


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--code", default="Deb9iRjtemv")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]{5,40}", args.code):
        parser.error("Invalid Instagram shortcode")
    posts = json.loads(Path("data/instagram/posts.json").read_text(encoding="utf-8"))
    post = next((p for p in posts if p.get("code") == args.code and (p.get("video") or {}).get("url")), None)
    if not post:
        parser.error("Video shortcode not found in posts.json")
    key = f"hidjaz/instagram/videos/{args.code}.mp4"
    client = boto3.client(
        "s3",
        endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        region_name="auto",
    )
    bucket = os.environ["R2_BUCKET_NAME"]
    head = client.head_object(Bucket=bucket, Key=key)
    expected = head.get("Metadata", {}).get("sha256", "")
    if not re.fullmatch("[a-f0-9]{64}", expected):
        raise RuntimeError("R2 source lacks verified SHA256 metadata")
    output = Path("asr-pilot")
    output.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        video = Path(td) / "source.mp4"
        client.download_file(bucket, key, str(video))
        if video.stat().st_size != head["ContentLength"] or digest(video) != expected:
            raise RuntimeError("Downloaded video failed integrity verification")
        audio = output / f"{args.code}.wav"
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
             "-i", str(video), "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(audio)],
            check=True,
        )
    if not audio.exists() or audio.stat().st_size == 0:
        raise RuntimeError("No usable audio track")
    manifest = {
        "code": args.code,
        "instagram_url": post["url"],
        "source_r2_key": key,
        "source_sha256": expected,
        "audio_file": audio.name,
        "audio_sha256": digest(audio),
        "audio_format": "PCM WAV mono 16000 Hz",
        "caption": post.get("caption", ""),
        "status": "audio_prepared_not_transcribed",
        "transcription_language": "ky",
    }
    (output / f"{args.code}.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": manifest["status"], "code": args.code, "audio_bytes": audio.stat().st_size}))


if __name__ == "__main__":
    main()
