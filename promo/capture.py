"""Çalışan uygulamanın (http://localhost:8000) gerçek arayüzünden ekran görüntüleri alır.

Ön koşul: sunucu açık olmalı (LLM_PROVIDER=nvidia ile gerçek yanıtlar alınır).
    python -m uvicorn app.main:app --port 8000
    python promo/capture.py
Çıktı: promo/build/shots/*.png ve boxes.json (öğelerin CSS piksel konumları; videodaki vurgular için).
"""

import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = "http://localhost:8000/"
OUT = Path(__file__).parent / "build" / "shots"
OUT.mkdir(parents=True, exist_ok=True)
BOXES: dict[str, dict] = {}


def box(page, name, selector, index=0):
    loc = page.locator(selector)
    if loc.count() > index:
        b = loc.nth(index).bounding_box()
        if b:
            BOXES[name] = {k: round(v, 1) for k, v in b.items()}


def wait_answer(page, timeout=40000):
    page.wait_for_function(
        "() => document.querySelectorAll('#chat-messages .message-block.assistant .message-bubble').length > 0"
        " && !document.querySelector('#chat-messages .typing')",
        timeout=timeout,
    )


def ask(page, question, shot_prefix=None):
    page.fill("#chat-input", "")
    if shot_prefix:
        half = question[: len(question) // 2]
        page.fill("#chat-input", half)
        page.wait_for_timeout(150)
        page.screenshot(path=OUT / f"{shot_prefix}_typing_half.png")
    page.fill("#chat-input", question)
    page.wait_for_timeout(150)
    if shot_prefix:
        page.screenshot(path=OUT / f"{shot_prefix}_typing_full.png")
    page.press("#chat-input", "Enter")
    if shot_prefix:
        page.wait_for_selector("#chat-messages .typing", timeout=5000)
        page.wait_for_timeout(250)
        page.screenshot(path=OUT / f"{shot_prefix}_thinking.png")
    wait_answer(page)
    page.wait_for_timeout(500)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        ctx = browser.new_context(viewport={"width": 1920, "height": 1080}, device_scale_factor=2, locale="tr-TR")
        page = ctx.new_page()
        page.goto(URL, wait_until="networkidle")
        page.wait_for_function("() => document.querySelector('#stat-documents').textContent.trim() !== '—'", timeout=15000)
        page.evaluate("document.fonts.ready")
        page.wait_for_timeout(600)

        # 1) ana sayfa
        page.screenshot(path=OUT / "home.png")
        box(page, "hero", ".hero")
        box(page, "stats", ".stats-row")
        box(page, "topics_panel", ".topics-panel")
        box(page, "assistant_card", ".assistant-card")
        box(page, "sidebar", ".sidebar")
        box(page, "brand", ".brand")

        # 2) konular
        page.click("[data-nav=topics].nav-item")
        page.wait_for_timeout(700)
        page.screenshot(path=OUT / "topics.png")

        # 3) boş sohbet
        page.click("[data-nav=chat].nav-item")
        page.wait_for_timeout(600)
        page.screenshot(path=OUT / "chat_empty.png")

        # 4) gerçek soru-cevap (sürüm çelişkili)
        ask(page, "İade süresi kaç gün?", shot_prefix="chat_q1")
        page.screenshot(path=OUT / "chat_q1_answer.png")
        box(page, "q1_composer", ".composer")
        box(page, "q1_answer_bubble", ".message-block.assistant .message-bubble", 0)
        box(page, "q1_user_bubble", ".message-block.user .message-bubble", 0)
        page.click(".source-disclosure summary")
        page.click(".conflict-disclosure summary")
        page.wait_for_timeout(500)
        page.screenshot(path=OUT / "chat_q1_open.png")
        box(page, "q1_sources", ".source-disclosure")
        box(page, "q1_conflict", ".conflict-disclosure")
        box(page, "q1_answer_bubble_open", ".message-block.assistant .message-bubble", 0)
        box(page, "chat_messages", "#chat-messages")

        # 5) cevapsız soru (yeni sohbet)
        page.click("#chat-new")
        page.wait_for_timeout(400)
        ask(page, "Lumora Hub Apple HomeKit ile uyumlu mu?", shot_prefix="chat_q2")
        page.screenshot(path=OUT / "chat_q2_answer.png")
        box(page, "q2_answer_bubble", ".message-block.assistant .message-bubble", 0)

        # 6) ana sayfa, sohbet geçmişi dolu
        page.click("[data-nav=home].nav-item")
        page.wait_for_timeout(700)
        page.screenshot(path=OUT / "home_after.png")

        BOXES["viewport"] = {"width": 1920, "height": 1080, "scale": 2}
        (OUT / "boxes.json").write_text(json.dumps(BOXES, indent=1), encoding="utf-8")
        browser.close()
    print("tamam:", sorted(p.name for p in OUT.glob("*.png")))


if __name__ == "__main__":
    t = time.time()
    main()
    print(f"{time.time() - t:.0f} sn")
