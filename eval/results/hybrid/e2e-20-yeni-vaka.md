# Uçtan uca arama karşılaştırması (gerçek LLM: gpt-oss-20b)

| Yapılandırma | koşu | geçen | uydurma | gereksiz ret | yanlış içerik | uçtan uca medyan / p90 (sn) | arama medyan / p90 (ms) |
|---|---|---|---|---|---|---|---|
| `bm25` | 60 | **37** | 0 | 22 | 1 | 4.20 / 22.49 | 0.7 / 1.0 |
| `bm25b` | 60 | **39** | 0 | 17 | 4 | 2.20 / 6.58 | 0.8 / 1.2 |
| `minilm` | 60 | **44** | 0 | 15 | 1 | 2.67 / 5.60 | 23.7 / 28.9 |
| `potion` | 60 | **44** | 0 | 15 | 1 | 3.21 / 6.46 | 2.7 / 3.5 |
| `mpnet` | 60 | **38** | 0 | 19 | 3 | 2.15 / 6.04 | 43.0 / 75.6 |
| `e5large` | 60 | **40** | 0 | 16 | 4 | 2.48 / 3.76 | 190.9 / 237.1 |

## Vaka bazında (tekrarlardan kaçı geçti)

| ID | Kategori | Soru | bm25 | bm25b | minilm | potion | mpnet | e5large |
|---|---|---|---|---|---|---|---|---|
| H01 | es-anlamli | Ürünü geri yollamak için elimde kaç gün var? | 3 | 3 | 3 | 3 | 3 | 3 |
| H02 | es-anlamli | Geri gönderim masrafını ben mi karşılıyorum? | 3 | 2 | 3 | 3 | 3 | 3 |
| H03 | es-anlamli | Üyeliğimi yenilerken kartımdan para çekilemezse ne olur? | 0 | 0 | 0 | 0 | 0 | 0 |
| H04 | es-anlamli | Paketin içinden neler çıkıyor? | 0 | 0 | 0 | 0 | 0 | 0 |
| H05 | dolayli | Cihazın ışığı sürekli kırmızı yanıyor, bu ne demek? | 3 | 3 | 3 | 3 | 3 | 3 |
| H06 | dolayli | Hub'ım yere düşüp kırıldı, garanti bunu karşılar mı? | 0 | 1 | 3 | 0 | 0 | 0 |
| H07 | es-anlamli | Sipariş verdikten sonra paket kaç günde kapıma gelir? | 2 | 3 | 3 | 3 | 3 | 3 |
| H08 | es-anlamli | Güvenlik kamerasının kayıtlarını ücretsiz pakette kaç gün görebilirim? | 3 | 3 | 3 | 3 | 3 | 3 |
| H09 | dolayli | Evdeki asistan beni sürekli dinleyip buluta mı gönderiyor? | 3 | 3 | 3 | 3 | 3 | 3 |
| H10 | es-anlamli | Tek bir merkeze en fazla kaç tane akıllı eşya bağlanır? | 3 | 3 | 3 | 3 | 3 | 3 |
| H11 | dolayli | Şirketim için kurumsal fatura kesilebilir mi? | 2 | 0 | 2 | 2 | 0 | 0 |
| H12 | dolayli | Hafta sonu müşteri hizmetlerini telefonla arayabilir miyim? | 0 | 3 | 3 | 3 | 1 | 2 |
| H13 | dolayli | Girişte ikinci bir doğrulama adımı eklemek istiyorum | 0 | 0 | 0 | 3 | 1 | 2 |
| H14 | ingilizce | How long is the password reset link valid? | 0 | 0 | 0 | 0 | 0 | 0 |
| H15 | es-anlamli | Parolamı birkaç kez yanlış girince ne kadar süre beklemem gerekir? | 0 | 0 | 0 | 0 | 0 | 0 |
| H16 | cevapsiz-komsu | Hub Zigbee protokolünü destekliyor mu? | 3 | 3 | 3 | 3 | 3 | 3 |
| H17 | cevapsiz-komsu | Servis randevusu nasıl alınır? | 3 | 3 | 3 | 3 | 3 | 3 |
| H18 | cevapsiz-komsu | Aboneliğimi başka bir ülkede kullanabilir miyim? | 3 | 3 | 3 | 3 | 3 | 3 |
| H19 | cevapsiz-komsu | Hub'ın boyutları ve ağırlığı nedir? | 3 | 3 | 3 | 3 | 3 | 3 |
| H20 | cevapsiz-komsu | Lumora hangi kargo firmasıyla çalışıyor? | 3 | 3 | 3 | 3 | 3 | 3 |
