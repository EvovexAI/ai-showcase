# -*- coding: utf-8 -*-
import subprocess, os
ws = r"D:/dev/github/evo/edu/ai-demos/1006-ai-creative-ad-video"
lines = [
    ("S02", "还有三分钟——", -2),
    ("S05", "您有订单即将超时。", 3),
    ("S07", "何方妖物！", -3),
    ("S08", "别碰。会洒。", -2),
    ("S09", "扫一下，就算签收了。", -1),
    ("S10", "那是何物？", -4),
    ("S12", "醉仙楼三楼。麻辣小龙虾。", -1),
    ("S13", "再来一只。", -4),
    ("S14", "记得给个好评，不然我回不去。", 1),
    ("S15", "记得给个好评", 0),
]
ps = ["Add-Type -AssemblyName System.Speech",
      "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer",
      "$s.SelectVoice('Microsoft Huihui Desktop')",
      "$s.SetOutputToWaveFile($args[0], (New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(44100,[System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen,[System.Speech.AudioFormat.AudioChannel]::Mono)))",
      "$s.Rate = [int]$args[1]",
      "$s.Speak($args[2])",
      "$s.SetOutputToNull()"]
ps_path = os.path.join(ws, "_runs", "edit", "gen_voice.ps1")
with open(ps_path, "w", encoding="utf-8-sig") as f:
    f.write("\n".join(ps) + "\n")
os.makedirs(os.path.join(ws, "_runs", "edit", "voice_raw"), exist_ok=True)
for sid, text, rate in lines:
    wav = os.path.join(ws, "_runs", "edit", "voice_raw", sid + ".wav")
    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                        "-File", ps_path, wav, str(rate), text],
                       capture_output=True, text=True)
    ok = os.path.exists(wav) and os.path.getsize(wav) > 1000
    print(sid, "OK" if ok else "FAIL", r.stderr.strip()[:80])
