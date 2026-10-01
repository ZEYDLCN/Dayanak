# QA sonuçları — `nvidia-openai_gpt-oss-20b-tr-V4`

- Vaka: 15 · koşu: 45 · **geçen koşu: 44/45**
- Kaynakta olmayan sayı (halüsinasyon bayrağı): **0** koşu
- LLM hatası → extractive'e düşen koşu: 0
- Dayanak korumasının reddettiği (uydurma sayı içeren) LLM yanıtı: 0 koşu
- Tutarlılık (aynı soru → aynı cevaplanabilirlik+kaynak): 14/15 vaka
- Gecikme: medyan 2.05s · maks 9.86s

| ID | Kategori | Soru | Beklenen | Yanıt (ilk koşu) | Kaynak | Sonuç |
|----|----------|------|----------|------------------|--------|-------|
| T01 | konu-aktarimi | Garanti başvurusunu telefonla yapabilir miyim? | cevapsız | Bu soruyla ilgili doküman kayıtlarında yeterli bilgi bulunmuyor. Lütfen destek ekibiyle iletişime geçin. | — | #1 ✅<br>#2 ✅<br>#3 ✅ |
| T02 | konu-aktarimi | Onarım için cihazı gönderirken ücretsiz kargo kodu alır mıyım? | cevapsız | Bu soruyla ilgili doküman kayıtlarında yeterli bilgi bulunmuyor. Lütfen destek ekibiyle iletişime geçin. | — | #1 ✅<br>#2 ✅<br>#3 ❌ answerable=True, beklenen False |
| T03 | konu-aktarimi | Servise gönderdiğim cihazın para iadesi kaç iş günü sürer? | cevapsız | Bu soruyla ilgili doküman kayıtlarında yeterli bilgi bulunmuyor. Lütfen destek ekibiyle iletişime geçin. | — | #1 ✅<br>#2 ✅<br>#3 ✅ |
| T04 | konu-aktarimi | Şifre sıfırlama bağlantısı gelmezse kaç dakika beklemeliyim? | cevapsız | Bu soruyla ilgili doküman kayıtlarında yeterli bilgi bulunmuyor. Lütfen destek ekibiyle iletişime geçin. | — | #1 ✅<br>#2 ✅<br>#3 ✅ |
| T05 | konu-aktarimi | Hesabım kilitliyken canlı destek kilidi açar mı? | cevapsız | Bu soruyla ilgili doküman kayıtlarında yeterli bilgi bulunmuyor. Lütfen destek ekibiyle iletişime geçin. | — | #1 ✅<br>#2 ✅<br>#3 ✅ |
| T06 | konu-aktarimi | Gece güncellemesi başarısız olursa ne olur? | cevapsız | Bu soruyla ilgili doküman kayıtlarında yeterli bilgi bulunmuyor. Lütfen destek ekibiyle iletişime geçin. | — | #1 ✅<br>#2 ✅<br>#3 ✅ |
| T07 | konu-aktarimi | Hub'ı fabrika ayarlarına döndürürsem hesabım da silinir mi? | cevapsız | Bu soruyla ilgili doküman kayıtlarında yeterli bilgi bulunmuyor. Lütfen destek ekibiyle iletişime geçin. | — | #1 ✅<br>#2 ✅<br>#3 ✅ |
| T08 | konu-aktarimi | Teslim edilemeyen gönderi depoya dönerse ücret iadesi nasıl olur? | cevapsız | Bu soruyla ilgili doküman kayıtlarında yeterli bilgi bulunmuyor. Lütfen destek ekibiyle iletişime geçin. | — | #1 ✅<br>#2 ✅<br>#3 ✅ |
| T09 | konu-aktarimi | Ürün iadesinde sipariş numarasını nereden bulurum? | cevapsız | Bu soruyla ilgili doküman kayıtlarında yeterli bilgi bulunmuyor. Lütfen destek ekibiyle iletişime geçin. | — | #1 ✅<br>#2 ✅<br>#3 ✅ |
| T10 | kontrol-cevaplanabilir | Garanti süresince onarımdayken bana yedek cihaz verilir mi? | cevaplanır | Hayır, servis süresince geçici cihaz verilmez. | garanti-ve-servis›Teknik Servis Süresi | #1 ✅<br>#2 ✅<br>#3 ✅ |
| T11 | kontrol-cevaplanabilir | İade için ücretsiz kargo kodunu nasıl alırım? | cevaplanır | Başvuru onaylandığında e-postayla ücretsiz kargo kodu gönderilir. (Not: Bu konuda v1 sürümünde farklı bilgi var; yürürlükteki v2 esas alınmıştır.) | iade-proseduru-v2›İade Kargo Ücreti | #1 ✅<br>#2 ✅<br>#3 ✅ |
| T12 | kontrol-cevaplanabilir | Garanti başvurusu için seri numarasını uygulamada nerede görürüm? | cevaplanır | Seri numarasını Lumora Home uygulamasında Cihaz Bilgisi ekranında görebilirsiniz. | garanti-ve-servis›Garanti Başvurusu | #1 ✅<br>#2 ✅<br>#3 ✅ |
| T13 | kontrol-cevaplanabilir | Kargo takip numarası bana nasıl iletilir? | cevaplanır | Kargo takip numarası SMS ile gönderilir. | kargo-ve-teslimat›Kargo Takibi | #1 ✅<br>#2 ✅<br>#3 ✅ |
| T14 | kontrol-cevaplanabilir | Abonelik ödemesi başarısız olursa sistem kaç kez yeniden dener? | cevaplanır; içerir: ['3'] | Sistem, kart çekimi başarısız olursa **3 kez** yeniden dener. | abonelik-ve-faturalama›Ödeme Hataları | #1 ✅<br>#2 ✅<br>#3 ✅ |
| T15 | kontrol-cevaplanabilir | Hasarlı kargo için tutanak tutulmazsa başvurum kabul edilir mi? | cevaplanır | Hayır, hasarlı paket için tutanak tutulmazsa başvuru değerlendirilemeyebilir. | kargo-ve-teslimat›Hasarlı Paket | #1 ✅<br>#2 ✅<br>#3 ✅ |
