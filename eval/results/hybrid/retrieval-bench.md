# Arama karşılaştırması (104 soru; 5 tekrar)

| Model | n | hit@1 | hit@2 | hit@4 | MRR | yeni-20 hit@2 | arama p50 / p90 / p99 (ms) | gömme p50 (ms) | soğuk / sıcak başlangıç (sn) | sıralama değişen soru |
|---|---|---|---|---|---|---|---|---|---|---|
| `bm25` | 67 | 0.866 | 0.910 | 0.925 | 0.893 | 0.73 (15) | 0.1 / 0.2 / 0.5 | 0.0 | 0.0 / 0.01 | 0 |
| `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | 67 | 0.821 | 0.910 | 0.940 | 0.874 | 0.73 (15) | 7.0 / 9.5 / 13.3 | 6.5 | 3.0 / 1.70 | 0 |
| `minishlab/potion-multilingual-128M` | 67 | 0.836 | 0.925 | 0.925 | 0.881 | 0.67 (15) | 0.6 / 0.8 / 1.2 | 0.3 | 2.6 / 3.32 | 0 |
| `sentence-transformers/paraphrase-multilingual-mpnet-base-v2` | 67 | 0.866 | 0.910 | 0.925 | 0.893 | 0.67 (15) | 21.8 / 25.3 / 29.8 | 21.0 | 7.1 / 5.91 | 0 |
| `intfloat/multilingual-e5-large` | 67 | 0.896 | 0.940 | 0.955 | 0.923 | 0.73 (15) | 70.2 / 80.3 / 93.6 | 70.7 | 14.5 / 8.04 | 0 |

## Anlamsal kapı kalibrasyonu (sözcük kapısı kapalıyken)

| Model | sözcükle kaçırılan cevaplanabilir | sözcükle kapalı cevapsız | AUC (cevaplanabilir↔cevapsız) | önerilen eşik → kurtarılan / sızan |
|---|---|---|---|---|
| `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | 3 | 20 | 0.691 | ≥0.5 → 2 / 4 |
| `minishlab/potion-multilingual-128M` | 3 | 20 | 0.673 | ≥0.36 → 1 / 4 |
| `sentence-transformers/paraphrase-multilingual-mpnet-base-v2` | 4 | 19 | 0.687 | ≥0.6 → 2 / 3 |
| `intfloat/multilingual-e5-large` | 3 | 20 | 0.738 | fayda yok (kapalı bırak) |
