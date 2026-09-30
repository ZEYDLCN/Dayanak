# Lumora Bilgi Asistanı

Kurgu bir şirketin (Lumora — akıllı ev merkezi "Lumora Hub" ve "Lumora+" aboneliği) müşteri destek ekibi için, bilgi dokümanlarından yararlanarak **Türkçe soruları yanıtlayan** bir API.

- Her yanıtta **kullanılan doküman, sürüm ve bölüm** gösterilir.
- Dokümanlarda bilgi yoksa **yanıt üretmek yerine bunu açıkça söyler**.
- Bir prosedürün eski ve güncel sürümü çeliştiğinde **güncel sürümü seçer ve nedenini yanıtta gösterir**.

Yığın: **Python / FastAPI** (Python 3.13 ile geliştirildi ve test edildi). LLM: **Anthropic Claude** (isteğe bağlı; anahtar yoksa alıntılayan moda düşer).

---

## Hızlı başlangıç

```bash
python -m venv .venv
# Windows PowerShell:  .venv\Scripts\Activate.ps1
# Git Bash / Linux / macOS:  source .venv/bin/activate   (Windows'ta: source .venv/Scripts/activate)
pip install -r requirements.txt

cp .env.example .env        # LLM kullanacaksanız ANTHROPIC_API_KEY değerini .env içine yazın
uvicorn app.main:app --reload
```

Swagger arayüzü: <http://localhost:8000/docs>

**API anahtarı olmadan da çalışır.** `ANTHROPIC_API_KEY` boşsa (veya `LLM_PROVIDER=none` ise) servis LLM çağırmaz; bulduğu bölümü aynen alıntılar (`mode: "extractive"`). Anahtar `.env` içinde durur, `.env` git'e girmez.

### Ortam değişkenleri (`.env.example`)

| Değişken | Varsayılan | Açıklama |
|---|---|---|
| `LLM_PROVIDER` | `anthropic` | `anthropic` veya `none` |
| `ANTHROPIC_API_KEY` | boş | Boşsa LLM devre dışı kalır |
| `LLM_MODEL` | `claude-opus-5-5` | İstenen model (maliyet için daha küçük bir model seçilebilir) |
| `DOCS_DIR` | `data/docs` | Doküman klasörü |
| `TOP_K` | `4` | Yanıta aday bölüm sayısı |
| `MIN_SCORE` / `MIN_COVERAGE` | `5.0` / `0.27` | "Cevapsız" ön elemesi eşikleri (aşağıya bakın) |

### Testler ve değerlendirme

```bash
pytest                                 # 25 test, LLM anahtarı gerekmez
python -m eval.run_eval --no-llm       # alıntılayan mod  -> eval/results/results-extractive.md
python -m eval.run_eval                # .env'de anahtar varsa LLM modu -> eval/results/results-llm.md
```

> Windows'ta çıktıda Türkçe karakter bozuksa önce `set PYTHONIOENCODING=utf-8` (PowerShell: `$env:PYTHONIOENCODING="utf-8"`) çalıştırın. `curl -d` ile Türkçe JSON gönderirken de konsol kodlaması sorun çıkarabilir; Swagger arayüzü veya Python/`httpx` ile denemek daha güvenlidir.

---

## API

| Endpoint | Açıklama |
|---|---|
| `POST /ask` | `{"question": "...", "as_of": "2024-06-01"?}` → yanıt + kaynaklar + çelişki raporu |
| `GET /documents` | Yüklü dokümanlar, sürüm/durum bilgisi ve bölümleri |
| `GET /health` | Doküman sayısı ve mod (`llm` / `extractive`) |

`as_of` isteğe bağlıdır: verilen tarihte **yürürlükte olan** sürüme göre yanıtlar (varsayılan bugün).

### Örnek: çelişkili kaynak (iade prosedürü v1 ↔ v2)

```json
POST /ask   {"question": "İade süresi kaç gün?"}
```
```json
{
  "answerable": true,
  "answer": "Müşteriler, ürünü teslim aldıkları tarihten itibaren 30 gün içinde iade talebinde bulunabilir. (Not: Bu konuda v1 sürümünde farklı bilgi var; yürürlükteki v2 esas alınmıştır.)",
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
  "mode": "extractive",
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

---

## Nasıl çalışır?

```
soru ─► [Arama: BM25] ─► [Sürüm çözümü] ─► [Yeterlilik eşiği] ─► [Yanıt üretimi] ─► yanıt + kaynak + çelişki raporu
         Türkçe normalize   family başına        skor + IDF-ağırlıklı   LLM (JSON şemalı) ya da
         F5 kök alma        güncel sürüm         kapsama                alıntılayan mod
```

| Dosya | Görev |
|---|---|
| `data/docs/*.md` | 10 kurgu doküman. Front-matter: `doc_id, family, title, version, status, effective_date` |
| `app/ingest.py` | Dokümanı okur, `##` başlıklarına göre bölümler, front-matter'ı doğrular |
| `app/textproc.py` | Türkçe normalizasyon (`I/İ/ı/i`), ASCII katlama, durak kelimeler, F5 kök alma |
| `app/index.py` | Bağımlılıksız BM25 + IDF-ağırlıklı sorgu kapsaması |
| `app/versioning.py` | **Güncel sürüm seçimi** ve seçim nedeninin üretilmesi |
| `app/retrieval.py` | Arama → sürüm çözümü → yeterlilik kararı |
| `app/llm.py`, `app/answer.py` | LLM çağrısı (JSON şemalı), alıntılayan mod, kaynak/çelişki raporu |
| `app/main.py`, `app/schemas.py` | FastAPI uç noktaları ve API sözleşmesi |

### Güncel sürüm nasıl seçiliyor?

Kural kodda, deterministik (LLM'e bırakılmadı — denetlenebilir olması için):

1. Aynı prosedürün sürümleri `family` alanıyla gruplanır (`iade-proseduru` → v1, v2).
2. Yürürlük tarihi `as_of`'tan sonra olan sürümler henüz geçerli değildir, elenir.
3. Kalanlar arasında **en yüksek sürüm numarası** (eşitlikte en yeni tarih) seçilir.
4. Elenen sürümlerin bölümleri **yanıt üretimine hiç verilmez**; LLM'in eski bilgiyi karıştırma şansı yoktur.
5. Yanıttaki `conflicts` alanı seçileni, elenenleri (alıntılarıyla) ve nedeni gösterir. Yalnızca yanıtta **kullanılan bölümle aynı bölümdeki** farklı sürümler raporlanır (ilgisiz gürültü yok).

Ek güvence: `status` alanı elle yazılıyor, bu yüzden yükleme sırasında sürüm numarasıyla tutarlılığı doğrulanır (`current` olmayan en yüksek sürüm varsa servis başlamaz).

### Cevapsız soru nasıl tespit ediliyor? İki katman

1. **Erişim katmanı (ucuz ön eleme):** En iyi bölümün BM25 skoru `< MIN_SCORE` **veya** IDF-ağırlıklı sorgu kapsaması `< MIN_COVERAGE` ise LLM'e hiç gidilmez. Kapsama: sorgu terimlerinin (IDF ağırlıklı) ne kadarı bölümde geçiyor. Korpusta hiç olmayan terimler ("HomeKit") en yüksek ağırlığı alır; "Lumora" gibi her yerde geçen terimler neredeyse hiç.
2. **LLM katmanı:** Model yalnızca numaralı bölümlerden yanıt vermeye ve bilgi yoksa `answerable=false` dönmeye yönlendirilir. Bu durumda `sources` boş döner.

---

## Teknik tercihler

| Karar | Neden |
|---|---|
| **FastAPI** (Python) | Önerilenlerden biri; küçük servis, hızlı doğrulama (Pydantic), otomatik Swagger. |
| **BM25, embedding değil** | 10 kısa doküman için ek model/vektör DB gereksiz; her skor açıklanabilir. Bedeli: eş anlamlıları yakalayamaz (aşağıda ölçüldü). |
| **Depolama: Markdown + bellekte indeks** | Dokümanlar zaten metin ve sürümleniyor; açılışta ~50 bölüm indekslenir. Veri büyürse SQLite FTS / vektör DB'ye geçilir. |
| **Sürüm çözümü kodda** | "Hangi sürüm geçerli?" bir iş kuralı; LLM tahminine bırakılırsa tutarsız ve denetlenemez olur. |
| **Bölüm bazlı (`##`) parçalama** | Bölüm başlığı hem doğal kaynak referansı ("İade Süresi") hem de anlamlı, kısa bir bağlam. |
| **F5 kök alma** | Türkçe IR'de basit ve makul bir taban çizgisi; morfolojik analizör bağımlılığı yok. Aksansız yazımı da yakalamak için ASCII katlama var. |
| **LLM: yapılandırılmış çıktı** (`output_config.format`, JSON şeması) | `answerable / answer / used_passages` alanları parse edilebilir; kaynak listesi modelin gerçekten dayandığı bölümlerden gelir. Yeni modellerde zorunlu `tool_choice` desteklenmediği için tool-call yerine bu yol seçildi. |
| **LLM'siz çalışma modu** | Anahtar/kota/ağ sorununda servis düşmez; test ve değerlendirme deterministik ve bedava koşar. |
| **Anahtar kodda yok** | Yalnızca `.env` (git'e girmez); `.env.example` örnek değerler içerir. |

---

## Değerlendirme

30 soru: 14 normal, 6 çelişkili (iade v1↔v2), 10 cevapsız. `eval/questions.json` içinde beklenen sonuçlar (cevaplanabilirlik, kaynak doküman, yanıtta bulunması/bulunmaması gereken ifadeler, seçilmesi gereken sürüm) tanımlı. **Beklenen ↔ gerçek çıktı tablosunun tamamı:** [`eval/results/results-extractive.md`](eval/results/results-extractive.md) (JSON: `results-extractive.json`).

İki bölüm var ve fark bilerek gösteriliyor:

- **dev (18 soru):** Eşikler (`MIN_SCORE`, `MIN_COVERAGE`) bu sorulardaki boşluklara bakılarak ayarlandı. İlk denemede 15/18 çıktı; hatalar sorudaki sözcüklerin dokümanda farklı biçimde geçmesindendi (eş anlam, ek farkı).
- **heldout (12 soru):** Eşikler dondurulduktan sonra yazıldı, tek seferde koşuldu, sonra **ayarlama yapılmadı**.

**Sonuç — alıntılayan mod (`--no-llm`), bu makinede koşturuldu:**

| | Geçen / toplam |
|---|---|
| dev | 18 / 18 |
| **heldout** | **8 / 12** |
| Normal | 13 / 14 |
| Çelişkili | 4 / 6 |
| Cevapsız | 9 / 10 |

Çelişkili sorularda 4 dev sorusunun hepsinde güncel sürüm (v2) seçildi ve eski değerler (14 gün, müşteri öder, telefon, 10 iş günü) yanıta girmedi; held-out'ta 2 çelişkili sorudan biri eşiğe takıldı, biri yanlış bölüm getirdi (aşağıda).

**Held-out'taki 4 hata ve nedenleri** (hepsi kelime eşleşmesine dayalı yöntemin sınırı):

| Soru | Ne oldu |
|---|---|
| H1 "…servis ne kadar sürede onarım yapar?" | "arıza/onarım" kelimeleri "Onarım ve Değişim" bölümünü öne çıkardı; cevap "Teknik Servis Süresi" bölümündeydi. |
| H7 "…kargo **parasını** ben mi ödüyorum?" | "para" ↔ "ücret" eş anlamlı ama eşleşmedi; kapsama eşiğin altında kaldı, servis "bilgi yok" dedi (yanlış ret). |
| H8 "İade için hangi **yoldan** başvuru yapılıyor?" | Doğru sürüm seçildi ama "İade Süresi" bölümü getirildi ("başvurular" kelimesi); "İade Başvurusu" bölümü ikinci sıradaydı. |
| H11 "…aboneliğimi başka bir kişiye **devredebilir** miyim?" | Yanlış bölüm eşiği geçti; alıntılayan mod bölümün soruyu gerçekten yanıtlayıp yanıtlamadığını kontrol edemez (yanlış kabul). |

> **LLM modu bu teslimde ölçülmedi.** Geliştirme sırasında geçerli bir API anahtarı kullanılmadı; `app/llm.py` canlı API'ye karşı **çalıştırılmadı**, yalnızca sahte (fake) üreticiyle test edildi (`tests/test_answer.py`). LLM'in H1/H8/H11 gibi durumları iyileştirmesi beklenir (aday bölümlerin hepsini okur ve cevaplanabilirliğe kendisi karar verir), ama bu bir varsayımdır. Ölçmek için `.env`'e anahtar koyup `python -m eval.run_eval` çalıştırmak yeterli; sonuç `eval/results/results-llm.md` dosyasına yazılır.

---

## Bilinen sınırlar

- **Sözcük tabanlı arama:** Eş anlamlı ve dolaylı ifadeleri kaçırır (H7). Doğal sonraki adım: embedding ile hibrit arama veya LLM ile sorgu yeniden yazma.
- **Eşikler küçük bir örnekle ayarlı:** 10 doküman/51 bölümde makul, gerçek bir korpusta yeniden kalibre edilmeli. `MIN_SCORE` BM25'in mutlak değerine dayandığı için korpus büyüklüğüne duyarlı.
- **Erişim katmanı yanlış ret verebilir (H7):** Eşik LLM'e gitmeden karar verdiği için, LLM'in cevaplayabileceği bir soruyu da eleyebilir. LLM modunda bu eşiğin gevşetilmesi düşünülebilir; ölçülmedi.
- **Alıntılayan mod cevaplanabilirliği doğrulayamaz (H11)** ve içeriğin tamamını aktarır; sohbet gibi kısa yanıt üretmez.
- **Eski sürümle ilgili sorular:** "2023'te iade süresi kaçtı?" gibi tarihsel sorular varsayılan olarak güncel sürümle yanıtlanır; yalnızca `as_of` parametresiyle eski sürüm sorgulanabilir. Soru metninden tarih çıkarma yapılmıyor.
- **Sürüm çözümü yalnızca `family` + sürüm/tarih ile çalışır.** Aynı sürümde birbiriyle çelişen iki doküman tespit edilmez; bölüm adı değişen sürümlerde eski bölüm eşleşmesi kaybolabilir.
- **LLM güvenliği:** Yalnızca güvenilir (kendi) dokümanlar indeksleniyor; kullanıcı sorusu talimat olarak yorumlanmasın diye sistem isteminde belirtildi ama bu ayrıca saldırı testine tabi tutulmadı.
- **Reddedilme (`refusal`) durumunda yedek model yok:** Model bir isteği reddederse servis "bilgi yok" döner; sunucu tarafı fallback ayarı kullanılmadı.
- **Kimlik doğrulama, hız sınırı, kalıcı log yok** — bir teslim projesi kapsamında bilinçli olarak dışarıda bırakıldı.
- **Tek dil / kurgu veri:** Türkçe dışı sorular ve gerçek müşteri verisi denenmedi.
