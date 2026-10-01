"""Uçtan uca (LLM'li) arama karşılaştırması: eval/results/qa-*-e2e-<ad>.json dosyalarını tek tabloda toplar.

Kullanım:  python -m eval.e2e_compare --names bm25,minilm,potion,mpnet,e5large
Önce her yapılandırma için:  RETRIEVER=... EMBEDDING_MODEL=... python -m eval.qa_run --cases hybrid_cases.json --repeat 3 --tag e2e-<ad>
"""

import argparse
import glob
import json
import statistics
from pathlib import Path

HERE = Path(__file__).parent
RES = HERE / "results" / "hybrid"


def load(name):
    files = glob.glob(str(RES / f"qa-*-e2e-{name}.json"))
    return json.loads(Path(files[0]).read_text(encoding="utf-8")) if files else None


def ok(run):
    return not run["problems"] and not run["grounding_fail"] and run["mode"] != "extractive-fallback"


def pct(v, p):
    s = sorted(v)
    return s[min(len(s) - 1, int(len(s) * p / 100))] if s else float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--names", default="bm25,minilm,potion,mpnet,e5large")
    ap.add_argument("--out", default="hybrid-e2e")
    args = ap.parse_args()
    names = args.names.split(",")
    data = {n: load(n) for n in names}
    data = {n: d for n, d in data.items() if d}
    rows, per_case = [], {}
    for n, d in data.items():
        runs = [(c, r) for c in d for r in c["runs"]]
        passed = sum(ok(r) for _, r in runs)
        fab = sum(1 for c, r in runs if c["expect"].get("answerable") is False and r["answerable"])
        refuse = sum(1 for c, r in runs if c["expect"].get("answerable") is True and not r["answerable"])
        wrong = sum(1 for c, r in runs if c["expect"].get("answerable") is True and r["answerable"] and (r["problems"] or r["grounding_fail"]))
        tot = [r["seconds"] for _, r in runs if r["mode"] in ("llm", "llm-rejected")]
        ret = [r["retrieval"].get("retrieval_ms") for _, r in runs if r["retrieval"].get("retrieval_ms") is not None]
        rows.append((n, len(runs), passed, fab, refuse, wrong, statistics.median(tot) if tot else float("nan"), pct(tot, 90),
                     statistics.median(ret) if ret else float("nan"), pct(ret, 90)))
        for c in d:
            per_case.setdefault(c["id"], {"q": c["q"], "cat": c["cat"]})[n] = sum(ok(r) for r in c["runs"])
    lines = ["# Uçtan uca arama karşılaştırması (gerçek LLM: gpt-oss-20b)", "",
             "| Yapılandırma | koşu | geçen | uydurma | gereksiz ret | yanlış içerik | uçtan uca medyan / p90 (sn) | arama medyan / p90 (ms) |", "|---|---|---|---|---|---|---|---|"]
    for n, total, passed, fab, refuse, wrong, m, p9, rm, rp9 in rows:
        lines.append(f"| `{n}` | {total} | **{passed}** | {fab} | {refuse} | {wrong} | {m:.2f} / {p9:.2f} | {rm:.1f} / {rp9:.1f} |")
    lines += ["", "## Vaka bazında (tekrarlardan kaçı geçti)", "", "| ID | Kategori | Soru | " + " | ".join(data) + " |", "|---|---|---|" + "---|" * len(data)]
    for cid, info in sorted(per_case.items()):
        lines.append(f"| {cid} | {info['cat']} | {info['q']} | " + " | ".join(str(info.get(n, "—")) for n in data) + " |")
    text = "\n".join(lines) + "\n"
    (RES / f"{args.out}.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
