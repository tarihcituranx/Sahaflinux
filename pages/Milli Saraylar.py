"""
Milli Saraylar Personel Alım Duyuruları - Streamlit Uygulaması
Kurulum: pip install streamlit groq requests beautifulsoup4
Çalıştırma: streamlit run millisaraylar_app.py
"""

import time
import re
from collections import defaultdict
from urllib.parse import urljoin
from datetime import datetime

import requests
import urllib3
import streamlit as st
from bs4 import BeautifulSoup
from groq import Groq

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ─────────────────────────────────────────────
# AYARLAR
# ─────────────────────────────────────────────
ANASAYFA_URL = "https://www.millisaraylar.gov.tr/Kurumsal/PersonelAlimDuyuru"
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
GROQ_MODEL   = "llama-3.3-70b-versatile"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# Rate limit: kaç saniyede bir Groq isteği yapılabilir
RATE_LIMIT_SANIYE = 4

# ─────────────────────────────────────────────
# KATEGORİ ETİKETLERİ
# ─────────────────────────────────────────────
KATEGORILER = [
    (["nihai sonuc", "nihai sonucu"],                           "🏆 Nihai Sonuç"),
    (["yerlestirme sonuc"],                                     "📋 Yerleştirme Sonucu"),
    (["sozlu sinav sonuc", "mulakat sinav sonuc"],              "📝 Sözlü Sınav Sonucu"),
    (["uygulamali sinav sonuc"],                                "🔬 Uygulamalı Sınav Sonucu"),
    (["sinav sonuc", "sinavi sonuc"],                           "📊 Sınav Sonucu"),
    (["basari puani"],                                          "📊 Başarı Puanları"),
    (["sozlu sinav takvim"],                                    "📅 Sözlü Sınav Takvimi"),
    (["uygulamali sinav takvim"],                               "📅 Uygulamalı Sınav Takvimi"),
    (["sinav takvim"],                                          "📅 Sınav Takvimi"),
    (["basvuru kontrol"],                                       "🔍 Başvuru Kontrol"),
    (["basvuru"],                                               "📨 Başvuru Duyurusu"),
    (["evrak teslim"],                                          "📦 Evrak Teslimi"),
    (["alim", "alimina", "kadro", "isci alim"],                 "📢 Personel Alımı"),
    (["giris sinavi", "sinav duyuru"],                          "✏️ Sınav Duyurusu"),
    (["kpss", "ekpss"],                                         "🎯 KPSS/EKPSS"),
    (["duyuru"],                                                "📣 Genel Duyuru"),
]

TURKCE_AYLAR = {
    "ocak": 1, "subat": 2, "mart": 3, "nisan": 4, "mayis": 5,
    "haziran": 6, "temmuz": 7, "agustos": 8, "eylul": 9,
    "ekim": 10, "kasim": 11, "aralik": 12
}


# ─────────────────────────────────────────────
# YARDIMCI FONKSİYONLAR
# ─────────────────────────────────────────────
def normalize(metin: str) -> str:
    return (metin.lower()
            .replace("ı","i").replace("ğ","g").replace("ü","u")
            .replace("ş","s").replace("ö","o").replace("ç","c")
            .replace("İ","i").replace("Ğ","g").replace("Ü","u")
            .replace("Ş","s").replace("Ö","o").replace("Ç","c"))


def kategori_bul(baslik: str) -> str:
    kucuk = normalize(baslik)
    for anahtar_listesi, etiket in KATEGORILER:
        for anahtar in anahtar_listesi:
            if anahtar in kucuk:
                return etiket
    return "📣 Duyuru"


TARIH_REGEX = re.compile(r"^\d{1,2}\s+\S+\s+\d{4}$")

def tarih_link_mi(metin: str) -> bool:
    return bool(TARIH_REGEX.match(metin.strip()))


def yil_metinden(metin: str):
    if not metin:
        return None
    m = re.search(r"\b\d{1,2}\.\d{1,2}\.(20\d{2})\b", metin)
    if m:
        return int(m.group(1))
    m = re.search(r"\b(20\d{2})/\d+\b", metin)
    if m:
        return int(m.group(1))
    norm = normalize(metin)
    m = re.search(r"\d{1,2}\s+(\w+)\s+(20\d{2})", norm)
    if m and m.group(1) in TURKCE_AYLAR:
        return int(m.group(2))
    if tarih_link_mi(metin):
        m = re.search(r"(20\d{2})", metin)
        if m:
            return int(m.group(1))
    return None


def container_bul(link):
    for tag in ["li", "tr", "article", "div"]:
        p = link.find_parent(tag)
        if p:
            return p
    return link.parent


def tarih_yili_container_dan_al(link):
    container = container_bul(link)
    if container is None:
        return None
    for a in container.find_all("a"):
        metin = a.get_text(strip=True)
        if tarih_link_mi(metin):
            yil = yil_metinden(metin)
            if yil:
                return yil
    return yil_metinden(container.get_text(" ", strip=True))


# ─────────────────────────────────────────────
# SCRAPING
# ─────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)   # 5 dakika cache
def duyurulari_cek() -> list[dict]:
    try:
        resp = requests.get(
            ANASAYFA_URL, headers=HEADERS,
            verify=False, timeout=20
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        st.error(f"Sayfa çekilemedi: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    gorulen = set()
    duyurular = []
    son_yil = None

    for link in soup.find_all("a"):
        href  = link.get("href", "")
        baslik = link.get_text(strip=True)

        if not href or not baslik:
            continue

        if tarih_link_mi(baslik):
            y = yil_metinden(baslik)
            if y:
                son_yil = y
            continue

        if "DuyuruDetay" not in href:
            continue

        tam_link = urljoin(ANASAYFA_URL, href)
        if tam_link in gorulen:
            continue
        gorulen.add(tam_link)

        yil = yil_metinden(baslik) or tarih_yili_container_dan_al(link) or son_yil

        duyurular.append({
            "baslik"  : baslik,
            "link"    : tam_link,
            "yil"     : yil,
            "kategori": kategori_bul(baslik),
        })

    return duyurular


def ilan_icerik_cek(url: str) -> str:
    """Duyuru sayfasının metin içeriğini çeker."""
    try:
        resp = requests.get(url, headers=HEADERS, verify=False, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        # Gereksiz tag'leri temizle
        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()
        metin = soup.get_text(separator="\n", strip=True)
        # Fazla boş satırları temizle
        satirlar = [s for s in metin.splitlines() if s.strip()]
        return "\n".join(satirlar[:300])   # ilk 300 satır yeterli
    except Exception as e:
        return f"İçerik alınamadı: {e}"


# ─────────────────────────────────────────────
# GROQ AI ÖZET
# ─────────────────────────────────────────────
def groq_ozet(ilan_baslik: str, ilan_icerik: str) -> str:
    """Groq ile ilanı özetler. Rate-limit korumalı."""

    # Session state'de son istek zamanını tut
    su_an = time.time()
    son_istek = st.session_state.get("son_groq_istegi", 0)
    bekleme   = RATE_LIMIT_SANIYE - (su_an - son_istek)

    if bekleme > 0:
        time.sleep(bekleme)

    try:
        client = Groq(api_key=GROQ_API_KEY)

        sistem_prompt = """Sen Türkiye kamu kurumlarındaki personel alım ilanlarını analiz eden bir uzmansın.
Görevin: Verilen ilan metnini okuyarak YALNIZCA metinde açıkça yazan bilgileri çıkarmak.
Metinde olmayan hiçbir bilgiyi UYDURMAYACAKSIN (halüsinasyon yasak).
Yanıtını Türkçe ver ve şu başlıkları kullan:

📋 **İlan Özeti**
🎯 **Aranan Pozisyon(lar)**
🔢 **Alınacak Kişi Sayısı**
📚 **Aranan Şartlar / Nitelikler**
📅 **Önemli Tarihler**
📝 **Başvuru Bilgileri**
⚠️ **Dikkat Edilmesi Gerekenler**

Eğer bir başlık için metinde bilgi yoksa o başlığı atla."""

        kullanici_prompt = f"""İlan Başlığı: {ilan_baslik}

İlan İçeriği:
{ilan_icerik}"""

        yanit = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": sistem_prompt},
                {"role": "user",   "content": kullanici_prompt},
            ],
            temperature=0.1,
            max_tokens=1500,
        )

        st.session_state["son_groq_istegi"] = time.time()
        return yanit.choices[0].message.content

    except Exception as e:
        hata = str(e)
        if "rate_limit" in hata.lower():
            return "⏳ Groq rate limit aşıldı. Lütfen birkaç saniye bekleyip tekrar deneyin."
        return f"❌ Groq hatası: {hata}"


# ─────────────────────────────────────────────
# STREAMLİT ARAYÜZÜ
# ─────────────────────────────────────────────
def sayfa_ayarlari():
    st.set_page_config(
        page_title="Milli Saraylar İlanları",
        page_icon="🏛️",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown("""
    <style>
    .ilan-kart {
        background: #f8f9fa;
        border-left: 4px solid #1f6aa5;
        border-radius: 6px;
        padding: 14px 18px;
        margin-bottom: 12px;
    }
    .ilan-baslik {
        font-size: 15px;
        font-weight: 600;
        color: #1a1a2e;
        margin-bottom: 6px;
    }
    .ilan-meta {
        font-size: 13px;
        color: #666;
        margin-bottom: 8px;
    }
    .ozet-kutu {
        background: #eef6ff;
        border-radius: 8px;
        padding: 16px;
        margin-top: 10px;
        font-size: 14px;
        line-height: 1.7;
    }
    </style>
    """, unsafe_allow_html=True)


def sidebar_filtre(tum_yillar: list) -> dict:
    st.sidebar.image(
        "https://www.millisaraylar.gov.tr/images/logo.png",
        width=180,
        use_container_width=False,
    )
    st.sidebar.title("🏛️ Milli Saraylar\nİlan Takip")
    st.sidebar.markdown("---")

    st.sidebar.subheader("📅 Yıl Filtresi")
    mod = st.sidebar.radio(
        "Göster:",
        options=["Sadece 2026 ve Sonrası", "Tüm Yıllar"],
        index=0,
    )

    secili_yillar = None
    if mod == "Tüm Yıllar" and tum_yillar:
        secili_yillar = st.sidebar.multiselect(
            "Yıl seçin (boş = hepsi):",
            options=sorted(tum_yillar, reverse=True),
            default=[],
        )

    st.sidebar.markdown("---")
    st.sidebar.subheader("🔎 Kategori Filtresi")
    kategoriler = [
        "Tümü",
        "📢 Personel Alımı",
        "🏆 Nihai Sonuç",
        "📝 Sözlü Sınav Sonucu",
        "🔬 Uygulamalı Sınav Sonucu",
        "📊 Sınav Sonucu",
        "📅 Sınav Takvimi",
        "🔍 Başvuru Kontrol",
        "📨 Başvuru Duyurusu",
        "🎯 KPSS/EKPSS",
        "📣 Genel Duyuru",
    ]
    secili_kategori = st.sidebar.selectbox("Kategori:", kategoriler)

    st.sidebar.markdown("---")
    st.sidebar.subheader("🔤 Arama")
    arama = st.sidebar.text_input("Başlıkta ara:", placeholder="örn: itfaiyeci")

    return {
        "mod"             : mod,
        "secili_yillar"   : secili_yillar or [],
        "secili_kategori" : secili_kategori,
        "arama"           : arama.strip().lower(),
    }


def ilan_filtrele(duyurular: list, filtre: dict) -> list:
    sonuc = duyurular

    # Yıl filtresi
    if filtre["mod"] == "Sadece 2026 ve Sonrası":
        sonuc = [d for d in sonuc if d["yil"] and d["yil"] >= 2026]
    elif filtre["secili_yillar"]:
        sonuc = [d for d in sonuc if d["yil"] in filtre["secili_yillar"]]

    # Kategori filtresi
    if filtre["secili_kategori"] != "Tümü":
        sonuc = [d for d in sonuc if filtre["secili_kategori"] in d["kategori"]]

    # Metin arama
    if filtre["arama"]:
        sonuc = [d for d in sonuc if filtre["arama"] in normalize(d["baslik"])]

    return sonuc


def ilan_karti_goster(d: dict, idx: int):
    """Tek bir ilanı kart olarak çizer."""
    with st.container():
        st.markdown(f"""
        <div class="ilan-kart">
            <div class="ilan-baslik">{d['kategori']} &nbsp; {d['baslik']}</div>
            <div class="ilan-meta">📆 {d['yil'] or '?'}</div>
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns([1, 1])

        with col1:
            st.link_button(
                "🔗 İlana Git",
                url=d["link"],
                use_container_width=True,
            )

        with col2:
            anahtar = f"ozet_{idx}"
            if st.button(
                "🤖 Detay Getir (AI Özet)",
                key=f"btn_{idx}",
                use_container_width=True,
            ):
                with st.spinner("İlan içeriği okunuyor ve özetleniyor..."):
                    icerik = ilan_icerik_cek(d["link"])
                    ozet   = groq_ozet(d["baslik"], icerik)
                    st.session_state[anahtar] = ozet

        # Özet göster
        if anahtar in st.session_state:
            with st.expander("📄 AI Özeti", expanded=True):
                st.markdown(
                    f'<div class="ozet-kutu">{st.session_state[anahtar]}</div>',
                    unsafe_allow_html=True,
                )
                if st.button("✖️ Özeti Kapat", key=f"kapat_{idx}"):
                    del st.session_state[anahtar]
                    st.rerun()

        st.markdown("<hr style='margin:8px 0; border-color:#e0e0e0'>", unsafe_allow_html=True)


def main():
    sayfa_ayarlari()

    # Session state başlat
    if "son_groq_istegi" not in st.session_state:
        st.session_state["son_groq_istegi"] = 0

    # ── Başlık ──
    st.title("🏛️ Milli Saraylar Personel Alım Duyuruları")
    st.caption(f"Kaynak: millisaraylar.gov.tr · Son güncelleme: {datetime.now().strftime('%d.%m.%Y %H:%M')}")

    # ── Veri yükle ──
    with st.spinner("Duyurular yükleniyor..."):
        duyurular = duyurulari_cek()

    if not duyurular:
        st.error("Duyurular yüklenemedi. Lütfen sayfayı yenileyin.")
        return

    tum_yillar = sorted({d["yil"] for d in duyurular if d["yil"]}, reverse=True)

    # ── Sidebar filtre ──
    filtre = sidebar_filtre(tum_yillar)

    # ── Filtrelenmiş liste ──
    filtreli = ilan_filtrele(duyurular, filtre)

    # ── Özet istatistik ──
    col1, col2, col3 = st.columns(3)
    col1.metric("📋 Toplam İlan", len(duyurular))
    col2.metric("🔍 Gösterilen", len(filtreli))
    col3.metric("📆 Yıl Aralığı", f"{min(tum_yillar)} – {max(tum_yillar)}" if tum_yillar else "-")

    st.markdown("---")

    if not filtreli:
        st.info("Seçilen filtrelere uygun ilan bulunamadı.")
        return

    # ── İlanları yıla göre grupla ve göster ──
    gruplar = defaultdict(list)
    for d in filtreli:
        gruplar[d["yil"] or 0].append(d)

    for yil in sorted(gruplar.keys(), reverse=True):
        grup = gruplar[yil]
        etiket = str(yil) if yil else "Tarih Belirtilmemiş"
        with st.expander(f"📆 {etiket} — {len(grup)} ilan", expanded=(yil == max(gruplar.keys()))):
            for idx, d in enumerate(grup):
                ilan_karti_goster(d, hash(d["link"]))


if __name__ == "__main__":
    main()
