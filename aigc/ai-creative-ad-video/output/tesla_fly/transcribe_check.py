import sys
from faster_whisper import WhisperModel

model = WhisperModel("small", device="cpu", compute_type="int8")
segments, _ = model.transcribe(sys.argv[1], language="zh", vad_filter=True)
lines = []
for seg in segments:
    lines.append(f"[{seg.start:.1f}-{seg.end:.1f}] {seg.text.strip()}")
print("\n".join(lines) if lines else "(no speech)")
