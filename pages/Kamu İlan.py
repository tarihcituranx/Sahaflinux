import time
import re
import io
import os
import json
from collections import defaultdict
from urllib.parse import urljoin, unquote
from datetime import datetime, timezone, timedelta

import requests
import urllib3
import streamlit as st
from bs4 import BeautifulSoup
from groq import Groq

try:
    import PyPDF2
    PDF_DESTEKLI = True
except ImportError:
    PDF_DESTEKLI = False

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ─────────────────────────────────────────────
# AYARLAR
# ─────────────────────────────────────────────
ANASAYFA_URL      = "https://kamuilan.sbb.gov.tr/"
BASE_URL          = "https://kamuilan.sbb.gov.tr/"
GROQ_API_KEY      = st.secrets["GROQ_API_KEY"]
GROQ_MODEL        = "llama-3.3-70b-versatile"
RATE_LIMIT_SANIYE = 4
TZ_TURKIYE        = timezone(timedelta(hours=3))

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9",
    "Connection": "keep-alive",
}

# Meslek/pozisyon kategorileri — arama ve filtreleme için
MESLEK_KATEGORILERI = {
    "👷 Teknik / Mühendis": [
        "mühendis","muhendis","tekniker","teknisyen","teknik","mimar",
        "bilişim","yazılım","elektrik","elektronik","makine","inşaat",
        "harita","jeoloji","jeofizik","çevre","kimya","metalurji",
    ],
    "💼 İdari / Mali": [
        "memur","uzman","şef","müdür","mudur","idari","mali","muhasebe",
        "hukuk","avukat","ekonomist","istatistik","araştırmacı","analist",
        "sekreter","büro","danışman","denetmen","kontrolör",
    ],
    "👮 Güvenlik / Askerlik": [
        "güvenlik","guvenlik","koruma","bekçi","bekci","komiser","subay",
        "astsubay","erbaş","er ","asker","jandarma","polis","itfaiye",
        "sivil savunma",
    ],
    "🏥 Sağlık": [
        "doktor","hekim","hemşire","hemsire","eczacı","eczaci","sağlık",
        "saglik","psikolog","fizyoterapist","laborant","röntgen","diş",
        "veteriner","biyolog",
    ],
    "🎓 Eğitim / Akademik": [
        "öğretmen","ogretmen","eğitim","egitim","akademik","öğretim",
        "ogretim","pedagog","rehber","koordinatör",
    ],
    "🔧 İşçi / Usta": [
        "işçi","isci","usta","şoför","sofor","sürücü","forklift",
        "kaynakçı","tesisatçı","boyacı","marangoz","aşçı","asci",
        "temizlik","bahçıvan","teknisyen yardımcısı","yardımcı",
    ],
    "📊 Diğer": [],  # Hiçbir kategoriye girmeyen
}

# ─────────────────────────────────────────────
# YARDIMCI
# ─────────────────────────────────────────────
def normalize(m):
    return (m.lower()
            .replace("ı","i").replace("ğ","g").replace("ü","u")
            .replace("ş","s").replace("ö","o").replace("ç","c")
            .replace("İ","i").replace("Ğ","g").replace("Ü","u")
            .replace("Ş","s").replace("Ö","o").replace("Ç","c"))

def simdi_tr():
    return datetime.now(TZ_TURKIYE)

def meslek_kategori_bul(metin):
    n = normalize(metin)
    for kat, kelimeler in MESLEK_KATEGORILERI.items():
        if kat == "📊 Diğer":
            continue
        for k in kelimeler:
            if k in n:
                return kat
    return "📊 Diğer"

def durum_bul(metin):
    ust = metin.upper()
    if "İPTAL" in ust or "IPTAL" in ust:
        return "iptal"
    if "UZATILDI" in ust:
        return "uzatildi"
    return "aktif"

def durum_badge(durum):
    return {"aktif": "🟢 Aktif", "uzatildi": "🟡 Uzatıldı", "iptal": "🔴 İptal"}.get(durum, "")

# ─────────────────────────────────────────────
# VERİ ÇEKME (kullanıcının çalışan script mantığı)
# ─────────────────────────────────────────────
def ilanları_cek_raw():
    """
    kamuilan.sbb.gov.tr ana sayfasından ilanları çeker.
    (Kullanıcının test ettiği çalışan script'ten uyarlandı)
    """
    try:
        r = requests.get(ANASAYFA_URL, headers=HEADERS, verify=False, timeout=20)
        r.raise_for_status()
    except Exception as e:
        st.error(f"Sayfa çekilemedi: {e}")
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    ilanlar = []
    gorulen = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "ilanDetay.aspx?kod=" not in href:
            continue

        # Kod çıkar — tekrar kontrolü için
        raw_kod = href.split("kod=")[1]
        kod     = unquote(raw_kod)
        if kod in gorulen:
            continue
        gorulen.add(kod)

        metin = a.get_text(strip=True)
        if not metin:
            continue

        link = urljoin(BASE_URL, href)

        # Başvuru tarihi aralığı (parantez içinde)
        basvuru = ""
        tarih_m = re.search(r"\(([^)]+)\)", metin)
        if tarih_m:
            basvuru = tarih_m.group(1).strip()
            metin   = metin[:tarih_m.start()].strip()

        # Kurum + pozisyon ayrıştır (genellikle BÜYÜK HARF kurum adı)
        # Format: "KURUM ADI\nX POZİSYON ALACAK" veya "KURUM ADI X POZİSYON ALACAK"
        satirlar = [s.strip() for s in metin.split("\n") if s.strip()]
        if len(satirlar) >= 2:
            kurum  = satirlar[0]
            baslik = " ".join(satirlar[1:])
        else:
            # Tek satır — büyük harfli başlangıç kurum, küçük harfli devam pozisyon
            parcalar = re.split(r"\s{2,}", metin, maxsplit=1)
            if len(parcalar) == 2:
                kurum, baslik = parcalar
            else:
                kurum  = ""
                baslik = metin

        durum    = durum_bul(metin)
        kategori = meslek_kategori_bul(metin)

        ilanlar.append({
            "kod"           : kod,
            "kurum"         : kurum.strip(),
            "baslik"        : baslik.strip() or metin,
            "tam_metin"     : metin,
            "basvuru_tarihi": basvuru,
            "link"          : link,
            "durum"         : durum,
            "kategori"      : kategori,
        })

    return ilanlar

def veri_guncelle():
    with st.spinner("🔄 İlanlar güncelleniyor..."):
        ilanlar = ilanları_cek_raw()
    st.session_state["ilanlar"]        = ilanlar
    st.session_state["son_guncelleme"] = simdi_tr()
    return ilanlar

def veri_yukle():
    simdi = simdi_tr()
    if "ilanlar" not in st.session_state:
        return veri_guncelle()
    son = st.session_state.get("son_guncelleme")
    if son and son.date() < simdi.date():
        return veri_guncelle()
    return st.session_state["ilanlar"]

# ─────────────────────────────────────────────
# İLAN DETAY + PDF
# ─────────────────────────────────────────────
def pdf_icerigi_cek(pdf_url):
    """PDF'in metin içeriğini çeker (Groq özetlemesi için)."""
    if not PDF_DESTEKLI:
        return ""
    try:
        r = requests.get(pdf_url, headers=HEADERS, verify=False, timeout=20)
        r.raise_for_status()
        # İçerik tipi PDF mi?
        ct = r.headers.get("Content-Type","")
        if "pdf" not in ct.lower() and not pdf_url.lower().endswith(".pdf"):
            # PDF değil, HTML olabilir
            return ""
        reader = PyPDF2.PdfReader(io.BytesIO(r.content))
        metin  = ""
        for sayfa in reader.pages[:6]:
            metin += sayfa.extract_text() or ""
        return metin[:4000].strip()
    except Exception:
        return ""

def ilan_icerik_cek(url):
    """
    İlan linkini açar.
    - Doğrudan PDF ise → PDF içeriğini çeker
    - HTML ise → metni + PDF linklerini çeker
    Döner: (metin, pdf_listesi, tip)
      tip: "pdf" | "html"
    """
    try:
        r = requests.get(url, headers=HEADERS, verify=False, timeout=20)
        r.raise_for_status()
        ct = r.headers.get("Content-Type","")

        # Doğrudan PDF geldi
        if "pdf" in ct.lower():
            if PDF_DESTEKLI:
                try:
                    reader  = PyPDF2.PdfReader(io.BytesIO(r.content))
                    metin   = ""
                    for sayfa in reader.pages[:8]:
                        metin += sayfa.extract_text() or ""
                    return metin[:5000].strip(), [{"ad": "İlan PDF", "url": url, "icerik": metin}], "pdf"
                except Exception:
                    pass
            return "(PDF içeriği okunamadı — PyPDF2 kurulu değil)", [{"ad": "İlan PDF", "url": url, "icerik": ""}], "pdf"

        # HTML sayfası
        soup = BeautifulSoup(r.text, "html.parser")

        # Sayfadaki PDF linklerini bul
        pdf_listesi = []
        gorulen_pdf = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            hl   = href.lower()
            if not (hl.endswith(".pdf") or "getfile" in hl or "download" in hl or "dosya" in hl):
                continue
            tam = urljoin(url, href)
            if tam in gorulen_pdf:
                continue
            gorulen_pdf.add(tam)
            ad     = a.get_text(strip=True) or href.split("/")[-1]
            icerik = pdf_icerigi_cek(tam)
            pdf_listesi.append({"ad": ad, "url": tam, "icerik": icerik})

        # İçerik için iframe veya embed kontrol et (bazı siteler PDF'i embed gösterir)
        for embed in soup.find_all(["iframe","embed"], src=True):
            src = embed["src"]
            if src.lower().endswith(".pdf") or "pdf" in src.lower():
                tam = urljoin(url, src)
                if tam not in gorulen_pdf:
                    gorulen_pdf.add(tam)
                    icerik = pdf_icerigi_cek(tam)
                    pdf_listesi.append({"ad": "Gömülü PDF", "url": tam, "icerik": icerik})

        # Sayfa ham metni
        for tag in soup(["script","style","nav","header","footer"]):
            tag.decompose()
        satirlar = [s for s in soup.get_text("\n", strip=True).splitlines() if s.strip()]
        metin    = "\n".join(satirlar[:400])

        return metin, pdf_listesi, "html"

    except Exception as e:
        return f"İçerik alınamadı: {e}", [], "hata"

# ─────────────────────────────────────────────
# GROQ AI
# ─────────────────────────────────────────────
def groq_ozet(ilan, icerik, pdf_listesi=None, icerik_tipi="html"):
    su_an   = time.time()
    bekleme = RATE_LIMIT_SANIYE - (su_an - st.session_state.get("son_groq_istegi", 0))
    if bekleme > 0:
        time.sleep(bekleme)
    try:
        client = Groq(api_key=GROQ_API_KEY)
        sistem = """Sen Türkiye kamu kurumlarındaki personel alım ilanlarını analiz eden bir uzmansın.

Görevin: İlan metnini EKSİKSİZ analiz et.

KRİTİK KURALLAR:
1. Tüm sayısal bilgileri yaz: adet, yaş sınırı, puan, tarih, adres vb.
2. İstenen belgeler listesini numaralı ve eksiksiz yaz.
3. Uydurmayacaksın — sadece metinde geçen bilgileri kullan.
4. Türkçe yanıt ver.

Şu başlıkları kullan (bilgi yoksa atla):
📋 **İlan Özeti**
🏛️ **Kurum**
🎯 **Pozisyon ve Kadro**
🔢 **Alınacak Kişi Sayısı**
📚 **Aranan Şartlar / Nitelikler**
📋 **İstenen Belgeler**
📅 **Başvuru Tarihleri**
📝 **Başvuru Yöntemi**
⚠️ **Dikkat Edilmesi Gerekenler**"""

        ek = ""
        if pdf_listesi:
            ek = "\n\n--- EKLİ PDF İÇERİKLERİ ---\n"
            for p in pdf_listesi:
                if p.get("icerik"):
                    ek += f"\n[{p['ad']}]\n{p['icerik'][:2000]}\n"

        yanit = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role":"system","content":sistem},
                {"role":"user","content":
                    f"Kurum: {ilan.get('kurum','')}\n"
                    f"İlan: {ilan.get('tam_metin','')}\n"
                    f"Başvuru: {ilan.get('basvuru_tarihi','')}\n\n"
                    f"İçerik ({icerik_tipi}):\n{icerik}{ek}"
                },
            ],
            temperature=0.1,
            max_tokens=2500,
        )
        st.session_state["son_groq_istegi"] = time.time()
        return yanit.choices[0].message.content
    except Exception as e:
        hata = str(e)
        if "rate_limit" in hata.lower():
            return "⏳ Rate limit — birkaç saniye bekleyip tekrar dene."
        return f"❌ Groq hatası: {hata}"

# ─────────────────────────────────────────────
# FAVORİLER
# ─────────────────────────────────────────────
def favori_toggle(kod):
    favs = st.session_state.setdefault("kamu_favoriler", set())
    if kod in favs: favs.discard(kod)
    else:           favs.add(kod)

def favori_mi(kod):
    return kod in st.session_state.get("kamu_favoriler", set())

# ─────────────────────────────────────────────
# FİLTRELE
# ─────────────────────────────────────────────
def arama_eslesiyor(arama, ilan):
    if not arama: return True
    hedef    = normalize(ilan["tam_metin"] + " " + ilan.get("kurum",""))
    kelimeler = normalize(arama).split()
    return all(k in hedef for k in kelimeler)

def ilan_filtrele(ilanlar, filtre):
    sonuc = ilanlar

    # Favoriler
    if filtre["sadece_favori"]:
        favs  = st.session_state.get("kamu_favoriler", set())
        sonuc = [d for d in sonuc if d["kod"] in favs]

    # Durum
    if filtre["durum"] != "Tümü":
        durum_map = {"🟢 Aktif":"aktif","🟡 Uzatıldı":"uzatildi","🔴 İptal":"iptal"}
        hedef = durum_map.get(filtre["durum"],"aktif")
        sonuc = [d for d in sonuc if d["durum"] == hedef]

    # Meslek kategorisi
    if filtre["kategori"] != "Tümü":
        sonuc = [d for d in sonuc if d["kategori"] == filtre["kategori"]]

    # Arama
    if filtre["arama"]:
        sonuc = [d for d in sonuc if arama_eslesiyor(filtre["arama"], d)]

    return sonuc

# ─────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────
CSS = """
<style>
.kamu-kart {
    background: #131620;
    border-left: 4px solid #7c3aed;
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 4px;
}
.kamu-baslik {
    font-size: 15px;
    font-weight: 600;
    color: #e8eaf0;
    line-height: 1.4;
    margin-bottom: 3px;
}
.kamu-kurum {
    font-size: 12px;
    font-weight: 700;
    color: #a78bfa;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    margin-bottom: 3px;
}
.kamu-meta {
    font-size: 12px;
    color: #9aa0b4;
}
.kamu-tarih {
    color: #f59e0b;
    font-weight: 500;
}
.kamu-durum-aktif   { color: #22c55e; font-weight: 600; }
.kamu-durum-uzatildi{ color: #eab308; font-weight: 600; }
.kamu-durum-iptal   { color: #ef4444; font-weight: 600; }
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
    fav      = favori_mi(d["kod"])
    fav_ikon = "⭐" if fav else "☆"

    durum_css = {"aktif":"kamu-durum-aktif","uzatildi":"kamu-durum-uzatildi","iptal":"kamu-durum-iptal"}.get(d["durum"],"")
    durum_txt = durum_badge(d["durum"])

    st.markdown(f"""
    <div class="kamu-kart">
        <div class="kamu-kurum">{d['kurum'] or '—'}</div>
        <div class="kamu-baslik">{d['kategori']} &nbsp; {d['baslik'] or d['tam_metin']}</div>
        <div class="kamu-meta">
            <span class="{durum_css}">{durum_txt}</span>
            {"&nbsp;·&nbsp;<span class='kamu-tarih'>📅 " + d['basvuru_tarihi'] + "</span>" if d['basvuru_tarihi'] else ""}
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([2, 2, 1])

    anahtar  = f"ki_ozet_{idx}"
    pdf_key  = f"ki_pdf_{idx}"

    with col1:
        st.link_button("🔗 İlana Git", url=d["link"], use_container_width=True)

    with col2:
        if st.button("🤖 AI Özet", key=f"ki_btn_{idx}", use_container_width=True):
            with st.spinner("📖 İlan açılıyor..."):
                icerik, pdf_listesi, tip = ilan_icerik_cek(d["link"])
                st.session_state[pdf_key] = pdf_listesi
            with st.spinner("🤖 AI özetleniyor..."):
                ozet = groq_ozet(d, icerik, pdf_listesi, tip)
                st.session_state[anahtar] = ozet

    with col3:
        if st.button(f"{fav_ikon} Favori", key=f"ki_fav_{idx}", use_container_width=True):
            favori_toggle(d["kod"])
            st.rerun()

    # AI Özet kutusu
    if anahtar in st.session_state:
        with st.expander("📄 AI Özeti", expanded=True):
            st.markdown(st.session_state[anahtar])

        # PDF butonları
        pdf_listesi = st.session_state.get(pdf_key, [])
        if pdf_listesi:
            st.markdown("**📎 Ekli Belgeler — İndir:**")
            for pdf in pdf_listesi:
                ca, cb = st.columns([4, 1])
                with ca:
                    st.markdown(
                        f"<div style='padding:5px 0;font-size:14px;'>📄 {pdf['ad']}</div>",
                        unsafe_allow_html=True,
                    )
                with cb:
                    st.link_button("⬇️ İndir", url=pdf["url"], use_container_width=True)

        if st.button("✖️ Kapat", key=f"ki_kapat_{idx}"):
            for k in [anahtar, pdf_key]:
                st.session_state.pop(k, None)
            st.rerun()

    st.divider()

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
def sidebar_filtre():
    st.sidebar.title("📋 Kamu Personel\nAlım İlanları")
    st.sidebar.markdown("---")

    # ── Durum filtresi ──
    st.sidebar.subheader("🔴 Durum")
    durum = st.sidebar.radio(
        "İlan durumu:",
        options=["Tümü","🟢 Aktif","🟡 Uzatıldı","🔴 İptal"],
        index=1,  # varsayılan: Aktif
        key="ki_durum",
    )

    # ── Meslek kategorisi ──
    st.sidebar.markdown("---")
    st.sidebar.subheader("👔 Meslek")
    kategoriler = ["Tümü"] + list(MESLEK_KATEGORILERI.keys())
    kategori = st.sidebar.selectbox("Kategori:", kategoriler, key="ki_kategori")

    # ── Akıllı Arama ──
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔤 Akıllı Arama")
    arama = st.sidebar.text_input(
        "Kurum veya pozisyon ara:",
        placeholder="örn: sahil, mühendis, istanbul",
        key="ki_arama",
    )
    st.sidebar.markdown(
        "<div class='arama-ipucu'>💡 Birden fazla kelime — hepsi eşleşmeli. Türkçe karakter fark etmez.</div>",
        unsafe_allow_html=True,
    )

    # ── Favoriler ──
    st.sidebar.markdown("---")
    sadece_favori = st.sidebar.checkbox(
        f"⭐ Sadece Favoriler ({len(st.session_state.get('kamu_favoriler', set()))})",
        key="ki_favori",
    )

    # ── Kullanma Kılavuzu ──
    st.sidebar.markdown("---")
    with st.sidebar.expander("📖 Nasıl Kullanılır?", expanded=False):
        st.sidebar.markdown("""
**🔴 Durum Filtresi**
İlanları durumuna göre filtreler:
- *Aktif* → Başvurusu devam eden ilanlar
- *Uzatıldı* → Süresi uzatılmış ilanlar
- *İptal* → İptal edilmiş ilanlar

---

**👔 Meslek Kategorisi**
İlanları meslek grubuna göre filtreler:
Mühendis, sağlık, güvenlik, işçi vb.

---

**🔤 Akıllı Arama**
Kurum adı veya pozisyon adına göre arar.
Birden fazla kelime yazabilirsin — hepsi eşleşmeli.
Türkçe karakter fark etmez.

---

**⭐ Favoriler**
☆ Favori butonuna bas → ilan yıldızlanır.
"Sadece Favoriler" kutusunu işaretle → sadece onları gör.
Favoriler her zaman sayfanın üstünde görünür.

---

**🤖 AI Özet**
İlana ait PDF veya HTML sayfasını otomatik okur,
yapay zeka ile özetler: şartlar, tarihler, belgeler.
PDF varsa altında indirme butonu çıkar.
        """)

    return {
        "durum"        : durum,
        "kategori"     : kategori,
        "arama"        : arama.strip(),
        "sadece_favori": sadece_favori,
    }

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    st.set_page_config(
        page_title="Kamu Personel Alım İlanları",
        page_icon="📋",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(CSS, unsafe_allow_html=True)

    for k, v in [("son_groq_istegi",0), ("kamu_favoriler",set())]:
        if k not in st.session_state:
            st.session_state[k] = v

    if not PDF_DESTEKLI:
        st.info("ℹ️ PDF içerikleri için `pip install PyPDF2` kur.")

    # ── Başlık + Güncelle ──
    col_b, col_btn = st.columns([5, 1])
    with col_b:
        st.title("📋 Kamu Personeli Alım İlanları")
    with col_btn:
        st.write("")
        if st.button("🔄 Verileri Güncelle", use_container_width=True):
            veri_guncelle()
            st.success("Güncellendi!")

    ilanlar = veri_yukle()

    son = st.session_state.get("son_guncelleme")
    if son:
        st.caption(f"📡 Kaynak: kamuilan.sbb.gov.tr · Son güncelleme: {son.strftime('%d.%m.%Y %H:%M')}")

    # ── Varsayılana Dön ──
    if st.button("🏠 Varsayılan Görünüme Dön  ·  Aktif İlanlar", use_container_width=True):
        for k in ["ki_durum","ki_kategori","ki_arama","ki_favori"]:
            st.session_state.pop(k, None)
        st.rerun()

    if not ilanlar:
        st.error("İlanlar yüklenemedi. 'Verileri Güncelle' butonuna tıklayın.")
        return

    filtre   = sidebar_filtre()
    filtreli = ilan_filtrele(ilanlar, filtre)

    # ── İstatistikler ──
    aktif_sayisi = sum(1 for d in ilanlar if d["durum"]=="aktif")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("📋 Toplam İlan",  len(ilanlar))
    c2.metric("🟢 Aktif İlan",   aktif_sayisi)
    c3.metric("🔍 Gösterilen",   len(filtreli))
    c4.metric("⭐ Favoriler",    len(st.session_state.get("kamu_favoriler",set())))

    st.markdown("---")

    if not filtreli:
        st.info("Seçilen filtrelere uygun ilan bulunamadı.")
        return

    # ── Favoriler — her zaman üstte ──
    favs = st.session_state.get("kamu_favoriler", set())
    favori_ilanlar = [d for d in ilanlar if d["kod"] in favs]
    if favori_ilanlar:
        with st.expander(f"⭐ Favorilerim — {len(favori_ilanlar)} ilan", expanded=True):
            for d in favori_ilanlar:
                ilan_karti_goster(d, hash(d["kod"] + "_fav"))
        st.markdown("---")

    # ── Meslek kategorisine göre grupla ──
    if filtre["kategori"] == "Tümü" and not filtre["arama"] and not filtre["sadece_favori"]:
        # Kategorilere göre gruplu görünüm
        gruplar = defaultdict(list)
        for d in filtreli:
            gruplar[d["kategori"]].append(d)

        # Önce dolu kategorileri, sıralı göster
        kat_sirasi = list(MESLEK_KATEGORILERI.keys())
        for kat in kat_sirasi:
            grup = gruplar.get(kat, [])
            if not grup: continue
            with st.expander(f"{kat} — {len(grup)} ilan", expanded=(kat != "📊 Diğer")):
                for d in grup:
                    ilan_karti_goster(d, hash(d["kod"]))
    else:
        # Düz liste
        with st.expander(f"📋 İlanlar — {len(filtreli)} sonuç", expanded=True):
            for d in filtreli:
                ilan_karti_goster(d, hash(d["kod"]))

if __name__ == "__main__":
    main()
