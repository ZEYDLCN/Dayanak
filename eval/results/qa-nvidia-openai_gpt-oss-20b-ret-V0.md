# QA sonuçları — `nvidia-openai_gpt-oss-20b-ret-V0`

- Vaka: 24 · koşu: 72 · **geçen koşu: 58/72**
- Kaynakta olmayan sayı (halüsinasyon bayrağı): **0** koşu
- LLM hatası → extractive'e düşen koşu: 0
- Dayanak korumasının reddettiği (uydurma sayı içeren) LLM yanıtı: 0 koşu
- Tutarlılık (aynı soru → aynı cevaplanabilirlik+kaynak): 19/24 vaka
- Gecikme: medyan 1.94s · maks 10.52s

| ID | Kategori | Soru | Beklenen | Yanıt (ilk koşu) | Kaynak | Sonuç |
|----|----------|------|----------|------------------|--------|-------|
| R01 | dolayli-cevaplanabilir | Kargom hasarlı çıktı, kurye hâlâ kapıdayken ne yapmalıyım? | cevaplanır | Kargo görevlisiyle birlikte hasar tespit tutanağı düzenlenmelidir. | kargo-ve-teslimat›Hasarlı Paket | #1 ✅<br>#2 ✅<br>#3 ✅ |
| R02 | evet-hayir | Doğrulama kodunu telefonuma mesaj olarak alabilir miyim? | cevaplanır | Bu soruyla ilgili doküman kayıtlarında yeterli bilgi bulunmuyor. Lütfen destek ekibiyle iletişime geçin. | — | #1 ❌ answerable=False, beklenen True<br>#2 ❌ answerable=False, beklenen True<br>#3 ❌ answerable=False, beklenen True |
| R03 | evet-hayir | Cumartesi günü telefonla destek alabilir miyim? | cevaplanır | Hayır, cumartesi günü telefonla destek alamazsınız. | destek-kanallari-sla›Telefon Desteği | #1 ✅<br>#2 ❌ answerable=False, beklenen True<br>#3 ✅ |
| R04 | evet-hayir | Hub 5 GHz kablosuz ağa bağlanır mı? | cevaplanır | Bu soruyla ilgili doküman kayıtlarında yeterli bilgi bulunmuyor. Lütfen destek ekibiyle iletişime geçin. | — | #1 ❌ answerable=False, beklenen True<br>#2 ❌ answerable=False, beklenen True<br>#3 ✅ |
| R05 | dolayli-cevaplanabilir | Hub'ıma kaç tane akıllı lamba ekleyebilirim? | cevaplanır; içerir: ['50'] | Bir Lumora Hub'a en fazla **50** akıllı cihaz eklenebilir. | kurulum-kilavuzu›Cihaz Sınırı | #1 ✅<br>#2 ✅<br>#3 ✅ |
| R06 | dolayli-cevaplanabilir | Cihazımın alt kısmındaki seri numarasını nereden görürüm? | cevaplanır | Cihazınızın alt kısmındaki seri numarasını cihazın alt etiketinde görebilirsiniz. | garanti-ve-servis›Garanti Başvurusu | #1 ✅<br>#2 ✅<br>#3 ✅ |
| R07 | dolayli-cevaplanabilir | Aboneliğimi bugün iptal edersem bu ayın parası geri yatar mı? | cevaplanır | Hayır, aboneliği bugün iptal ettiğinizde bu ayın parası geri yatar. | abonelik-ve-faturalama›Abonelik İptali | #1 ✅<br>#2 ✅<br>#3 ✅ |
| R08 | es-anlamli | Kullanıcı kaydım silinmek istenirse bu işlem ne kadar sürer? | cevaplanır; içerir: ['30'] | Bu soruyla ilgili doküman kayıtlarında yeterli bilgi bulunmuyor. Lütfen destek ekibiyle iletişime geçin. | — | #1 ❌ answerable=False, beklenen True<br>#2 ❌ answerable=False, beklenen True<br>#3 ❌ answerable=False, beklenen True |
| R09 | dolayli-cevaplanabilir | Hub kırmızı yanıp sönüyorsa bu ne demek? | cevaplanır | Kırmızı LED yanıp sönüyorsa cihaz fabrika ayarlarına dönmüştür. | kurulum-kilavuzu›Fabrika Ayarlarına Dönme | #1 ✅<br>#2 ✅<br>#3 ❌ şunlardan biri yok: ['fabrika'] |
| R10 | es-anlamli | Siparişim kargoya verildikten sonra nasıl takip edebilirim? | cevaplanır | Siparişiniz kargoya verildiğinde, takip numarası SMS ile gönderilir ve bu numara ile kargo firmasının sitesinden gönderinizi izleyebilirsiniz. | kargo-ve-teslimat›Kargo Takibi | #1 ✅<br>#2 ✅<br>#3 ✅ |
| R11 | dolayli-cevaplanabilir | Gece yarısı Hub'ım turuncu yandı, fişini çekeyim mi? | cevaplanır | Hayır, turuncu LED yanarken cihazın fişini çekmeyin. | sorun-giderme›Güncelleme Sırasında Yapılmaması Gerekenler | #1 ✅<br>#2 ✅<br>#3 ✅ |
| R12 | evet-hayir | Ödemem iki kez başarısız olursa aboneliğim hemen kapanır mı? | cevaplanır | Bu soruyla ilgili doküman kayıtlarında yeterli bilgi bulunmuyor. Lütfen destek ekibiyle iletişime geçin. | — | #1 ❌ answerable=False, beklenen True<br>#2 ✅<br>#3 ✅ |
| R13 | dolayli-cevaplanabilir | Ücretsiz üyelikte kamera görüntülerim kaç gün durur? | cevaplanır; içerir: ['7 gun'] | Ücretsiz üyelikte kamera görüntüleri **7 gün** sürer. | gizlilik-ve-veri-silme›Kamera Kayıtlarının Saklanması | #1 ✅<br>#2 ✅<br>#3 ✅ |
| R14 | evet-hayir | Lumora+ aboneleri destekten daha hızlı yanıt alır mı? | cevaplanır; içerir: ['4 saat'] | Lumora+ aboneleri, acil talepler için ilk yanıt süresi 4 saat olduğundan, destekten daha hızlı yanıt alır. | destek-kanallari-sla›Öncelikli Talepler | #1 ✅<br>#2 ✅<br>#3 ✅ |
| R15 | cevapsiz-komsu | Hub'ım bozulursa evde otururken servis elemanı gelip bakar mı? | cevapsız | Bu soruyla ilgili doküman kayıtlarında yeterli bilgi bulunmuyor. Lütfen destek ekibiyle iletişime geçin. | — | #1 ✅<br>#2 ✅<br>#3 ✅ |
| R16 | cevapsiz-komsu | Kaç Lumora+ üyesi aynı anda bulut kaydı izleyebilir? | cevapsız | Bu soruyla ilgili doküman kayıtlarında yeterli bilgi bulunmuyor. Lütfen destek ekibiyle iletişime geçin. | — | #1 ✅<br>#2 ✅<br>#3 ✅ |
| R17 | cevapsiz-komsu | Servise gönderdiğim cihazın kargo ücretini kim öder? | cevapsız | Lumora kargo ücretini karşılar. (Not: Bu konuda v1 sürümünde farklı bilgi var; yürürlükteki v2 esas alınmıştır.) | iade-proseduru-v2›İade Kargo Ücreti | #1 ❌ answerable=True, beklenen False<br>#2 ❌ answerable=True, beklenen False<br>#3 ❌ answerable=True, beklenen False |
| R18 | cevapsiz-komsu | Gravürlü ürünlerde değişim yapılıyor mu? | cevapsız | Bu soruyla ilgili doküman kayıtlarında yeterli bilgi bulunmuyor. Lütfen destek ekibiyle iletişime geçin. | — | #1 ✅<br>#2 ✅<br>#3 ✅ |
| R19 | cevapsiz-komsu | Şifremi belirlerken özel karakter kullanmak zorunda mıyım? | cevapsız | Bu soruyla ilgili doküman kayıtlarında yeterli bilgi bulunmuyor. Lütfen destek ekibiyle iletişime geçin. | — | #1 ✅<br>#2 ✅<br>#3 ✅ |
| R20 | cevapsiz-komsu | Canlı destek yoğunken bekleme süresi ne kadar? | cevapsız | Bu soruyla ilgili doküman kayıtlarında yeterli bilgi bulunmuyor. Lütfen destek ekibiyle iletişime geçin. | — | #1 ✅<br>#2 ✅<br>#3 ✅ |
| R21 | cevapsiz-komsu | Hub'ın Wi-Fi şifresini değiştirdiğimde hangi LED rengi yanar? | cevapsız | Bu soruyla ilgili doküman kayıtlarında yeterli bilgi bulunmuyor. Lütfen destek ekibiyle iletişime geçin. | — | #1 ✅<br>#2 ✅<br>#3 ✅ |
| R22 | cevapsiz-komsu | Kurumsal faturayı 10 gün sonra istesem düzenlenir mi? | cevapsız | Bu soruyla ilgili doküman kayıtlarında yeterli bilgi bulunmuyor. Lütfen destek ekibiyle iletişime geçin. | — | #1 ✅<br>#2 ✅<br>#3 ✅ |
| R23 | cevapsiz-komsu | Lumora+ aboneliğinde aile paylaşımı özelliği var mı? | cevapsız | Bu soruyla ilgili doküman kayıtlarında yeterli bilgi bulunmuyor. Lütfen destek ekibiyle iletişime geçin. | — | #1 ✅<br>#2 ✅<br>#3 ✅ |
| R24 | cevapsiz-komsu | Telefonumu kaybettim, iki adımlı doğrulamayı nasıl kapatırım? | cevapsız | Bu soruyla ilgili doküman kayıtlarında yeterli bilgi bulunmuyor. Lütfen destek ekibiyle iletişime geçin. | — | #1 ✅<br>#2 ✅<br>#3 ✅ |
