# Pilot ASR QA — Deb9iRjtemv

- Source: user-provided `hidjaz-kyrgyz-transcript-pilot.zip` from successful GitHub Actions run on 2026-11-04.
- R2 source: `hidjaz/instagram/videos/Deb9iRjtemv.mp4`
- Video SHA-256: `11f61302e49dea408eb7c704f3d1b87af829bb136371bd451ce132b0debb1699`
- Audio SHA-256: `1a1c25bb8788d947c73685fd1cd2419ed4c904ca03c876b22f8d3e677abbbe0c`
- Engine: `faster-whisper/small`; requested language `ky`, auto-detected `kk`.
- QA result: **REJECTED** for Kyrgyz transcription. The first segment is unintelligible/malformed (`Маға атом бүр құранды...`); multiple segments have Kazakh-style orthography and nonsensical words; no segment from approximately 43.4 to 73.4 seconds.
- The workflow succeeding means only that inference completed; it does not validate accuracy.
- Do **not** derive verified Quran product claims, sales scripts, or quotations from this transcript.
- Next: test a model explicitly supporting Kyrgyz (e.g. Meta MMS with Kyrgyz adapter) on the same audio, then independently evaluate the output against source speech before bulk processing.
- Avoid rerunning `faster-whisper/small` on the other archived videos until quality is demonstrated.
