"""Synchronize MMS draft transcripts from R2 into versioned GitHub files."""
import json
import os
from pathlib import Path

import boto3

PREFIX = "hidjaz/asr/mms-1b-all/"
DEST = Path("data/transcripts/mms")
INDEX = Path("data/transcripts/index.json")


def main():
    posts = json.loads(Path("data/instagram/posts.json").read_text(encoding="utf-8"))
    codes = list(dict.fromkeys(p["code"] for p in posts if p.get("code") and (p.get("video") or {}).get("url")))
    s3 = boto3.client("s3", endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com", region_name="auto")
    bucket = os.environ["R2_BUCKET_NAME"]
    DEST.mkdir(parents=True, exist_ok=True)
    entries = []
    missing = []
    for code in codes:
        key = PREFIX + code + ".mms.json"
        try:
            obj = s3.get_object(Bucket=bucket, Key=key)
        except s3.exceptions.ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in ("NoSuchKey", "404", "NotFound"):
                missing.append(code)
                continue
            raise
        raw = obj["Body"].read()
        record = json.loads(raw)
        if (record.get("code") != code or record.get("model") != "facebook/mms-1b-all"
                or record.get("language_adapter") != "kir" or not isinstance(record.get("segments"), list)
                or not record["segments"] or not record.get("source_sha256")):
            raise RuntimeError(f"Invalid transcript record: {code}")
        record["status"] = "draft_requires_human_review"
        target = DEST / (code + ".json")
        target.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        lines = [f"[{s['start']:.2f}-{s['end']:.2f}] {s['text']}" for s in record["segments"]]
        (DEST / (code + ".txt")).write_text("\n".join(lines) + "\n", encoding="utf-8")
        entries.append({"code": code, "instagram_url": f"https://www.instagram.com/reel/{code}/",
                        "json": str(target), "text": str(DEST / (code + ".txt")),
                        "status": "draft_requires_human_review", "segments": len(lines)})
    INDEX.parent.mkdir(parents=True, exist_ok=True)
    INDEX.write_text(json.dumps({"total_video_posts": len(codes), "synced": len(entries),
                                 "missing": missing, "transcripts": entries}, ensure_ascii=False, indent=2) + "\n",
                     encoding="utf-8")
    print(json.dumps({"total": len(codes), "synced": len(entries), "missing": missing}, ensure_ascii=False))
    if missing:
        raise SystemExit("Not all R2 transcripts are present; no GitHub commit should be made")


if __name__ == "__main__":
    main()
