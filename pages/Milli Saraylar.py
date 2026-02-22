"""
Milli Saraylar Personel Alım Duyuruları - Streamlit Uygulaması
Kurulum: pip install streamlit groq requests beautifulsoup4
Çalıştırma: streamlit run millisaraylar_app.py
"""

import time
import re
from collections import defaultdict
from urllib.parse import urljoin
from datetime import datetime, date

import requests
import urllib3
import streamlit as st
from bs4 import BeautifulSoup
from groq import Groq

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

def veri_guncelle():
    """Veriyi çekip session_state'e kaydeder."""
    with st.spinner("🔄 Duyurular güncelleniyor..."):
        duyurular = duyurulari_cek_raw()
    st.session_state["duyurular"]      = duyurular
    st.session_state["son_guncelleme"] = datetime.now()
    return duyurular

def veri_yukle():
    """Günlük otomatik güncelleme + ilk yükleme."""
    simdi = datetime.now()

    # İlk yükleme
    if "duyurular" not in st.session_state:
        return veri_guncelle()

    # Günlük otomatik güncelleme
    son = st.session_state.get("son_guncelleme")
    if son and son.date() < simdi.date():
        return veri_guncelle()

    return st.session_state["duyurular"]

# ─────────────────────────────────────────────
# İLAN İÇERİK
# ─────────────────────────────────────────────
def ilan_icerik_cek(url):
    try:
        resp = requests.get(url, headers=HEADERS, verify=False, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script","style","nav","header","footer"]):
            tag.decompose()
        satirlar = [s for s in soup.get_text("\n",strip=True).splitlines() if s.strip()]
        return "\n".join(satirlar[:300])
    except Exception as e:
        return f"İçerik alınamadı: {e}"

# ─────────────────────────────────────────────
# GROQ AI
# ─────────────────────────────────────────────
def groq_ozet(baslik, icerik):
    su_an   = time.time()
    bekleme = RATE_LIMIT_SANIYE - (su_an - st.session_state.get("son_groq_istegi", 0))
    if bekleme > 0:
        time.sleep(bekleme)
    try:
        client = Groq(api_key=GROQ_API_KEY)
        sistem = """Sen Türkiye kamu kurumlarındaki personel alım ilanlarını analiz eden bir uzmansın.
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

        yanit = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role":"system","content":sistem},
                {"role":"user","content":f"İlan Başlığı: {baslik}\n\nİlan İçeriği:\n{icerik}"},
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
        anahtar = f"ozet_{idx}"
        if st.button("🤖 Detay Getir (AI Özet)", key=f"btn_{idx}", use_container_width=True):
            with st.spinner("Okunuyor ve özetleniyor..."):
                icerik = ilan_icerik_cek(d["link"])
                ozet   = groq_ozet(d["baslik"], icerik)
                st.session_state[anahtar] = ozet

    with col3:
        if st.button(f"{fav_ikon} Favori", key=f"fav_{idx}", use_container_width=True):
            favori_toggle(d["link"])
            st.rerun()

    # AI Özet — st.markdown kullanıyoruz, HTML div değil
    if anahtar in st.session_state:
        with st.expander("📄 AI Özeti", expanded=True):
            st.markdown(st.session_state[anahtar])
            if st.button("✖️ Kapat", key=f"kapat_{idx}"):
                del st.session_state[anahtar]
                st.rerun()

    st.divider()

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
def sidebar_filtre(tum_yillar):
    st.sidebar.title("🏛️ Milli Saraylar\nİlan Takip")
    st.sidebar.markdown("---")

    # Yıl modu — 3 seçenek
    st.sidebar.subheader("📅 Yıl Filtresi")
    mod = st.sidebar.radio(
        "Göster:",
        options=["Sadece 2026 ve Sonrası", "Önceki Yıllar (2025 ve Öncesi)", "Filtresiz (Tümü)"],
        index=0,
    )

    # Tüm modda ek yıl seçimi
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
    st.sidebar.subheader("🔤 Arama")
    arama = st.sidebar.text_input("Başlıkta ara:", placeholder="örn: itfaiyeci")

    # Favori filtresi
    st.sidebar.markdown("---")
    sadece_favori = st.sidebar.checkbox(
        f"⭐ Sadece Favoriler ({len(st.session_state.get('favoriler', set()))})"
    )

    return {
        "mod"             : mod,
        "secili_yillar"   : secili_yillar,
        "secili_kategori" : secili_kategori,
        "arama"           : arama.strip().lower(),
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

    if filtre["arama"]:
        sonuc = [d for d in sonuc if filtre["arama"] in normalize(d["baslik"])]

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

    # ── Başlık + Güncelle butonu ──
    col_baslik, col_btn = st.columns([5, 1])
    with col_baslik:
        st.title("🏛️ Milli Saraylar Personel Alım Duyuruları")
    with col_btn:
        st.write("")
        if st.button("🔄 Verileri Güncelle", use_container_width=True):
            st.cache_data.clear()
            veri_guncelle()
            st.success("Güncellendi!")

    # ── Veri yükle (günlük otomatik) ──
    duyurular = veri_yukle()

    son_guncelleme = st.session_state.get("son_guncelleme")
    if son_guncelleme:
        st.caption(f"📡 Kaynak: millisaraylar.gov.tr · Son güncelleme: {son_guncelleme.strftime('%d.%m.%Y %H:%M')}")

    if not duyurular:
        st.error("Duyurular yüklenemedi. Lütfen 'Verileri Güncelle' butonuna tıklayın.")
        return

    tum_yillar = sorted({d["yil"] for d in duyurular if d["yil"]}, reverse=True)

    # ── Sidebar ──
    filtre  = sidebar_filtre(tum_yillar)
    filtreli = ilan_filtrele(duyurular, filtre)

    # ── İstatistik ──
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📋 Toplam İlan", len(duyurular))
    c2.metric("🔍 Gösterilen", len(filtreli))
    c3.metric("⭐ Favoriler", len(st.session_state.get("favoriler", set())))
    c4.metric("📆 Yıl Aralığı", f"{min(tum_yillar)}–{max(tum_yillar)}" if tum_yillar else "-")

    st.markdown("---")

    if not filtreli:
        st.info("Seçilen filtrelere uygun ilan bulunamadı.")
        return

    # ── Yıla göre grupla ──
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
