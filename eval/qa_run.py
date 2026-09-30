"""QA: gerçek LLM sağlayıcısına karşı uçtan uca, halüsinasyon odaklı sınama.

Sistemden BAĞIMSIZ bir "grounding bekçisi" her yanıtı kaynak metnine karşı denetler:
  - yanıttaki her sayı/saat, gösterilen kaynaklarda geçiyor mu? (geçmiyorsa HALÜSİNASYON)
  - cevapsız yanıt iddia (rakam) taşıyor mu?
  - yanıt kendi içinde çelişiyor mu (answerable=true ama "bilgi yok" diyor)?

Kullanım:
    python -m eval.qa_run                 # .env'deki sağlayıcı
    python -m eval.qa_run --no-llm        # alıntılayan mod
    python -m eval.qa_run --repeat 3      # her soruyu 3 kez sor (tutarlılık)
"""

import argparse
import json
import re
import statistics
import time
from pathlib import Path

from app.answer import AnswerService
from app.config import Settings, get_settings
from app.retrieval import KnowledgeBase
from app.textproc import normalize

HERE = Path(__file__).parent
_NUM = re.compile(r"\d+(?:[.,:]\d+)*")
_NOTE = re.compile(r"\s*\(Not:.*?\)\s*$", re.DOTALL)
_NOINFO = re.compile(r"yeterli bilgi|bilgi bulunmuyor|bilgi yok|bulunmamaktadir|belirtilmemis|yer almiyor")


def numbers(text: str) -> set[str]:
    return {n.rstrip(".,:") for n in _NUM.findall(normalize(text))}


def grounding_flags(question: str, a) -> tuple[list[str], list[str]]:
    """(HATA bayrakları, İNCELE bayrakları)"""
    fails, review = [], []
    body = _NOTE.sub("", a.answer)
    if a.answerable and a.mode == "version-comparison":
        # Eski ve güncel sürümü bilerek yan yana gösterir: superseded kaynak beklenir, sürüm/tarih etiketleri sayı taşır
        src_text = " ".join(f"{s.snippet} {s.version} {s.effective_date.isoformat()}" for s in a.sources)
        real = numbers(body) - numbers(src_text) - numbers(question)
        if real:
            fails.append(f"KAYNAKTA OLMAYAN SAYI: {sorted(real)}")
    elif a.answerable:
        src_text = " ".join(s.snippet for s in a.sources)
        ungrounded = numbers(body) - numbers(src_text)
        echoed = ungrounded & numbers(question)
        real = ungrounded - echoed
        if real:
            fails.append(f"KAYNAKTA OLMAYAN SAYI: {sorted(real)}")
        if echoed:
            review.append(f"sorudaki sayı yanıtta tekrarlandı ama kaynakta yok: {sorted(echoed)}")
        sentences = [s for s in re.split(r"(?<=[.!?])\s+", normalize(body)) if s.strip()]
        if sentences and all(_NOINFO.search(s) for s in sentences):  # kısmi yanıt ("...Bluetooth için bilgi yok") meşru
            fails.append("answerable=true ama yanıtın tamamı 'bilgi yok' diyor (çelişki)")
        if not a.sources:
            fails.append("answerable=true ama kaynak yok")
        stale = [s.doc_id for s in a.sources if s.status != "current"]
        if stale:
            fails.append(f"eski sürüm kaynak gösterildi: {stale}")
    else:
        if numbers(body):
            fails.append(f"cevapsız yanıtta rakam var: {sorted(numbers(body))}")
        if a.sources:
            fails.append("cevapsız yanıtta kaynak gösterildi")
    return fails, review


def check(case: dict, a) -> list[str]:
    exp, problems = case["expect"], []
    if "answerable" in exp and a.answerable != exp["answerable"]:
        problems.append(f"answerable={a.answerable}, beklenen {exp['answerable']}")
        return problems
    text = normalize(a.answer).replace("*", "")  # **kalın** işaretini yok say
    if exp.get("docs") and a.answerable and not {s.doc_id for s in a.sources} & set(exp["docs"]):
        problems.append(f"kaynak {sorted({s.doc_id for s in a.sources})}, beklenen {exp['docs']}")
    for s in exp.get("all", []):
        if normalize(s) not in text:
            problems.append(f"yanıtta yok: {s!r}")
    for group in exp.get("any", []):
        if not any(normalize(s) in text for s in group):
            problems.append(f"şunlardan biri yok: {group}")
    for s in exp.get("none", []):
        if normalize(s) in text:
            problems.append(f"yanıtta olmamalı: {s!r}")
    return problems


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-llm", action="store_true")
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--pause", type=float, default=1.5, help="istekler arası bekleme (rate limit)")
    ap.add_argument("--only", help="virgülle ayrılmış vaka id'leri")
    ap.add_argument("--fail-under", type=int, default=0, help="geçen koşu sayısı bunun altındaysa çıkış kodu 1")
    ap.add_argument("--max-hallucinations", type=int, default=-1, help="kaynakta olmayan sayı içeren koşu sayısı bunu aşarsa çıkış kodu 1")
    ap.add_argument("--tag", default="", help="çıktı dosya adına eklenir (deney adı)")
    args = ap.parse_args()

    settings = get_settings()
    if args.no_llm:
        settings = Settings(_env_file=None, llm_provider="none", docs_dir=settings.docs_dir)
    svc = AnswerService(KnowledgeBase(settings), settings)
    provider = "extractive" if not svc.generator else f"{settings.llm_provider}-{getattr(svc.generator, 'model', '?').replace('/', '_')}"

    if args.tag:
        provider += f"-{args.tag}"
    cases = json.loads((HERE / "qa_cases.json").read_text(encoding="utf-8"))
    if args.only:
        wanted = set(args.only.split(","))
        cases = [c for c in cases if c["id"] in wanted]

    rows, latencies = [], []
    for case in cases:
        runs = []
        for _ in range(args.repeat):
            t0 = time.perf_counter()
            a = svc.ask(case["q"])
            dt = time.perf_counter() - t0
            latencies.append(dt)
            fails, review = grounding_flags(case["q"], a)
            problems = check(case, a)
            runs.append({"a": a, "dt": dt, "problems": problems, "fails": fails, "review": review})
            if svc.generator:
                time.sleep(args.pause)
        rows.append({"case": case, "runs": runs})

    def run_ok(r):
        return not r["problems"] and not r["fails"] and r["a"].mode != "extractive-fallback"

    total_runs = sum(len(r["runs"]) for r in rows)
    ok_runs = sum(run_ok(x) for r in rows for x in r["runs"])
    llm_errors = sum(x["a"].mode == "extractive-fallback" for r in rows for x in r["runs"])
    guard_rejects = sum(x["a"].mode == "llm-rejected" for r in rows for x in r["runs"])
    halluc = sum(any("KAYNAKTA OLMAYAN" in f for f in x["fails"]) for r in rows for x in r["runs"])
    stable = sum(
        len({(x["a"].answerable, tuple(sorted(s.doc_id + s.section for s in x["a"].sources))) for x in r["runs"]}) == 1
        for r in rows
    )

    lines = [
        f"# QA sonuçları — `{provider}`",
        "",
        f"- Vaka: {len(rows)} · koşu: {total_runs} · **geçen koşu: {ok_runs}/{total_runs}**",
        f"- Kaynakta olmayan sayı (halüsinasyon bayrağı): **{halluc}** koşu",
        f"- LLM hatası → extractive'e düşen koşu: {llm_errors}",
        f"- Dayanak korumasının reddettiği (uydurma sayı içeren) LLM yanıtı: {guard_rejects} koşu",
        f"- Tutarlılık (aynı soru → aynı cevaplanabilirlik+kaynak): {stable}/{len(rows)} vaka",
        f"- Gecikme: medyan {statistics.median(latencies):.2f}s · maks {max(latencies):.2f}s",
        "",
        "| ID | Kategori | Soru | Beklenen | Yanıt (ilk koşu) | Kaynak | Sonuç |",
        "|----|----------|------|----------|------------------|--------|-------|",
    ]
    for r in rows:
        c, x = r["case"], r["runs"][0]
        a = x["a"]
        exp = c["expect"]
        exp_txt = ("cevapsız" if exp.get("answerable") is False else "cevaplanır") + (
            f"; içerir: {exp['all']}" if exp.get("all") else ""
        ) + (f"; içermez: {exp['none']}" if exp.get("none") else "")
        verdicts = []
        for i, y in enumerate(r["runs"], 1):
            v = "✅" if run_ok(y) else "❌ " + "; ".join(y["problems"] + y["fails"] + (["LLM hatası"] if y["a"].mode == "extractive-fallback" else []))
            if y["review"]:
                v += " ⚠ " + "; ".join(y["review"])
            verdicts.append(v if len(r["runs"]) == 1 else f"#{i} {v}")
        src = ", ".join(f"{s.doc_id}›{s.section}" for s in a.sources) or "—"
        lines.append(
            f"| {c['id']} | {c['cat']} | {c['q']} | {exp_txt} | {a.answer.replace('|', '/')} | {src} | {'<br>'.join(verdicts)} |"
        )

    out = HERE / "results"
    out.mkdir(exist_ok=True)
    (out / f"qa-{provider}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out / f"qa-{provider}.json").write_text(
        json.dumps(
            [
                {
                    "id": r["case"]["id"], "cat": r["case"]["cat"], "q": r["case"]["q"], "expect": r["case"]["expect"],
                    "runs": [
                        {
                            "answerable": x["a"].answerable, "answer": x["a"].answer, "mode": x["a"].mode,
                            "sources": [f"{s.doc_id}#{s.section}" for s in x["a"].sources],
                            "retrieval": x["a"].retrieval, "seconds": round(x["dt"], 2),
                            "problems": x["problems"], "grounding_fail": x["fails"], "review": x["review"],
                        }
                        for x in r["runs"]
                    ],
                }
                for r in rows
            ],
            ensure_ascii=False, indent=2,
        ),
        encoding="utf-8",
    )
    print(f"{provider}: geçen {ok_runs}/{total_runs} · halüsinasyon bayrağı {halluc} · LLM hatası {llm_errors} · "
          f"tutarlı {stable}/{len(rows)} · medyan {statistics.median(latencies):.1f}s")
    for r in rows:
        for i, x in enumerate(r["runs"], 1):
            if not run_ok(x):
                reasons = x["problems"] + x["fails"] + (["LLM hatası"] if x["a"].mode == "extractive-fallback" else [])
                print(f"  ✗ {r['case']['id']}#{i} {r['case']['q']!r} -> {'; '.join(reasons)}")
    if ok_runs < args.fail_under:
        raise SystemExit(f"REGRESYON: geçen koşu {ok_runs} < {args.fail_under}")
    if 0 <= args.max_hallucinations < halluc:
        raise SystemExit(f"REGRESYON: halüsinasyon bayrağı {halluc} > {args.max_hallucinations}")


if __name__ == "__main__":
    main()
