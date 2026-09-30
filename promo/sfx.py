"""Tanıtım videosu için müzik ve ses efektleri (tamamı NumPy ile sentezlenir, dış servis/örnek yok).

build_audio(total, events) -> (n, 2) float32.  events: [(zaman_sn, tür, parametre), ...]
Türler: tick, click, pop, whoosh, hit, boom, ding, riser, count, sparkle, sting, fall, thud, send, expand
Müzik: 120 bpm, C majör (C - G - Am - F). Davul/bas/arp sahnelerle birlikte girer; kick'e "sidechain" vurgusu verilir.
"""

import numpy as np
from scipy.signal import fftconvolve

SR = 44100
BPM = 120
BEAT = 60 / BPM
_RNG = np.random.default_rng(11)

NOTE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def hz(name, octave):
    return 440.0 * 2 ** ((NOTE[name] + 12 * (octave - 4) - 9) / 12)


def tarr(dur):
    return np.arange(int(dur * SR)) / SR


def place(buf, sig, at, gain=1.0):
    s = int(at * SR)
    if s >= len(buf) or s < 0:
        return
    e = min(len(buf), s + len(sig))
    buf[s:e] += sig[: e - s] * gain


def hp(x, k=1):
    for _ in range(k):
        x = np.diff(x, prepend=0.0)
    return x


# --- temel sesler -------------------------------------------------------------------------------------------------
def kick():
    t = tarr(0.42)
    f = 46 + 120 * np.exp(-t / 0.035)
    body = np.sin(np.cumsum(2 * np.pi * f / SR)) * np.exp(-t / 0.16)
    click = hp(_RNG.normal(0, 1, len(t))) * np.exp(-t / 0.004) * 0.25
    return (body + click).astype(np.float32)


def hat(open_=False):
    t = tarr(0.25 if open_ else 0.06)
    return (hp(_RNG.normal(0, 1, len(t)), 2) * np.exp(-t / (0.09 if open_ else 0.018)) * 0.22).astype(np.float32)


def clap():
    t = tarr(0.22)
    n = hp(_RNG.normal(0, 1, len(t)))
    env = np.exp(-t / 0.06) + 0.6 * np.exp(-np.clip(t - 0.012, 0, None) / 0.05) * (t > 0.012) + 0.5 * np.exp(-np.clip(t - 0.028, 0, None) / 0.05) * (t > 0.028)
    return (n * env * 0.25).astype(np.float32)


def pluck(freq, dur=0.55):
    t = tarr(dur)
    sig = np.zeros_like(t)
    for h in range(1, 8):
        sig += np.sin(2 * np.pi * freq * h * t) / h * np.exp(-t / (0.22 / (1 + 0.5 * h)))
    sig *= np.minimum(t / 0.004, 1)
    return (sig * 0.5).astype(np.float32)


def bell(freq, dur=1.6, bright=1.0):
    t = tarr(dur)
    sig = np.zeros_like(t)
    for mult, amp, dec in ((1, 1.0, 0.9), (2.01, 0.55, 0.6), (2.76, 0.35 * bright, 0.45), (5.4, 0.2 * bright, 0.25), (8.93, 0.1 * bright, 0.15)):
        sig += np.sin(2 * np.pi * freq * mult * t) * amp * np.exp(-t / dec)
    sig *= np.minimum(t / 0.002, 1)
    return (sig * 0.35).astype(np.float32)


def pad_chord(freqs, dur):
    t = tarr(dur)
    env = np.clip(t / 1.2, 0, 1) * np.clip((dur - t) / 1.0, 0, 1)
    sig = np.zeros_like(t)
    for i, f in enumerate(freqs):
        for det in (-0.7, 0.0, 0.7):
            sig += np.sin(2 * np.pi * (f + det) * t + i) * (0.05 / (1 + i * 0.35))
    return (sig * env).astype(np.float32)


def bass_note(freq, dur=0.45):
    t = tarr(dur)
    sig = np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(4 * np.pi * freq * t) * np.exp(-t / 0.12)
    return (sig * np.exp(-t / 0.3) * np.minimum(t / 0.006, 1) * 0.55).astype(np.float32)


# --- efektler ------------------------------------------------------------------------------------------------------
def whoosh(dur=0.7, rising=True, gain=1.0):
    t = tarr(dur)
    env = np.sin(np.linspace(0, np.pi, len(t))) ** 2
    sweep = np.linspace(300, 6000, len(t)) if rising else np.linspace(6000, 300, len(t))
    tone = np.sin(np.cumsum(2 * np.pi * sweep / SR))
    noise = hp(_RNG.normal(0, 1, len(t)), 1)
    return ((noise * 0.25 + tone * 0.4) * env * 0.5 * gain).astype(np.float32)


def pop(pitch=1.0):
    t = tarr(0.12)
    f = (900 - 500 * np.minimum(t / 0.1, 1)) * pitch
    return (np.sin(np.cumsum(2 * np.pi * f / SR)) * np.exp(-t / 0.035) * 0.55).astype(np.float32)


def key_tick(variant=0):
    t = tarr(0.03)
    n = hp(_RNG.normal(0, 1, len(t))) * np.exp(-t / 0.004)
    tone = np.sin(2 * np.pi * (2100 + 160 * variant) * t) * np.exp(-t / 0.006)
    return ((n * 0.3 + tone * 0.5) * 0.5).astype(np.float32)


def mouse_click():
    a = key_tick(2) * 1.2
    t = tarr(0.09)
    b = np.sin(2 * np.pi * 1200 * t) * np.exp(-t / 0.012) * 0.25
    out = np.zeros(len(t), np.float32)
    out[: len(a)] += a
    out += b.astype(np.float32)
    return out


def boom(size=1.0):
    t = tarr(1.3)
    f = 38 + 70 * np.exp(-t / 0.08)
    body = np.sin(np.cumsum(2 * np.pi * f / SR)) * np.exp(-t / 0.42)
    burst = hp(_RNG.normal(0, 1, len(t)), 1) * np.exp(-t / 0.05) * 0.35
    return ((body * 0.9 + burst) * size).astype(np.float32)


def hit(size=1.0):
    t = tarr(0.7)
    f = 60 + 90 * np.exp(-t / 0.04)
    body = np.sin(np.cumsum(2 * np.pi * f / SR)) * np.exp(-t / 0.2)
    burst = hp(_RNG.normal(0, 1, len(t)), 2) * np.exp(-t / 0.03) * 0.4
    return ((body * 0.8 + burst) * size).astype(np.float32)


def riser(dur=1.0):
    t = tarr(dur)
    env = (t / dur) ** 2.2
    sweep = 180 * (2000 / 180) ** (t / dur)
    tone = np.sin(np.cumsum(2 * np.pi * sweep / SR))
    noise = hp(_RNG.normal(0, 1, len(t)))
    return ((tone * 0.25 + noise * 0.18) * env * 0.8).astype(np.float32)


def sparkle(n=9):
    out = np.zeros(int(0.9 * SR), np.float32)
    for i in range(n):
        f = _RNG.choice([hz("C", 6), hz("E", 6), hz("G", 6), hz("A", 6), hz("D", 7)])
        t = tarr(0.35)
        s = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.09) * 0.22
        place(out, s.astype(np.float32), i * 0.045 + _RNG.random() * 0.03)
    return out


def fall(dur=0.7):
    t = tarr(dur)
    f = 620 * np.exp(-t / 0.35) + 70
    return (np.sin(np.cumsum(2 * np.pi * f / SR)) * np.exp(-t / 0.45) * 0.45 * np.minimum(t / 0.01, 1)).astype(np.float32)


def thud():
    t = tarr(0.5)
    f = 90 * np.exp(-t / 0.1) + 45
    return (np.sin(np.cumsum(2 * np.pi * f / SR)) * np.exp(-t / 0.14) * 0.9).astype(np.float32)


def reverb_ir(dur=1.4, decay=0.4):
    t = tarr(dur)
    ir = _RNG.normal(0, 1, len(t)) * np.exp(-t / decay)
    ir[0] = 0
    return (ir / np.abs(ir).sum() * 6).astype(np.float32)


# --- ana karışım ---------------------------------------------------------------------------------------------------
PROG = [("C", [hz("C", 3), hz("E", 3), hz("G", 3), hz("C", 4), hz("E", 4)], "C"),
        ("G", [hz("G", 2), hz("D", 3), hz("G", 3), hz("B", 3), hz("D", 4)], "G"),
        ("Am", [hz("A", 2), hz("E", 3), hz("A", 3), hz("C", 4), hz("E", 4)], "A"),
        ("F", [hz("F", 2), hz("C", 3), hz("F", 3), hz("A", 3), hz("C", 4)], "F")]
ARP = {"C": ["C", "E", "G", "E"], "G": ["G", "B", "D", "B"], "A": ["A", "C", "E", "C"], "F": ["F", "A", "C", "A"]}
ARP_OCT = {"C": 5, "G": 4, "A": 4, "F": 4}


def build_audio(total, events, sections):
    """sections: {'drums': t, 'hats': t, 'arp': t, 'bass': t, 'claps': t, 'stop': t}  (mutlak saniye)."""
    n = int(total * SR)
    music_dry = np.zeros(n, np.float32)   # sidechain uygulanacak (pad, arp, bas)
    drums = np.zeros(n, np.float32)
    sfx = np.zeros(n, np.float32)
    wet_src = np.zeros(n, np.float32)     # reverb'e gidecek parlak sesler

    bar = 4 * BEAT
    # pad: her 2 ölçüde bir akor
    k = 0
    t0 = 0.0
    while t0 < total:
        _, freqs, _ = PROG[k % 4]
        place(music_dry, pad_chord(freqs, 2 * bar + 1.0), t0, 1.0)
        t0 += 2 * bar
        k += 1
    kick_times = []
    beat_i = 0
    t = 0.0
    while t < total - 0.01:
        chord = PROG[int(t // (2 * bar)) % 4]
        root = chord[2]
        if sections["drums"] <= t < sections["stop"]:
            place(drums, kick(), t, 0.95)
            kick_times.append(t)
            if t >= sections["claps"] and beat_i % 2 == 1:
                place(drums, clap(), t, 0.8)
        if sections["hats"] <= t < sections["stop"]:
            place(drums, hat(), t + BEAT / 2, 0.8)
            if beat_i % 4 == 3:
                place(drums, hat(True), t + BEAT / 2, 0.6)
        if sections["bass"] <= t < sections["stop"]:
            fq = hz(root, 2) * (2 if beat_i % 2 == 1 else 1)
            place(music_dry, bass_note(fq), t + BEAT / 2, 0.9)
            place(music_dry, bass_note(hz(root, 2)), t, 0.7)
        if sections["arp"] <= t < sections["stop"]:
            pat = ARP[root]
            for j in range(4):
                nm = pat[j]
                oct_ = ARP_OCT[root] + (1 if j == 3 else 0)
                g = 0.55 if j % 2 == 0 else 0.4
                pl = pluck(hz(nm, oct_))
                at = t + j * BEAT / 4
                place(music_dry, pl, at, g)
                place(wet_src, pl, at, g * 0.7)
        t += BEAT
        beat_i += 1

    # sidechain: kick sonrası müzik kısa süre kısılır
    duck = np.ones(n, np.float32)
    for kt in kick_times:
        s = int(kt * SR)
        m = min(int(0.3 * SR), n - s)
        if m > 0:
            duck[s : s + m] = np.minimum(duck[s : s + m], 1 - 0.55 * np.exp(-np.arange(m) / (0.11 * SR)))
    music = music_dry * duck

    # olay efektleri
    for at, kind, param in events:
        if kind == "tick":
            place(sfx, key_tick(int(param or 0) % 4), at, 0.7)
        elif kind == "click":
            place(sfx, mouse_click(), at, 0.9)
        elif kind == "pop":
            place(sfx, pop(param or 1.0), at, 0.8)
            place(wet_src, pop(param or 1.0), at, 0.25)
        elif kind == "whoosh":
            place(sfx, whoosh(0.75, True, param or 1.0), at, 0.9)
        elif kind == "hit":
            place(sfx, hit(param or 1.0), at, 0.85)
            place(wet_src, hit(param or 1.0), at, 0.12)
        elif kind == "boom":
            place(sfx, boom(param or 1.0), at, 0.85)
        elif kind == "ding":
            f = hz("C", 6) * 2 ** ((param or 0) / 12)
            b = bell(f, 1.4)
            place(sfx, b, at, 0.75)
            place(wet_src, b, at, 0.6)
        elif kind == "riser":
            place(sfx, riser(param or 1.0), at, 0.8)
        elif kind == "count":
            f = hz("C", 6) * 2 ** ((param or 0) / 12)
            t2 = tarr(0.07)
            place(sfx, (np.sin(2 * np.pi * f * t2) * np.exp(-t2 / 0.02) * 0.25).astype(np.float32), at)
        elif kind == "sparkle":
            sp = sparkle()
            place(sfx, sp, at, 0.9)
            place(wet_src, sp, at, 0.6)
        elif kind == "sting":
            for j, (nm, oc) in enumerate((("C", 5), ("E", 5), ("G", 5), ("C", 6))):
                b = bell(hz(nm, oc), 2.6, 0.8)
                place(sfx, b, at + j * 0.03, 0.55)
                place(wet_src, b, at + j * 0.03, 0.8)
            place(sfx, boom(0.9), at, 0.7)
        elif kind == "fall":
            place(sfx, fall(), at, 0.9)
        elif kind == "thud":
            place(sfx, thud(), at, 0.95)
        elif kind == "send":
            place(sfx, whoosh(0.28, True, 0.8), at, 0.7)
        elif kind == "expand":
            place(sfx, pop(1.3), at, 0.6)

    # reverb (parlak sesler ve efektler için)
    ir = reverb_ir()
    wet = fftconvolve(wet_src, ir)[:n].astype(np.float32)

    mix = music * 0.72 + drums * 0.8 + sfx * 1.0 + wet * 0.55
    # giriş/çıkış
    tt = np.arange(n) / SR
    mix *= np.clip(np.minimum(tt / 0.35, (total - tt) / 1.0), 0, 1)
    # yumuşak sınırlayıcı + normalizasyon
    mix = np.tanh(mix * 1.15) / np.tanh(1.15)
    mix *= 0.9 / max(1e-6, np.abs(mix).max())
    stereo = np.stack([mix, mix], axis=1)
    # hafif stereo genişlik: reverb'i sağ/sol farklı gecikmeyle ekle
    d = int(0.012 * SR)
    stereo[d:, 0] += wet[: n - d] * 0.08
    stereo[:, 1] += np.roll(wet, d) * 0.08
    stereo *= 0.6 / max(1e-6, np.abs(stereo).max())  # tepe ≈ -4.4 dBFS: AAC kodlaması tepeleri ~2 dB taşırabilir
    return stereo.astype(np.float32)
