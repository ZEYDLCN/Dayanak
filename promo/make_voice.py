"""Seslendirmeyi üretir (edge-tts, Türkçe nöral ses) ve sahne başına süreleri promo/build/durations.json'a yazar."""

import asyncio
import json
import sys
from pathlib import Path

import edge_tts
from moviepy import AudioFileClip

sys.path.insert(0, str(Path(__file__).parent))
from script import NARRATION, RATE, VOICE  # noqa: E402

BUILD = Path(__file__).parent / "build"
BUILD.mkdir(exist_ok=True)


async def main() -> None:
    durations = []
    for i, text in enumerate(NARRATION, start=1):
        out = BUILD / f"voice_{i}.mp3"
        await edge_tts.Communicate(text, VOICE, rate=RATE).save(str(out))
        with AudioFileClip(str(out)) as clip:
            durations.append(round(clip.duration, 3))
        print(f"sahne {i}: {durations[-1]:.2f} sn  {text[:60]}...")
    (BUILD / "durations.json").write_text(json.dumps(durations), encoding="utf-8")
    print(f"toplam konuşma: {sum(durations):.1f} sn")


if __name__ == "__main__":
    asyncio.run(main())
