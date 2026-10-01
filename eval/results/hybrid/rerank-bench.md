# Reranker karşılaştırması (104 soru; 67 etiketli; 1 tekrar)

| Yöntem | hit@1 | hit@2 | hit@4 | MRR | reranker p50 / p90 (ms) | model yükleme (sn) |
|---|---|---|---|---|---|---|
| **BM25 (taban)** | 0.821 | 0.866 | 0.881 | 0.848 | 0 | 0 |
| `jina-reranker-v2-base-multilingual` — BM25 ilk 8 → rerank | 0.881 | 0.925 | 0.925 | 0.903 | 741 / 1193 | 9.5 |
| `jina-reranker-v2-base-multilingual` — tüm bölümler → rerank | 0.925 | 0.970 | 1.000 | 0.956 | 4776 / 5023 | 9.5 |

## En iyi reranker skoru ile "bilgi var / yok" ayrımı

| Model / senaryo | AUC | cevapsızların ≤%15'i geçerken cevaplanabilirlerin geçen oranı (eşik) |
|---|---|---|
| `jina-reranker-v2-base-multilingual` A | 0.783 | %56 (eşik -0.29, sızan %13) |
| `jina-reranker-v2-base-multilingual` B | 0.799 | %53 (eşik 0.08, sızan %11) |
