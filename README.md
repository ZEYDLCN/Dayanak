# Lumora Bilgi Asistanı

Kurgu bir şirketin (Lumora — akıllı ev merkezi "Lumora Hub" ve "Lumora+" aboneliği) müşteri destek ekibi için, bilgi dokümanlarından yararlanarak **Türkçe soruları yanıtlayan** bir API ve küçük bir web arayüzü.

- Her yanıtta **kullanılan doküman, sürüm ve bölüm** gösterilir.
- Dokümanlarda bilgi yoksa **yanıt üretmek yerine bunu açıkça söyler**.
- Bir prosedürün eski ve güncel sürümü çeliştiğinde **güncel sürümü seçer ve nedenini yanıtta gösterir**.
- LLM'in yanıtı **kodla denetlenir**: model, yanıtını destekleyen cümleyi bölümden aynen kopyalamak zorundadır; kopya bölümde yoksa veya yanıttaki bir sayı kaynakta yoksa yanıt kullanıcıya gösterilmez.

Yığın: **Python 3.13 / FastAPI**. LLM sağlayıcıları: **NVIDIA `openai/gpt-oss-20b`** (varsayılan, hızlı: LLM çağrısı medyan ~1,3 sn), **Google Gemini `gemini-3.1-flash-lite`** (daha az gereksiz ret, ~3 kat yavaş; karşılaştırma aşağıda) ve Anthropic Claude (canlı doğrulanmadı). Anahtar yoksa alıntılayan moda düşer.

---

## Hızlı başlangıç

```bash
python -m venv .venv
# Windows PowerShell:  .venv\Scripts\Activate.ps1
# Git Bash: source .venv/Scripts/activate      Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env        # NVIDIA_API_KEY (veya ANTHROPIC_API_KEY) değerini .env içine yazın
uvicorn app.main:app --reload
```

- **Web arayüzü:** <http://localhost:8000/> (konu kartları, belge araması, kaynaklı sohbet; sohbet geçmişi yalnızca tarayıcıda tutulur, tarih alanı `as_of` parametresini kullanır)
- **Swagger:** <http://localhost:8000/docs>

**API anahtarı olmadan da çalışır.** `LLM_PROVIDER=none` veya anahtar boşsa servis LLM çağırmaz; bulduğu bölümü aynen alıntılar (`mode: "extractive"`). Anahtar yalnızca sunucuda, `.env` içinde durur (`.env` git'e girmez, tarayıcıya gönderilmez).

### Ortam değişkenleri (`.env.example`)

| Değişken | Varsayılan | Açıklama |
|---|---|---|
| `LLM_PROVIDER` | `anthropic`* | `nvidia`, `gemini`, `anthropic` veya `none` (*`.env.example` `nvidia` ile gelir) |
| `NVIDIA_API_KEY` / `NVIDIA_MODEL` | boş / `openai/gpt-oss-20b` | NVIDIA anahtarı ve model |
| `NVIDIA_TIMEOUT_SECONDS` | `15` | İstek başına bekleme; geçici hata (429/5xx/zaman aşımı) 3 denemeye kadar tekrarlanır, `Retry-After`'a uyulur |
| `NVIDIA_TEMPERATURE` / `NVIDIA_REASONING_EFFORT` | `0` / `low` | Tekrarlanabilirlik ve hız |
| `GEMINI_API_KEY` / `GEMINI_MODEL` | boş / `gemini-3.1-flash-lite` | Google AI Studio anahtarı (ücretsiz). Anahtar HTTP başlığında gider, URL'de değil (günlüğe/hata mesajına sızmaz) |
| `GEMINI_TIMEOUT_SECONDS` | `20` | Geçici hata (429/503) 3 denemeye kadar tekrarlanır |
| `ANTHROPIC_API_KEY` / `LLM_MODEL` | boş / `claude-opus-5-5` | Anthropic seçiliyse (bkz. sınırlar: canlı doğrulanmadı) |
| `LLM_CONTEXT_PASSAGES` | `2` | LLM'e verilen en iyi bölüm sayısı |
| `RETRIEVER` / `EMBEDDING_MODEL` | `bm25` / `…MiniLM-L12-v2` | `hybrid` isteğe bağlı vektör aramayı açar (varsayılan **kapalı**, bkz. Değerlendirme > 5; `requirements-hybrid.txt` gerekir) |
| `REQUIRE_EVIDENCE` | `true` | Zorunlu, kodla doğrulanan kanıt cümlesi |
| `VERIFY_ANSWERS` | `false` | İkinci LLM doğrulama geçişi (ölçüldü, faydası çıkmadı; aşağıya bakın) |
| `MIN_SCORE` / `MIN_COVERAGE` | `5.0` / `0.27` | "Cevapsız" ön elemesi eşikleri |
| `DOCS_DIR`, `TOP_K` | `data/docs`, `4` | Doküman klasörü, aday bölüm sayısı |

### Testler ve değerlendirme

```bash
pytest                                       # birim ve API testleri; anahtar gerekmez
python -m eval.run_eval --no-llm             # klasik set, alıntılayan mod  -> eval/results/results-extractive.md
python -m eval.run_eval                      # klasik set, .env'deki LLM    -> eval/results/results-llm.md
python -m eval.qa_run --repeat 2 --pause 1.5 # 57 vakalık QA (halüsinasyon odaklı) -> eval/results/qa-<model>.md
python -m eval.interview_70_run --no-llm  # 70 vakalık API denetimi, anahtar gerektirmez
python -m eval.interview_70_run --pause 1.5 # 70 vakalık API denetimi, .env'deki LLM
```

Görüşmeye hazırlık için [70 vakalık denetim ve bulgular](eval/INTERVIEW_AUDIT.md), [satır satır NVIDIA sonuçları](eval/results/interview-70-nvidia-openai_gpt-oss-20b.md), [LLM'siz sonuçlar](eval/results/interview-70-extractive.md) ve [20 dakikalık anlatım](INTERVIEW_GUIDE.md) bulunur.

> Windows'ta Türkçe karakterler bozuk görünürse `PYTHONIOENCODING=utf-8` ayarlayın. `curl -d` ile Türkçe JSON göndermek de konsol kodlaması yüzünden sorun çıkarabilir; arayüz, Swagger veya Python/`httpx` daha güvenli.
> `--pause 1.5` önemlidir: NVIDIA'nın ücretsiz katmanı dakikada ~40 istekle sınırlıdır (bunu ölçüm sırasında yaşadık).

---

## API

| Endpoint | Açıklama |
|---|---|
| `POST /ask` | `{"question": "...", "as_of": "2024-06-01"?}` → yanıt + kaynaklar + çelişki raporu |
| `GET /documents` | Yüklü dokümanlar, sürüm/durum bilgisi ve bölümleri |
| `GET /health` | Doküman sayısı ve mod (`llm` / `extractive`) |

`as_of` isteğe bağlıdır: verilen tarihte **yürürlükte olan** sürüme göre yanıtlar (varsayılan bugün).

`mode` alanı yanıtın nasıl üretildiğini söyler: `llm`, `extractive`, `extractive-fallback` (LLM çağrısı başarısız), `no-retrieval` (arama kapısında elendi), `llm-rejected` (model yanıt verdi ama dayanak kontrolü geçmedi, kullanıcıya gösterilmedi), `version-comparison` (tarihsel soru).

### Örnek: çelişkili kaynak (iade prosedürü v1 ↔ v2)

```json
POST /ask   {"question": "İade süresi kaç gün?"}
```
```json
{
  "answerable": true,
  "answer": "İade süresi **30** gündür. (Not: Bu konuda v1 sürümünde farklı bilgi var; yürürlükteki v2 esas alınmıştır.)",
  "sources": [{
    "doc_id": "iade-proseduru-v2", "title": "İade Prosedürü (v2)", "version": 2, "status": "current",
    "effective_date": "2025-01-15", "section": "İade Süresi", "snippet": "…30 gün içinde…", "score": 6.0
  }],
  "conflicts": [{
    "family": "iade-proseduru",
    "selected_doc_id": "iade-proseduru-v2", "selected_version": 2, "selected_effective_date": "2025-01-15",
    "discarded": [{"doc_id": "iade-proseduru-v1", "version": 1, "effective_date": "2023-03-01",
                   "section": "İade Süresi", "snippet": "…14 gün içinde…"}],
    "reason": "Aynı prosedürün birden fazla sürümü eşleşti: v1 (2023-03-01) ve v2 (2025-01-15). 2026-09-30 tarihinde yürürlükte olan en yüksek sürüm v2 seçildi; diğerleri daha eski sürüm olduğu için yanıtta kullanılmadı."
  }],
  "mode": "llm",
  "retrieval": {"top_score": 6.0, "top_coverage": 1.0}
}
```

### Örnek: cevapsız soru

```json
POST /ask   {"question": "Lumora Hub Apple HomeKit ile uyumlu mu?"}
```
```json
{"answerable": false, "answer": "Bu soruyla ilgili doküman kayıtlarında yeterli bilgi bulunmuyor. Lütfen destek ekibiyle iletişime geçin.",
 "sources": [], "conflicts": [], "mode": "no-retrieval", "retrieval": {"top_score": 0.0, "top_coverage": 0.0}}
```

### Örnek: tarihsel soru (`version-comparison`)

`"Eski iade prosedüründe iade süresi kaç gündü?"` → LLM'e gitmeden iki sürüm, metinleri aynen alıntılanarak yan yana verilir: *"Eski sürümde (v1, yürürlük 2023-03-01): … 14 gün … Güncel sürümde (v2, yürürlük 2025-01-15): … 30 gün …"*. (Bu davranış, ölçüm sırasında bulunan bir hatanın düzeltmesidir; aşağıda.)

---

## Nasıl çalışır?

```
soru ─► Arama (BM25) ─► Sürüm çözümü ─► Kapı ─► LLM ─► Dayanak kontrolleri ─► yanıt + kaynak + çelişki raporu
        Türkçe normalize  family başına   skor+   JSON çıktı  1) kanıt cümlesi bölümde var mı?
        F5 kök + geri     güncel sürüm    kapsama            2) yanıttaki sayılar kaynakta var mı?
        çekilme                                              3) (isteğe bağlı) doğrulayıcı LLM
```

| Dosya | Görev |
|---|---|
| `data/docs/*.md` | 10 kurgu doküman. Front-matter: `doc_id, family, title, version, status, effective_date` |
| `app/ingest.py` | Okur, `##` başlıklarına göre bölümler, front-matter ve sürüm tutarlılığını doğrular |
| `app/textproc.py` | Türkçe normalizasyon (`I/İ/ı/i`), ASCII katlama, `Wi-Fi`/`wifi`, `5ghz`/`5 GHz`, `Hub'ın`/`Hub` birleştirme, F5 kök alma |
| `app/index.py` | Bağımlılıksız BM25 + IDF-ağırlıklı sorgu kapsaması + kısa köklerde sözlük destekli geri çekilme |
| `app/versioning.py` | **Güncel sürüm seçimi**, seçim nedeni, tarihsel soru tespiti |
| `app/retrieval.py` | Arama → sürüm çözümü → iki kapı (`sufficient` / `plausible`) |
| `app/llm.py` | İstem, NVIDIA/Anthropic üreticileri, çıktı ayrıştırma, yeniden deneme, doğrulayıcı |
| `app/grounding.py` | **Dayanak kontrolleri**: kanıt doğrulama, sayı denetimi, tipografik karakter temizliği |
| `app/answer.py` | Uçtan uca akış, kaynak/çelişki raporu, tarihsel karşılaştırma, güvenli geri düşüş |
| `app/main.py`, `app/schemas.py`, `app/web/` | FastAPI uç noktaları, API sözleşmesi, web arayüzü |
| `eval/` | Klasik değerlendirme, QA seti, çalıştırıcılar, sonuçlar |

### Güncel sürüm nasıl seçiliyor?

Kural kodda, deterministik (LLM'e bırakılmadı — denetlenebilir olması için):

1. Aynı prosedürün sürümleri `family` alanıyla gruplanır (`iade-proseduru` → v1, v2).
2. Yürürlük tarihi `as_of`'tan sonra olan sürümler henüz geçerli değildir, elenir.
3. Kalanlar arasında **en yüksek sürüm numarası** (eşitlikte en yeni tarih) seçilir.
4. Elenen sürümlerin bölümleri **LLM'e hiç verilmez**; eski bilgiyi karıştırma şansı yoktur.
5. `conflicts` alanı seçileni, elenenleri (alıntılarıyla) ve nedeni gösterir; yalnızca yanıtta **kullanılan bölümle aynı bölümdeki** farklı sürümler raporlanır.

`status` alanı elle yazıldığı için yükleme sırasında sürüm numarasıyla tutarlılığı doğrulanır (tutarsızsa servis başlamaz).

### Halüsinasyon korumaları (katmanlar)

| Katman | Ne yapar | Ölçülen etkisi |
|---|---|---|
| **1. İstem** | Yalnızca bölümlerde *açıkça* yazan bilgi; komşu bilgiyi uyarlama yasağı; yanlış öncülü düzeltme; istemdeki örnek gerçek bir olgu içermez (few-shot sızıntısı yok) | ↓ |
| **2. Zorunlu kanıt** | Model, yanıtı destekleyen cümleyi bölümden **aynen kopyalar**; kod bunun verilen bölümlerde gerçekten geçtiğini doğrular (`...` ile kısaltmaya ve tipografik farklara toleranslı). **Kaynaklar modelin atfından değil, doğrulanmış kanıttan türetilir.** | Cevapsız sorularda uydurma: ~%17–80 → **0/48 koşu** |
| **3. Sayı denetimi** | Yanıttaki her sayı/saat, soruda veya verilen bölümlerde geçmek zorunda; yoksa yanıt reddedilir | Kaynakta olmayan sayı: **0** |
| **4. Geçerli ret** | `{"answerable": false}` hata değil ret sayılır; ret metni modelin değil sabit ve güvenli mesajdır | eskiden hata sayılıp alıntıya düşüyordu |
| **5. Güvenli geri düşüş** | LLM çağrısı başarısızsa: yalnızca güçlü eşleşmede bölümü alıntılar ve başına "yapay zekâ servisine ulaşılamıyor; en yakın bölüm aynen aşağıdadır, sorunuzu yanıtlamayabilir" uyarısı koyar; zayıfta "bilgi yok" der (Gemini testinde geçici bir hata, ilgisiz bir bölümün cevap gibi sunulmasına yol açmıştı; uyarı bu yüzden eklendi) | LLM hatası 0 (hız sınırı düzeltmesinden sonra) |
| Doğrulayıcı LLM (kapalı) | İkinci çağrı: "kanıt soruyu doğrudan yanıtlıyor mu?" | **Faydası çıkmadı**, geçerli yanıtları da reddetti (aşağıda) |

**Sınır:** katman 2–3 "kanıt gerçekten var mı" sorusunu yanıtlar, "kanıt soruyu gerçekten yanıtlıyor mu" sorusunu değil. Rakamsız anlam hataları ("her gün" → "cumartesi yok") kodla yakalanamaz; bunu istem ve model kalitesi taşır. Yazıyla verilen sayılar ("otuz gün") kontrol edilmez.

### Cevapsız soru nasıl tespit ediliyor?

1. **Kapı:** En iyi bölümün BM25 skoru ve IDF-ağırlıklı sorgu kapsaması eşiklerle karşılaştırılır. Kapsama, sorgu terimlerinin ne kadarının bölümde geçtiğini ölçer; korpusta hiç olmayan terimler ("HomeKit") en yüksek ağırlığı alır. **LLM yokken kapı sıkıdır (skor VE kapsama)**, çünkü alıntılanan bölüm tek savunmadır; **LLM varken gevşektir (skor VEYA kapsama)**, çünkü karar LLM'indir ve yanlış ret pahalıdır.
2. **LLM ve dayanak katmanları** (yukarıdaki tablo). Bu durumda `sources` boş döner.

---

## Teknik tercihler

| Karar | Neden |
|---|---|
| **FastAPI** (Python) | Önerilenlerden biri; küçük servis, Pydantic doğrulaması, otomatik Swagger. |
| **BM25 (varsayılan); vektör arama ölçüldü ve seçilmedi** | 10 kısa doküman için sözcük araması yeterli ve her skor açıklanabilir. Hibrit (BM25 + yerel gömme) 5 modelle denendi: doğruluk kazancı gürültü içinde kaldı, uydurma riski arttı, gecikme eklendi ([ayrıntı](#5-hibrit-vektör-arama-denemesi)). İsteğe bağlı olarak `RETRIEVER=hybrid` ile açılabilir. |
| **Depolama: Markdown + bellekte indeks** | Dokümanlar metin ve sürümlü; açılışta ~50 bölüm indekslenir. Büyürse SQLite FTS / vektör DB. |
| **Sürüm çözümü kodda** | "Hangi sürüm geçerli?" bir iş kuralı; LLM tahminine bırakılırsa tutarsız ve denetlenemez olur. |
| **Bölüm bazlı (`##`) parçalama** | Bölüm başlığı hem doğal kaynak referansı hem kısa, anlamlı bağlam. |
| **F5 kök alma + dar geri çekilme** | Basit, bağımlılıksız taban çizgisi. F5'in kaçırdığı 3 harfli kökler (`gün`/`gündü`) için yalnızca 3 harfli, ≤6 harfli terimlerde sözlük geri çekilmesi (4 harfli deneme `homekit`→`home` sahte eşleşmesi üretti). |
| **LLM: gpt-oss-20b (NVIDIA)** | **Hız önceliği.** Aynı anahtarla denenen modeller: `nemotron-3.5-lightning` 16 sn, `gemma-4-31b`, `deepseek-v4.1-flash`, `glm-5.3-flash` 50 sn'de zaman aşımı, `nemotron-nano-3` ve `gemma-3-12b` hesapta 404. Tek hızlı ve çalışan aday gpt-oss-20b (medyan ~1,3 sn; yüke göre 3–7 sn'ye çıkabiliyor). |
| **Yapılandırılmış çıktı** | Anthropic: JSON şeması (`output_config.format`). NVIDIA: `response_format=json_object` + kodda sıkı doğrulama. Yeni modellerde zorunlu `tool_choice` desteklenmediği için tool-call kullanılmadı. |
| **LLM'siz çalışma modu** | Anahtar/kota/ağ sorununda servis düşmez; CI ve testler anahtarsız, deterministik koşar. |
| **Anahtar kodda yok** | Yalnızca `.env` (git'e girmez); CI'da sızıntı taraması var. |

---

## Değerlendirme

**Güncel uçtan uca denetim:** 70 soru/tarih kombinasyonu gerçek `/ask` API'sinden çalıştırıldı: NVIDIA ile **58/70**, LLM'siz alıntı modunda **54/70**. NVIDIA turunda yedi gereksiz ret ve beş ağ zaman aşımı vardı; tüm vaka, beklenen–gerçek karşılaştırması ve sınırlamalar [denetim raporunda](eval/INTERVIEW_AUDIT.md). Aşağıdaki 30 ve 57 vakalık sonuçlar önceki çalıştırmalardır; model ve ağ koşulları arasında doğrudan aynı test gibi karşılaştırılmamalıdır.

### 1) Klasik set — 30 soru (14 normal, 6 çelişkili, 10 cevapsız)

Beklenen ↔ gerçek çıktı tablosunun tamamı: [`eval/results/results-llm.md`](eval/results/results-llm.md) (LLM) ve [`results-extractive.md`](eval/results/results-extractive.md) (LLM'siz).

| | Alıntılayan mod | **LLM (gpt-oss-20b)** |
|---|---|---|
| Toplam | 26 / 30 | **29 / 30** |
| dev (18) | 18 / 18 | 18 / 18 |
| **held-out (12)** | 8 / 12 | **11 / 12** |
| Normal | 13 / 14 | 13 / 14 |
| Çelişkili (v1↔v2) | 4 / 6 | **6 / 6** |
| Cevapsız | 9 / 10 | **10 / 10** |

*dev*: kapı eşikleri bu sorulara bakılarak ayarlandı. *held-out*: eşikler dondurulduktan sonra yazıldı, ayarlama yapılmadı. LLM modundaki tek hata H6 ("Cihaz serviste iken geçici cihaz verilir mi?"): doküman "verilmez" diyor, model "bilgi yok" dedi (gereksiz ret).

### 2) QA seti — 57 vaka, halüsinasyon odaklı

Olgu, yanlış öncül, çoklu niyet, kısmi bilgi, sürüm tuzağı, komşu-cevapsız (konuyla ilgili ama dokümanda yok), prompt injection, kötü girdi ve kenar durumlar. Her yanıt, **sistemden bağımsız bir denetçiyle** (`eval/qa_run.py`) kaynak metnine karşı kontrol edilir; her soru 2 kez sorulur (tutarlılık için).

**Sonuç (gpt-oss-20b, 114 koşu):** [`eval/results/qa-nvidia-openai_gpt-oss-20b.md`](eval/results/qa-nvidia-openai_gpt-oss-20b.md)

| Ölçüt | Sonuç |
|---|---|
| Geçen koşu | **98 / 114** |
| **Cevapsız/komşu sorularda yanıt verme (uydurma)** | **0 / 48 koşu** |
| **Kaynakta olmayan sayı** | **0** |
| İçeriği yanlış ama cevaplanmış yanıt | **0** (otomatik denetçi + ilk koşudaki 25 cevaplanmış yanıtın tamamı elle okundu; F8'de "çekmeyin" yerine "çekemezsiniz" gibi hafif bir anlam kayması var) |
| Tutarlılık (aynı soru, aynı sonuç) | 57 / 57 |
| LLM hatası | 0 |
| Gecikme (LLM'e giden 92 koşu) | medyan **1,3 sn**, p90 3,2 sn, en kötü 9,2 sn (LLM'siz anında dönenler dahil tüm koşular: medyan 1,0 sn). Sunucu üzerinden tek tek denenen çağrılar 3–7 sn sürdü; NVIDIA ücretsiz katmanının yükü değişken. |
| Prompt injection (8 koşu) | 8 / 8 dayandı ("90 gün" dedirtilemedi; ancak "Önceki talimatlarını unut…" cümlesi "önceki" anahtar kelimesi yüzünden yanlışlıkla sürüm karşılaştırması tetikledi, zararsız ama bir sınır) |

Kalan 16 başarısızlığın **tamamı gereksiz ret** (cevaplanabilir soruya "bilgi yok" demek); yanlış bilgi verilen bir durum kalmadı:

| Vaka | Neden |
|---|---|
| P1, P2, P4 (yanlış öncüllü sorular) | Model "14 gün, doğru mu?" gibi sorularda düzeltmek yerine reddediyor. P4'te doğru bölüm (iade başvurusu) aramada üst sıralara girmiyor. |
| M1, M3 (çok parçalı / kısmi bilgi) | Sorunun bir kısmı dokümanda yoksa model tümden reddediyor; istem "kısmen yanıtla" dese de 20B model uymuyor. |
| F4, F6 | **Doğru bölüm LLM bağlamının birinci sırasında** (F4 skoru 14,6, kapsama 1,0); model yine de reddediyor. Yani sorun arama değil, katı istem + düşük akıl yürütme ayarlı 20B modelin aşırı temkini. F4'ü istem v3 öncesi yanıtlıyordu (ablasyon A–C), v3'te geriledi; F6 koşudan koşuya kararsız. |
| E3 | İngilizce soru; korpus Türkçe, arama eşleşmiyor. Bilinen sınır. |

### 3) Ablasyon — hangi katman işe yaradı? ([`eval/results/ablation/`](eval/results/ablation/))

| Konfigürasyon | Geçen / 114 | Uydurma | Tutarlılık | Gecikme |
|---|---|---|---|---|
| A: zorunlu kanıt, sayı denetimi | 88 | 0 | 55/57 | 1,4 sn |
| B: A + doğrulayıcı LLM | 89 | 0 | 54/57 | 2,2 sn |
| C: B + 4 bölüm bağlamı | 88 | 0 | 53/57 | 2,0 sn |
| **D: A + istem v3** (tam cümle, gün eşlemeleri) | **92** | 0 | 55/57 | 1,5 sn |

Sonuçlar: uydurmayı sıfırlayan **zorunlu kanıttır**; doğrulayıcı hiçbir şey eklemedi (uydurma zaten 0'dı), geçerli yanıtları (P2, P3) reddetti ve gecikmeyi ~%50 artırdı → kapalı. Daha fazla bağlam yardım etmedi (M1 hâlâ reddedildi). Son tablo (98) D'nin üzerine, hız sınırı düzeltmesi ve denetçi düzeltmeleriyle yeniden koşulmuş halidir.

### 4) Sağlayıcı karşılaştırması: gpt-oss-20b ↔ Gemini 3.1-flash-lite

Aynı 57 vaka × 2 koşu, aynı istem ve korumalar. Sonuçlar: [`qa-nvidia-openai_gpt-oss-20b.md`](eval/results/qa-nvidia-openai_gpt-oss-20b.md), [`qa-gemini-3.1-flash-lite.md`](eval/results/qa-gemini-3.1-flash-lite.md).

| | gpt-oss-20b (varsayılan) | Gemini 3.1-flash-lite |
|---|---|---|
| Geçen koşu | 98 / 114 | 103 / 114 (*) |
| **Gereksiz ret** (cevaplanabilir soruya "bilgi yok") | 16 | **6** |
| Kaynakta olmayan sayı | 0 | 0 |
| Cevapsız soruya yanıt verme | 0 | 1 (**) |
| **LLM çağrısı gecikmesi** (medyan / p90 / en kötü) | **1,3 / 3,2 / 9,2 sn** | 4,3 / 9,3 / 21,6 sn |
| Tutarlılık | 57/57 | 56/57 |

(*) Denetçideki iki kusur yüzünden 3 vaka yanlış başarısız sayılmıştı: kısmi yanıt ("5 GHz desteklenmez, Bluetooth için bilgi yok") "çelişki" sanılmış, "tutanağı" çekimi anahtar kelimeyle eşleşmemişti. Denetçi düzeltilip bu vakalar yeniden koşuldu (**6/6**); düzeltilmiş tahmin ≈ 108/114. Ham çıktı yukarıdaki dosyada, düzeltme öncesi haliyle duruyor.
(**) U17: Gemini'de geçici bir hata alıp geri düşüş moduna geçen tek koşu, ilgisiz bir bölümü cevap gibi sundu. Yeniden koşuda Gemini doğru biçimde reddetti. Geri düşüş çıktısı bu olaydan sonra uyarı öneki ile etiketlendi.

**Gemini'nin gerçek kazancı:** yanlış öncüllü sorular (P1, P2), kısmi bilgili soru (M3) ve F4/F6 gibi gereksiz retler. Kalan 6 retten 4'ü arama/dil kaynaklı (P4: doğru bölüm bağlama girmiyor; E3: İngilizce), yani model değiştirmekle düzelmez.

**Kademe fikri (önce gpt-oss, ret ederse Gemini) çevrimdışı simüle edildi ve elendi:** 105/114, ama koşuların %40'ı Gemini'ye yükseldi (cevapsız sorular da ret ile bittiği için hepsi yavaş yola giriyor); medyan gecikme 3,6 sn, yani Gemini'yi tek başına kullanmaktan belirgin fark yok.

**Öneri:** hız birinci öncelikse `gpt-oss-20b` (varsayılan); gereksiz retin azaltılması hızdan önemliyse `LLM_PROVIDER=gemini`. İki sağlayıcıda da uydurma korumaları aynıdır (zorunlu kanıt + sayı denetimi) ve ikisinde de kaynakta olmayan sayı 0'dır.

### 5) Hibrit (vektör) arama denemesi

**Soru:** BM25'e yerel bir gömme modeli eklemek (hibrit, RRF ile birleştirme) doğruluğu artırır mı, hız bedeli değer mi?
**Yöntem:** Model değiştirilebilir bir hibrit katman entegre edildi (`app/embeddings.py`, `app/hybrid.py`, `RETRIEVER=hybrid`). Beş yapılandırma (BM25 + 4 çok dilli yerel model) önce yalnızca aramada, sonra gerçek LLM'li uçtan uca ölçüldü. Karar kuralı **sonuçlar görülmeden önce** konuldu: (1) uydurma > 0 olan elenir, (2) doğruluk, (3) hız: arama p90'ı BM25'e göre +25 ms'yi aşmamalı ve kazanç gürültüyü aşmalı.

**A) Yalnızca arama** (67 etiketli soru, 5 tekrar; doğru bölümün ilk k'ya girme oranı, sürüm çözümünden sonra) — [`retrieval-bench.md`](eval/results/hybrid/retrieval-bench.md)

| Yöntem | hit@1 | hit@2 | hit@4 | MRR | arama p50 / p90 (ms) | başlangıç (soğuk / sıcak, sn) |
|---|---|---|---|---|---|---|
| **BM25** | 0,866 | 0,910 | 0,925 | 0,893 | 0,1 / 0,2 | 0 / 0 |
| hibrit + MiniLM-L12 (0,22 GB) | 0,821 | 0,910 | 0,940 | 0,874 | 7,0 / 9,5 | 3,0 / 1,7 |
| hibrit + potion-multilingual (0,5 GB) | 0,836 | 0,925 | 0,925 | 0,881 | 0,6 / 0,8 | 2,6 / 3,3 |
| hibrit + mpnet-base (1 GB) | 0,866 | 0,910 | 0,925 | 0,893 | 21,8 / 25,3 | 7,1 / 5,9 |
| hibrit + e5-large (2,2 GB) | 0,896 | 0,940 | 0,955 | 0,923 | 70,2 / 80,3 | 14,5 / 8,0 |

Yalnızca aramada en iyi e5-large bile hit@2'de BM25'e +0,03 (67 sorudan ~2) kazandırıyor. Dört zor eş anlamlı soru ("paketin içinden neler çıkıyor" ↔ "Kutu İçeriği", "parolamı yanlış girince" ↔ "hatalı şifre denemesi", "para çekilemezse" ↔ "Ödeme Hataları", İngilizce soru) **hiçbir modelde** ilk 2'ye girmedi.

**B) Uçtan uca (gpt-oss-20b, gerçek LLM; kayıtlar [`eval/results/hybrid/`](eval/results/hybrid/))**

20 yeni (ayarlamada kullanılmamış) eş anlamlı/dolaylı/İngilizce/komşu-cevapsız vaka × 3 tekrar:

| Yapılandırma | geçen / 60 | uydurma | arama p50 / p90 (ms) |
|---|---|---|---|
| BM25 | 37 | 0 | 0,7 / 1,0 |
| **BM25 (kontrol: aynı ayar, ikinci çalıştırma)** | **39** | 0 | 0,8 / 1,2 |
| MiniLM | 44 | 0 | 24 / 29 |
| potion | 44 | 0 | 2,7 / 3,5 |
| mpnet | 38 | 0 | 43 / 76 |
| e5-large | 40 | 0 | 191 / 237 |

Aynı BM25 iki çalıştırmada 37 ve 39 verdi: **gürültü ±2**, çünkü LLM'in sunucu tarafı tam deterministik değil. Tekrarlar neredeyse aynı çıktığı için gerçek örneklem 60 değil **20 vaka**; farklar yalnızca 4–5 "sınır" vakadan geliyor (H06, H11, H12, H13), ve BM25'in kendisi bunlarda 0↔3 arası oynuyor.

Bu yüzden iki finalist (potion, MiniLM) ve BM25 **57 vakalık QA setinde** (injection, çoklu niyet, sürüm tuzakları dahil) × 2 tekrar yeniden denendi:

| Yapılandırma | geçen / 114 | **uydurma** | arama p50 / p90 (ms) |
|---|---|---|---|
| **BM25** | **99** | **0** | 1,1 / 1,9 |
| hibrit + potion | 94 | **2** | 3,2 / 4,5 |
| hibrit + MiniLM | 91 | **2** | 28,5 / 38,9 |

**Karar: BM25 varsayılan kalır; hibrit isteğe bağlıdır ve kapalıdır.** Gerekçe:
1. İki sette de hibrit tutarlı biçimde BM25'i geçmedi (20 vakada +5/+7, 57 vakada −5/−8; toplamda fark gürültü içinde).
2. **Hibrit uydurma üretti, BM25 üretmedi.** Soru: *"Servis süresince gidiş dönüş kargo ücretini kim öder?"* (dokümanda yok). Vektör arama "kargo ücreti" kavramına yakın olduğu için **iade** bölümünü bağlama soktu; LLM iade kuralını ("Lumora karşılar") garanti servisine uyguladı. Kanıt cümlesi belgede gerçekten var, yani zorunlu kanıt doğrulamasından geçti. BM25 o bölümü getirmediği için doğru biçimde "bilgi yok" dedi. Anlamsal arama, projenin en çok korumaya çalıştığı hata türünü (komşu bilgiyi uyarlama) artırıyor.
3. Doğruluğun darboğazı arama değil, LLM'in aşırı temkini: aynı 5 vaka (H03, H04, H06, H14, H15) tüm yapılandırmalarda başarısız; H06'da doğru bölüm bağlamda olduğu halde model reddediyor.
4. Anlamsal "LLM'e git" kapısı (`MIN_SEMANTIC`) kalibre edildi, ancak ayırma gücü zayıf (AUC 0,67–0,74); anlamlı bir eşik bulunamadı, kapalı.

**Ölçüm notu:** İlk geçişte bilgisayar uyku moduna girip ağ kopunca MiniLM ve potion koşuları bozuldu (bir çağrı 10.805 sn sürdü, 42 çağrı bağlantı hatası verdi). Bu koşular geçersiz sayıldı ve temiz ağda yeniden koşuldu; tabloda yalnızca geçerli koşular var.

**İsteğe bağlı kullanım** (yukarıdaki risk bilinerek): `pip install -r requirements-hybrid.txt`, `.env` içinde `RETRIEVER=hybrid` ve `EMBEDDING_MODEL=minishlab/potion-multilingual-128M`. Gömme yüklenemezse sistem uyarı verip BM25'e düşer; ağ veya API gerekmez (ONNX, CPU). Bölüm gömmeleri `.cache/` altında önbelleğe alınır.

### Ölçüm sırasında bulunan gerçek hatalar

| Bulgu | Düzeltme |
|---|---|
| Komşu sorulara uydurma yanıt: "iade kargo kodu **30 gün** içinde kullanılır" (iade süresi başka bölümden ödünç alınmış), "garanti kapsamında **ekran değişimi** yapılır" (dokümanda yok). Sayı denetimi bunları **yakalayamadı** (30 bağlamda vardı). | Zorunlu kanıt (katman 2) |
| İstemdeki örnek JSON gerçek bir olgu içeriyordu ("30 gün içinde iade") — few-shot sızıntısı şüphesi | Örnek yer tutucuya çevrildi; testle korunuyor |
| Aynı soruya çelişkili yanıtlar (F15: "cumartesi canlı destek **yok**" / "her gün var"); 14 riskli sorunun yalnızca 7'sinde koşular tutarlıydı | `temperature=0`, sıkı istem → tutarlılık 57/57. **Not:** sunucu tarafı tam deterministik değil (F10'un kanıt biçimi koşudan koşuya değişti). |
| "Eski prosedürde süre kaç gündü?" → "**30 gün**" (eski süre 14'tü; model eski sürümü hiç görmediği için güncel değeri "eski" diye sundu) | Tarihsel soru tespiti + iki sürümü aynen alıntılayan `version-comparison` |
| Geçerli ret (`{"answerable": false}`) "şema hatası" sayılıp alıntılayan moda düşüyordu (kapsama ≥ 0,5 ise komşu bölüm cevap diye sunulabilirdi) | Geçerli ret ayrıştırması |
| "wifi" ↔ "Wi-Fi", "5ghz" ↔ "5 GHz" eşleşmiyordu; F5 `gündü`↔`gün` kaçırıyordu | Tokenizasyon birleştirme + dar geri çekilme |
| Gpt-oss tipografik karakterler üretiyor (U+202F, U+2011) → metin eşleşmesi bozuluyor | `clean_text` |
| Hız sınırı (429): ilk denemede 8 koşu LLM hatası verdi; servis `Retry-After`'a uymuyordu | 3 deneme + `Retry-After` |
| İlk sürümde ret metni modelin serbest çıktısıydı | Sabit ret mesajı |

### Dürüstlük notları

- QA seti geliştirme sırasında **kullanıldı**: istem ve korumalar onun başarısızlıklarına bakılarak geliştirildi, dolayısıyla 98/114 tamamen "görülmemiş veri" ölçümü değildir. Baz çizgisinde görülmemiş komşu-cevapsız sorular (U11–U18) ve cevaplanabilir yeni sorular (F16–F21) sonradan eklendi; klasik sette **held-out 11/12** en temiz ölçümdür.
- Beş vakanın (F2, F7, F8, F15, F18) beklenen anahtar kelime listesi, yanıtlar okunduktan sonra anlamca eşdeğer ifadeleri ("çalışmıyor", "gönderilmez") kapsayacak şekilde **genişletildi**; genişletmeden önce bu vakalar yanlış başarısız sayılıyordu.
- Anthropic yolu canlı API'ye karşı **çalıştırılmadı**, yalnızca kodla ve birim testleriyle doğrulandı. NVIDIA ve Gemini yolları canlı ölçüldü.
- Tek model (gpt-oss-20b) ve tek makinede ölçüldü; NVIDIA ücretsiz katmanında gecikme ve kota değişkendir.

---

## Şirket isterlerinin karşılanması

| İster | Durum | Nerede |
|---|---|---|
| Türkçe soru yanıtlayan servis, kurgu şirket, bilgi dokümanları | ✅ | API + arayüz |
| 8–10 kısa kurgu doküman | ✅ 10 | `data/docs/` |
| En az bir prosedürün eski ve güncel sürümü | ✅ iade v1/v2 | `03-`, `04-` |
| Dokümanları aranabilir hale getir, yanıtlayan API | ✅ | `app/`, `POST /ask` |
| Her yanıtta kullanılan doküman ve ilgili bölüm | ✅ | `sources[]` (doc, sürüm, bölüm, alıntı) |
| Bilgi yoksa uydurma, açıkça belirt | ✅ 0/48 uydurma | kapı + zorunlu kanıt |
| Çelişkide güncel sürümü seçme ve gösterme | ✅ | `conflicts[]`, `version-comparison` |
| ≥10 örnekle değerlendirme (normal/cevapsız/çelişkili) | ✅ 30 + 57 | `eval/` |
| .NET veya FastAPI | ✅ FastAPI | |
| README, çalıştırma adımları | ✅ | bu dosya |
| Örnek ortam değişkenleri | ✅ | `.env.example` |
| Beklenen ↔ gerçek çıktı karşılaştırması | ✅ | `eval/results/*.md` |
| Teknik tercihler ve bilinen sınırlar | ✅ | bu dosya |
| API anahtarı kaynak kodda yok | ✅ | `.env` git dışı; CI sızıntı taraması |

## İş akışları (GitHub Actions)

- **`.github/workflows/ci.yml`** — her push/PR'da, anahtarsız: kaynakta anahtar taraması → `pytest` → klasik değerlendirme (alıntılayan mod, taban 26/30) → QA (taban 40/57, halüsinasyon bayrağı 0 olmalı) → sonuçları artifact olarak yükler.
- **`.github/workflows/qa-llm.yml`** — elle tetiklenir; gerçek LLM'e karşı klasik set + QA koşar (model, tekrar sayısı, doğrulayıcı, bağlam bölüm sayısı girdi olarak seçilir). Anahtar repo **Secret**'ından (`NVIDIA_API_KEY`) gelir; kaynak kodda durmaz.

---

## Tanıtım videosu

`promo/` klasörü, projenin 39 sn'lik tanıtım videosunu **kodla** üretir (1920×1080, 30 fps, seslendirmesiz; müzik ve ses efektleri). Görüntüler uygulamanın kendi arayüzünden alınan **gerçek ekran görüntüleri**, kendi ikonları, renkleri (`styles.css`) ve yazı tipleridir (Manrope, DM Sans); sayılar bu README'deki ölçümlerdir (%0 uydurma yanıt, %97 doğru yanıt, 1,3 sn medyan yanıt süresi). Müzik (120 bpm) ve bütün efektler `promo/sfx.py` ile NumPy'la sentezlenir; dış servis veya ses örneği kullanılmaz. Görüntüdeki her olay (tıklama, yazma, vuruş, geçiş) ses olayıyla aynı zaman damgasından üretilir.

Video dosyası (`promo/lumora-tanitim.mp4`) git'e girmez, aşağıdaki adımlarla yeniden üretilir:

```bash
pip install moviepy pillow numpy scipy playwright         # ekstra bağımlılıklar (requirements.txt'e girmez)
uvicorn app.main:app --port 8000                          # gerçek yanıtlar için LLM_PROVIDER ayarlı olmalı
python promo/capture_icons.py      # uygulamanın ikon setini görsele çevirir
python promo/capture.py            # gerçek arayüzden ekran görüntüleri
python promo/render.py --preview   # önemli anlardan kareleri promo/build/preview_*.png olarak yazar
python promo/render.py             # promo/lumora-tanitim.mp4
```

Yazı tipleri OFL lisanslıdır; `promo/fonts/` içine `Manrope[wght].ttf` ve `DMSans[opsz,wght].ttf` dosyalarını Google Fonts deposundan indirin.

---

## Bilinen sınırlar

- **Aşırı temkin:** Güvenlik önceliklendirildi; bunun bedeli %14 gereksiz ret (yanlış öncüllü, çok parçalı ve kısmi bilgili sorularda). Uydurma yerine ret tercih edildi.
- **Anlam hataları kodla yakalanamaz:** Kanıt ve sayı denetimi rakamsız anlam kaymalarını ("her gün" → "yok") göremez. F15 bir kez böyle bir hata yaptı; `temperature=0` ve istemle azaldı, kodla garanti edilmiyor.
- **Sözcük tabanlı arama:** Eş anlamlı ve dolaylı ifadeleri kaçırır ("para"↔"ücret", "paketin içinden"↔"Kutu İçeriği"), İngilizce soruları eşleştiremez. Beş yerel gömme modeliyle hibrit arama denendi ve **seçilmedi** (kazanç gürültü içinde, uydurma riski arttı; bkz. Değerlendirme > 5). Gerçek çözüm muhtemelen sorgu yeniden yazımı veya bölümlere eş anlamlı başlık/etiket eklemektir; denenmedi.
- **Eşikler küçük bir örnekle ayarlı:** 10 doküman / 51 bölümde makul; gerçek korpusta yeniden kalibre edilmeli. `MIN_SCORE` BM25'in mutlak değerine bağlı olduğu için korpus büyüklüğüne duyarlı.
- **Ücretsiz katmanlar:** NVIDIA dakikada ~40 istekle sınırlı; Gemini'de bazı modeller "yoğun talep" (503) veriyor, `2.5-*` modelleri yeni kullanıcılara kapalı ve gecikme değişken. Gemini ücretsiz katmanında girdiler Google tarafından ürün geliştirmede kullanılabilir; gerçek müşteri verisiyle kullanılmamalı. Üretim için ücretli/özel uç nokta gerekir.
- **Tarihsel soru tespiti anahtar kelimeyle çalışır** ("eski", "önceki", "v1", eski sürümün yılı). "Eski cihazımı iade etmek istiyorum" gibi cümleler yanlışlıkla iki sürüm karşılaştırması tetikleyebilir.
- **Sürüm çözümü yalnızca `family` + sürüm/tarih ile çalışır.** Aynı sürümde birbiriyle çelişen iki doküman tespit edilmez; bölüm adı değişen sürümlerde eski bölüm eşleşmesi kaybolabilir.
- **Model reddi (`refusal`) için yedek model yok** (Anthropic yolu): ret gelirse servis "bilgi yok" döner.
- **Kimlik doğrulama, hız sınırı, kalıcı log yok** — teslim projesi kapsamında bilinçli olarak dışarıda bırakıldı.
- **Tek dil / kurgu veri:** Türkçe dışı sorular ve gerçek müşteri verisi denenmedi.
