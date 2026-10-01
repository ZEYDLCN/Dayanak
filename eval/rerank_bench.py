"""Reranker (cross-encoder) karşılaştırması: BM25 ↔ BM25 + reranker. LLM gerekmez.

Senaryolar:
  A) BM25'in (sürüm çözümünden sonraki) ilk 8 adayını yeniden sırala
  B) bütün güncel bölümleri yeniden sırala (korpus küçük olduğu için mümkün)
Ölçülenler: hit@1/2/4, MRR (67 etiketli soru), reranker çağrı gecikmesi (p50/p90), model yükleme süresi,
            ve en iyi reranker skorunun "cevaplanabilir ↔ cevapsız" ayırma gücü (AUC) + önerilen eşik.

Kullanım:  python -m eval.rerank_bench --models jinaai/jina-reranker-v2-base-multilingual,BAAI/bge-reranker-base
"""

import argparse
import json
import time
from pathlib import Path

import numpy as np

from app.config import Settings
from app.retrieval import KnowledgeBase
from eval.retrieval_bench import auc, gold_chunks, load_items, pct

HERE = Path(__file__).parent
CACHE = HERE.parent / ".cache" / "fastembed"


def load_reranker(name):
    from fastembed.rerank.cross_encoder import TextCrossEncoder

    t0 = time.perf_counter()
    model = TextCrossEncoder(model_name=name, cache_dir=str(CACHE))
    list(model.rerank("ısınma", ["ısınma metni"]))
    return model, time.perf_counter() - t0


def evaluate(name, items, kb8, kb_all, passes):
    model, load_s = load_reranker(name)
    golds = {it["id"]: gold_chunks(kb_all, it) for it in items}
    scored = [it for it in items if golds[it["id"]]]
    row = {"model": name, "load_s": load_s}
    current = [c for c in kb_all.chunks if c.doc.status == "current"]

    def rank_a(q):
        hits = kb8.retrieve(q).hits
        if not hits:
            return [], []
        scores = list(model.rerank(q, [h.chunk.index_text for h in hits]))
        order = sorted(range(len(hits)), key=lambda i: -scores[i])
        return [hits[i].chunk.chunk_id for i in order], [float(scores[i]) for i in order]

    def rank_b(q):
        scores = list(model.rerank(q, [c.index_text for c in current]))
        order = sorted(range(len(current)), key=lambda i: -scores[i])
        return [current[i].chunk_id for i in order], [float(scores[i]) for i in order]

    for label, fn in (("A", rank_a), ("B", rank_b)):
        lat, pos, top_scores = [], {}, {}
        for p in range(passes):
            for it in items:
                t0 = time.perf_counter()
                ids, sc = fn(it["q"])
                lat.append((time.perf_counter() - t0) * 1000)
                if p == 0:
                    top_scores[it["id"]] = sc[0] if sc else -99.0
                    if golds[it["id"]]:
                        pos[it["id"]] = next((i for i, c in enumerate(ids) if c in golds[it["id"]]), None)
        sel = [pos[i["id"]] for i in scored]
        row[label] = {
            "hit1": sum(1 for x in sel if x is not None and x < 1) / len(sel),
            "hit2": sum(1 for x in sel if x is not None and x < 2) / len(sel),
            "hit4": sum(1 for x in sel if x is not None and x < 4) / len(sel),
            "mrr": float(np.mean([1 / (x + 1) if x is not None else 0 for x in sel])),
            "p50": pct(lat, 50), "p90": pct(lat, 90),
            "auc": auc([top_scores[i["id"]] for i in items if i["ans"]], [top_scores[i["id"]] for i in items if not i["ans"]]),
            "scores_ans": [top_scores[i["id"]] for i in items if i["ans"]],
            "scores_un": [top_scores[i["id"]] for i in items if not i["ans"]],
        }
        # eşik: cevapsızların en fazla %15'inin geçtiği en düşük eşikte cevaplanabilirlerin kaçı geçer?
        un = np.array(row[label]["scores_un"]); an = np.array(row[label]["scores_ans"])
        best = None
        for t in np.unique(np.concatenate([an, un])):
            leak = float((un >= t).mean()); rec = float((an >= t).mean())
            if leak <= 0.15 and (best is None or rec > best[1]):
                best = (float(t), rec, leak)
        row[label]["gate"] = best
    row["n"] = len(scored)
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="jinaai/jina-reranker-v2-base-multilingual,BAAI/bge-reranker-base")
    ap.add_argument("--passes", type=int, default=3)
    ap.add_argument("--out", default="rerank-bench")
    args = ap.parse_args()
    items = load_items()
    kb_all = KnowledgeBase(Settings(_env_file=None, llm_provider="none"))
    kb8 = KnowledgeBase(Settings(_env_file=None, llm_provider="none", top_k=8))

    # taban çizgi: BM25
    golds = {it["id"]: gold_chunks(kb_all, it) for it in items}
    scored = [it for it in items if golds[it["id"]]]
    pos = [next((i for i, h in enumerate(kb_all.retrieve(it["q"]).hits) if h.chunk.chunk_id in golds[it["id"]]), None) for it in scored]
    base = {
        "hit1": sum(1 for x in pos if x is not None and x < 1) / len(pos), "hit2": sum(1 for x in pos if x is not None and x < 2) / len(pos),
        "hit4": sum(1 for x in pos if x is not None and x < 4) / len(pos), "mrr": float(np.mean([1 / (x + 1) if x is not None else 0 for x in pos])),
    }
    rows = [evaluate(m.strip(), items, kb8, kb_all, args.passes) for m in args.models.split(",")]

    L = [f"# Reranker karşılaştırması ({len(items)} soru; {rows[0]['n']} etiketli; {args.passes} tekrar)", "",
         "| Yöntem | hit@1 | hit@2 | hit@4 | MRR | reranker p50 / p90 (ms) | model yükleme (sn) |", "|---|---|---|---|---|---|---|",
         f"| **BM25 (taban)** | {base['hit1']:.3f} | {base['hit2']:.3f} | {base['hit4']:.3f} | {base['mrr']:.3f} | 0 | 0 |"]
    for r in rows:
        for label, desc in (("A", "BM25 ilk 8 → rerank"), ("B", "tüm bölümler → rerank")):
            x = r[label]
            L.append(f"| `{r['model'].split('/')[-1]}` — {desc} | {x['hit1']:.3f} | {x['hit2']:.3f} | {x['hit4']:.3f} | {x['mrr']:.3f} | {x['p50']:.0f} / {x['p90']:.0f} | {r['load_s']:.1f} |")
    L += ["", "## En iyi reranker skoru ile \"bilgi var / yok\" ayrımı", "", "| Model / senaryo | AUC | cevapsızların ≤%15'i geçerken cevaplanabilirlerin geçen oranı (eşik) |", "|---|---|---|"]
    for r in rows:
        for label in ("A", "B"):
            x = r[label]
            g = x["gate"]
            L.append(f"| `{r['model'].split('/')[-1]}` {label} | {x['auc']:.3f} | " + (f"%{g[1]*100:.0f} (eşik {g[0]:.2f}, sızan %{g[2]*100:.0f})" if g else "yok") + " |")
    text = "\n".join(L) + "\n"
    out = HERE / "results" / "hybrid"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{args.out}.md").write_text(text, encoding="utf-8")
    (out / f"{args.out}.json").write_text(json.dumps({"baseline": base, "rows": rows}, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
