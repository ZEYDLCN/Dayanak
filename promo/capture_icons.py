"""Uygulamanın kendi ikon setini (app/web/app.js -> iconPaths) şeffaf PNG'ye çevirir (siyah, 256 px)."""

import re
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).parent / "build" / "icons"
OUT.mkdir(parents=True, exist_ok=True)

js = (ROOT / "app" / "web" / "app.js").read_text(encoding="utf-8")
block = js[js.index("const iconPaths = {") : js.index("};", js.index("const iconPaths = {"))]
icons = dict(re.findall(r"""['"]?([\w-]+)['"]?\s*:\s*'(.*?)'\s*,?\n""", block))

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 256, "height": 256}, device_scale_factor=1)
    for name, paths in icons.items():
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="256" height="256" fill="none" '
            'stroke="#000" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">' + paths + "</svg>"
        )
        page.set_content(f"<html><body style='margin:0;background:transparent'>{svg}</body></html>")
        page.screenshot(path=OUT / f"{name}.png", omit_background=True)
    browser.close()
print(len(icons), "ikon:", ", ".join(sorted(icons)))
