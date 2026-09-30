"""Değerlendirme: eval/questions.json'daki soruları servise sorar, beklenen ve gerçek çıktıyı karşılaştırır.

Kullanım:
    python -m eval.run_eval              # .env'deki ayarlarla (anahtar varsa LLM, yoksa extractive)
    python -m eval.run_eval --no-llm     # LLM'i kapat, yalnızca alıntılayan modu ölç

Çıktı: eval/results/results-<mod>.json ve results-<mod>.md
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

from app.answer import AnswerService
from app.config import Settings, get_settings
from app.retrieval import KnowledgeBase
from app.textproc import normalize

HERE = Path(__file__).parent
SPLIT_TR = {"dev": "Geliştirme seti (eşikler bu sette ayarlandı)", "heldout": "Held-out (ayarlamada kullanılmadı)"}
TYPE_TR = {"normal": "Normal", "conflict": "Çelişkili", "unanswerable": "Cevapsız"}


def check(case: dict, answer) -> list[str]:
    """Başarısızlık nedenlerini döner; boş liste = geçti."""
    exp, problems = case["expect"], []
    if answer.answerable != exp["answerable"]:
        return [f"answerable={answer.answerable}, beklenen {exp['answerable']}"]
    if not exp["answerable"]:
        if answer.sources:
            problems.append("cevapsız soruda kaynak gösterildi")
        return problems

    text = normalize(answer.answer)
    cited = {s.doc_id for s in answer.sources}
    if not cited & set(exp["doc_ids"]):
        problems.append(f"kaynak {sorted(cited)}, beklenen {exp['doc_ids']}")
    for s in exp.get("must_include", []):
        if normalize(s) not in text:
            problems.append(f"yanıtta yok: {s!r}")
    for s in exp.get("must_not_include", []):
        if normalize(s) in text:
            problems.append(f"yanıtta olmamalı: {s!r}")
    selected = exp.get("conflict_selected")
    if selected:
        if not any(c.selected_doc_id == selected for c in answer.conflicts):
            problems.append(f"çelişki raporunda seçilen sürüm {selected} değil/rapor yok")
    elif answer.conflicts:
        problems.append("beklenmeyen çelişki raporu")
    return problems


def describe_expected(exp: dict) -> str:
    if not exp["answerable"]:
        return "Cevapsız (bilgi yok), kaynak yok"
    parts = [f"doc: {', '.join(exp['doc_ids'])}"]
    if exp.get("must_include"):
        parts.append("içerir: " + ", ".join(f"«{s}»" for s in exp["must_include"]))
    if exp.get("must_not_include"):
        parts.append("içermez: " + ", ".join(f"«{s}»" for s in exp["must_not_include"]))
    if exp.get("conflict_selected"):
        parts.append(f"seçilen: {exp['conflict_selected']}")
    return "; ".join(parts)


def describe_actual(a) -> str:
    if not a.answerable:
        return f"Cevapsız ({a.mode}): {a.answer}"
    src = ", ".join(f"{s.doc_id} › {s.section}" for s in a.sources)
    out = f"{a.answer}<br>Kaynak: {src}"
    if a.conflicts:
        c = a.conflicts[0]
        out += f"<br>Çelişki: {c.selected_doc_id} seçildi, elenen: " + ", ".join(
            sorted({d.doc_id for d in c.discarded})
        )
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-llm", action="store_true", help="LLM'i kapat (extractive mod)")
    args = ap.parse_args()

    settings = get_settings()
    if args.no_llm:
        settings = Settings(_env_file=None, llm_provider="none", docs_dir=settings.docs_dir)
    service = AnswerService(KnowledgeBase(settings), settings)
    mode = "llm" if service.generator else "extractive"

    cases = json.loads((HERE / "questions.json").read_text(encoding="utf-8"))
    rows, by_type, by_split = [], defaultdict(lambda: [0, 0]), defaultdict(lambda: [0, 0])
    for case in cases:
        answer = service.ask(case["question"])
        problems = check(case, answer)
        for tally in (by_type[case["type"]], by_split[case.get("split", "dev")]):
            tally[1] += 1
            tally[0] += not problems
        rows.append({"case": case, "answer": answer, "problems": problems})

    passed = sum(1 for r in rows if not r["problems"])
    lines = [
        f"# Değerlendirme sonuçları (mod: `{mode}`" + (f", model: `{settings.llm_model}`" if mode == "llm" else "") + ")",
        "",
        f"**Genel: {passed}/{len(rows)} geçti.** "
        + " · ".join(f"{TYPE_TR[t]}: {p}/{n}" for t, (p, n) in by_type.items()),
        "",
        "Bölümler: " + " · ".join(f"{SPLIT_TR[s]}: {p}/{n}" for s, (p, n) in by_split.items()),
        "",
        "| ID | Bölüm | Tür | Soru | Beklenen | Gerçek çıktı | Sonuç |",
        "|----|-------|-----|------|----------|--------------|-------|",
    ]
    for r in rows:
        c, a = r["case"], r["answer"]
        verdict = "✅" if not r["problems"] else "❌ " + "; ".join(r["problems"])
        lines.append(
            f"| {c['id']} | {c.get('split', 'dev')} | {TYPE_TR[c['type']]} | {c['question']} | {describe_expected(c['expect'])} "
            f"| {describe_actual(a)} | {verdict} |"
        )

    out_dir = HERE / "results"
    out_dir.mkdir(exist_ok=True)
    (out_dir / f"results-{mode}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out_dir / f"results-{mode}.json").write_text(
        json.dumps(
            [
                {
                    "id": r["case"]["id"],
                    "type": r["case"]["type"],
                    "question": r["case"]["question"],
                    "expected": r["case"]["expect"],
                    "actual": {
                        "answerable": r["answer"].answerable,
                        "answer": r["answer"].answer,
                        "mode": r["answer"].mode,
                        "sources": [f"{s.doc_id}#{s.section}" for s in r["answer"].sources],
                        "conflict_selected": [c.selected_doc_id for c in r["answer"].conflicts],
                        "retrieval": r["answer"].retrieval,
                    },
                    "passed": not r["problems"],
                    "problems": r["problems"],
                }
                for r in rows
            ],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"mod={mode}  {passed}/{len(rows)} geçti  (" + ", ".join(f"{t}: {p}/{n}" for t, (p, n) in by_type.items()) + ")")
    print("bölümler: " + ", ".join(f"{s}: {p}/{n}" for s, (p, n) in by_split.items()))
    for r in rows:
        if r["problems"]:
            print(f"  ✗ {r['case']['id']} {r['case']['question']} -> {'; '.join(r['problems'])}")


if __name__ == "__main__":
    main()
