# Meta MMS Kyrgyz pilot QA — Deb9iRjtemv

## Source and technical status
- User supplied the successful GitHub Actions artifact `hidjaz-mms-kyrgyz-pilot.zip`.
- Model: `facebook/mms-1b-all`, adapter `kir`.
- Audio length: 87.84 seconds.
- Output: 5 approximate 20-second chunks, with text. These are processing windows, **not** accurate word-level timestamps.
- Technical execution: PASS.

## Content and quality
- **Provisional result: intelligible Kyrgyz draft, requires human audio review.**
- Compared with the rejected `faster-whisper/small` diagnostic transcript, Meta MMS is much more intelligible.
- Apparent narrative: a father exchanges/sells a household-raised ox to obtain a Quran; the speaker discusses the value of the Quran and cost. **Do not treat this paraphrase as a verified quotation until checked against audio.**
- Recognizable phrases include `мага атам бир куранды`, `үйдө багылып аткан өгүздү`, `куранын баасы жок`, `курамдын кадырына жеткен адам`.
- Problems: fused words, dropped or distorted syllables, spelling errors, uncertain numbers (e.g. `1н 7ети`), and unreliable exact phrasing.
- No independently verified word-error-rate score is available because no human reference transcript was supplied.

## Decision
- Keep Meta MMS as **candidate** ASR engine, not yet approved for bulk production.
- Next: review the same audio with a Kyrgyz-speaking human; correct transcript, mark uncertain intervals, then compare to draft.
- Store raw ASR separately from corrected text and source facts. Never infer Quran specifications, prices, or religious claims from unverified ASR.
- Do not launch all remaining 43 videos until pilot quality is accepted.
