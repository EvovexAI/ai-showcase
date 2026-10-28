# -*- coding: utf-8 -*-
import wave, struct, math, random
random.seed(20261020)
SR = 44100
DUR = 30.083
N = int(DUR * SR)
buf = [0.0] * N

def put(off, seg, gain=1.0):
    j0 = int(off * SR)
    for i, v in enumerate(seg):
        j = j0 + i
        if 0 <= j < N:
            buf[j] += v * gain

def pluck(amp, dur, f, decay=8.0, harm=0.35):
    out = []
    n = int(dur * SR)
    for i in range(n):
        t = i / n
        s = math.sin(2 * math.pi * f * i / SR) + harm * math.sin(4 * math.pi * f * i / SR) + 0.15 * math.sin(6 * math.pi * f * i / SR)
        out.append(s * amp * math.exp(-decay * t))
    return out

def drone(amp, dur, f):
    out = []
    n = int(dur * SR)
    for i in range(n):
        t = i / n
        e = min(1.0, t * 6) * min(1.0, (1 - t) * 5)
        s = math.sin(2 * math.pi * f * i / SR) + 0.6 * math.sin(2 * math.pi * f * 1.005 * i / SR)
        out.append(s * amp * e)
    return out

PENT = [262, 294, 330, 392, 440, 523, 587, 659, 784]  # A羽/D宫 feel

# --- 0-4s 雨夜：稀疏低音脉冲，紧张
for k, off in enumerate([0.3, 1.1, 1.9, 2.7, 3.5]):
    put(off, pluck(0.30, 0.5, 98 if k % 2 else 131, 7), 0.9)
put(0.0, drone(0.10, 4.0, 65))

# --- 4-10s 古街：古筝式拨弦，五声音阶渐起
seq = [523, 440, 392, 330, 392, 440, 523, 587, 523, 440, 392, 330]
for k, f in enumerate(seq):
    put(4.0 + k * 0.42, pluck(0.26, 0.7, f, 7), 0.9)
put(6.2, pluck(0.22, 0.9, 262, 5, 0.5), 0.7)

# --- 10-16s 危机：低音持续 + 急促拨弦
put(10.0, drone(0.16, 6.0, 73.4))
for k in range(14):
    f = PENT[k % 5] * 2
    put(10.2 + k * 0.30, pluck(0.16, 0.30, f, 10), 0.8)
put(12.0, pluck(0.30, 1.2, 98, 4, 0.5), 0.8)
put(14.0, pluck(0.28, 1.0, 110, 4, 0.5), 0.8)

# --- 16-20s 反差萌：俏皮顿音
for k, f in enumerate([523, 659, 523, 440, 523, 659, 784, 659, 523, 440, 392, 440, 523, 659]):
    put(16.0 + k * 0.26, pluck(0.22, 0.28, f, 11), 0.85)
put(16.0, pluck(0.24, 0.8, 131, 6), 0.8)

# --- 20-24s 爽点：节奏加快上行
for k, f in enumerate([392, 440, 523, 587, 659, 784, 880, 784, 659, 523, 587, 659, 784, 880, 1046, 880]):
    put(20.0 + k * 0.22, pluck(0.24, 0.26, f, 12), 0.9)

# --- 24-28s 高潮：密旋律 + 低音
put(24.0, drone(0.14, 4.0, 98))
for k, f in enumerate([523, 659, 784, 1046, 880, 784, 659, 523, 587, 659, 784, 880, 1046, 1175, 1319, 1046, 880, 784]):
    put(24.0 + k * 0.20, pluck(0.26, 0.3, f, 10), 0.95)

# --- 28-30s 收尾：落音 + 尾韵
put(28.05, pluck(0.32, 1.6, 523, 3.5, 0.5), 1.0)
put(28.35, pluck(0.28, 1.6, 784, 3.5, 0.4), 0.9)
put(28.05, pluck(0.24, 1.8, 262, 3, 0.5), 0.8)

# 轻鼓点（噪声帽）全程 0.5s 网格，弱
n_hat = int(0.05 * SR)
for t in [x * 0.5 for x in range(int(DUR / 0.5))]:
    if t < 10 or t > 16:  # 雨夜与古街段更克制
        continue
    j0 = int(t * SR)
    for i in range(n_hat):
        j = j0 + i
        if j < N:
            buf[j] += random.uniform(-1, 1) * 0.05 * math.exp(-30 * i / n_hat)

# 归一化 + 头尾淡入淡出
m = max(abs(v) for v in buf)
buf = [v * (0.85 / m) for v in buf]
fade_in = int(0.3 * SR); fade_out = int(0.8 * SR)
for i in range(fade_in):
    buf[i] *= i / fade_in
for i in range(fade_out):
    buf[N - 1 - i] *= i / fade_out
with wave.open('60-audio/bgm.wav', 'w') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(b''.join(struct.pack('<h', int(v * 32767)) for v in buf))
print('bgm.wav ok, %.3fs' % DUR)
