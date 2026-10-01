"""Arama (retrieval) karşılaştırması: BM25 ↔ hibrit (farklı gömme modelleriyle). LLM gerekmez.

Ölçülenler (her model için, gerçek KnowledgeBase.retrieve hattı üzerinden):
  - doğruluk: doğru bölümün ilk 1/2/4'e girme oranı ve MRR (sürüm çözümünden SONRA)
  - hız: sorgu başına retrieve() gecikmesi (p50/p90/p99), yalnızca gömme gecikmesi, soğuk/sıcak başlangıç
  - tekrarlanabilirlik: aynı sorular N kez sorulduğunda sıralama değişiyor mu?
  - anlamsal kapı kalibrasyonu: sözcük kapısının kaçırdığı kaç cevaplanabilir soruyu kurtarır, kaç cevapsız sızar?

Kullanım:
    python -m eval.retrieval_bench --models bm25,sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
"""

import argparse
import json
import shutil
import statistics
import time
from pathlib import Path

import numpy as np

from app.config import Settings
from app.retrieval import KnowledgeBase
from app.textproc import normalize

HERE = Path(__file__).parent
SUITES = ("questions.json", "qa_cases.json", "hybrid_cases.json")


def load_items():
    seen, items = set(), []
    for name in SUITES:
        for c in json.loads((HERE / name).read_text(encoding="utf-8")):
            e = c["expect"]
            if "answerable" not in e:
                continue
            q = c.get("question") or c["q"]
            key = normalize(q)
            if key in seen:
                continue
            seen.add(key)
            must = list(e.get("must_include", [])) + list(e.get("all", [])) + [x for g in e.get("any", []) for x in g]
            items.append({"id": c["id"], "suite": name, "q": q, "ans": e["answerable"], "docs": e.get("doc_ids") or e.get("docs") or [], "must": must})
    return items


def gold_chunks(kb, it):
    """Beklenen ifadeyi içeren GÜNCEL bölümler (en fazla 3; belirsizse soru ölçüme alınmaz)."""
    if not it["ans"] or not it["must"]:
        return None
    docs = set(it["docs"])
    gold = set()
    for c in kb.chunks:
        if c.doc.status != "current":
            continue
        if docs and not (c.doc.doc_id in docs or c.doc.family in docs or any(d.startswith(c.doc.family) for d in docs)):
            continue
        text = normalize(c.text).replace("*", "")
        if any(normalize(m).replace("*", "") in text for m in it["must"]):
            gold.add(c.chunk_id)
    return gold if 1 <= len(gold) <= 3 else None


def pct(values, p):
    return float(np.percentile(values, p)) if len(values) else float("nan")


def auc(pos, neg):
    allv = sorted([(v, 1) for v in pos] + [(v, 0) for v in neg])
    rank_sum = sum(i + 1 for i, (_, y) in enumerate(allv) if y == 1)
    return (rank_sum - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)) if pos and neg else float("nan")


def make_kb(model, cache_dir):
    if model == "bm25":
        return KnowledgeBase(Settings(_env_file=None, llm_provider="none", retriever="bm25"))
    kb = KnowledgeBase(Settings(_env_file=None, llm_provider="none", retriever="hybrid", embedding_model=model, cache_dir=cache_dir))
    if kb.hybrid is None:
        raise RuntimeError("gömme modeli yüklenemedi")
    return kb


def evaluate(model, items, passes, model_cache):
    row = {"model": model}
    # soğuk başlangıç: model yükleme + bölüm gömme (boş önbellek); sıcak: önbellekten
    try:
        if model != "bm25":
            make_kb(model, model_cache)  # indirme ve ilk yükleme ölçüme girmesin
            shutil.rmtree(model_cache / "embeddings", ignore_errors=True)  # yalnızca bölüm-gömme önbelleğini boşalt
        cache = model_cache if model != "bm25" else None
        t0 = time.perf_counter()
        kb = make_kb(model, cache)  # soğuk: model yükleme + bölümleri gömme
        row["cold_start_s"] = time.perf_counter() - t0
        t0 = time.perf_counter()
        kb = make_kb(model, cache)  # sıcak: model yükleme + önbellekten okuma
        row["warm_start_s"] = time.perf_counter() - t0
    except Exception as exc:
        row["error"] = str(exc)[:120]
        return row

    golds = {it["id"]: gold_chunks(kb, it) for it in items}
    scored = [it for it in items if golds[it["id"]]]
    # ısınma
    for it in items[:5]:
        kb.retrieve(it["q"])

    snapshots, lat, positions = [], [], {}
    for p in range(passes):
        snap = {}
        for it in items:
            t0 = time.perf_counter()
            r = kb.retrieve(it["q"])
            lat.append((time.perf_counter() - t0) * 1000)
            snap[it["id"]] = tuple(h.chunk.chunk_id for h in r.hits)
        snapshots.append(snap)
    row["nondeterministic_questions"] = sum(1 for it in items if len({s[it["id"]] for s in snapshots}) > 1)

    for it in scored:
        ids = snapshots[0][it["id"]]
        pos = next((i for i, cid in enumerate(ids) if cid in golds[it["id"]]), None)
        positions[it["id"]] = pos

    def hit(k, subset):
        sel = [positions[i["id"]] for i in subset]
        return sum(1 for p in sel if p is not None and p < k) / len(sel) if sel else float("nan")

    def mrr(subset):
        sel = [positions[i["id"]] for i in subset]
        return float(np.mean([1 / (p + 1) if p is not None else 0 for p in sel])) if sel else float("nan")

    fresh = [it for it in scored if it["suite"] == "hybrid_cases.json"]
    old = [it for it in scored if it["suite"] != "hybrid_cases.json"]
    row.update(
        n=len(scored), n_fresh=len(fresh),
        hit1=hit(1, scored), hit2=hit(2, scored), hit4=hit(4, scored), mrr=mrr(scored),
        fresh_hit2=hit(2, fresh), fresh_mrr=mrr(fresh), old_hit2=hit(2, old),
        lat_p50=pct(lat, 50), lat_p90=pct(lat, 90), lat_p99=pct(lat, 99), lat_max=max(lat),
    )
    if kb.hybrid:
        q_lat = []
        for _ in range(passes):
            for it in items:
                t0 = time.perf_counter()
                kb.hybrid.embedder.embed_query(it["q"])
                q_lat.append((time.perf_counter() - t0) * 1000)
        row["embed_p50"], row["embed_p90"] = pct(q_lat, 50), pct(q_lat, 90)
        # anlamsal kapı kalibrasyonu
        cfg = kb.settings
        recs = []
        for it in items:
            r = kb.retrieve(it["q"])
            lex_ok = bool(r.hits) and (r.top_score >= cfg.min_score or r.top_coverage >= cfg.min_coverage)
            recs.append((it["ans"], lex_ok, r.top_semantic))
        ans_closed = [s for a, ok, s in recs if a and not ok]
        un_closed = [s for a, ok, s in recs if (not a) and not ok]
        row["gate_answerable_missed_by_lexical"] = len(ans_closed)
        row["gate_unanswerable_closed"] = len(un_closed)
        row["sem_auc"] = auc([s for a, _, s in recs if a], [s for a, _, s in recs if not a])
        best = None
        for t in np.arange(0.15, 0.95, 0.01):
            gain = sum(1 for s in ans_closed if s >= t)
            leak = sum(1 for s in un_closed if s >= t)
            if un_closed and leak / len(un_closed) <= 0.20 and gain > 0 and (best is None or gain > best[1]):
                best = (round(float(t), 2), gain, leak)
        row["gate_best"] = best  # (esik, kurtarilan cevaplanabilir, sizan cevapsiz)
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="bm25,sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    ap.add_argument("--passes", type=int, default=5)
    ap.add_argument("--out", default="retrieval-bench")
    args = ap.parse_args()

    items = load_items()
    model_cache = Path(__file__).resolve().parent.parent / ".cache"
    rows = [evaluate(m.strip(), items, args.passes, model_cache) for m in args.models.split(",")]

    lines = [f"# Arama karşılaştırması ({len(items)} soru; {args.passes} tekrar)", "",
             "| Model | n | hit@1 | hit@2 | hit@4 | MRR | yeni-20 hit@2 | arama p50 / p90 / p99 (ms) | gömme p50 (ms) | soğuk / sıcak başlangıç (sn) | sıralama değişen soru |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        if "error" in r:
            lines.append(f"| {r['model']} | — | yüklenemedi: {r['error']} |")
            continue
        lines.append(
            f"| `{r['model']}` | {r['n']} | {r['hit1']:.3f} | {r['hit2']:.3f} | {r['hit4']:.3f} | {r['mrr']:.3f} | {r['fresh_hit2']:.2f} ({r['n_fresh']}) "
            f"| {r['lat_p50']:.1f} / {r['lat_p90']:.1f} / {r['lat_p99']:.1f} | {r.get('embed_p50', 0):.1f} "
            f"| {r['cold_start_s']:.1f} / {r['warm_start_s']:.2f} | {r['nondeterministic_questions']} |"
        )
    lines += ["", "## Anlamsal kapı kalibrasyonu (sözcük kapısı kapalıyken)", "",
              "| Model | sözcükle kaçırılan cevaplanabilir | sözcükle kapalı cevapsız | AUC (cevaplanabilir↔cevapsız) | önerilen eşik → kurtarılan / sızan |", "|---|---|---|---|---|"]
    for r in rows:
        if "gate_best" in r:
            b = r["gate_best"]
            lines.append(f"| `{r['model']}` | {r['gate_answerable_missed_by_lexical']} | {r['gate_unanswerable_closed']} | {r['sem_auc']:.3f} | "
                         + (f"≥{b[0]} → {b[1]} / {b[2]}" if b else "fayda yok (kapalı bırak)") + " |")
    text = "\n".join(lines) + "\n"
    (HERE / "results" / "hybrid").mkdir(parents=True, exist_ok=True)
    (HERE / "results" / "hybrid" / f"{args.out}.md").write_text(text, encoding="utf-8")
    (HERE / "results" / "hybrid" / f"{args.out}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
