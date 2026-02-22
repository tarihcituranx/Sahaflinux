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

# Sayfa gezintisi olan linkler — bunlar dosya değil
SAYFA_LINKLERI = re.compile(
    r"DuyuruDetay|PersonelAlim|Kurumsal|Saraylar|Muzeler|Ziyaret"
    r"|javascript:|#|mailto:|tel:",
    re.I
)

# Jenerik buton metinleri — dosya adı olarak kullanılmaz
JENERIK_METINLER = {
    "dosyayi gorun", "goruntule", "goster", "indir", "tikla",
    "tiklayin", "tiklayniz", "icin tiklayin", "buraya tiklayin",
    "download", "open", "view", "click here", "dosyayi indir"
}


def dosya_linki_mi(href, base_url):
    """
    Linkin bir dosya indirme linki olup olmadığını kontrol eder.
    Milli Saraylar sitesi çeşitli URL yapıları kullanabilir.
    """
    hl = href.lower()
    tam = urljoin(base_url, href).lower()

    # Kesinlikle dosya olan uzantılar
    for ext in (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".zip"):
        if hl.endswith(ext) or (ext in hl and "?" in hl):
            return True

    # Site içi dosya sunucusu kalıpları
    kaliplar = [
        "getfile", "dosyagetir", "filedownload", "download",
        "dosyaindir", "getdoc", "belgeal", "document",
        "/dosya/", "/files/", "/upload", "/icerik/",
    ]
    for k in kaliplar:
        if k in hl:
            return True

    # millisaraylar.gov.tr alanındaki ve sayfa olmayan linkler
    if "millisaraylar" in tam and not SAYFA_LINKLERI.search(href):
        # Uzun ID'li veya dosya yolu gibi görünen linkler
        if re.search(r"[?&](id|dosyaid|file|f)=\d+", hl):
            return True
        if re.search(r"/\d{4,}/", hl):  # /2025/123456/ gibi
            return True

    return False


def pdf_ad_bul(a_tag, href):
    """
    Dosya için anlamlı bir isim bulmaya çalışır.
    Öncelik: yakın kardeş/ebeveyn metin → URL → "Belge"
    """
    from urllib.parse import unquote

    # 1. Linkin kendi metni anlamlıysa kullan
    link_metni = a_tag.get_text(strip=True)
    norm_link  = normalize(link_metni)
    if (link_metni and len(link_metni) > 4
            and not any(j in norm_link for j in JENERIK_METINLER)):
        return link_metni

    # 2. Üst kartta dosya adı yazıyor mu? (.pdf içeren yakın metin)
    #    Milli Saraylar'da kart yapısı: dosya adı üstte, buton altta
    aday_elementler = []
    try:
        # Aynı kart/hücre içindeki önceki elemanlar
        kapsayici = a_tag.parent
        for _ in range(5):
            if kapsayici is None: break
            aday_elementler.append(kapsayici)
            kapsayici = kapsayici.parent

        for el in aday_elementler:
            metin = el.get_text(" ", strip=True)
            # .pdf geçen kısa metin bul
            eslesme = re.search(r"([^\n]{3,80}[.]pdf)", metin, re.I)
            if eslesme:
                ad = eslesme.group(1).strip()
                if len(ad) < 100:
                    return ad
    except Exception:
        pass

    # 3. URL'den dosya adı
    dosya = href.split("/")[-1].split("?")[0]
    try:
        dosya = unquote(dosya)
    except Exception:
        pass
    if dosya and len(dosya) > 2:
        return dosya

    return "Belge"


def ilan_icerik_cek(url):
    """
    İlan sayfasından metin + dosya linklerini çeker.
    Döner: (metin: str, pdf_listesi: list[dict], tum_linkler: list[dict])
      - pdf_listesi: tespit edilen dosya linkleri
      - tum_linkler: DEBUG için sayfadaki tüm linkler
    """
    try:
        resp = requests.get(url, headers=HEADERS, verify=False, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Tüm linkleri DEBUG için kaydet
        tum_linkler = []
        for a in soup.find_all("a", href=True):
            metin = a.get_text(strip=True)
            href  = a["href"]
            if href and href not in ("#", "javascript:void(0)"):
                tum_linkler.append({
                    "metin": metin[:60],
                    "href" : href[:120],
                    "tam"  : urljoin(url, href)[:150],
                })

        # Nav/footer/header'ı temizle — sadece içerik kalsın
        for tag in soup(["nav", "header", "footer", "script", "style"]):
            tag.decompose()

        # PDF / dosya linklerini topla
        pdf_listesi = []
        gorulen     = set()

        for a in soup.find_all("a", href=True):
            href = a["href"]
            if not href or href.startswith(("javascript:", "mailto:", "tel:")):
                continue

            if not dosya_linki_mi(href, url):
                continue

            tam_url = urljoin(url, href)
            if tam_url in gorulen:
                continue
            gorulen.add(tam_url)

            ad     = pdf_ad_bul(a, href)
            icerik = pdf_icerigi_cek(tam_url)
            pdf_listesi.append({"ad": ad, "url": tam_url, "icerik": icerik})

        # Sayfa metni
        satirlar = [s for s in soup.get_text("\n", strip=True).splitlines() if s.strip()]
        metin    = "\n".join(satirlar[:400])

        return metin, pdf_listesi, tum_linkler

    except Exception as e:
        return f"İçerik alınamadı: {e}", [], []

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
                icerik, pdf_listesi, tum_linkler = ilan_icerik_cek(d["link"])
                st.session_state[pdf_anahtar]   = pdf_listesi
                st.session_state[f"linkler_{idx}"] = tum_linkler

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
                        f"<div style='padding:6px 0;font-size:14px;'>📄 {pdf['ad']}</div>",
                        unsafe_allow_html=True,
                    )
                with col_btn:
                    st.link_button("⬇️ İndir", url=pdf["url"], use_container_width=True)
            st.markdown("")
        else:
            # Dosya bulunamadıysa debug expander göster
            tum_linkler = st.session_state.get(f"linkler_{idx}", [])
            if tum_linkler:
                with st.expander("🔍 Sayfada Bulunan Linkler (PDF tespit edilemedi — debug)", expanded=False):
                    st.caption("Bu linklerden hangisinin PDF/dosya olduğunu anlayabilmek için gösteriliyor.")
                    for lnk in tum_linkler:
                        st.markdown(
                            f"**Metin:** `{lnk['metin']}` | **href:** `{lnk['href']}`",
                        )

        if st.button("✖️ Kapat", key=f"kapat_{idx}"):
            del st.session_state[anahtar]
            for k in [pdf_anahtar, f"linkler_{idx}"]:
                if k in st.session_state:
                    del st.session_state[k]
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
