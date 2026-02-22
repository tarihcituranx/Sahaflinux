import time
import re
import io
from collections import defaultdict
from urllib.parse import urljoin
from datetime import datetime, date, timezone, timedelta

TZ_TURKIYE = timezone(timedelta(hours=3))

import requests
import urllib3
import streamlit as st
from bs4 import BeautifulSoup
from groq import Groq

# PyPDF2 opsiyonel - kurulu değilse PDF içeriği çekilmez ama link gösterilir
try:
    import PyPDF2
    PDF_DESTEKLI = True
except ImportError:
    PDF_DESTEKLI = False

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ─────────────────────────────────────────────
# AYARLAR
# ─────────────────────────────────────────────
ANASAYFA_URL      = "https://www.millisaraylar.gov.tr/Kurumsal/PersonelAlimDuyuru"
GROQ_API_KEY      = st.secrets["GROQ_API_KEY"]
GROQ_MODEL        = "llama-3.3-70b-versatile"
RATE_LIMIT_SANIYE = 4

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

TURKCE_AYLAR = {
    "ocak":1,"subat":2,"mart":3,"nisan":4,"mayis":5,
    "haziran":6,"temmuz":7,"agustos":8,"eylul":9,
    "ekim":10,"kasim":11,"aralik":12
}

KATEGORILER = [
    (["nihai sonuc","nihai sonucu"],                     "🏆 Nihai Sonuç"),
    (["yerlestirme sonuc"],                              "📋 Yerleştirme Sonucu"),
    (["sozlu sinav sonuc","mulakat sinav sonuc"],         "📝 Sözlü Sınav Sonucu"),
    (["uygulamali sinav sonuc"],                         "🔬 Uygulamalı Sınav Sonucu"),
    (["sinav sonuc","sinavi sonuc"],                     "📊 Sınav Sonucu"),
    (["basari puani"],                                   "📊 Başarı Puanları"),
    (["sozlu sinav takvim"],                             "📅 Sözlü Sınav Takvimi"),
    (["uygulamali sinav takvim"],                        "📅 Uygulamalı Sınav Takvimi"),
    (["sinav takvim"],                                   "📅 Sınav Takvimi"),
    (["basvuru kontrol"],                                "🔍 Başvuru Kontrol"),
    (["basvuru"],                                        "📨 Başvuru Duyurusu"),
    (["evrak teslim"],                                   "📦 Evrak Teslimi"),
    (["alim","alimina","kadro","isci alim"],             "📢 Personel Alımı"),
    (["giris sinavi","sinav duyuru"],                    "✏️ Sınav Duyurusu"),
    (["kpss","ekpss"],                                   "🎯 KPSS/EKPSS"),
    (["duyuru"],                                         "📣 Genel Duyuru"),
]

# ─────────────────────────────────────────────
# YARDIMCI
# ─────────────────────────────────────────────
def normalize(m):
    return (m.lower()
            .replace("ı","i").replace("ğ","g").replace("ü","u")
            .replace("ş","s").replace("ö","o").replace("ç","c")
            .replace("İ","i").replace("Ğ","g").replace("Ü","u")
            .replace("Ş","s").replace("Ö","o").replace("Ç","c"))

def kategori_bul(baslik):
    k = normalize(baslik)
    for liste, etiket in KATEGORILER:
        for a in liste:
            if a in k:
                return etiket
    return "📣 Duyuru"

TARIH_RE = re.compile(r"^\d{1,2}\s+\S+\s+\d{4}$")

def tarih_link_mi(m):
    return bool(TARIH_RE.match(m.strip()))

def yil_metinden(m):
    if not m: return None
    r = re.search(r"\b\d{1,2}\.\d{1,2}\.(20\d{2})\b", m)
    if r: return int(r.group(1))
    r = re.search(r"\b(20\d{2})/\d+\b", m)
    if r: return int(r.group(1))
    n = normalize(m)
    r = re.search(r"\d{1,2}\s+(\w+)\s+(20\d{2})", n)
    if r and r.group(1) in TURKCE_AYLAR: return int(r.group(2))
    if tarih_link_mi(m):
        r = re.search(r"(20\d{2})", m)
        if r: return int(r.group(1))
    return None

def container_bul(link):
    for tag in ["li","tr","article","div"]:
        p = link.find_parent(tag)
        if p: return p
    return link.parent

def yil_container_dan(link):
    c = container_bul(link)
    if not c: return None
    for a in c.find_all("a"):
        t = a.get_text(strip=True)
        if tarih_link_mi(t):
            y = yil_metinden(t)
            if y: return y
    return yil_metinden(c.get_text(" ", strip=True))

# ─────────────────────────────────────────────
# VERİ ÇEKME
# ─────────────────────────────────────────────
def duyurulari_cek_raw():
    try:
        resp = requests.get(ANASAYFA_URL, headers=HEADERS, verify=False, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        st.error(f"Sayfa çekilemedi: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    gorulen, duyurular, son_yil = set(), [], None

    for link in soup.find_all("a"):
        href   = link.get("href","")
        baslik = link.get_text(strip=True)
        if not href or not baslik: continue

        if tarih_link_mi(baslik):
            y = yil_metinden(baslik)
            if y: son_yil = y
            continue

        if "DuyuruDetay" not in href: continue
        tam = urljoin(ANASAYFA_URL, href)
        if tam in gorulen: continue
        gorulen.add(tam)

        yil = yil_metinden(baslik) or yil_container_dan(link) or son_yil
        duyurular.append({
            "baslik"  : baslik,
            "link"    : tam,
            "yil"     : yil,
            "kategori": kategori_bul(baslik),
        })
    return duyurular

def simdi_tr():
    """Türkiye saatini döner (UTC+3)."""
    return datetime.now(TZ_TURKIYE)

def veri_guncelle():
    """Veriyi çekip session_state'e kaydeder."""
    with st.spinner("🔄 Duyurular güncelleniyor..."):
        duyurular = duyurulari_cek_raw()
    st.session_state["duyurular"]      = duyurular
    st.session_state["son_guncelleme"] = simdi_tr()
    return duyurular

def veri_yukle():
    """Günlük otomatik güncelleme + ilk yükleme."""
    simdi = simdi_tr()

    if "duyurular" not in st.session_state:
        return veri_guncelle()

    son = st.session_state.get("son_guncelleme")
    if son and son.date() < simdi.date():
        return veri_guncelle()

    return st.session_state["duyurular"]

# ─────────────────────────────────────────────
# İLAN İÇERİK + PDF LİNKLERİ
# ─────────────────────────────────────────────
def pdf_icerigi_cek(pdf_url):
    """PDF URL'sinden metin çeker. PyPDF2 kurulu değilse boş döner."""
    if not PDF_DESTEKLI:
        return ""
    try:
        resp = requests.get(pdf_url, headers=HEADERS, verify=False, timeout=20)
        resp.raise_for_status()
        reader = PyPDF2.PdfReader(io.BytesIO(resp.content))
        metin = ""
        for sayfa in reader.pages[:5]:  # en fazla 5 sayfa
            metin += sayfa.extract_text() or ""
        return metin[:3000].strip()
    except Exception:
        return ""

# Anlamlı olmayan, jenerik link metinleri (bunlardan dosya adı çıkarılmaz)
GORSUZ_LINK_METINLERI = {
    "dosyayi gorun", "goruntule", "goster", "indir", "tikla",
    "tiklayin", "tiklayniz", "icin tiklayin", "buraya tiklayin",
    "download", "open", "view", "dosya", "pdf", "click here"
}

def pdf_ad_bul(a_tag, href):
    """
    PDF dosyası için anlamlı bir ad bulmaya çalışır.
    Öncelik sırası:
      1. Linkin kendi metni (jenerik değilse)
      2. Link öncesindeki kardeş/ebeveyn elementlerin metni (.pdf içeriyorsa)
      3. URL'den dosya adı
    """
    from urllib.parse import unquote

    link_metni = a_tag.get_text(strip=True)
    norm_link  = normalize(link_metni)

    # Anlamlı link metni → direkt kullan
    if (link_metni
            and len(link_metni) > 4
            and not any(j in norm_link for j in GORSUZ_LINK_METINLERI)):
        return link_metni

    # Yakın çevrede .pdf içeren metin ara (genellikle dosya adı linkin üstündedir)
    for onceki in [a_tag.find_previous_sibling(), a_tag.parent,
                   a_tag.parent.find_previous_sibling() if a_tag.parent else None]:
        if onceki is None:
            continue
        try:
            metin = onceki.get_text(strip=True)
            if metin and ".pdf" in metin.lower() and len(metin) < 120:
                return metin
        except Exception:
            pass

    # Fallback: URL'den dosya adı
    dosya = href.split("/")[-1].split("?")[0]
    try:
        dosya = unquote(dosya)
    except Exception:
        pass
    return dosya or "Belge"


def ilan_icerik_cek(url):
    """
    İlan sayfasından ham metin ve PDF linklerini çeker.
    - Sadece ana içerik alanındaki PDF'leri alır (nav/footer/sidebar hariç)
    - PDF adını linkin metninden değil, dosya adından veya yakın başlıktan alır
    Döner: (metin: str, pdf_listesi: list[dict])
      pdf_listesi elemanları: {"ad": str, "url": str, "icerik": str}
    """
    try:
        resp = requests.get(url, headers=HEADERS, verify=False, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # ── Ana içerik alanını bul ──
        # nav / header / footer içindeki PDF'leri istemiyoruz
        icerik_alani = (
            soup.find("main")
            or soup.find("article")
            or soup.find(id=re.compile(r"content|icerik|detay|main", re.I))
            or soup.find(class_=re.compile(r"content|icerik|detay|main", re.I))
            or soup  # hiçbiri yoksa tüm sayfa
        )

        # ── PDF linklerini topla ──
        pdf_listesi = []
        gorulen_pdf = set()

        for a in icerik_alani.find_all("a", href=True):
            href = a["href"]

            # .pdf uzantılı veya site içi GetFile/dosya yolları
            href_lower = href.lower()
            if not (href_lower.endswith(".pdf")
                    or "getfile" in href_lower
                    or ("dosya" in href_lower and "millisaraylar" in urljoin(url, href))):
                continue

            # Nav / header / footer içindeyse atla
            icerik_disi = False
            ata = a.parent
            for _ in range(10):
                if ata is None:
                    break
                tag_adi = getattr(ata, "name", "") or ""
                cls_id  = " ".join(ata.get("class", [])) + " " + (ata.get("id") or "")
                if tag_adi in ("nav", "header", "footer"):
                    icerik_disi = True
                    break
                if re.search(r"\bnav\b|sidebar|footer|header|menu", cls_id, re.I):
                    icerik_disi = True
                    break
                ata = ata.parent
            if icerik_disi:
                continue

            tam_url = urljoin(url, href)
            if tam_url in gorulen_pdf:
                continue
            gorulen_pdf.add(tam_url)

            ad     = pdf_ad_bul(a, href)
            icerik = pdf_icerigi_cek(tam_url)
            pdf_listesi.append({"ad": ad, "url": tam_url, "icerik": icerik})

        # ── Sayfa ham metni ──
        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()
        satirlar = [s for s in soup.get_text("\n", strip=True).splitlines() if s.strip()]
        metin = "\n".join(satirlar[:400])

        return metin, pdf_listesi

    except Exception as e:
        return f"İçerik alınamadı: {e}", []

# ─────────────────────────────────────────────
# GROQ AI
# ─────────────────────────────────────────────
def groq_ozet(baslik, icerik, pdf_listesi=None):
    su_an   = time.time()
    bekleme = RATE_LIMIT_SANIYE - (su_an - st.session_state.get("son_groq_istegi", 0))
    if bekleme > 0:
        time.sleep(bekleme)
    try:
        client = Groq(api_key=GROQ_API_KEY)
        sistem = """Sen Türkiye kamu kurumlarındaki personel alım ilanlarını analiz eden bir uzmansın.

Görevin: Verilen ilan metnini AYNEN ve EKSİKSİZ analiz etmek.

KRİTİK KURALLAR:
1. Metinde geçen TÜM sayısal ve spesifik bilgileri yaz: ölçüler (mm, cm), adetler, saatler, tarihler, adresler, banka adları, şube adları, form adları vb.
2. Listeler varsa (örn: istenen belgeler) HER maddeyi ayrı satırda numaralı yaz, hiçbirini atlama.
3. Metinde OLMAYAN hiçbir bilgiyi uydurma.
4. İlanda PDF dosyaları varsa bunları da ⬇️ **Ekli Dosyalar** başlığı altında listele.
5. Yanıtını Türkçe ver.

Şu başlıkları kullan (bilgi yoksa o başlığı atla):

📋 **İlan Özeti**
🎯 **Aranan Pozisyon(lar)**
🔢 **Alınacak Kişi Sayısı**
📚 **Aranan Şartlar / Nitelikler**
📋 **İstenen Belgeler** (her belgeyi numaralı liste olarak, tüm detaylarıyla)
📅 **Önemli Tarihler**
📝 **Başvuru Bilgileri**
⚠️ **Dikkat Edilmesi Gerekenler**
⬇️ **Ekli Dosyalar** (varsa)"""

        # PDF içeriklerini ana metne ekle
        ek_metin = ""
        if pdf_listesi:
            ek_metin = "\n\n--- EKLİ PDF DOSYALARI ---\n"
            for p in pdf_listesi:
                ek_metin += f"\nDosya Adı: {p['ad']}\nURL: {p['url']}\n"
                if p["icerik"]:
                    ek_metin += f"İçerik:\n{p['icerik'][:1500]}\n"
                else:
                    ek_metin += "(İçerik okunamadı)\n"

        yanit = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role":"system","content":sistem},
                {"role":"user","content":f"İlan Başlığı: {baslik}\n\nİlan İçeriği:\n{icerik}{ek_metin}"},
            ],
            temperature=0.1,
            max_tokens=2500,
        )
        st.session_state["son_groq_istegi"] = time.time()
        return yanit.choices[0].message.content
    except Exception as e:
        hata = str(e)
        if "rate_limit" in hata.lower():
            return "⏳ Groq rate limit aşıldı. Lütfen birkaç saniye bekleyip tekrar deneyin."
        return f"❌ Groq hatası: {hata}"

# ─────────────────────────────────────────────
# FAVORİLER
# ─────────────────────────────────────────────
def favori_toggle(link):
    favs = st.session_state.setdefault("favoriler", set())
    if link in favs:
        favs.discard(link)
    else:
        favs.add(link)

def favori_mi(link):
    return link in st.session_state.get("favoriler", set())

# ─────────────────────────────────────────────
# AKILLI ARAMA
# ─────────────────────────────────────────────
def arama_eslesiyor(arama_metni, baslik):
    """
    Çok kelimeli AND mantığı: tüm kelimeler başlıkta geçmeli.
    Türkçe karakterler normalize edilir.
    Örn: "uzman yardimci 2025" → her kelime başlıkta olmalı.
    """
    if not arama_metni:
        return True
    norm_baslik = normalize(baslik)
    kelimeler = normalize(arama_metni).split()
    return all(k in norm_baslik for k in kelimeler)

# ─────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────
CSS = """
<style>
.ilan-kart {
    background: #1e2130;
    border-left: 4px solid #4c8bf5;
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 4px;
}
.ilan-baslik {
    font-size: 15px;
    font-weight: 600;
    color: #e8eaf0;
    margin-bottom: 4px;
    line-height: 1.4;
}
.ilan-meta {
    font-size: 13px;
    color: #9aa0b4;
}
.ozet-kutu {
    background: #1e2130;
    border: 1px solid #3a4060;
    border-radius: 8px;
    padding: 20px;
    margin-top: 8px;
    color: #e8eaf0 !important;
    font-size: 14px;
    line-height: 1.8;
}
.ozet-kutu strong, .ozet-kutu b {
    color: #7eb8f7 !important;
}
.favori-badge {
    font-size: 12px;
    color: #ffd700;
    margin-left: 6px;
}
.pdf-kutu {
    background: #161b2e;
    border: 1px solid #2d3555;
    border-radius: 6px;
    padding: 10px 14px;
    margin-top: 6px;
}
.arama-ipucu {
    font-size: 11px;
    color: #6b7280;
    margin-top: 2px;
}
</style>
"""

# ─────────────────────────────────────────────
# KART
# ─────────────────────────────────────────────
def ilan_karti_goster(d, idx):
    fav = favori_mi(d["link"])
    fav_ikon = "⭐" if fav else "☆"

    st.markdown(f"""
    <div class="ilan-kart">
        <div class="ilan-baslik">{d['kategori']} &nbsp; {d['baslik']}</div>
        <div class="ilan-meta">📆 {d['yil'] or '?'}</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        st.link_button("🔗 İlana Git", url=d["link"], use_container_width=True)

    with col2:
        anahtar       = f"ozet_{idx}"
        pdf_anahtar   = f"pdfler_{idx}"
        if st.button("🤖 Detay Getir (AI Özet)", key=f"btn_{idx}", use_container_width=True):
            with st.spinner("📖 Sayfa okunuyor, PDF'ler kontrol ediliyor..."):
                icerik, pdf_listesi = ilan_icerik_cek(d["link"])
                st.session_state[pdf_anahtar] = pdf_listesi

            with st.spinner("🤖 AI ile özetleniyor..."):
                ozet = groq_ozet(d["baslik"], icerik, pdf_listesi)
                st.session_state[anahtar] = ozet

    with col3:
        if st.button(f"{fav_ikon} Favori", key=f"fav_{idx}", use_container_width=True):
            favori_toggle(d["link"])
            st.rerun()

    # AI Özet
    if anahtar in st.session_state:
        with st.expander("📄 AI Özeti", expanded=True):
            st.markdown(st.session_state[anahtar])

        # ── PDF İndirme Butonları (expander dışında, her zaman görünür) ──
        pdf_listesi = st.session_state.get(pdf_anahtar, [])
        if pdf_listesi:
            st.markdown("**📎 Ekli Belgeler — İndir:**")
            for pdf in pdf_listesi:
                col_ad, col_btn = st.columns([4, 1])
                with col_ad:
                    st.markdown(
                        f"<div style='padding:6px 0; font-size:14px;'>📄 {pdf['ad']}</div>",
                        unsafe_allow_html=True,
                    )
                with col_btn:
                    st.link_button(
                        "⬇️ İndir",
                        url=pdf["url"],
                        use_container_width=True,
                    )
            st.markdown("")  # boşluk

        if st.button("✖️ Kapat", key=f"kapat_{idx}"):
            del st.session_state[anahtar]
            if pdf_anahtar in st.session_state:
                del st.session_state[pdf_anahtar]
            st.rerun()

    st.divider()

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
def sidebar_filtre(tum_yillar):
    st.sidebar.title("🏛️ Milli Saraylar\nİlan Takip")
    st.sidebar.markdown("---")

    # Yıl modu
    st.sidebar.subheader("📅 Yıl Filtresi")
    mod = st.sidebar.radio(
        "Göster:",
        options=["Sadece 2026 ve Sonrası", "Önceki Yıllar (2025 ve Öncesi)", "Filtresiz (Tümü)"],
        index=0,
    )

    secili_yillar = []
    if mod == "Filtresiz (Tümü)" and tum_yillar:
        secili_yillar = st.sidebar.multiselect(
            "Belirli yıllar (boş = hepsi):",
            options=sorted(tum_yillar, reverse=True),
            default=[],
        )

    st.sidebar.markdown("---")
    st.sidebar.subheader("🔎 Kategori")
    kategoriler = [
        "Tümü","📢 Personel Alımı","🏆 Nihai Sonuç",
        "📝 Sözlü Sınav Sonucu","🔬 Uygulamalı Sınav Sonucu",
        "📊 Sınav Sonucu","📅 Sınav Takvimi","🔍 Başvuru Kontrol",
        "📨 Başvuru Duyurusu","🎯 KPSS/EKPSS","📣 Genel Duyuru",
    ]
    secili_kategori = st.sidebar.selectbox("Kategori:", kategoriler)

    st.sidebar.markdown("---")
    st.sidebar.subheader("🔤 Akıllı Arama")
    arama = st.sidebar.text_input(
        "Başlıkta ara:",
        placeholder="örn: uzman yardimci istanbul",
    )
    # İpucu
    st.sidebar.markdown(
        "<div class='arama-ipucu'>💡 Birden fazla kelime yazabilirsin — tümü eşleşmeli (AND). "
        "Türkçe karakter fark etmez: 'sef' → 'şef' bulur.</div>",
        unsafe_allow_html=True,
    )

    # Favori filtresi
    st.sidebar.markdown("---")
    sadece_favori = st.sidebar.checkbox(
        f"⭐ Sadece Favoriler ({len(st.session_state.get('favoriler', set()))})"
    )

    # Kullanma Kılavuzu
    st.sidebar.markdown("---")
    with st.sidebar.expander("📖 Nasıl Kullanılır?", expanded=False):
        st.sidebar.markdown("""
**🔄 Verileri Güncelle** *(sağ üst köşe)*
Siteyi anlık tarar, yeni ilanları çeker.
Normalde her gün otomatik güncellenir ama
"yeni bir şey çıktı mu acaba" dersen buna bas.

---

**📅 Yıl Filtresi**
İlanları yıla göre ayıklar.
- *2026 ve Sonrası* → En güncel ilanlar
- *2025 ve Öncesi* → Geçmiş ilanlar
- *Filtresiz* → Hepsi birden
  (çok fazla olur ama sen bilirsin 😄)

---

**🔎 Kategori**
İlanları türüne göre filtreler.
Mesela sadece *Nihai Sonuç* görmek istiyorsan
buradan seçersin. İsmin listede var mı
bakmak için ideal.

---

**🔤 Akıllı Arama**
Başlıkta geçen kelimeye göre arama yapar.
Birden fazla kelime yazabilirsin, hepsi
eşleşmeli (AND mantığı).
Türkçe karakter takılma: "sef" yazsan "şef"
de bulur, "uzman yardimci" yazsan
"uzman yardımcısı" da çıkar.

---

**⭐ Favoriler**
Takip etmek istediğin ilanın yanındaki
☆ Favori butonuna basarsan yıldızlanır ⭐
Sonra "Sadece Favoriler" kutucuğunu
işaretleyince sadece onları görürsün.

---

**🤖 Detay Getir (AI Özet)**
Her ilanın altındaki bu butona basınca:
1. İlan sayfası otomatik açılıp okunur
2. Varsa ekli PDF'ler de taranır
3. Yapay zeka her şeyi özetler:
   kaç kişi alınıyor, hangi belgeler lazım vs.
4. PDF varsa altında indirme butonu çıkar

*Not: Her özet birkaç saniyelik bekleme
yapar, yapay zeka bunalmasın diye 🙂*
        """)

    return {
        "mod"             : mod,
        "secili_yillar"   : secili_yillar,
        "secili_kategori" : secili_kategori,
        "arama"           : arama.strip(),
        "sadece_favori"   : sadece_favori,
    }

# ─────────────────────────────────────────────
# FİLTRELE
# ─────────────────────────────────────────────
def ilan_filtrele(duyurular, filtre):
    sonuc = duyurular

    if filtre["sadece_favori"]:
        favs = st.session_state.get("favoriler", set())
        sonuc = [d for d in sonuc if d["link"] in favs]
    else:
        mod = filtre["mod"]
        if mod == "Sadece 2026 ve Sonrası":
            sonuc = [d for d in sonuc if d["yil"] and d["yil"] >= 2026]
        elif mod == "Önceki Yıllar (2025 ve Öncesi)":
            sonuc = [d for d in sonuc if d["yil"] and d["yil"] <= 2025]
        elif filtre["secili_yillar"]:
            sonuc = [d for d in sonuc if d["yil"] in filtre["secili_yillar"]]

    if filtre["secili_kategori"] != "Tümü":
        sonuc = [d for d in sonuc if filtre["secili_kategori"] in d["kategori"]]

    # Akıllı çok kelimeli arama
    if filtre["arama"]:
        sonuc = [d for d in sonuc if arama_eslesiyor(filtre["arama"], d["baslik"])]

    return sonuc

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    st.set_page_config(
        page_title="Milli Saraylar İlanları",
        page_icon="🏛️",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(CSS, unsafe_allow_html=True)

    # Session state başlat
    for k, v in [("son_groq_istegi",0), ("favoriler",set())]:
        if k not in st.session_state:
            st.session_state[k] = v

    # PyPDF2 uyarısı
    if not PDF_DESTEKLI:
        st.info("ℹ️ PDF içerikleri için `pip install PyPDF2` kurabilirsin. PDF linkleri yine de gösterilir.")

    # Başlık + Güncelle
    col_baslik, col_btn = st.columns([5, 1])
    with col_baslik:
        st.title("🏛️ Milli Saraylar Personel Alım Duyuruları")
    with col_btn:
        st.write("")
        if st.button("🔄 Verileri Güncelle", use_container_width=True):
            st.cache_data.clear()
            veri_guncelle()
            st.success("Güncellendi!")

    duyurular = veri_yukle()

    son_guncelleme = st.session_state.get("son_guncelleme")
    if son_guncelleme:
        st.caption(f"📡 Kaynak: millisaraylar.gov.tr · Son güncelleme: {son_guncelleme.strftime('%d.%m.%Y %H:%M')}")

    if not duyurular:
        st.error("Duyurular yüklenemedi. Lütfen 'Verileri Güncelle' butonuna tıklayın.")
        return

    tum_yillar = sorted({d["yil"] for d in duyurular if d["yil"]}, reverse=True)

    filtre   = sidebar_filtre(tum_yillar)
    filtreli = ilan_filtrele(duyurular, filtre)

    # İstatistik
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📋 Toplam İlan", len(duyurular))
    c2.metric("🔍 Gösterilen", len(filtreli))
    c3.metric("⭐ Favoriler", len(st.session_state.get("favoriler", set())))
    c4.metric("📆 Yıl Aralığı", f"{min(tum_yillar)}–{max(tum_yillar)}" if tum_yillar else "-")

    st.markdown("---")

    if not filtreli:
        st.info("Seçilen filtrelere uygun ilan bulunamadı.")
        return

    # Yıla göre grupla
    gruplar = defaultdict(list)
    for d in filtreli:
        gruplar[d["yil"] or 0].append(d)

    maks_yil = max(gruplar.keys())
    for yil in sorted(gruplar.keys(), reverse=True):
        grup   = gruplar[yil]
        etiket = str(yil) if yil else "Tarih Belirtilmemiş"
        with st.expander(f"📆 {etiket} — {len(grup)} ilan", expanded=(yil == maks_yil)):
            for d in grup:
                ilan_karti_goster(d, hash(d["link"]))

if __name__ == "__main__":
    main()
