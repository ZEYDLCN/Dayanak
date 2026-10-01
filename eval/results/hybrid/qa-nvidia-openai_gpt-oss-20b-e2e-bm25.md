# QA sonuçları — `nvidia-openai_gpt-oss-20b-e2e-bm25`

- Vaka: 20 · koşu: 60 · **geçen koşu: 37/60**
- Kaynakta olmayan sayı (halüsinasyon bayrağı): **0** koşu
- LLM hatası → extractive'e düşen koşu: 0
- Dayanak korumasının reddettiği (uydurma sayı içeren) LLM yanıtı: 0 koşu
- Tutarlılık (aynı soru → aynı cevaplanabilirlik+kaynak): 19/20 vaka
- Gecikme: medyan 3.25s · maks 47.78s

| ID | Kategori | Soru | Beklenen | Yanıt (ilk koşu) | Kaynak | Sonuç |
|----|----------|------|----------|------------------|--------|-------|
| H01 | es-anlamli | Ürünü geri yollamak için elimde kaç gün var? | cevaplanır; içerir: ['30 gün']; içermez: ['14 gün'] | **30** gün (Not: Bu konuda v1 sürümünde farklı bilgi var; yürürlükteki v2 esas alınmıştır.) | iade-proseduru-v2›İade Süresi | #1 ✅<br>#2 ✅<br>#3 ✅ |
| H02 | es-anlamli | Geri gönderim masrafını ben mi karşılıyorum? | cevaplanır; içermez: ['müşteriye aittir'] | Geri gönderim masrafını **Lumora** karşılar. (Not: Bu konuda v1 sürümünde farklı bilgi var; yürürlükteki v2 esas alınmıştır.) | iade-proseduru-v2›İade Kargo Ücreti | #1 ✅<br>#2 ✅<br>#3 ✅ |
| H03 | es-anlamli | Üyeliğimi yenilerken kartımdan para çekilemezse ne olur? | cevaplanır | Bu soruyla ilgili doküman kayıtlarında yeterli bilgi bulunmuyor. Lütfen destek ekibiyle iletişime geçin. | — | #1 ❌ answerable=False, beklenen True<br>#2 ❌ answerable=False, beklenen True<br>#3 ❌ answerable=False, beklenen True |
| H04 | es-anlamli | Paketin içinden neler çıkıyor? | cevaplanır | Bu soruyla ilgili doküman kayıtlarında yeterli bilgi bulunmuyor. Lütfen destek ekibiyle iletişime geçin. | — | #1 ❌ answerable=False, beklenen True<br>#2 ❌ answerable=False, beklenen True<br>#3 ❌ answerable=False, beklenen True |
| H05 | dolayli | Cihazın ışığı sürekli kırmızı yanıyor, bu ne demek? | cevaplanır | Sürekli kırmızı LED, cihazın internet bağlantısının olmadığını gösterir. | sorun-giderme›LED Renklerinin Anlamı | #1 ✅<br>#2 ✅<br>#3 ✅ |
| H06 | dolayli | Hub'ım yere düşüp kırıldı, garanti bunu karşılar mı? | cevaplanır | Bu soruyla ilgili doküman kayıtlarında yeterli bilgi bulunmuyor. Lütfen destek ekibiyle iletişime geçin. | — | #1 ❌ answerable=False, beklenen True<br>#2 ❌ answerable=False, beklenen True<br>#3 ❌ answerable=False, beklenen True |
| H07 | es-anlamli | Sipariş verdikten sonra paket kaç günde kapıma gelir? | cevaplanır | Bu soruyla ilgili doküman kayıtlarında yeterli bilgi bulunmuyor. Lütfen destek ekibiyle iletişime geçin. | — | #1 ❌ answerable=False, beklenen True<br>#2 ✅<br>#3 ✅ |
| H08 | es-anlamli | Güvenlik kamerasının kayıtlarını ücretsiz pakette kaç gün görebilirim? | cevaplanır; içerir: ['7 gün'] | Ücretsiz pakette güvenlik kamerası kayıtlarını **7 gün** görebilirsiniz. | gizlilik-ve-veri-silme›Kamera Kayıtlarının Saklanması | #1 ✅<br>#2 ✅<br>#3 ✅ |
| H09 | dolayli | Evdeki asistan beni sürekli dinleyip buluta mı gönderiyor? | cevaplanır | Hayır, Hub sesli komut özelliği kullanılmadığı sürece mikrofon verisini kaydetmez veya buluta göndermez. | gizlilik-ve-veri-silme›Ses Verisi | #1 ✅<br>#2 ✅<br>#3 ✅ |
| H10 | es-anlamli | Tek bir merkeze en fazla kaç tane akıllı eşya bağlanır? | cevaplanır; içerir: ['50'] | Bir Lumora Hub'a en fazla **50** akıllı cihaz bağlanabilir. | kurulum-kilavuzu›Cihaz Sınırı | #1 ✅<br>#2 ✅<br>#3 ✅ |
| H11 | dolayli | Şirketim için kurumsal fatura kesilebilir mi? | cevaplanır; içerir: ['7 gün'] | Evet, şirketiniz için kurumsal fatura talep edilebilir. | abonelik-ve-faturalama›Fatura | #1 ❌ yanıtta yok: '7 gün'<br>#2 ✅<br>#3 ✅ |
| H12 | dolayli | Hafta sonu müşteri hizmetlerini telefonla arayabilir miyim? | cevaplanır | Bu soruyla ilgili doküman kayıtlarında yeterli bilgi bulunmuyor. Lütfen destek ekibiyle iletişime geçin. | — | #1 ❌ answerable=False, beklenen True<br>#2 ❌ answerable=False, beklenen True<br>#3 ❌ answerable=False, beklenen True |
| H13 | dolayli | Girişte ikinci bir doğrulama adımı eklemek istiyorum | cevaplanır | Bu soruyla ilgili doküman kayıtlarında yeterli bilgi bulunmuyor. Lütfen destek ekibiyle iletişime geçin. | — | #1 ❌ answerable=False, beklenen True<br>#2 ❌ answerable=False, beklenen True<br>#3 ❌ answerable=False, beklenen True |
| H14 | ingilizce | How long is the password reset link valid? | cevaplanır | Bu soruyla ilgili doküman kayıtlarında yeterli bilgi bulunmuyor. Lütfen destek ekibiyle iletişime geçin. | — | #1 ❌ answerable=False, beklenen True<br>#2 ❌ answerable=False, beklenen True<br>#3 ❌ answerable=False, beklenen True |
| H15 | es-anlamli | Parolamı birkaç kez yanlış girince ne kadar süre beklemem gerekir? | cevaplanır; içerir: ['15 dakika'] | Bu soruyla ilgili doküman kayıtlarında yeterli bilgi bulunmuyor. Lütfen destek ekibiyle iletişime geçin. | — | #1 ❌ answerable=False, beklenen True<br>#2 ❌ answerable=False, beklenen True<br>#3 ❌ answerable=False, beklenen True |
| H16 | cevapsiz-komsu | Hub Zigbee protokolünü destekliyor mu? | cevapsız | Bu soruyla ilgili doküman kayıtlarında yeterli bilgi bulunmuyor. Lütfen destek ekibiyle iletişime geçin. | — | #1 ✅<br>#2 ✅<br>#3 ✅ |
| H17 | cevapsiz-komsu | Servis randevusu nasıl alınır? | cevapsız | Bu soruyla ilgili doküman kayıtlarında yeterli bilgi bulunmuyor. Lütfen destek ekibiyle iletişime geçin. | — | #1 ✅<br>#2 ✅<br>#3 ✅ |
| H18 | cevapsiz-komsu | Aboneliğimi başka bir ülkede kullanabilir miyim? | cevapsız | Bu soruyla ilgili doküman kayıtlarında yeterli bilgi bulunmuyor. Lütfen destek ekibiyle iletişime geçin. | — | #1 ✅<br>#2 ✅<br>#3 ✅ |
| H19 | cevapsiz-komsu | Hub'ın boyutları ve ağırlığı nedir? | cevapsız | Bu soruyla ilgili doküman kayıtlarında yeterli bilgi bulunmuyor. Lütfen destek ekibiyle iletişime geçin. | — | #1 ✅<br>#2 ✅<br>#3 ✅ |
| H20 | cevapsiz-komsu | Lumora hangi kargo firmasıyla çalışıyor? | cevapsız | Bu soruyla ilgili doküman kayıtlarında yeterli bilgi bulunmuyor. Lütfen destek ekibiyle iletişime geçin. | — | #1 ✅<br>#2 ✅<br>#3 ✅ |
