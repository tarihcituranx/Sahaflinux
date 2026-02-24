# Dijital Sahaf - Sahaflinux

> **Not:** Ana uygulama (app.py) şu anda bakımda. Sadece /pages klasöründeki dosyalar aktif ve kullanılabilir durumdadır. Lütfen uygulamayı Streamlit ile çalıştırırken direkt pages tabanlı deneyimleyiniz!

## Genel Bakış

Bu repo, dijital arşiv ve çeşitli kamuya açık bilgileri erişilebilir ve işlevsel hâle getiren bir dizi Streamlit tabanlı sayfa içeriyor.
Farklı sitelerden, arşivlerden ve servislere odaklanan modüller içerir. Modern Python kütüphaneleriyle geliştirilmiştir.

Ana işlevler / bölümler şunlardır:

- Dijital Kaynaklar: Brave API, Dergipark, Project Gutenberg, Sidestone Press gibi dijital kütüphanelerde arama ve indirme.
- Kamu İlan: Türkiye kamu ilanları takip ve detaylı filtreleme.
- Milli Saraylar: millisaraylar.gov.tr üzerindeki güncel personel alım ve duyuruların takibi, AI özetler ve PDF analizi.
- Finans: Döviz, Altın ve Kripto para canlı takip paneli.
- Oyun Fırsatları: GamerPower API ile ücretsiz oyun / loot takip ve açıklamaların AI ile Türkçeleştirilmesi.
- Sınavlar: 2026 yılı ÖSYM/MEB sınav takvimi, live sayaçlarla birlikte.
- YouTube İndirici: 403 hatasına karşı dayanıklı, otomatik ffmpeg kurabilen gelişmiş video/ses indirme modülü.
- Örümcek: Scrapling ve Groq entegrasyonuyla verdiğiniz web sayfasından API/endpoint analizi.
- ...ve diğer ek Streamlit sayfaları.

## Kurulum

1. Gerekenler  
   Python 3.9+  
   Tavsiye edilen paketler: streamlit, requests, pandas, beautifulsoup4, cloudscraper, selenium, PyPDF2, deep-translator, (isteğe göre: scrapling)

2. Kurulum (örnek)  
   ```bash
   git clone https://github.com/tarihcituranx/Sahaflinux.git
   cd Sahaflinux
   pip install -r requirements.txt   # (varsa)
   # veya temel paketleri elle kurun
   pip install streamlit requests pandas beautifulsoup4 cloudscraper selenium PyPDF2 deep-translator
   ```

3. Gizli Anahtarlar (Opsiyonel / Bazı bölümler için gerekli)  
   - pages/arama_motoru.py ve pages/Dijital Kaynaklar.py gibi bazı sayfalar için .streamlit/secrets.toml içine Brave API anahtarınızı ekleyin:
     ```toml
     BRAVE_API_KEY = "BURAYA_KENDİ_KEYİNİZİ_YAZIN"
     ```
   - AI çeviri/özet için Groq veya OpenAI anahtarı gerekebilir.

## Kullanım

Yalnızca Streamlit ile pages klasöründeki dosyalar üzerinden çalıştırın:
```bash
streamlit run pages/Dijital\ Kaynaklar.py
# veya başka bir modül için
streamlit run pages/Finans.py
```
Tüm modüller ayrı ayrı çalışır.  
Her bir dosya (sayfa), açıldığı anda Streamlit ile kendi web arayüzünü başlatır.

## Sayfa Özellikleri (Kısa)

- Dijital Kaynaklar.py: Arama motoru (Brave), makale, kitap, dergi, arkeolojik kaynak bulucu ve indirici.
- Kamu İlan.py: Güncel devlet, kamu, personel ilanlarının detaylı takibi ve filtrelemesi.
- Milli Saraylar.py: Milli Saraylar ilanları, PDF ekleriyle birlikte AI özetli analiz.
- YTVideo.py: Youtube ses/video indirme (katı korumalara karşı özel çözüm).
- Finans.py: Döviz, altın, kripto dövizleri ve anlık finans panosu.
- Oyun Fırsatları.py: Ücretsiz dijital oyun/hediye bulucu & takip.
- Sınavlar.py: Yaklaşan sınavlar için geri sayım sayacı.
- Örümcek.py: Bir web sayfasının API yapısını otomatik keşfettir, Swagger çıktısı.
- ve diğer modüller...

## Katkı / Lisans

Her türlü katkıya açıktır.  
Lisans: MIT (veya dosyalardaki belirli uyarılara göre).

## Notlar & Destek

- Her bir sayfanın üst kısmında veya sidebarında kısa kullanım açıklamaları bulunur.
- app.py ana sayfa şimdilik bakımda, DİREKT OLARAK KULLANILMAZ.
- Sorularınız için: https://github.com/tarihcituranx/Sahaflinux/issues

---