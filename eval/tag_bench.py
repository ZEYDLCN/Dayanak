"""Eş anlamlı etiket ölçümü (LLM'siz): doğru bölüm kaçıncı sırada, cevapsız sorular kapıdan geçiyor mu?

Kullanım:  python -m eval.tag_bench --cases synonym_cases.json,hybrid_cases.json,refusal_cases.json
(altın bölümü olmayan vakalar yalnızca kapı davranışı için sayılır)
"""

import argparse
import json
from pathlib import Path

from app.config import Settings
from app.retrieval import KnowledgeBase

HERE = Path(__file__).parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default="synonym_cases.json")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    kb = KnowledgeBase(Settings(_env_file=None, llm_provider="none"))
    tot = {"n": 0, "h1": 0, "h2": 0, "h4": 0, "gate_miss": 0, "un": 0, "un_pass": 0}
    for name in args.cases.split(","):
        for c in json.loads((HERE / name).read_text(encoding="utf-8")):
            r = kb.retrieve(c["q"])
            ids = [h.chunk.chunk_id for h in r.hits]
            if c["expect"].get("answerable") is False:
                tot["un"] += 1
                tot["un_pass"] += bool(r.plausible)
                continue
            gold = c.get("gold")
            if not gold:
                continue
            pos = next((i for i, x in enumerate(ids) if x in gold), None)
            tot["n"] += 1
            tot["h1"] += pos == 0
            tot["h2"] += pos is not None and pos < 2
            tot["h4"] += pos is not None and pos < 4
            tot["gate_miss"] += not r.plausible
            if not args.quiet and (pos is None or pos > 1):
                print(f"  {c['id']:4} gold@{pos} plausible={r.plausible} {c['q'][:60]}")
    n = max(tot["n"], 1)
    print(f"etiketli={tot['n']}  hit@1={tot['h1']/n:.3f}  hit@2={tot['h2']/n:.3f}  hit@4={tot['h4']/n:.3f}  kapida elenen={tot['gate_miss']}  "
          f"cevapsiz={tot['un']} LLM'e gecen={tot['un_pass']}")


if __name__ == "__main__":
    main()
