"""Batch archived-video Kyrgyz ASR; checkpoint drafts in R2 after each video."""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import boto3

PREFIX = "hidjaz/asr/mms-1b-all/"
OUT = Path("asr-batch")
WORK = Path("asr-pilot")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--offset", type=int, default=0)
    p.add_argument("--limit", type=int, default=3)
    args = p.parse_args()
    if args.offset < 0 or not 1 <= args.limit <= 44:
        p.error("offset >= 0 and limit 1..44 required")
    posts = json.loads(Path("data/instagram/posts.json").read_text(encoding="utf-8"))
    codes = list(dict.fromkeys(
        x["code"] for x in posts if x.get("code") and (x.get("video") or {}).get("url")
    ))
    selected = codes[args.offset:args.offset + args.limit]
    if not selected:
        p.error(f"No videos in range. Total videos: {len(codes)}")
    OUT.mkdir(exist_ok=True)
    client = boto3.client("s3", endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com", region_name="auto")
    bucket = os.environ["R2_BUCKET_NAME"]
    report = {"offset": args.offset, "limit": args.limit, "total_videos": len(codes),
              "completed": [], "already_present": [], "failed": []}

    def save_report():
        (OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for code in selected:
        key = PREFIX + code + ".mms.json"
        try:
            try:
                head = client.head_object(Bucket=bucket, Key=key)
            except client.exceptions.ClientError as e:
                if e.response["Error"]["Code"] not in ("404", "NoSuchKey", "NotFound"):
                    raise
            else:
                if head.get("ContentLength", 0) > 100:
                    report["already_present"].append(code)
                    print(json.dumps({"code": code, "status": "already_present"}), flush=True)
                    save_report()
                    continue
            for path in WORK.glob("*"):
                if path.is_file():
                    path.unlink()
            subprocess.run([sys.executable, "importer/prepare_asr.py", "--code", code], check=True)
            subprocess.run([sys.executable, "importer/transcribe_mms.py", "--code", code], check=True)
            transcript = WORK / (code + ".mms.json")
            data = json.loads(transcript.read_text(encoding="utf-8"))
            if data.get("code") != code or data.get("status") != "draft_requires_human_review":
                raise RuntimeError("Transcript metadata mismatch")
            for ext in (".mms.json", ".mms.txt"):
                local = WORK / (code + ext)
                client.upload_file(str(local), bucket, PREFIX + code + ext,
                                   ExtraArgs={"ContentType": "application/json" if ext.endswith("json") else "text/plain; charset=utf-8"})
                client.head_object(Bucket=bucket, Key=PREFIX + code + ext)
            report["completed"].append(code)
            print(json.dumps({"code": code, "status": "saved_to_r2", "segments": len(data["segments"])}), flush=True)
        except Exception as exc:
            report["failed"].append({"code": code, "error": str(exc)[:300]})
            print(json.dumps({"code": code, "status": "failed", "error": str(exc)[:300]}), flush=True)
        finally:
            save_report()
    print(json.dumps({"completed": len(report["completed"]), "already_present": len(report["already_present"]),
                      "failed": len(report["failed"]), "total_videos": len(codes)}))
    if report["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
