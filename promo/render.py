"""Lumora Bilgi Asistanı - Türkçe tanıtım videosu (~39 sn, 1920x1080, 30 fps).

Tasarım, uygulamanın kendi arayüzünden alınmıştır (app/web/styles.css): krem zemin, şeftali (#ffd0a4) vurgu,
koyu yeşil-gri (#292f2b), Manrope + DM Sans, dört noktalı "lumora." logosu, uygulamanın kendi SVG ikonları.
Demo bölümü, çalışan uygulamadan alınan GERÇEK ekran görüntüleridir (promo/capture.py).

Sıra:  python promo/capture_icons.py  -> uygulamanın ikonları
       python promo/capture.py        -> gerçek ekran görüntüleri (sunucu açık olmalı)
       python promo/make_voice.py     -> Türkçe seslendirme (edge-tts)
       python promo/render.py --preview   /   python promo/render.py
"""

import json
import math
import sys
import time
from functools import lru_cache
from pathlib import Path

import numpy as np
from moviepy import AudioFileClip, VideoClip
from moviepy.audio.AudioClip import AudioArrayClip
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).parent
BUILD = HERE / "build"
SHOTS = BUILD / "shots"
ICONS = BUILD / "icons"
FONTS = HERE / "fonts"
W, H, FPS, SR = 1920, 1080, 30, 44100

# --- uygulamanın renk paleti (styles.css) -----------------------------------------------------------------------
CREAM, INK, DARK = (247, 246, 242), (37, 41, 37), (41, 47, 43)
PEACH, PEACH2, ORANGE, ORANGE_TXT = (255, 208, 164), (255, 201, 149), (238, 159, 98), (218, 148, 92)
MUTED, LINE, WHITE = (133, 137, 130), (239, 239, 235), (255, 255, 255)
PEACH_BG, PEACH_FG = (255, 229, 209), (188, 116, 80)
LILAC_BG, LILAC_FG = (234, 229, 248), (132, 110, 174)
SAND_BG, SAND_FG = (247, 241, 223), (156, 137, 80)


def rgba(c, a=1.0):
    return (c[0], c[1], c[2], int(255 * max(0.0, min(1.0, a))))


def clamp01(x):
    return max(0.0, min(1.0, x))


def smooth(x):
    x = clamp01(x)
    return x * x * (3 - 2 * x)


def ease_out(x):
    return 1 - (1 - clamp01(x)) ** 3


def ease_back(x):
    x = clamp01(x)
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def seg(t, a, b):
    return clamp01((t - a) / (b - a)) if b > a else float(t >= a)


# --- yazı tipleri ve metin ------------------------------------------------------------------------------------
@lru_cache(maxsize=None)
def brand_font(kind, size, weight):
    if kind == "m":
        f = ImageFont.truetype(str(FONTS / "Manrope[wght].ttf"), size)
        f.set_variation_by_axes([weight])
    else:
        f = ImageFont.truetype(str(FONTS / "DMSans[opsz,wght].ttf"), size)
        f.set_variation_by_axes([14, weight])
    return f


@lru_cache(maxsize=1024)
def text_sprite(s, kind, size, weight, color, spacing):
    """(görsel, baseline_x_ofseti, baseline_y). Baseline'a göre konumlanır."""
    f = brand_font(kind, size, weight)
    asc, desc = f.getmetrics()
    pad = 8
    if spacing:
        widths = [f.getlength(ch) + spacing for ch in s]
        total = int(sum(widths) - spacing + 1)
    else:
        total = int(f.getlength(s) + 1)
    img = Image.new("RGBA", (total + 2 * pad, asc + desc + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if spacing:
        x = pad
        for ch, adv in zip(s, widths):
            d.text((x, pad + asc), ch, font=f, fill=rgba(color), anchor="ls")
            x += adv
    else:
        d.text((pad, pad + asc), s, font=f, fill=rgba(color), anchor="ls")
    return img, pad, pad + asc, total


def blit(layer, img, x, y):
    x, y = int(round(x)), int(round(y))
    sx, sy = max(0, -x), max(0, -y)
    ex, ey = min(img.width, layer.width - x), min(img.height, layer.height - y)
    if ex <= sx or ey <= sy:
        return
    layer.alpha_composite(img.crop((sx, sy, ex, ey)), dest=(x + sx, y + sy))


def scaled_alpha(img, a):
    if a >= 0.999:
        return img
    img = img.copy()
    img.putalpha(img.getchannel("A").point(lambda v: int(v * a)))
    return img


def text(L, xy, s, size=32, color=INK, weight=700, kind="m", align="l", alpha=1.0, spacing=0, va="b"):
    """xy = (x, y); y baseline'dır (va='m' ise satırın görsel ortası)."""
    if alpha <= 0 or not s:
        return 0
    img, ox, oy, total = text_sprite(s, kind, size, weight, color, spacing)
    x, y = xy
    if align == "m":
        x -= total / 2
    elif align == "r":
        x -= total
    if va == "m":
        y += size * 0.36
    blit(L, scaled_alpha(img, alpha), x - ox, y - oy)
    return total


def text_width(s, size, weight=700, kind="m", spacing=0):
    return text_sprite(s, kind, size, weight, INK, spacing)[3]


@lru_cache(maxsize=256)
def _icon(name, size, color):
    src = Image.open(ICONS / f"{name}.png").convert("RGBA").resize((size, size), Image.LANCZOS)
    tinted = Image.new("RGBA", src.size, rgba(color))
    tinted.putalpha(src.getchannel("A"))
    return tinted


def icon(L, name, cx, cy, size, color=INK, alpha=1.0):
    img = _icon(name, int(size), color)
    blit(L, scaled_alpha(img, alpha), cx - size / 2, cy - size / 2)


@lru_cache(maxsize=256)
def _shadow(w, h, r, blur, a):
    pad = blur * 3
    img = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(img).rounded_rectangle((pad, pad, pad + w, pad + h), r, fill=(72, 52, 30, int(255 * a)))
    return img.filter(ImageFilter.GaussianBlur(blur)), pad


def rrect(L, box, r, fill=None, outline=None, width=2, alpha=1.0, shadow=0.0, sblur=24, soff=14):
    x0, y0, x1, y1 = [int(round(v)) for v in box]
    w, h = x1 - x0, y1 - y0
    if w <= 0 or h <= 0 or alpha <= 0:
        return
    if shadow > 0:
        sh, sp = _shadow(w, h, r, sblur, shadow * alpha)
        blit(L, sh, x0 - sp, y0 - sp + soff)
    pad = width + 2
    tmp = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(tmp).rounded_rectangle((pad, pad, pad + w, pad + h), r, fill=fill, outline=outline, width=width)
    blit(L, scaled_alpha(tmp, alpha), x0 - pad, y0 - pad)


def circle(L, cx, cy, r, fill=None, outline=None, width=2, alpha=1.0):
    r = int(r)
    pad = width + 2
    tmp = Image.new("RGBA", (2 * r + 2 * pad, 2 * r + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(tmp).ellipse((pad, pad, pad + 2 * r, pad + 2 * r), fill=fill, outline=outline, width=width)
    blit(L, scaled_alpha(tmp, alpha), cx - r - pad, cy - r - pad)


def asterisk(L, cx, cy, r, color=WHITE, alpha=1.0, rot=0.0, width=4):
    """Uygulamadaki ✳ işareti."""
    size = int(r * 2 + 12)
    tmp = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    c = size / 2
    for k in range(4):
        a = math.radians(rot + 45 * k)
        d.line([(c - r * math.cos(a), c - r * math.sin(a)), (c + r * math.cos(a), c + r * math.sin(a))], fill=rgba(color), width=width)
    blit(L, scaled_alpha(tmp, alpha), cx - c, cy - c)


def sparkle4(L, cx, cy, r, color=WHITE, alpha=1.0):
    """Uygulamadaki ✦ işareti."""
    size = int(r * 2 + 8)
    tmp = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    c = size / 2
    k = r * 0.22
    ImageDraw.Draw(tmp).polygon([(c, c - r), (c + k, c - k), (c + r, c), (c + k, c + k), (c, c + r), (c - k, c + k), (c - r, c), (c - k, c - k)], fill=rgba(color))
    blit(L, scaled_alpha(tmp, alpha), cx - c, cy - c)


def logo_mark(L, cx, cy, size, color=PEACH2, alpha=1.0, spin=-20.0, pop=1.0):
    """Dört noktalı marka işareti (CSS: .brand-mark, -20° döndürülmüş)."""
    r = size * 0.155 * pop
    off = size * 0.5 - size * 0.155
    a = math.radians(spin)
    for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        px, py = sx * off, sy * off
        x = cx + px * math.cos(a) - py * math.sin(a)
        y = cy + px * math.sin(a) + py * math.cos(a)
        circle(L, x, y, max(1, r), fill=rgba(color), alpha=alpha)


def logo(L, x, y, size, ink=WHITE, dot=PEACH2, alpha=1.0, pop=1.0, spin=-20.0):
    """'lumora.' — sol: marka işareti, sağ: yazı (Manrope 800)."""
    logo_mark(L, x + size * 0.5, y, size * 0.95, dot, alpha, spin, pop)
    w = text(L, (x + size * 1.25, y), "lumora", int(size * 1.25), ink, 800, "m", "l", alpha, spacing=-size * 0.06, va="m")
    text(L, (x + size * 1.25 + w + size * 0.02, y), ".", int(size * 1.25), dot, 800, "m", "l", alpha, va="m")
    return size * 1.25 + w + size * 0.3


def check_badge(L, cx, cy, r, alpha=1.0, ring=WHITE):
    circle(L, cx, cy, r, fill=rgba(DARK), outline=rgba(ring), width=max(3, int(r * 0.22)), alpha=alpha)
    d_layer = Image.new("RGBA", (int(r * 3), int(r * 3)), (0, 0, 0, 0))
    o = r * 1.5
    ImageDraw.Draw(d_layer).line([(o - r * 0.42, o + r * 0.02), (o - r * 0.1, o + r * 0.34), (o + r * 0.46, o - r * 0.32)], fill=(255, 255, 255, 255), width=max(3, int(r * 0.24)), joint="curve")
    blit(L, scaled_alpha(d_layer, alpha), cx - o, cy - o)


# --- arka plan ------------------------------------------------------------------------------------------------
def _make_bg():
    y = np.linspace(0, 1, H)[:, None, None]
    base = np.array(CREAM, np.float32)[None, None, :] * (1 - 0.02 * y) + np.array((243, 240, 233), np.float32)[None, None, :] * (0.02 * y)
    return np.broadcast_to(base, (H, W, 3)).copy()


_BG = _make_bg()


def _blob(size, col):
    g = np.linspace(-1, 1, size)
    xx, yy = np.meshgrid(g, g)
    return (np.exp(-(xx ** 2 + yy ** 2) * 3.0)[..., None] * np.array(col, np.float32)[None, None, :]).astype(np.float32)


_BLOB = _blob(900, (1, 1, 1))


def cream_background(t):
    out = _BG.copy()
    for (fx, fy, px, py, k) in ((0.05, 0.07, 0.0, 1.0, 20), (0.04, 0.06, 2.5, 0.2, 14)):
        cx = int(W * (0.5 + 0.4 * math.sin(t * fx * 2 * math.pi + px)))
        cy = int(H * (0.5 + 0.3 * math.cos(t * fy * 2 * math.pi + py)))
        s = _BLOB.shape[0]
        x0, y0 = cx - s // 2, cy - s // 2
        sx0, sy0, sx1, sy1 = max(0, -x0), max(0, -y0), min(s, W - x0), min(s, H - y0)
        if sx1 > sx0 and sy1 > sy0:
            m = _BLOB[sy0:sy1, sx0:sx1, 0:1] * k / 255.0
            tgt = out[y0 + sy0 : y0 + sy1, x0 + sx0 : x0 + sx1]
            tgt += (np.array(PEACH, np.float32)[None, None, :] - tgt) * m
    return out


def orbits(L, cx, cy, t, alpha=0.5, scale=1.0):
    for i, r in enumerate((250, 330, 430)):
        rr = int((r + 10 * math.sin(t * 0.8 + i)) * scale)
        circle(L, cx, cy, rr, outline=rgba(WHITE, alpha * (1 - i * 0.22)), width=2)


# --- ekran görüntüsü kamerası ------------------------------------------------------------------------------------
_SHOT_CACHE = {}
BOXES = json.loads((SHOTS / "boxes.json").read_text(encoding="utf-8")) if (SHOTS / "boxes.json").exists() else {}


def shot(name):
    if name not in _SHOT_CACHE:
        _SHOT_CACHE[name] = Image.open(SHOTS / f"{name}.png").convert("RGB")
    return _SHOT_CACHE[name]


WX0, WY0, WW, WH = 124, 84, 1672, 940  # pencere (16:9)
_WMASK = Image.new("L", (WW, WH), 0)
ImageDraw.Draw(_WMASK).rounded_rectangle((0, 0, WW, WH), 28, fill=255)


def keyframes(f, kfs):
    """kfs: [(f, cx, cy, z), ...] -> yumuşak geçişli kamera."""
    if f <= kfs[0][0]:
        return kfs[0][1:]
    for a, b in zip(kfs, kfs[1:]):
        if f <= b[0]:
            u = smooth((f - a[0]) / (b[0] - a[0]))
            return tuple(a[i] + (b[i] - a[i]) * u for i in (1, 2, 3))
    return kfs[-1][1:]


def cam_map(cam):
    cx, cy, z = cam
    k = (WW / W) * z  # CSS px -> tuval px
    vx0, vy0 = cx - (W / 2) / z, cy - (H / 2) / z
    return lambda x, y: (WX0 + (x - vx0) * k, WY0 + (y - vy0) * k), k, (vx0, vy0, vx0 + W / z, vy0 + H / z)


def draw_window(L, states, cam, alpha=1.0, pop=1.0):
    """states: {shot_adı: ağırlık}. Kırpma/yakınlaştırma doğrudan 3840x2160 kaynaktan yapılır (net kalır)."""
    _, _, (vx0, vy0, vx1, vy1) = cam_map(cam)
    acc, first = None, True
    for name, wgt in states.items():
        if wgt <= 0.001:
            continue
        im = shot(name).resize((WW, WH), Image.BICUBIC, box=(vx0 * 2, vy0 * 2, vx1 * 2, vy1 * 2))
        if first:
            acc, first = im, False
            done = wgt
        else:
            acc = Image.blend(acc, im, wgt / (done + wgt))
            done += wgt
    if acc is None:
        return
    win = acc.convert("RGBA")
    win.putalpha(_WMASK)
    x0, y0 = WX0, WY0
    if pop != 1.0:
        w2, h2 = int(WW * pop), int(WH * pop)
        win = win.resize((w2, h2), Image.BILINEAR)
        x0, y0 = WX0 + (WW - w2) / 2, WY0 + (WH - h2) / 2
        rrect(L, (x0, y0, x0 + w2, y0 + h2), 28, fill=rgba(WHITE, 0), shadow=0.22 * alpha, sblur=34, soff=22)
    else:
        rrect(L, (x0, y0, x0 + WW, y0 + WH), 28, fill=rgba(WHITE, 0), shadow=0.22 * alpha, sblur=34, soff=22)
    blit(L, scaled_alpha(win, alpha), x0, y0)
    rrect(L, (x0, y0, x0 + win.width, y0 + win.height), 28, outline=rgba((225, 222, 214), alpha), width=2)


def highlight(L, cam, key, pad=10, alpha=1.0, pulse=0.0):
    b = BOXES.get(key)
    if not b or alpha <= 0:
        return None
    m, k, _ = cam_map(cam)
    x0, y0 = m(b["x"] - pad, b["y"] - pad)
    x1, y1 = m(b["x"] + b["width"] + pad, b["y"] + b["height"] + pad)
    grow = 3 * pulse
    rrect(L, (x0 - grow, y0 - grow, x1 + grow, y1 + grow), 22 * k, fill=rgba(ORANGE, 0.10 * alpha), outline=rgba(ORANGE, alpha), width=4)
    return x0, y0, x1, y1


def pill(L, x, y, s, alpha=1.0, dot=PEACH2, slide=0.0):
    """Koyu, yuvarlak açıklama etiketi (uygulamanın .dark-button diliyle)."""
    size = 27
    w = text_width(s, size, 700) + 84
    yy = y + slide
    rrect(L, (x, yy - 32, x + w, yy + 32), 32, fill=rgba(DARK, 0.97 * alpha), shadow=0.25, sblur=18, soff=10, alpha=alpha)
    circle(L, x + 32, yy, 9, fill=rgba(dot, alpha))
    text(L, (x + 58, yy), s, size, WHITE, 700, "m", "l", alpha, va="m")


# --- sahneler ------------------------------------------------------------------------------------------------
def scene_intro(L, t, dur):
    rrect(L, (0, 0, W, H), 0, fill=rgba(PEACH))
    cx, cy = W // 2, 400
    orbits(L, cx, cy + 40, t, 0.55, 1.5)
    for (px, py, r, ph) in ((250, 250, 30, 0.0), (1650, 300, 22, 1.2), (1500, 800, 26, 2.1), (330, 760, 18, 0.7)):
        a = 0.5 + 0.5 * math.sin(t * 2 + ph)
        (sparkle4 if r < 24 else asterisk)(L, px, py, r, WHITE, alpha=a * smooth(seg(t, 0.4, 1.0)))
    # marka
    k = ease_back(seg(t, 0.15, 0.95))
    total = 1.0
    size = 150
    tw = text_width("lumora", int(size * 1.25), 800, "m", -size * 0.06) + size * 0.3 + size * 1.25
    x0 = cx - tw / 2
    logo(L, x0, cy, size, INK, WHITE, alpha=smooth(seg(t, 0.15, 0.8)), pop=clamp01(k), spin=-20 + (1 - ease_out(seg(t, 0.1, 1.4))) * 160)
    # slogan
    a = smooth(seg(t, 1.5, 2.3))
    y = 640 + (1 - ease_out(seg(t, 1.5, 2.4))) * 26
    w1 = text_width("Her sorunun ", 78, 800, "m", -3)
    w2 = text_width("bir dayanağı var.", 78, 800, "m", -3)
    sx = cx - (w1 + w2) / 2
    text(L, (sx, y), "Her sorunun ", 78, INK, 800, "m", "l", a, spacing=-3)
    text(L, (sx + w1, y), "bir dayanağı var.", 78, WHITE, 800, "m", "l", a, spacing=-3)
    text(L, (cx, y + 92), "Ürün, sipariş ve abonelik sorularına kaynaklı yanıtlar.", 34, (104, 86, 72), 400, "d", "m", smooth(seg(t, 2.2, 3.0)))


QUESTIONS = [
    ("İade süresi kaç gün?", "file", 330, 305, 0.00, -3),
    ("Garanti neleri kapsıyor?", "shield", 1000, 285, 0.30, 2),
    ("Şifremi unuttum!", "lock", 1560, 330, 0.55, -2),
    ("Kargo ücretsiz mi?", "truck", 350, 470, 0.80, 2),
    ("Aboneliği nasıl iptal ederim?", "card", 900, 480, 1.05, -2),
    ("5 GHz Wi-Fi'ye bağlanır mı?", "wifi", 1520, 480, 1.30, 3),
]


def scene_problem(L, t, dur):
    f = t / dur
    text(L, (W // 2, 176), "Aynı sorular. Her gün.", 88, INK, 800, "m", "m", smooth(seg(f, 0.02, 0.18)), spacing=-3.5)
    for s, ic, bx, by, t0, rot in QUESTIONS:
        k = ease_back(seg(t, 0.35 + t0 * 0.5, 0.85 + t0 * 0.5))
        if k <= 0:
            continue
        w = text_width(s, 34, 500, "d") + 150
        cx = bx + math.sin(t * 1.2 + bx * 0.01) * 6
        cy = by + math.cos(t * 1.0 + by * 0.01) * 6
        box = (cx - w / 2 * k, cy - 48 * k, cx + w / 2 * k, cy + 48 * k)
        rrect(L, box, 30 * k, fill=rgba(WHITE), outline=rgba(LINE), width=2, alpha=clamp01(k), shadow=0.10, sblur=22, soff=12)
        if k > 0.75:
            a = clamp01((k - 0.75) / 0.25)
            rrect(L, (cx - w / 2 + 18, cy - 30, cx - w / 2 + 78, cy + 30), 16, fill=rgba(PEACH_BG, a))
            icon(L, ic, cx - w / 2 + 48, cy, 30, PEACH_FG, a)
            text(L, (cx - w / 2 + 98, cy), s, 34, INK, 500, "d", "l", a, va="m")
    # güven göstergesi düşüyor
    a = smooth(seg(f, 0.52, 0.66))
    if a > 0:
        bx0, bx1, by = W // 2 - 400, W // 2 + 400, 905
        text(L, (bx0, by - 30), "Müşteri güveni", 32, MUTED, 500, "d", "l", a)
        rrect(L, (bx0, by, bx1, by + 22), 11, fill=rgba(LINE, a))
        drop = ease_out(seg(f, 0.66, 0.92))
        frac = 1 - 0.86 * drop
        rrect(L, (bx0, by, bx0 + (bx1 - bx0) * frac, by + 22), 11, fill=rgba(ORANGE, a))
    # uyarı kartı (marka koyusu)
    wa = ease_back(seg(f, 0.70, 0.84))
    if wa > 0:
        shake = math.sin(t * 55) * 4 * (1 - seg(f, 0.84, 0.95))
        cx, cy = W // 2 + shake, 700
        rrect(L, (cx - 380, cy - 64, cx + 380, cy + 64), 34, fill=rgba(DARK, clamp01(wa)), shadow=0.28, sblur=26, soff=16, alpha=clamp01(wa))
        circle(L, cx - 318, cy, 30, fill=rgba(PEACH2, clamp01(wa)))
        text(L, (cx - 318, cy), "!", 40, DARK, 800, "m", "m", clamp01(wa), va="m")
        text(L, (cx - 262, cy), "Tek bir yanlış cevap, güveni bitirir.", 38, WHITE, 700, "m", "l", clamp01(wa), va="m")


def scene_demo(L, t, dur, wstate):
    f = t / dur
    pop = 0.90 + 0.10 * ease_out(seg(f, 0.0, 0.10))
    a = smooth(seg(f, 0.0, 0.08))

    def blend(name, a0, a1, b0=None):
        return smooth(seg(f, a0, a1))

    # ekran görüntüsü durumları (çapraz geçiş)
    order = [
        ("home", 0.00),
        ("chat_empty", 0.11),
        ("chat_q1_typing_half", 0.19),
        ("chat_q1_typing_full", 0.26),
        ("chat_q1_thinking", 0.33),
        ("chat_q1_answer", 0.42),
        ("chat_q1_open", 0.55),
    ]
    weights = {}
    for i, (name, start) in enumerate(order):
        nxt = order[i + 1][1] if i + 1 < len(order) else 2.0
        w_in = 1.0 if i == 0 else smooth(seg(f, start - 0.01, start + 0.035))
        w_out = 0.0 if i + 1 == len(order) else smooth(seg(f, nxt - 0.01, nxt + 0.035))
        weights[name] = w_in * (1 - w_out)
    cam = keyframes(f, [
        (0.00, 960, 540, 1.0), (0.12, 960, 540, 1.0), (0.20, 1090, 720, 1.5), (0.34, 1090, 700, 1.5),
        (0.43, 1090, 400, 1.6), (0.56, 1090, 420, 1.6), (0.65, 1090, 470, 1.55), (0.90, 1090, 500, 1.5), (1.00, 960, 540, 1.0),
    ])
    draw_window(L, weights, cam, alpha=a, pop=pop)
    m, k, _ = cam_map(cam)
    pulse = 0.5 + 0.5 * math.sin(t * 4)
    # vurgular ve açıklama etiketleri (gerçek öğe konumlarına bağlı)
    fa = smooth(seg(f, 0.45, 0.50)) * (1 - smooth(seg(f, 0.61, 0.65)))
    b = highlight(L, cam, "q1_answer_bubble", 8, fa, pulse)
    if b:
        pill(L, b[2] + 26, (b[1] + b[3]) / 2, "Türkçe yanıt, saniyeler içinde", fa, slide=(1 - fa) * 14)
    fs = smooth(seg(f, 0.63, 0.69)) * (1 - smooth(seg(f, 0.77, 0.81)))
    b = highlight(L, cam, "q1_sources", 8, fs, pulse)
    if b:
        pill(L, b[2] + 26, (b[1] + b[3]) / 2, "Belge · sürüm · bölüm", fs, slide=(1 - fs) * 14)
    fc = smooth(seg(f, 0.79, 0.85)) * (1 - smooth(seg(f, 0.94, 0.985)))
    b = highlight(L, cam, "q1_conflict", 8, fc, pulse)
    if b:
        pill(L, b[2] + 26, (b[1] + b[3]) / 2, "Güncel sürüm otomatik seçilir", fc, slide=(1 - fc) * 14)
    # başlık (pencere üstünde, ilk anda)
    ta = smooth(seg(f, 0.0, 0.06)) * (1 - smooth(seg(f, 0.14, 0.19)))
    if ta > 0:
        text(L, (W // 2, 56), "Gerçek uygulama. Gerçek yanıt.", 40, INK, 800, "m", "m", ta, spacing=-1.2, va="m")


NODES = [("Arama", "BM25 · Türkçe", "search"), ("Sürüm seçimi", "v1 ↔ v2", "layers"),
         ("Kanıt cümlesi", "belgede aynen var mı?", "file"), ("Sayı denetimi", "kaynakta olmayan sayı yok", "shield"),
         ("Yanıt", "kaynak + bölüm", "message")]


def crop_card(L, src, css_xy_w, box, r=22, alpha=1.0):
    """Gerçek ekran görüntüsünden bir bölgeyi (CSS px: sol, üst, genişlik) kart içine koyar; yükseklik hedef
    kutunun en-boy oranından türetilir, görüntü gerilmez."""
    x0, y0, x1, y1 = box
    w, h = int(x1 - x0), int(y1 - y0)
    cx0, cy0, cw = css_xy_w
    ch = cw * h / w
    im = shot(src).resize((w, h), Image.LANCZOS, box=(cx0 * 2, cy0 * 2, (cx0 + cw) * 2, (cy0 + ch) * 2)).convert("RGBA")
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w, h), r, fill=255)
    im.putalpha(mask)
    blit(L, scaled_alpha(im, alpha), x0, y0)
    rrect(L, (x0, y0, x1, y1), r, outline=rgba(LINE, alpha), width=2)


def scene_trust(L, t, dur):
    f = t / dur
    text(L, (110, 128), "GÜVEN KATMANLARI", 22, ORANGE_TXT, 800, "m", "l", smooth(seg(f, 0, 0.08)), spacing=4)
    text(L, (110, 214), "Uydurmaya izin yok", 88, INK, 800, "m", "l", smooth(seg(f, 0.0, 0.1)), spacing=-3.5)
    n = len(NODES)
    cw, gap = 290, 62
    x0 = (W - (n * cw + (n - 1) * gap)) / 2
    y0, ch = 270, 200
    prog = seg(f, 0.10, 0.60)
    for i, (name, sub, ic) in enumerate(NODES):
        a = smooth(seg(f, 0.03 + i * 0.03, 0.13 + i * 0.03))
        x = x0 + i * (cw + gap)
        lit = clamp01(prog * n - i)
        rrect(L, (x, y0, x + cw, y0 + ch), 26, fill=rgba(WHITE), outline=rgba(ORANGE if lit >= 1 else LINE, 1.0), width=3 if lit >= 1 else 2, alpha=a, shadow=0.10, sblur=22, soff=12)
        rrect(L, (x + 24, y0 + 24, x + 24 + 64, y0 + 24 + 64), 18, fill=rgba(PEACH_BG if lit < 1 else PEACH, a))
        icon(L, ic, x + 56, y0 + 56, 34, PEACH_FG, a)
        text(L, (x + 24, y0 + 134), name, 30, INK, 700, "m", "l", a, spacing=-0.8)
        text(L, (x + 24, y0 + 170), sub, 20, MUTED, 400, "d", "l", a)
        if lit >= 1:
            check_badge(L, x + cw - 30, y0 + 30, 17, alpha=smooth(seg(lit, 0.85, 1.0)), ring=WHITE)
        if i < n - 1:
            lx0, lx1, ly = x + cw + 10, x + cw + gap - 10, y0 + ch / 2
            d = ImageDraw.Draw(L)
            d.line([(lx0, ly), (lx1, ly)], fill=rgba(DARK, 0.25 * a), width=3)
            fill_frac = clamp01(prog * n - i - 0.6)
            if fill_frac > 0:
                d.line([(lx0, ly), (lx0 + (lx1 - lx0) * fill_frac, ly)], fill=rgba(ORANGE), width=5)
    # iki gerçek sonuç
    ca = ease_out(seg(f, 0.60, 0.74))
    cb = ease_out(seg(f, 0.74, 0.88))
    top = 545
    for (ax, cap, sub, src, css, key, badge) in (
        (110, "Kanıt belgede bulundu", "Yanıt, belge ve bölümüyle birlikte gösterilir", "chat_q1_open", (662, 292, 800), ca, "ok"),
        (990, "Kanıt yok", "Tahmin yok: açıkça “bilgi yok” der", "chat_q2_answer", (672, 296, 760), cb, "no"),
    ):
        if key <= 0:
            continue
        yo = (1 - key) * 46
        x1 = ax + 820
        rrect(L, (ax, top + yo, x1, top + 470 + yo), 30, fill=rgba(WHITE), outline=rgba(LINE), width=2, alpha=key, shadow=0.10, sblur=26, soff=14)
        if badge == "ok":
            check_badge(L, ax + 52, top + 58 + yo, 22, alpha=key, ring=WHITE)
        else:
            circle(L, ax + 52, top + 58 + yo, 22, fill=rgba(PEACH2, key))
            text(L, (ax + 52, top + 58 + yo), "!", 28, DARK, 800, "m", "m", key, va="m")
        text(L, (ax + 92, top + 50 + yo), cap, 34, INK, 800, "m", "l", key, spacing=-1, va="m")
        text(L, (ax + 92, top + 88 + yo), sub, 22, MUTED, 400, "d", "l", key, va="m")
        crop_card(L, src, css, (ax + 30, top + 118 + yo, x1 - 30, top + 118 + 336 + yo), 20, key)
        if badge == "no":
            pa = smooth(seg(key, 0.6, 1.0))
            pill(L, ax + 62, top + 118 + 250 + yo, "Kaynak yok · tahmin yok · uydurma yok", pa)


def count_str(target, p, decimals=0):
    return f"{target * ease_out(p):.{decimals}f}".replace(".", ",")


def scene_numbers(L, t, dur):
    f = t / dur
    text(L, (W // 2, 128), "ÖLÇÜLMÜŞ SONUÇLAR", 22, ORANGE_TXT, 800, "m", "m", smooth(seg(f, 0, 0.08)), spacing=4)
    text(L, (W // 2, 232), "Sayılarla Lumora", 88, INK, 800, "m", "m", smooth(seg(f, 0.0, 0.1)), spacing=-3.5)
    cards = [
        ("file", PEACH_BG, PEACH_FG, "0", "Uydurma yanıt", "48 cevapsız testte"),
        ("layers", LILAC_BG, LILAC_FG, "29/30", "Doğru yanıt", "30 soruluk klasik değerlendirme"),
        ("clock", SAND_BG, SAND_FG, "1,3 sn", "Medyan yanıt süresi", "canlı LLM çağrısı"),
    ]
    cw, gap = 520, 40
    x0 = (W - (3 * cw + 2 * gap)) / 2
    y0, ch = 340, 360
    for i, (ic, bg, fg, val, label, sub) in enumerate(cards):
        s0 = 0.10 + i * 0.12
        a = ease_out(seg(f, s0, s0 + 0.14))
        x = x0 + i * (cw + gap)
        yo = (1 - a) * 50
        rrect(L, (x, y0 + yo, x + cw, y0 + ch + yo), 34, fill=rgba(WHITE), outline=rgba((240, 240, 235)), width=2, alpha=a, shadow=0.10, sblur=28, soff=16)
        rrect(L, (x + 36, y0 + 36 + yo, x + 36 + 96, y0 + 36 + 96 + yo), 28, fill=rgba(bg, a))
        icon(L, ic, x + 84, y0 + 84 + yo, 46, fg, a)
        text(L, (x + cw - 40, y0 + 62 + yo), "↗", 34, (184, 189, 182), 400, "d", "r", a, va="m")
        p = seg(f, s0 + 0.06, s0 + 0.34)
        if i == 0:
            v = "0"
        elif i == 1:
            v = f"{int(round(29 * ease_out(p)))}/30"
        else:
            v = count_str(1.3, p, 1) + " sn"
        text(L, (x + 40, y0 + 250 + yo), v, 118, INK, 800, "m", "l", a, spacing=-5)
        text(L, (x + 40, y0 + 306 + yo), label, 32, INK, 700, "m", "l", a, spacing=-0.8)
        text(L, (x + 40, y0 + 342 + yo), sub, 22, MUTED, 400, "d", "l", a)
    pa = smooth(seg(f, 0.70, 0.86))
    pills = ["10 doküman", "57 vakalık QA seti", "83 otomatik test"]
    widths = [text_width(s, 28, 700) + 64 for s in pills]
    x = (W - (sum(widths) + 2 * 24)) / 2
    for s, w in zip(pills, widths):
        rrect(L, (x, 800, x + w, 860), 30, fill=rgba(PEACH_BG, pa), outline=rgba(PEACH, pa), width=2)
        text(L, (x + w / 2, 830), s, 28, PEACH_FG, 700, "m", "m", pa, va="m")
        x += w + 24


def scene_outro(L, t, dur):
    f = t / dur
    a = ease_out(seg(t, 0.0, 0.7))
    px0, py0, px1, py1 = 110, 110, 1810, 970
    rrect(L, (px0, py0, px1, py1), 44, fill=rgba(PEACH), alpha=a, shadow=0.14, sblur=36, soff=20)
    orbits(L, 1400, 540, t, 0.6 * a, 1.25)
    logo(L, 170, 200, 44, INK, WHITE, alpha=smooth(seg(t, 0.2, 0.9)), spin=-20 + (1 - ease_out(seg(t, 0.1, 1.2))) * 120)
    text(L, (170, 330), "— LUMORA BİLGİ MERKEZİ", 20, (91, 72, 60), 800, "m", "l", smooth(seg(t, 0.3, 0.9)), spacing=3.5)
    h1 = smooth(seg(t, 0.5, 1.3))
    yo = (1 - ease_out(seg(t, 0.5, 1.4))) * 30
    text(L, (170, 470 + yo), "Her sorunun", 122, INK, 800, "m", "l", h1, spacing=-5.5)
    text(L, (170, 600 + yo), "bir dayanağı var.", 122, WHITE, 800, "m", "l", h1, spacing=-5.5)
    words = [("Hızlı", 0.0), ("Kaynaklı", 0.3), ("Güvenilir", 0.6)]
    x = 170
    for wd, d0 in words:
        k = ease_out(seg(t, 1.3 + d0, 1.8 + d0))
        w = text_width(wd, 30, 800) + 72
        rrect(L, (x, 680 + (1 - k) * 24, x + w, 750 + (1 - k) * 24), 35, fill=rgba(DARK), alpha=k)
        circle(L, x + 34, 715 + (1 - k) * 24, 8, fill=rgba(PEACH2, k))
        text(L, (x + 54, 715 + (1 - k) * 24), wd, 30, WHITE, 800, "m", "l", k, va="m")
        x += w + 20
    text(L, (170, 840), "FastAPI  ·  Türkçe BM25 arama  ·  gpt-oss-20b  ·  Gemini", 24, (104, 86, 72), 500, "d", "l", smooth(seg(t, 2.2, 2.9)))
    # hero sanat kartları (uygulamadaki gibi)
    ca = ease_out(seg(t, 0.6, 1.5))
    for (cx, cy, w, h, rot, al) in ((1400, 380, 300, 230, 13, 0.72), (1450, 560, 380, 290, -11, 1.0)):
        card = Image.new("RGBA", (w + 80, h + 80), (0, 0, 0, 0))
        rrect(card, (40, 40, 40 + w, 40 + h), 30, fill=rgba(WHITE, al), shadow=0.16, sblur=22, soff=14)
        d = ImageDraw.Draw(card)
        if al == 1.0:
            asterisk(card, 90, 92, 16, ORANGE, 1.0, width=4)
            for j, ww in enumerate((0.75, 0.56, 0.34)):
                d.rounded_rectangle((70, 130 + j * 34, 70 + (w - 60) * ww, 142 + j * 34), 6, fill=(233, 234, 230, 255))
        else:
            d.ellipse((70, 70, 100, 100), fill=(255, 225, 199, 255))
            d.rounded_rectangle((70, 118, 70 + w * 0.3, 130), 6, fill=(233, 234, 230, 255))
            d.rounded_rectangle((70, 150, 70 + (w - 60), 162), 6, fill=(233, 234, 230, 255))
        card = card.rotate(rot, resample=Image.BICUBIC, expand=True)
        blit(L, scaled_alpha(card, ca), cx - card.width / 2, cy - card.height / 2 + (1 - ca) * 40)
    check_badge(L, 1660, 690, 34, alpha=smooth(seg(t, 1.6, 2.2)), ring=PEACH)
    asterisk(L, 1690, 230, 22, WHITE, alpha=smooth(seg(t, 1.0, 1.6)) * (0.6 + 0.4 * math.sin(t * 3)), rot=t * 20)
    sparkle4(L, 1120, 850, 16, WHITE, alpha=smooth(seg(t, 1.2, 1.8)) * (0.6 + 0.4 * math.sin(t * 2.4)))


SCENES = ["intro", "problem", "demo", "trust", "numbers", "outro"]
MIN_DUR = [5.0, 4.6, 10.0, 7.6, 6.2, 5.6]
LEAD = [0.9, 0.35, 0.35, 0.35, 0.35, 0.35]
TAIL = [0.5, 0.45, 0.45, 0.45, 0.45, 1.6]


# --- ses ---------------------------------------------------------------------------------------------------------
def load_voice(i):
    clip = AudioFileClip(str(BUILD / f"voice_{i}.mp3"))
    arr = clip.to_soundarray(fps=SR)
    clip.close()
    if arr.ndim == 1:
        arr = np.stack([arr, arr], 1)
    amp = np.abs(arr).max(axis=1)
    idx = np.where(amp > 0.012)[0]
    a, b = (max(0, idx[0] - int(0.05 * SR)), min(len(arr), idx[-1] + int(0.08 * SR))) if len(idx) else (0, len(arr))
    return arr[a:b].astype(np.float32)


def plan():
    voices = [load_voice(i) for i in range(1, 7)]
    durs, starts, t = [], [], 0.0
    for i, v in enumerate(voices):
        d = max(MIN_DUR[i], LEAD[i] + len(v) / SR + TAIL[i])
        starts.append(t)
        durs.append(d)
        t += d
    return voices, starts, durs, t


def synth_audio(voices, starts, durs, total):
    n = int(total * SR)
    tt = np.arange(n) / SR
    rng = np.random.default_rng(3)
    # sıcak, majör bir zemin (C - G - Am - F); marka tonuna uygun yumuşak pad
    chords = [(130.8, 196.0, 261.6, 329.6, 392.0), (98.0, 196.0, 246.9, 293.7, 392.0), (110.0, 164.8, 220.0, 261.6, 329.6), (87.3, 174.6, 220.0, 261.6, 349.2)]
    pad = np.zeros(n, np.float32)
    seg_len = total / len(chords)
    for ci, ch in enumerate(chords):
        a0, a1 = int(ci * seg_len * SR), int(min(n, (ci + 1) * seg_len * SR + 2 * SR))
        local = tt[a0:a1] - ci * seg_len
        env = np.clip(local / 2.0, 0, 1) * np.clip((seg_len + 2 - local) / 2.0, 0, 1)
        for k, fq in enumerate(ch):
            for det in (-0.5, 0.5):
                pad[a0:a1] += (np.sin(2 * np.pi * (fq + det) * tt[a0:a1]) * env * (0.09 / (1 + k * 0.45))).astype(np.float32)
    pad *= (0.8 + 0.2 * np.sin(2 * np.pi * tt / 7.0)).astype(np.float32)
    bed = pad.copy()
    # yumuşak nabız + hafif "tık"lar (sahne 2'den itibaren, 88 bpm)
    beat = 60 / 88
    for k in range(int((total - 3) / beat)):
        s = int((starts[1] + k * beat) * SR)
        if s + 5000 < n:
            e = np.exp(-np.arange(5000) / 1000)
            bed[s : s + 5000] += (np.sin(2 * np.pi * (58 + 30 * e) * np.arange(5000) / SR) * e * 0.16).astype(np.float32)
            if k % 2 == 1:
                st = s + int(beat / 2 * SR)
                m = min(2200, n - st)
                if m > 0:
                    bed[st : st + m] += (rng.normal(0, 1, m) * np.exp(-np.arange(m) / 280) * 0.022).astype(np.float32)

    def whoosh(at, length=0.8, gain=0.24):
        m = int(length * SR)
        s = int(at * SR)
        if s < 0 or s + m > n:
            return
        sweep = np.linspace(500, 4200, m)
        car = np.sin(np.cumsum(2 * np.pi * sweep / SR))
        env = np.sin(np.linspace(0, np.pi, m)) ** 2
        bed[s : s + m] += ((rng.normal(0, 1, m) * 0.4 + car * 0.6) * env * gain * 0.3).astype(np.float32)

    def hit(at, gain=0.4):
        m = int(1.4 * SR)
        s = int(at * SR)
        if s + m > n:
            return
        e = np.exp(-np.arange(m) / (0.3 * SR))
        bed[s : s + m] += (np.sin(2 * np.pi * (50 + 55 * np.exp(-np.arange(m) / (0.05 * SR))) * np.arange(m) / SR) * e * gain).astype(np.float32)

    for i in range(1, 6):
        whoosh(starts[i] - 0.45)
    hit(starts[0] + 0.9)
    hit(starts[5] + 0.2, 0.45)
    whoosh(starts[0] + 1.4, 0.7, 0.2)
    voice = np.zeros((n, 2), np.float32)
    for i, v in enumerate(voices):
        s = int((starts[i] + LEAD[i]) * SR)
        voice[s : s + len(v)] += v[: n - s]
    env = np.abs(voice).max(axis=1)
    k = int(0.25 * SR)
    env = np.convolve(env, np.ones(k) / k, mode="same")
    duck = 1 - 0.55 * np.clip(env * 6, 0, 1)
    music = (bed * duck)[:, None] * np.array([1.0, 1.0], np.float32)[None, :] * 0.72
    mix = voice * 1.15 + music
    mix *= np.clip(np.minimum(tt / 0.5, (total - tt) / 1.2), 0, 1)[:, None]
    mix /= max(1.0, np.abs(mix).max() / 0.92)
    return mix.astype(np.float32)


# --- kare üretimi ------------------------------------------------------------------------------------------------
class Renderer:
    def __init__(self, starts, durs, total):
        self.starts, self.durs, self.total = starts, durs, total

    def frame(self, t):
        t = min(t, self.total - 1e-3)
        idx = max(i for i, s in enumerate(self.starts) if s <= t)
        lt, dur = t - self.starts[idx], self.durs[idx]
        fade_in = 1.0 if idx == 0 and lt < 0.05 else smooth(lt / 0.28)
        fade_out = smooth((dur - lt) / (1.0 if idx == len(SCENES) - 1 else 0.28))
        base = cream_background(t)
        img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert("RGBA")
        content = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        name = SCENES[idx]
        if name == "intro":
            scene_intro(content, lt, dur)
        elif name == "problem":
            scene_problem(content, lt, dur)
        elif name == "demo":
            scene_demo(content, lt, dur, None)
        elif name == "trust":
            scene_trust(content, lt, dur)
        elif name == "numbers":
            scene_numbers(content, lt, dur)
        else:
            scene_outro(content, lt, dur)
        # küçük logo (krem sahnelerde) + ilerleme
        if name in ("problem", "demo", "trust", "numbers"):
            logo(content, 56, 54, 20, INK, ORANGE, alpha=0.9 * smooth(seg(lt, 0.2, 0.6)))
        content = scaled_alpha(content, fade_in * fade_out)
        img.alpha_composite(content)
        ImageDraw.Draw(img).rectangle((0, H - 6, int(W * t / self.total), H), fill=rgba(ORANGE))
        # sahne geçişlerinde ince şeftali süpürme çizgisi
        for b in self.starts[1:]:
            d = t - b
            if -0.12 < d < 0.4:
                k = seg(d, -0.12, 0.4)
                x = -160 + (W + 320) * ease_out(k)
                bar = Image.new("RGBA", (160, H), (0, 0, 0, 0))
                ImageDraw.Draw(bar).rectangle((0, 0, 160, H), fill=rgba(PEACH, 0.55 * math.sin(k * math.pi)))
                img.alpha_composite(bar.filter(ImageFilter.GaussianBlur(26)), dest=(int(max(0, x)), 0)) if 0 <= x < W - 160 else None
        return np.asarray(img.convert("RGB"))


def main():
    voices, starts, durs, total = plan()
    print("sahne süreleri:", [round(d, 2) for d in durs], "toplam:", round(total, 2), "sn")
    if total > 40.5:
        print("UYARI: 40 sn'yi aşıyor")
    r = Renderer(starts, durs, total)
    if "--preview" in sys.argv:
        f = lambda i, x: starts[i] + durs[i] * x  # noqa: E731
        pts = [1.2, 3.2, f(1, 0.55), f(1, 0.95), f(2, 0.06), f(2, 0.24), f(2, 0.50), f(2, 0.70), f(2, 0.88),
               f(3, 0.92), f(4, 0.92), starts[5] + 3.2]
        for k, tp in enumerate(pts):
            Image.fromarray(r.frame(tp)).save(BUILD / f"preview_{k}.png")
        print("önizleme:", len(pts), "kare")
        return
    t0 = time.time()
    audio = synth_audio(voices, starts, durs, total)
    video = VideoClip(r.frame, duration=total).with_audio(AudioArrayClip(audio, fps=SR))
    out = HERE / "lumora-tanitim.mp4"
    video.write_videofile(str(out), fps=FPS, codec="libx264", audio_codec="aac", audio_bitrate="192k", preset="medium",
                          ffmpeg_params=["-pix_fmt", "yuv420p", "-crf", "17", "-movflags", "+faststart"], threads=4, logger="bar")
    print(f"tamam: {out}  ({time.time() - t0:.0f} sn)")


if __name__ == "__main__":
    main()
