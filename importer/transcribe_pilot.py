"""Pilot Kyrgyz transcription using local faster-whisper. No external paid API."""
import argparse
import json
import wave
from pathlib import Path

import numpy as np

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
    # The WAV is already 16 kHz mono PCM16 from FFmpeg. Decode with stdlib
    # to avoid PyAV's incompatible metadata_errors keyword on some runners.
    with wave.open(str(audio), "rb") as wav:
        if wav.getnchannels() != 1 or wav.getframerate() != 16000 or wav.getsampwidth() != 2:
            raise RuntimeError("Expected mono 16 kHz PCM16 WAV")
        samples = np.frombuffer(wav.readframes(wav.getnframes()), dtype="<i2").astype(np.float32) / 32768.0
    if samples.size == 0:
        raise RuntimeError("Audio is empty")
    model = WhisperModel(args.model, device="cpu", compute_type="int8", cpu_threads=4)
    segments, info = model.transcribe(
        samples,
        language=None,  # Whisper does not support Kyrgyz; diagnostic auto-detection only
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
        "status": "diagnostic_unsupported_kyrgyz_not_verified",
        "notice": "Whisper does NOT support Kyrgyz (ky). This auto-detected transcript is diagnostic only; do not use it as verified Kyrgyz or product facts.",
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
