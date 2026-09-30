"""Lumora Bilgi Asistanı - Türkçe tanıtım videosu (39 sn, 1920x1080, 30 fps, seslendirmesiz; müzik + ses efektleri).

Tasarım, uygulamanın kendi arayüzünden alınmıştır (app/web/styles.css): krem zemin, şeftali (#ffd0a4) vurgu,
koyu yeşil-gri (#292f2b), Manrope + DM Sans, dört noktalı "lumora." logosu, uygulamanın kendi SVG ikonları.
Demo bölümü, çalışan uygulamadan alınan GERÇEK ekran görüntüleridir (promo/capture.py).
Müzik ve efektler promo/sfx.py ile sentezlenir; görüntüdeki her olay ses olayıyla aynı zaman damgasından üretilir.

Sıra:  python promo/capture_icons.py  -> uygulamanın ikonları
       python promo/capture.py        -> gerçek ekran görüntüleri (sunucu açık olmalı)
       python promo/render.py --preview   /   python promo/render.py
"""

import json
import math
import sys
import time
from functools import lru_cache
from pathlib import Path

import numpy as np
from moviepy import VideoClip
from moviepy.audio.AudioClip import AudioArrayClip
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from sfx import build_audio  # noqa: E402

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
    # görünür kutu ekran görüntüsünün dışına taşmasın (yakınlaştırmada merkez sınırlanır)
    cx = min(max(cx, (W / 2) / z), W - (W / 2) / z)
    cy = min(max(cy, (H / 2) / z), H - (H / 2) / z)
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
        src_w, src_h = shot(name).size
        box = (max(0.0, vx0 * 2), max(0.0, vy0 * 2), min(float(src_w), vx1 * 2), min(float(src_h), vy1 * 2))
        im = shot(name).resize((WW, WH), Image.BICUBIC, box=box)
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


# --- zaman çizelgesi (müzikle aynı: 120 bpm, 1 vuruş = 0.5 sn) ---------------------------------------------------
DURS = [5.0, 4.5, 11.5, 7.5, 5.5, 5.0]
STARTS = [sum(DURS[:i]) for i in range(len(DURS))]
TOTAL = sum(DURS)
NAMES = ["intro", "problem", "demo", "trust", "numbers", "outro"]


# --- yeni yardımcılar ------------------------------------------------------------------------------------------------
def slam(L, cx, cy, s, size, color, t, t0, weight=800, dur=0.22, from_scale=1.5, spacing=0, kind="m", alpha=1.0):
    """Metin büyük başlar, vuruşla yerine oturur."""
    p = seg(t, t0, t0 + dur)
    if p <= 0:
        return
    img, ox, oy, total = text_sprite(s, kind, size, weight, color, spacing)
    sc = 1 + (from_scale - 1) * (1 - ease_out(p))
    if sc != 1:
        img = img.resize((max(1, int(img.width * sc)), max(1, int(img.height * sc))), Image.BICUBIC)
    # metnin görsel merkezi (cx, cy)'de kalır
    blit(L, scaled_alpha(img, clamp01(p * 2.5) * alpha), cx - img.width / 2, cy - img.height / 2 + size * 0.04)


def pop_in(L, cx, cy, s, size, color, t, t0, weight=800, kind="m", dur=0.35, spacing=0):
    p = seg(t, t0, t0 + dur)
    if p <= 0:
        return
    img, ox, oy, total = text_sprite(s, kind, size, weight, color, spacing)
    sc = 0.25 + 0.75 * ease_back(p)
    img = img.resize((max(1, int(img.width * sc)), max(1, int(img.height * sc))), Image.BICUBIC)
    blit(L, scaled_alpha(img, clamp01(p * 3)), cx - img.width / 2, cy - img.height / 2 + size * 0.04)


def shock(L, cx, cy, t, t0, color=WHITE, maxr=900, dur=1.1, width=5, alpha=0.8):
    p = seg(t, t0, t0 + dur)
    if 0 < p < 1:
        r = int(40 + (maxr - 40) * ease_out(p))
        circle(L, cx, cy, r, outline=rgba(color, alpha * (1 - p) ** 1.6), width=max(2, int(width * (1 - p) + 1)))


def cursor(L, x, y, alpha=1.0, press=0.0):
    s = 1.0 - 0.12 * press
    pts = [(0, 0), (0, 29), (7, 23), (12, 35), (18, 32), (13, 21), (22, 21)]
    tmp = Image.new("RGBA", (70, 80), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    sh = [(10 + px * s + 3, 10 + py * s + 4) for px, py in pts]
    d.polygon(sh, fill=(0, 0, 0, 70))
    tmp = tmp.filter(ImageFilter.GaussianBlur(3))
    d = ImageDraw.Draw(tmp)
    poly = [(10 + px * s, 10 + py * s) for px, py in pts]
    d.polygon(poly, fill=(255, 255, 255, 255), outline=(29, 29, 31, 255))
    d.line(poly + [poly[0]], fill=(29, 29, 31, 255), width=2)
    blit(L, scaled_alpha(tmp, alpha), x - 10, y - 10)


def ripple(L, x, y, t, t0):
    p = seg(t, t0, t0 + 0.5)
    if 0 < p < 1:
        circle(L, x, y, int(10 + 50 * ease_out(p)), outline=rgba(ORANGE, 0.9 * (1 - p)), width=5)
        circle(L, x, y, int(6 + 18 * ease_out(p)), fill=rgba(ORANGE, 0.25 * (1 - p)))


def lerp(a, b, u):
    return a + (b - a) * u


def ring(L, cx, cy, r, frac, color, width=12, alpha=1.0, track=True):
    """İlerleme halkası (saat yönünde, 12'den başlar)."""
    pad = width + 4
    size = int(2 * r + 2 * pad)
    tmp = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    box = (pad, pad, pad + 2 * r, pad + 2 * r)
    if track:
        d.arc(box, 0, 360, fill=rgba(DARK, 0.08), width=width)
    if frac > 0.002:
        d.arc(box, -90, -90 + 360 * clamp01(frac), fill=rgba(color), width=width)
    blit(L, scaled_alpha(tmp, alpha), cx - r - pad, cy - r - pad)


def path_pos(t, pts):
    """pts: [(t, x, y), ...] -> yumuşak geçişli konum."""
    if t <= pts[0][0]:
        return pts[0][1], pts[0][2]
    for a, b in zip(pts, pts[1:]):
        if t <= b[0]:
            u = smooth((t - a[0]) / (b[0] - a[0]))
            return lerp(a[1], b[1], u), lerp(a[2], b[2], u)
    return pts[-1][1], pts[-1][2]


_CONF = np.random.default_rng(5).random((90, 6))


def confetti(L, ox, oy, t, t0, dur=2.2):
    p = t - t0
    if p < 0 or p > dur:
        return
    cols = [PEACH, ORANGE, WHITE, DARK, PEACH2, ORANGE_TXT]
    for i, (a, sp, sz, rt, ci, sh) in enumerate(_CONF):
        ang = -2.75 + a * 3.15  # yalnızca yukarı/sağ: metnin üstünden geçmesin
        v = 380 + sp * 720
        x = ox + math.cos(ang) * v * p * (1 - 0.18 * p)
        y = oy + math.sin(ang) * v * p * (1 - 0.18 * p) + 420 * p * p
        al = clamp01(1 - (p / dur) ** 2)
        r = 6 + sz * 9
        c = cols[int(ci * len(cols)) % len(cols)]
        if sh < 0.4:
            circle(L, x, y, r, fill=rgba(c, al))
        elif sh < 0.7:
            asterisk(L, x, y, r * 1.6, c, al, rot=rt * 90 + p * 200, width=3)
        else:
            sparkle4(L, x, y, r * 1.7, c, al)


# --- sahneler -------------------------------------------------------------------------------------------------------
def scene_intro(L, t, dur):
    rrect(L, (0, 0, W, H), 0, fill=rgba(PEACH))
    cx, cy = W // 2, 370
    if t > 1.6:
        orbits(L, cx, cy + 50, t, 0.5 * smooth(seg(t, 1.6, 2.2)), 1.5)
    for t0 in (1.6, 2.3, 2.75):
        shock(L, cx, cy + 20, t, t0, WHITE, 1000, 1.2)
    for (px, py, r, ph) in ((250, 250, 30, 0.0), (1650, 300, 22, 1.2), (1500, 800, 26, 2.1), (330, 760, 18, 0.7)):
        a = (0.5 + 0.5 * math.sin(t * 2 + ph)) * smooth(seg(t, 1.8, 2.4))
        (sparkle4 if r < 24 else asterisk)(L, px, py, r, WHITE, alpha=a)
    size = 168
    tw = text_width("lumora", int(size * 1.25), 800, "m", -size * 0.06) + size * 0.45 + size * 1.25
    x0 = cx - tw / 2
    mx, my = x0 + size * 0.5, cy
    off = size * 0.5 - size * 0.155
    a_rot = math.radians(-20)
    starts = [(-260, -200), (W + 260, -160), (-260, H + 200), (W + 260, H + 160)]
    for i, (sx, sy) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1))):
        px, py = sx * off, sy * off
        fx = mx + px * math.cos(a_rot) - py * math.sin(a_rot)
        fy = my + px * math.sin(a_rot) + py * math.cos(a_rot)
        p = seg(t, 0.15 + 0.12 * i, 0.75 + 0.12 * i)
        if p <= 0:
            continue
        k = ease_back(p)
        x = lerp(starts[i][0], fx, min(1.0, k)) if k <= 1 else fx + (fx - starts[i][0]) * 0
        y = lerp(starts[i][1], fy, min(1.0, k))
        circle(L, x, y, max(2, size * 0.155 * (0.4 + 0.6 * min(1, p * 1.4))), fill=rgba(WHITE), alpha=clamp01(p * 4))
    # kelime işareti: harf harf belirir
    lx = x0 + size * 1.25
    for i, ch in enumerate("lumora"):
        w = text_width(ch, int(size * 1.25), 800, "m") - size * 0.06
        pop_in(L, lx + w / 2, cy, ch, int(size * 1.25), INK, t, 0.95 + 0.07 * i, 800, "m", 0.3)
        lx += w
    pop_in(L, lx + size * 0.12, cy, ".", int(size * 1.25), WHITE, t, 0.95 + 0.07 * 6, 800, "m", 0.3)
    # slogan
    slam(L, cx - text_width("bir dayanağı var.", 96, 800, "m", -3.5) / 2 - 10, 610, "Her sorunun", 96, INK, t, 2.3, spacing=-3.5, from_scale=1.6) if False else None
    w1 = text_width("Her sorunun", 96, 800, "m", -3.5)
    w2 = text_width("bir dayanağı var.", 96, 800, "m", -3.5)
    slam(L, cx, 640, "Her sorunun", 96, INK, t, 2.3, spacing=-3.5, from_scale=1.7)
    slam(L, cx, 755, "bir dayanağı var.", 96, WHITE, t, 2.75, spacing=-3.5, from_scale=1.7)
    if 2.75 <= t < 2.95:
        rrect(L, (0, 0, W, H), 0, fill=rgba(WHITE, 0.30 * (1 - (t - 2.75) / 0.2)))
    text(L, (cx, 850), "Ürün, sipariş ve abonelik sorularına kaynaklı yanıtlar.", 34, (104, 86, 72), 400, "d", "m", smooth(seg(t, 3.5, 4.1)))


QUESTIONS = [
    ("İade süresi kaç gün?", "file", 330, 330, -3),
    ("Garanti neleri kapsıyor?", "shield", 1000, 305, 2),
    ("Şifremi unuttum!", "lock", 1560, 350, -2),
    ("Kargo ücretsiz mi?", "truck", 350, 490, 2),
    ("Aboneliği nasıl iptal ederim?", "card", 900, 500, -2),
    ("5 GHz Wi-Fi'ye bağlanır mı?", "wifi", 1520, 500, 3),
]


def scene_problem(L, t, dur):
    # başlık: iki parça, vuruşla
    w1 = text_width("Aynı sorular. ", 92, 800, "m", -3.5)
    w2 = text_width("Her gün.", 92, 800, "m", -3.5)
    x = W // 2 - (w1 + w2) / 2
    slam(L, x + w1 / 2, 170, "Aynı sorular. ", 92, INK, t, 0.15, spacing=-3.5, from_scale=1.5)
    slam(L, x + w1 + w2 / 2, 170, "Her gün.", 92, ORANGE_TXT, t, 0.65, spacing=-3.5, from_scale=1.5)
    for i, (s, ic, bx, by, rot) in enumerate(QUESTIONS):
        k = ease_back(seg(t, 0.6 + 0.25 * i, 0.95 + 0.25 * i))
        if k <= 0:
            continue
        w = text_width(s, 34, 500, "d") + 150
        cx = bx + math.sin(t * 1.2 + bx * 0.01) * 6
        cy = by + math.cos(t * 1.0 + by * 0.01) * 6
        box = (cx - w / 2 * k, cy - 48 * k, cx + w / 2 * k, cy + 48 * k)
        rrect(L, box, 30 * k, fill=rgba(WHITE), outline=rgba(LINE), width=2, alpha=clamp01(k), shadow=0.12, sblur=22, soff=12)
        if k > 0.75:
            a = clamp01((k - 0.75) / 0.25)
            rrect(L, (cx - w / 2 + 18, cy - 30, cx - w / 2 + 78, cy + 30), 16, fill=rgba(PEACH_BG, a))
            icon(L, ic, cx - w / 2 + 48, cy, 30, PEACH_FG, a)
            text(L, (cx - w / 2 + 98, cy), s, 34, INK, 500, "d", "l", a, va="m")
    # güven çubuğu: dolar, sonra çöker
    a = smooth(seg(t, 2.0, 2.3))
    if a > 0:
        bx0, bx1, by = W // 2 - 400, W // 2 + 400, 880
        text(L, (bx0, by - 30), "Müşteri güveni", 32, MUTED, 500, "d", "l", a)
        rrect(L, (bx0, by, bx1, by + 22), 11, fill=rgba(LINE, a))
        fill_up = ease_out(seg(t, 2.0, 2.6))
        drop = ease_out(seg(t, 2.7, 3.15))
        frac = fill_up * (1 - 0.88 * drop)
        rrect(L, (bx0, by, bx0 + (bx1 - bx0) * max(frac, 0.012), by + 22), 11, fill=rgba(ORANGE if drop > 0.05 else PEACH2, a))
    wa = ease_back(seg(t, 3.2, 3.55))
    if wa > 0:
        cx, cy = W // 2, 700
        rrect(L, (cx - 420, cy - 66, cx + 420, cy + 66), 36, fill=rgba(DARK, clamp01(wa)), shadow=0.30, sblur=28, soff=18, alpha=clamp01(wa))
        circle(L, cx - 352, cy, 30, fill=rgba(PEACH2, clamp01(wa)))
        text(L, (cx - 352, cy), "!", 40, DARK, 800, "m", "m", clamp01(wa), va="m")
        text(L, (cx - 296, cy), "Tek bir yanlış cevap, güveni bitirir.", 38, WHITE, 700, "m", "l", clamp01(wa), va="m")


# demo zaman çizelgesi (sahne yerel saniyesi)
D_CLICK1, D_CLICK2, D_SEND = 1.7, 2.7, 4.3
D_TYPE0, D_TYPE1 = 3.0, 3.95
D_ANS, D_OPEN = 5.5, 7.0
CSS = {"hero_btn": (576, 427)}


def scene_demo(L, t, dur):
    pop = 0.92 + 0.08 * ease_out(seg(t, 0.0, 0.45))
    a = smooth(seg(t, 0.0, 0.35))
    order = [("home", 0.0), ("chat_empty", D_CLICK1 + 0.1), ("chat_q1_typing_half", 3.25), ("chat_q1_typing_full", 3.95),
             ("chat_q1_thinking", D_SEND + 0.15), ("chat_q1_answer", D_ANS), ("chat_q1_open", D_OPEN + 0.1)]
    weights = {}
    for i, (name, start) in enumerate(order):
        nxt = order[i + 1][1] if i + 1 < len(order) else 99
        w_in = 1.0 if i == 0 else smooth(seg(t, start - 0.05, start + 0.22))
        w_out = 0.0 if i + 1 == len(order) else smooth(seg(t, nxt - 0.05, nxt + 0.22))
        weights[name] = w_in * (1 - w_out)
    cam = keyframes(t, [
        (0.0, 960, 540, 1.0), (2.0, 960, 540, 1.0), (2.8, 1090, 720, 1.45), (4.2, 1090, 700, 1.45),
        (5.3, 1090, 400, 1.6), (6.9, 1090, 420, 1.6), (7.6, 1090, 470, 1.55), (10.0, 1090, 500, 1.5), (11.5, 960, 540, 1.0),
    ])
    draw_window(L, weights, cam, alpha=a, pop=pop)
    m, k, _ = cam_map(cam)
    pulse = 0.5 + 0.5 * math.sin(t * 5)
    # vurgular
    fa = smooth(seg(t, 5.6, 5.85)) * (1 - smooth(seg(t, 6.85, 7.05)))
    b = highlight(L, cam, "q1_answer_bubble", 8, fa, pulse)
    if b:
        pill(L, b[2] + 26, (b[1] + b[3]) / 2, "Türkçe yanıt, saniyeler içinde", fa, slide=(1 - fa) * 14)
    fs = smooth(seg(t, 7.35, 7.6)) * (1 - smooth(seg(t, 8.55, 8.75)))
    b = highlight(L, cam, "q1_sources", 8, fs, pulse)
    if b:
        pill(L, b[2] + 26, (b[1] + b[3]) / 2, "Belge · sürüm · bölüm", fs, slide=(1 - fs) * 14)
    fc = smooth(seg(t, 8.8, 9.05)) * (1 - smooth(seg(t, 10.0, 10.3)))
    b = highlight(L, cam, "q1_conflict", 8, fc, pulse)
    if b:
        pill(L, b[2] + 26, (b[1] + b[3]) / 2, "Güncel sürüm otomatik seçilir", fc, slide=(1 - fc) * 14)
    ta = smooth(seg(t, 0.0, 0.3)) * (1 - smooth(seg(t, 1.5, 1.85)))
    if ta > 0:
        text(L, (W // 2, 56), "Gerçek uygulama. Gerçek yanıt.", 40, INK, 800, "m", "m", ta, spacing=-1.2, va="m")
    # imleç
    comp = BOXES.get("q1_composer", {"x": 687, "y": 960, "width": 806, "height": 51})
    srcb = BOXES.get("q1_sources", {"x": 742, "y": 415, "width": 578, "height": 116})
    pts = [(0.0, 1500, 780), (0.4, 1500, 780), (1.6, CSS["hero_btn"][0], CSS["hero_btn"][1]),
           (D_CLICK1 + 0.3, CSS["hero_btn"][0] + 40, CSS["hero_btn"][1] + 60), (2.05, 1000, 760),
           (D_CLICK2 - 0.05, comp["x"] + 200, comp["y"] + comp["height"] / 2),
           (4.4, comp["x"] + 420, comp["y"] + 20), (6.2, 1200, 520), (D_OPEN - 0.05, srcb["x"] + 160, srcb["y"] + 18),
           (8.4, srcb["x"] + 320, srcb["y"] + 60)]
    cx_, cy_ = path_pos(t, pts)
    X, Y = m(cx_, cy_)
    vis = smooth(seg(t, 0.25, 0.5)) * (1 - smooth(seg(t, 8.4, 8.9)))
    press = max(seg(t, D_CLICK1 - 0.05, D_CLICK1 + 0.05) * (1 - seg(t, D_CLICK1 + 0.05, D_CLICK1 + 0.2)),
                seg(t, D_CLICK2 - 0.05, D_CLICK2 + 0.05) * (1 - seg(t, D_CLICK2 + 0.05, D_CLICK2 + 0.2)),
                seg(t, D_OPEN - 0.05, D_OPEN + 0.05) * (1 - seg(t, D_OPEN + 0.05, D_OPEN + 0.2)))
    for tc in (D_CLICK1, D_CLICK2, D_OPEN):
        ripple(L, X, Y, t, tc)
    if vis > 0:
        cursor(L, X, Y, vis, press)


NODES = [("Arama", "BM25 · Türkçe", "search"), ("Sürüm seçimi", "v1 ↔ v2", "layers"),
         ("Kanıt cümlesi", "belgede aynen var mı?", "file"), ("Sayı denetimi", "kaynakta olmayan sayı yok", "shield"),
         ("Yanıt", "kaynak + bölüm", "message")]
T_CHECK = [1.6, 2.2, 2.8, 3.4, 4.0]


def crop_card(L, src, css_xy_w, box, r=22, alpha=1.0):
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
    text(L, (110, 128), "GÜVEN KATMANLARI", 22, ORANGE_TXT, 800, "m", "l", smooth(seg(t, 0, 0.4)), spacing=4)
    slam(L, 110 + text_width("Uydurmaya izin yok", 92, 800, "m", -3.5) / 2, 190, "Uydurmaya izin yok", 92, INK, t, 0.0, spacing=-3.5, from_scale=1.35)
    n = len(NODES)
    cw, gap = 290, 62
    x0 = (W - (n * cw + (n - 1) * gap)) / 2
    y0, ch = 290, 200
    d = ImageDraw.Draw(L)
    for i, (name, sub, ic) in enumerate(NODES):
        pa = ease_back(seg(t, 0.2 + 0.1 * i, 0.6 + 0.1 * i))
        if pa <= 0:
            continue
        x = x0 + i * (cw + gap)
        lit = smooth(seg(t, T_CHECK[i] - 0.25, T_CHECK[i]))
        sc = 0.85 + 0.15 * min(1, pa)
        bx0, by0 = x + cw / 2 * (1 - sc), y0 + ch / 2 * (1 - sc)
        bx1, by1 = x + cw / 2 * (1 + sc), y0 + ch / 2 * (1 + sc)
        flash = max(0, 1 - abs(t - T_CHECK[i]) / 0.25) if t >= T_CHECK[i] - 0.05 else 0
        rrect(L, (bx0, by0, bx1, by1), 26, fill=rgba(WHITE if flash < 0.3 else (255, 244, 232)), outline=rgba(ORANGE if lit > 0.6 else LINE), width=3 if lit > 0.6 else 2,
              alpha=clamp01(pa), shadow=0.10 + 0.10 * flash, sblur=22, soff=12)
        a = clamp01(pa)
        rrect(L, (x + 24, y0 + 24, x + 88, y0 + 88), 18, fill=rgba(PEACH if lit > 0.6 else PEACH_BG, a))
        icon(L, ic, x + 56, y0 + 56, 34, PEACH_FG, a)
        text(L, (x + 24, y0 + 134), name, 30, INK, 700, "m", "l", a, spacing=-0.8)
        text(L, (x + 24, y0 + 170), sub, 19 if len(sub) > 22 else 20, MUTED, 400, "d", "l", a)
        cp = ease_back(seg(t, T_CHECK[i], T_CHECK[i] + 0.3))
        if cp > 0:
            check_badge(L, x + cw - 30, y0 + 30, 17 * max(0.2, min(1.25, cp)), alpha=clamp01(cp * 2), ring=WHITE)
        if i < n - 1:
            lx0, lx1, ly = x + cw + 10, x + cw + gap - 10, y0 + ch / 2
            d.line([(lx0, ly), (lx1, ly)], fill=rgba(DARK, 0.22 * clamp01(pa)), width=3)
            ff = clamp01((t - T_CHECK[i] + 0.15) / 0.55)
            if ff > 0:
                d.line([(lx0, ly), (lx0 + (lx1 - lx0) * ff, ly)], fill=rgba(ORANGE), width=5)
                if ff < 1:
                    circle(L, lx0 + (lx1 - lx0) * ff, ly, 8, fill=rgba(ORANGE), alpha=1)
    # iki gerçek sonuç
    ca = ease_out(seg(t, 4.4, 4.95))
    cb = ease_out(seg(t, 5.6, 6.15))
    top = 565
    for (ax, cap, sub, src, css, key, badge) in (
        (110, "Kanıt belgede bulundu", "Yanıt, belge ve bölümüyle birlikte gösterilir", "chat_q1_open", (662, 292, 800), ca, "ok"),
        (990, "Kanıt yok", "Tahmin yok: açıkça “bilgi yok” der", "chat_q2_answer", (672, 296, 760), cb, "no"),
    ):
        if key <= 0:
            continue
        xo = (1 - key) * (-160 if badge == "ok" else 160)
        ax2 = ax + xo
        x1 = ax2 + 820
        rrect(L, (ax2, top, x1, top + 450), 30, fill=rgba(WHITE), outline=rgba(LINE), width=2, alpha=key, shadow=0.12, sblur=26, soff=14)
        if badge == "ok":
            check_badge(L, ax2 + 52, top + 58, 22, alpha=key, ring=WHITE)
        else:
            circle(L, ax2 + 52, top + 58, 22, fill=rgba(PEACH2, key))
            text(L, (ax2 + 52, top + 58), "!", 28, DARK, 800, "m", "m", key, va="m")
        text(L, (ax2 + 92, top + 50), cap, 34, INK, 800, "m", "l", key, spacing=-1, va="m")
        text(L, (ax2 + 92, top + 88), sub, 22, MUTED, 400, "d", "l", key, va="m")
        crop_card(L, src, css, (ax2 + 30, top + 118, x1 - 30, top + 118 + 312), 20, key)
        if badge == "no":
            pill(L, ax2 + 62, top + 118 + 240, "Kaynak yok · tahmin yok · uydurma yok", smooth(seg(key, 0.6, 1.0)))


def count_str(target, p, decimals=0):
    return f"{target * ease_out(p):.{decimals}f}".replace(".", ",")


T_N = [1.0, 1.4, 1.8]


def scene_numbers(L, t, dur):
    text(L, (W // 2, 128), "ÖLÇÜLMÜŞ SONUÇLAR", 22, ORANGE_TXT, 800, "m", "m", smooth(seg(t, 0, 0.3)), spacing=4)
    slam(L, W // 2, 222, "Rakamlarla Lumora", 92, INK, t, 0.0, spacing=-3.5, from_scale=1.35)
    cards = [
        ("file", PEACH_BG, PEACH_FG, GREEN_RING, "uydurma yanıt", "48 cevapsız testte", 0.0, "%", 0),
        ("layers", LILAC_BG, LILAC_FG, LILAC_FG, "doğru yanıt", "30 soruluk klasik değerlendirmede", 96.7, "%", 0),
        ("clock", SAND_BG, SAND_FG, SAND_FG, "medyan yanıt süresi", "canlı LLM çağrısı", 1.3, "", 1),
    ]
    cw, gap = 520, 40
    x0 = (W - (3 * cw + 2 * gap)) / 2
    y0, ch = 330, 390
    for i, (ic, bg, fg, ringc, label, sub, val, prefix, dec) in enumerate(cards):
        s0 = T_N[i]
        a = ease_back(seg(t, s0, s0 + 0.4))
        if a <= 0:
            continue
        x = x0 + i * (cw + gap)
        sc = 0.88 + 0.12 * min(1, a)
        bx0, by0, bx1, by1 = x + cw / 2 * (1 - sc), y0 + ch / 2 * (1 - sc), x + cw / 2 * (1 + sc), y0 + ch / 2 * (1 + sc)
        al = clamp01(a)
        rrect(L, (bx0, by0, bx1, by1), 34, fill=rgba(WHITE), outline=rgba((240, 240, 235)), width=2, alpha=al, shadow=0.12, sblur=28, soff=16)
        rrect(L, (x + 36, y0 + 36, x + 132, y0 + 132), 28, fill=rgba(bg, al))
        icon(L, ic, x + 84, y0 + 84, 46, fg, al)
        p = seg(t, s0 + 0.1, s0 + 2.0)
        # halka göstergesi
        rc_x, rc_y, rr = x + cw - 110, y0 + 96, 58
        frac = {0: 1.0, 1: 0.967, 2: None}[i]
        if frac is None:
            ring(L, rc_x, rc_y, rr, 0.28, ringc, 12, alpha=al, track=True)
        else:
            ring(L, rc_x, rc_y, rr, frac * ease_out(p), ringc, 12, alpha=al)
        if i == 0:
            check_badge(L, rc_x, rc_y, 24, alpha=al * smooth(seg(p, 0.8, 1.0)), ring=WHITE)
        if i == 0:
            v = "%0"
        elif i == 1:
            v = "%" + f"{96.7 * ease_out(p):.0f}"
        else:
            v = count_str(1.3, p, 1) + " sn"
        text(L, (x + 40, y0 + 268), v, 124, INK, 800, "m", "l", al, spacing=-5)
        text(L, (x + 40, y0 + 326), label, 34, INK, 700, "m", "l", al, spacing=-0.8)
        text(L, (x + 40, y0 + 364), sub, 22, MUTED, 400, "d", "l", al)
        if abs(t - (s0 + 0.05)) < 0.22:
            shock(L, x + cw / 2, y0 + ch / 2, t, s0, ORANGE, 380, 0.5, 4, 0.5)
    pills = [("10 doküman", 3.6), ("57 vakalık QA seti", 3.8), ("83 otomatik test", 4.0)]
    widths = [text_width(s, 28, 700) + 64 for s, _ in pills]
    x = (W - (sum(widths) + 2 * 24)) / 2
    for (s, pt), w in zip(pills, widths):
        k = ease_back(seg(t, pt, pt + 0.3))
        if k > 0:
            cyp = 830
            rrect(L, (x + w / 2 * (1 - k), cyp - 30 * k, x + w / 2 * (1 + k), cyp + 30 * k), 30 * k, fill=rgba(PEACH_BG, clamp01(k)), outline=rgba(PEACH, clamp01(k)), width=2)
            if k > 0.8:
                text(L, (x + w / 2, cyp), s, 28, PEACH_FG, 700, "m", "m", clamp01((k - 0.8) / 0.2), va="m")
        x += w + 24


GREEN_RING = (52, 168, 120)


def scene_outro(L, t, dur):
    a = ease_out(seg(t, 0.0, 0.6))
    px0, py0, px1, py1 = 110, 110, 1810, 970
    yo = (1 - a) * 160
    rrect(L, (px0, py0 + yo, px1, py1 + yo), 44, fill=rgba(PEACH), alpha=a, shadow=0.16, sblur=36, soff=20)
    if a < 0.98:
        return
    orbits(L, 1400, 540, t, 0.6, 1.25)
    logo(L, 170, 200, 44, INK, WHITE, alpha=smooth(seg(t, 0.3, 0.8)), spin=-20 + (1 - ease_out(seg(t, 0.2, 1.2))) * 120)
    text(L, (170, 330), "— LUMORA BİLGİ MERKEZİ", 20, (91, 72, 60), 800, "m", "l", smooth(seg(t, 0.5, 1.0)), spacing=3.5)
    slam(L, 170 + text_width("Her sorunun", 122, 800, "m", -5.5) / 2, 440, "Her sorunun", 122, INK, t, 1.0, spacing=-5.5, from_scale=1.35)
    slam(L, 170 + text_width("bir dayanağı var.", 122, 800, "m", -5.5) / 2, 570, "bir dayanağı var.", 122, WHITE, t, 1.4, spacing=-5.5, from_scale=1.35)
    x = 170
    for wd, t0 in (("Hızlı", 2.0), ("Kaynaklı", 2.35), ("Güvenilir", 2.7)):
        k = ease_back(seg(t, t0, t0 + 0.35))
        w = text_width(wd, 30, 800) + 72
        if k > 0:
            cyp = 715
            rrect(L, (x + w / 2 * (1 - k), cyp - 35 * k, x + w / 2 * (1 + k), cyp + 35 * k), 35 * k, fill=rgba(DARK, clamp01(k)))
            if k > 0.75:
                aa = clamp01((k - 0.75) / 0.25)
                circle(L, x + 34, cyp, 8, fill=rgba(PEACH2, aa))
                text(L, (x + 54, cyp), wd, 30, WHITE, 800, "m", "l", aa, va="m")
        x += w + 20
    text(L, (170, 840), "FastAPI  ·  Türkçe BM25 arama  ·  gpt-oss-20b  ·  Gemini", 24, (104, 86, 72), 500, "d", "l", smooth(seg(t, 3.0, 3.6)))
    ca = ease_out(seg(t, 0.5, 1.3))
    for (cx, cy, w, h, rot, al) in ((1400, 380, 300, 230, 13, 0.72), (1450, 560, 380, 290, -11, 1.0)):
        card = Image.new("RGBA", (w + 80, h + 80), (0, 0, 0, 0))
        rrect(card, (40, 40, 40 + w, 40 + h), 30, fill=rgba(WHITE, al), shadow=0.16, sblur=22, soff=14)
        dd = ImageDraw.Draw(card)
        if al == 1.0:
            asterisk(card, 90, 92, 16, ORANGE, 1.0, width=4)
            for j, ww in enumerate((0.75, 0.56, 0.34)):
                dd.rounded_rectangle((70, 130 + j * 34, 70 + (w - 60) * ww, 142 + j * 34), 6, fill=(233, 234, 230, 255))
        else:
            dd.ellipse((70, 70, 100, 100), fill=(255, 225, 199, 255))
            dd.rounded_rectangle((70, 118, 70 + w * 0.3, 130), 6, fill=(233, 234, 230, 255))
            dd.rounded_rectangle((70, 150, 70 + (w - 60), 162), 6, fill=(233, 234, 230, 255))
        card = card.rotate(rot + (1 - ca) * 25, resample=Image.BICUBIC, expand=True)
        blit(L, scaled_alpha(card, ca), cx - card.width / 2, cy - card.height / 2 + (1 - ca) * 120)
    check_badge(L, 1660, 690, 34, alpha=smooth(seg(t, 1.5, 2.0)), ring=PEACH)
    asterisk(L, 1690, 230, 22, WHITE, alpha=smooth(seg(t, 1.0, 1.6)) * (0.6 + 0.4 * math.sin(t * 3)), rot=t * 20)
    sparkle4(L, 1120, 850, 16, WHITE, alpha=smooth(seg(t, 1.2, 1.8)) * (0.6 + 0.4 * math.sin(t * 2.4)))
    shock(L, 1450, 700, t, 2.7, WHITE, 900, 1.1)
    confetti(L, 1450, 720, t, 2.7)


# --- olaylar (görüntü ve ses aynı zamandan beslenir) --------------------------------------------------------------------
def events():
    E = []

    def ev(scene, local, kind, param=None):
        E.append((STARTS[scene] + local, kind, param))

    # 1 açılış
    ev(0, 0.05, "whoosh", 0.9)
    for i in range(4):
        ev(0, 0.65 + 0.12 * i, "pop", 0.9 + 0.12 * i)
    for i in range(6):
        ev(0, 0.95 + 0.07 * i, "tick", i)
    ev(0, 1.6, "boom", 0.8)
    ev(0, 2.3, "hit", 0.7)
    ev(0, 2.75, "hit", 1.0)
    ev(0, 2.75, "boom", 0.6)
    ev(0, 3.5, "sparkle")
    ev(0, 3.9, "riser", 1.1)
    # 2 problem
    ev(1, 0.15, "hit", 0.6)
    ev(1, 0.65, "hit", 0.8)
    for i in range(6):
        ev(1, 0.6 + 0.25 * i + 0.05, "pop", 0.85 + 0.07 * i)
    ev(1, 2.7, "fall")
    ev(1, 3.2, "thud")
    ev(1, 3.2, "boom", 0.7)
    ev(1, 4.1, "whoosh", 0.9)
    # 3 demo
    ev(2, 0.0, "whoosh", 0.8)
    ev(2, D_CLICK1, "click")
    ev(2, D_CLICK1 + 0.1, "pop", 1.2)
    ev(2, D_CLICK2, "click")
    n_keys = 20
    for i in range(n_keys):
        ev(2, D_TYPE0 + (D_TYPE1 - D_TYPE0) * i / (n_keys - 1), "tick", i)
    ev(2, D_SEND, "send")
    ev(2, D_ANS, "ding", 0)
    ev(2, D_ANS, "pop", 1.0)
    ev(2, D_OPEN, "click")
    ev(2, D_OPEN + 0.05, "expand")
    ev(2, 7.35, "ding", 4)
    ev(2, 8.8, "ding", 7)
    ev(2, 11.0, "whoosh", 0.9)
    # 4 güven
    ev(3, 0.0, "whoosh", 0.8)
    for i in range(5):
        ev(3, 0.2 + 0.1 * i + 0.1, "pop", 0.9 + 0.06 * i)
    for i, tc in enumerate(T_CHECK):
        ev(3, tc, "ding", [0, 2, 4, 7, 12][i])
    ev(3, 4.4, "whoosh", 0.7)
    ev(3, 4.55, "ding", 12)
    ev(3, 5.6, "whoosh", 0.7)
    ev(3, 5.8, "thud")
    ev(3, 7.0, "whoosh", 0.9)
    # 5 rakamlar
    ev(4, 0.0, "riser", 1.0)
    for i, tn in enumerate(T_N):
        ev(4, tn, "hit", 0.8)
        ev(4, tn, "ding", [0, 4, 7][i])
    for i in range(20):
        ev(4, 1.1 + i * 0.1, "count", 2 + i * 0.6)
    for pt in (3.6, 3.8, 4.0):
        ev(4, pt, "pop", 1.0 + (pt - 3.6))
    ev(4, 4.9, "whoosh", 0.9)
    # 6 kapanış
    ev(5, 0.0, "whoosh", 1.0)
    ev(5, 0.55, "pop", 0.9)
    ev(5, 1.0, "hit", 0.8)
    ev(5, 1.4, "hit", 1.0)
    for tw in (2.0, 2.35, 2.7):
        ev(5, tw, "hit", 0.7)
    ev(5, 2.7, "sparkle")
    ev(5, 2.7, "sting")
    return sorted(E, key=lambda e: e[0])


SECTIONS = {"drums": STARTS[1], "hats": STARTS[2], "bass": STARTS[2], "arp": STARTS[2], "claps": STARTS[4], "stop": STARTS[5] + 2.7}


def shake_offset(t, evs):
    dx = dy = 0.0
    for at, kind, param in evs:
        if kind in ("hit", "boom", "thud") and 0 <= t - at < 0.28:
            amp = {"hit": 10, "boom": 9, "thud": 14}[kind] * (param or 1.0) * math.exp(-(t - at) / 0.09)
            dx += amp * math.sin((t - at) * 95)
            dy += amp * 0.7 * math.cos((t - at) * 83)
    return dx, dy


SCENE_FUNCS = {"intro": scene_intro, "problem": scene_problem, "demo": scene_demo, "trust": scene_trust, "numbers": scene_numbers, "outro": scene_outro}


class Renderer:
    def __init__(self):
        self.evs = events()

    def frame(self, t):
        t = min(t, TOTAL - 1e-3)
        idx = max(i for i, s in enumerate(STARTS) if s <= t)
        lt, dur = t - STARTS[idx], DURS[idx]
        name = NAMES[idx]
        base = cream_background(t)
        img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert("RGBA")
        content = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        SCENE_FUNCS[name](content, lt, dur)
        if name in ("problem", "demo", "trust", "numbers"):
            logo(content, 56, 54, 20, INK, ORANGE, alpha=0.9 * smooth(seg(lt, 0.2, 0.6)))
        # geçiş: yatay "whip" (kayma + hareket bulanıklığı) ve solma
        tin = 0.0 if idx == 0 else ease_out(seg(lt, 0, 0.38))
        tout = 0.0 if idx == len(NAMES) - 1 else ease_out(seg(lt, dur - 0.32, dur)) ** 1.5
        off = (1 - tin) * 240 * (0 if idx == 0 else 1) - tout * 240
        alpha = (1.0 if idx == 0 else smooth(seg(lt, 0, 0.22))) * (1.0 if idx == len(NAMES) - 1 else 1 - smooth(seg(lt, dur - 0.22, dur)))
        if idx == len(NAMES) - 1:
            alpha *= 1 - smooth(seg(lt, dur - 0.9, dur))
        if abs(off) > 1:
            content = content.transform(content.size, Image.AFFINE, (1, 0, -off, 0, 1, 0), resample=Image.BILINEAR)
            k = min(0.85, abs(off) / 240 * 0.9)
            hb = content.resize((max(8, W // 16), H), Image.BILINEAR).resize((W, H), Image.BILINEAR)
            content = Image.blend(content, hb, k)
        # vuruşlarda kamera sarsıntısı
        dx, dy = shake_offset(t, self.evs)
        if abs(dx) + abs(dy) > 0.5:
            content = content.transform(content.size, Image.AFFINE, (1, 0, -dx, 0, 1, -dy), resample=Image.BILINEAR)
        content = scaled_alpha(content, alpha)
        img.alpha_composite(content)
        ImageDraw.Draw(img).rectangle((0, H - 6, int(W * t / TOTAL), H), fill=rgba(ORANGE))
        return np.asarray(img.convert("RGB"))


def mux_audio(video_src, audio, out):
    """Sesi WAV olarak yazar, görüntüyü yeniden kodlamadan birleştirir ve TEK seferde AAC'ye kodlar.
    AAC, vuruş anlarında tepeyi birkaç dB taşırabildiği için kodlamadan önce -3 dBFS'lik bir limiter uygulanır."""
    import subprocess

    import imageio_ffmpeg
    from scipy.io import wavfile

    wav = BUILD / "audio.wav"
    wavfile.write(str(wav), SR, (np.clip(audio, -1, 1) * 32767).astype(np.int16))
    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-v", "error", "-i", str(video_src), "-i", str(wav), "-map", "0:v", "-map", "1:a",
           "-c:v", "copy", "-af", "alimiter=limit=0.45:level=disabled:attack=2:release=60", "-c:a", "aac", "-b:a", "256k",
           "-shortest", "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True)


def main():
    r = Renderer()
    print("sahne süreleri:", DURS, "toplam:", TOTAL, "sn;", len(r.evs), "ses olayı")
    if "--preview" in sys.argv:
        pts = [0.7, 1.3, 2.5, 3.2, STARTS[1] + 1.4, STARTS[1] + 3.0, STARTS[1] + 3.6, STARTS[2] + 1.0, STARTS[2] + 1.75, STARTS[2] + 4.0,
               STARTS[2] + 6.4, STARTS[2] + 7.7, STARTS[2] + 9.3, STARTS[3] + 3.0, STARTS[3] + 6.3, STARTS[4] + 1.3, STARTS[4] + 3.0,
               STARTS[4] + 4.4, STARTS[5] + 1.8, STARTS[5] + 3.0, STARTS[5] + 4.0]
        for k, tp in enumerate(pts):
            Image.fromarray(r.frame(tp)).save(BUILD / f"preview_{k:02d}.png")
        print("önizleme:", len(pts), "kare")
        return
    t0 = time.time()
    audio = build_audio(TOTAL, r.evs, SECTIONS)
    print(f"ses hazır: tepe {20 * np.log10(np.abs(audio).max()):.1f} dBFS, RMS {20 * np.log10(np.sqrt((audio ** 2).mean())):.1f} dBFS")
    out = HERE / "lumora-tanitim.mp4"
    silent = BUILD / "video_silent.mp4"
    VideoClip(r.frame, duration=TOTAL).write_videofile(str(silent), fps=FPS, codec="libx264", audio=False, preset="medium",
                                                       ffmpeg_params=["-pix_fmt", "yuv420p", "-crf", "17"], threads=4, logger="bar")
    mux_audio(silent, audio, out)
    print(f"tamam: {out}  ({time.time() - t0:.0f} sn)")


if __name__ == "__main__":
    main()
