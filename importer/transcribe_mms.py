"""Kyrgyz Meta MMS CTC pilot. Requires prepared mono 16 kHz PCM16 WAV."""
import argparse
import json
import os
import wave
from pathlib import Path

import numpy as np
import torch
from transformers import AutoProcessor, Wav2Vec2ForCTC

MODEL_ID = "facebook/mms-1b-all"
LANGUAGE = "kir"
SAMPLE_RATE = 16000
CHUNK_SECONDS = 20


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--code", default="Deb9iRjtemv")
    args = ap.parse_args()
    folder = Path("asr-pilot")
    wav_path = folder / f"{args.code}.wav"
    manifest_path = folder / f"{args.code}.json"
    if not wav_path.is_file() or not manifest_path.is_file():
        ap.error("Audio and manifest required from prepare_asr.py")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["code"] != args.code:
        raise RuntimeError("Manifest code mismatch")
    with wave.open(str(wav_path), "rb") as f:
        if (f.getnchannels(), f.getframerate(), f.getsampwidth()) != (1, SAMPLE_RATE, 2):
            raise RuntimeError("Expected mono PCM16 16kHz")
        samples = np.frombuffer(f.readframes(f.getnframes()), dtype="<i2").astype(np.float32) / 32768
    if samples.size == 0:
        raise RuntimeError("Empty audio")
    torch.set_num_threads(2)
    processor = AutoProcessor.from_pretrained(MODEL_ID, target_lang=LANGUAGE)
    model = Wav2Vec2ForCTC.from_pretrained(MODEL_ID)
    model.load_adapter(LANGUAGE)
    model.eval()
    if hasattr(processor.tokenizer, "set_target_lang"):
        processor.tokenizer.set_target_lang(LANGUAGE)
    segments = []
    chunk_size = SAMPLE_RATE * CHUNK_SECONDS
    for offset in range(0, len(samples), chunk_size):
        chunk = samples[offset:offset + chunk_size]
        inputs = processor(chunk, sampling_rate=SAMPLE_RATE, return_tensors="pt")
        with torch.inference_mode():
            logits = model(inputs.input_values).logits
        tokens = torch.argmax(logits, dim=-1)
        text = processor.batch_decode(tokens)[0].strip()
        start = round(offset / SAMPLE_RATE, 2)
        end = round(min(offset + len(chunk), len(samples)) / SAMPLE_RATE, 2)
        segments.append({"start": start, "end": end, "text": text})
        print(json.dumps({"start": start, "end": end, "text": text}, ensure_ascii=False), flush=True)
    output = {
        "code": args.code,
        "source_r2_key": manifest["source_r2_key"],
        "source_sha256": manifest["source_sha256"],
        "audio_sha256": manifest["audio_sha256"],
        "model": MODEL_ID,
        "language_adapter": LANGUAGE,
        "status": "draft_requires_human_review",
        "timing_note": "20-second processing windows, not word-level timestamps",
        "segments": segments,
    }
    (folder / f"{args.code}.mms.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (folder / f"{args.code}.mms.txt").write_text(
        "\n".join(f"[{s['start']:.2f}-{s['end']:.2f}] {s['text']}" for s in segments) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": output["status"], "segments": len(segments), "adapter": LANGUAGE}))


if __name__ == "__main__":
    main()
