"""Tanıtım videosu metni. Her sahne için ekran yazısı ve seslendirme cümlesi.

Rakamlar proje ölçümlerinden gelir (README > Değerlendirme):
  - 48 cevapsız/komşu-cevapsız test koşusunda 0 uydurma yanıt
  - klasik değerlendirme setinde 29/30
  - LLM çağrısı medyan gecikmesi 1,3 sn
"""

VOICE = "tr-TR-AhmetNeural"  # kurumsal, sakin erkek sesi (alternatif: tr-TR-EmelNeural)
RATE = "+18%"

# Seslendirme metinleri (sayılar okunuşuyla yazıldı). Kısa tutuldu: bilgiyi ekran yazıları taşır.
NARRATION = [
    "Lumora Bilgi Asistanı. Doğru cevap, doğru kaynaktan.",
    "Tek bir yanlış cevap, müşteri güvenini bitirebilir.",
    "Lumora dokümanları okur, Türkçe soruları saniyeler içinde yanıtlar. "
    "Belge, sürüm ve bölüm her cevapta görünür. Güncel sürümü kendisi seçer.",
    "Uydurmaya izin yok. Kanıt cümlesi belgeden aynen doğrulanır. Bilgi yoksa, açıkça söyler.",
    "Kırk sekiz cevapsız testte, sıfır uydurma. Otuz sorunun yirmi dokuzunda doğru yanıt.",
    "Hızlı. Kaynaklı. Güvenilir.",
]
