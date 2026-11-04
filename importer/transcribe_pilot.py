"""Pilot Kyrgyz transcription using local faster-whisper. No external paid API."""
import argparse
import json
from pathlib import Path

from faster_whisper import WhisperModel


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--code", default="Deb9iRjtemv")
    parser.add_argument("--model", default="small", choices=["tiny", "base", "small"])
    args = parser.parse_args()
    folder = Path("asr-pilot")
    audio = folder / f"{args.code}.wav"
    manifest_file = folder / f"{args.code}.json"
    if not audio.is_file() or not manifest_file.is_file():
        parser.error("Pilot audio/manifest not found. Run prepare_asr.py first.")
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    if manifest.get("code") != args.code:
        raise RuntimeError("Audio manifest shortcode mismatch")
    model = WhisperModel(args.model, device="cpu", compute_type="int8", cpu_threads=4)
    segments, info = model.transcribe(
        str(audio),
        language="ky",
        task="transcribe",
        beam_size=5,
        vad_filter=True,
        condition_on_previous_text=False,
    )
    rows = [
        {"start": round(seg.start, 2), "end": round(seg.end, 2), "text": seg.text.strip()}
        for seg in segments if seg.text.strip()
    ]
    result = {
        "code": args.code,
        "source_r2_key": manifest["source_r2_key"],
        "source_sha256": manifest["source_sha256"],
        "audio_sha256": manifest["audio_sha256"],
        "model": f"faster-whisper/{args.model}",
        "requested_language": "ky",
        "reported_language": info.language,
        "segments": rows,
        "status": "draft_requires_human_review",
        "notice": "Automatic Kyrgyz ASR may be inaccurate. Do not use as verified product claims.",
    }
    (folder / f"{args.code}.transcript.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (folder / f"{args.code}.transcript.txt").write_text(
        "\n".join(f"[{s['start']:.2f}-{s['end']:.2f}] {s['text']}" for s in rows) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"code": args.code, "segments": len(rows), "language": info.language, "status": result["status"]}))


if __name__ == "__main__":
    main()
