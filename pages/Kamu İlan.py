import time
import re
import io
from collections import defaultdict
from urllib.parse import urljoin, quote
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
GROQ_API_KEY      = st.secrets["GROQ_API_KEY"]
GROQ_MODEL        = "llama-3.3-70b-versatile"
RATE_LIMIT_SANIYE = 4
TZ_TURKIYE        = timezone(timedelta(hours=3))

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/145.0.0.0 Mobile Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
              "image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Upgrade-Insecure-Requests": "1",
    "Connection": "keep-alive",
}

TURKCE_AYLAR = {
    "ocak":1,"şubat":2,"mart":3,"nisan":4,"mayıs":5,
    "haziran":6,"temmuz":7,"ağustos":8,"eylül":9,
    "ekim":10,"kasım":11,"aralık":12,
    "subat":2,"mayis":5,"agustos":8,"eylul":9,"kasim":11,"aralik":12,
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

def session_olustur():
    """ASP.NET session cookie alır."""
    s = requests.Session()
    s.headers.update(HEADERS)
    try:
        s.get(ANASAYFA_URL, verify=False, timeout=15)
    except Exception:
        pass
    return s

def get_session():
    if "http_session" not in st.session_state:
        st.session_state["http_session"] = session_olustur()
    return st.session_state["http_session"]

# ─────────────────────────────────────────────
# VERİ ÇEKME
# ─────────────────────────────────────────────
def tarih_parse(metin):
    """'21 Şubat' veya '21 Şubat 2026' → (gun, ay, yil)"""
    metin = metin.strip()
    m = re.match(r"(\d{1,2})\s+(\w+)(?:\s+(\d{4}))?", metin)
    if not m:
        return None
    gun = int(m.group(1))
    ay_str = normalize(m.group(2))
    yil = int(m.group(3)) if m.group(3) else simdi_tr().year
    ay = TURKCE_AYLAR.get(ay_str)
    if not ay:
        return None
    return (yil, ay, gun)

def ilanları_cek_raw():
    """
    Ana sayfadan tüm ilanları çeker.
    Her ilan: {kurum, baslik, basvuru_tarihi, link, tarih_tuple, logo_url}
    """
    session = get_session()
    try:
        resp = session.get(ANASAYFA_URL, verify=False, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        st.error(f"Sayfa çekilemedi: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    ilanlar = []
    gorulen = set()
    son_tarih = None

    # Sayfa yapısı: tarih başlıkları + altında ilan kartları
    # Tarihler genellikle "21 Şubat" formatında ayrı bir element
    # İlan kartları: kurum adı + ilan başlığı + başvuru tarihi + link

    # Tüm a taglerini tara — ilan detay linkleri ilanDetay.aspx içeriyor
    for eleman in soup.find_all(True):
        tag = eleman.name

        # Tarih başlıklarını yakala (21 Şubat, 20 Şubat gibi)
        metin = eleman.get_text(strip=True)
        if tag in ("h3","h4","h5","span","div","p"):
            t = tarih_parse(metin)
            if t and len(metin) < 20:
                son_tarih = t
                continue

        # İlan linklerini yakala
        if tag == "a":
            href = eleman.get("href", "")
            if "ilanDetay.aspx" not in href:
                continue
            tam_url = urljoin(ANASAYFA_URL, href)
            if tam_url in gorulen:
                continue
            gorulen.add(tam_url)

            # Kart içeriğini al - en yakın anlamlı kapsayıcıya çık
            kapsayici = eleman
            for _ in range(5):
                p = kapsayici.parent
                if not p:
                    break
                metin_uzunluk = len(p.get_text(strip=True))
                if metin_uzunluk > 20:
                    kapsayici = p
                    break
                kapsayici = p

            kart_metin = kapsayici.get_text(" ", strip=True)

            # Logo URL
            logo = None
            img = kapsayici.find("img")
            if img and img.get("src"):
                logo = urljoin(ANASAYFA_URL, img["src"])

            # Başvuru tarihi aralığı (parantez içinde genellikle)
            basvuru = ""
            tarih_m = re.search(r"\(([^)]+)\)", kart_metin)
            if tarih_m:
                basvuru = tarih_m.group(1).strip()

            # Kurum adı ve ilan başlığı
            # Genellikle BÜYÜK HARF kurum adı + ilan başlığı
            satirlar = [s for s in kart_metin.splitlines() if s.strip()]
            kurum = ""
            baslik = eleman.get_text(strip=True)

            # İlanın link metni boşsa kart metninden çıkar
            if not baslik or len(baslik) < 5:
                baslik = kart_metin[:120]

            ilanlar.append({
                "kurum"         : kurum,
                "baslik"        : baslik,
                "basvuru_tarihi": basvuru,
                "link"          : tam_url,
                "tarih"         : son_tarih,
                "logo_url"      : logo,
            })

    # Eğer yukarıdaki yaklaşım az ilan döndürüyorsa alternatif yöntem
    if len(ilanlar) < 3:
        ilanlar = ilanları_cek_alternatif(soup)

    return ilanlar


def ilanları_cek_alternatif(soup):
    """
    Alternatif: sayfadaki tüm ilanDetay linklerini bul,
    her birinin kart yapısını farklı şekilde oku.
    """
    ilanlar = []
    gorulen = set()
    son_tarih = None

    # Önce tüm metni tara, tarih kalıplarını bul
    for el in soup.find_all(string=re.compile(r"^\d{1,2}\s+\w+$")):
        t = tarih_parse(el.strip())
        if t:
            son_tarih = t

    for a in soup.find_all("a", href=re.compile(r"ilanDetay\.aspx")):
        href = a.get("href","")
        tam_url = urljoin(ANASAYFA_URL, href)
        if tam_url in gorulen:
            continue
        gorulen.add(tam_url)

        # Kart: linkin en yakın büyük kapsayıcısı
        kart = a
        for _ in range(8):
            parent = kart.parent
            if not parent:
                break
            if parent.name in ("li","article","div","td"):
                txt = parent.get_text(" ", strip=True)
                if len(txt) > 15:
                    kart = parent
                    break
            kart = parent

        kart_metin = kart.get_text(" ", strip=True)

        # Logo
        logo = None
        img = kart.find("img")
        if img:
            logo = urljoin(ANASAYFA_URL, img.get("src",""))

        # Başvuru tarihi
        basvuru = ""
        tarih_m = re.search(r"\(\s*(\d+\s+\w+\s*[-–]\s*\d+\s+\w+)\s*\)", kart_metin)
        if tarih_m:
            basvuru = tarih_m.group(1).strip()

        baslik = a.get_text(strip=True) or kart_metin[:100]

        ilanlar.append({
            "kurum"         : "",
            "baslik"        : baslik,
            "basvuru_tarihi": basvuru,
            "link"          : tam_url,
            "tarih"         : son_tarih,
            "logo_url"      : logo,
        })

    return ilanlar


def veri_guncelle():
    with st.spinner("🔄 İlanlar güncelleniyor..."):
        # Session yenile
        st.session_state["http_session"] = session_olustur()
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
JENERIK_METINLER = {
    "dosyayi gorun", "goruntule", "goster", "indir", "tikla",
    "tiklayin", "download", "open", "view", "dosyayi indir", "ekler"
}

SAYFA_LINKLERI = re.compile(r"ilanDetay|arsiv|Default|javascript:|#|mailto:|tel:", re.I)

def dosya_linki_mi(href, base_url):
    hl = href.lower()
    for ext in (".pdf",".doc",".docx",".xls",".xlsx",".zip"):
        if hl.endswith(ext):
            return True
    kaliplar = ["getfile","dosyagetir","filedownload","download","/dosya/","/files/","/upload"]
    for k in kaliplar:
        if k in hl:
            return True
    if re.search(r"[?&](id|dosyaid|file|f)=\d+", hl):
        return True
    return False

def pdf_icerigi_cek(pdf_url, session):
    if not PDF_DESTEKLI:
        return ""
    try:
        resp = session.get(pdf_url, verify=False, timeout=15)
        resp.raise_for_status()
        reader = PyPDF2.PdfReader(io.BytesIO(resp.content))
        metin = ""
        for sayfa in reader.pages[:5]:
            metin += sayfa.extract_text() or ""
        return metin[:3000].strip()
    except Exception:
        return ""

def pdf_ad_bul(a_tag, href):
    from urllib.parse import unquote
    link_metni = a_tag.get_text(strip=True)
    norm_link  = normalize(link_metni)
    if link_metni and len(link_metni) > 4 and not any(j in norm_link for j in JENERIK_METINLER):
        return link_metni
    try:
        kapsayici = a_tag.parent
        for _ in range(5):
            if kapsayici is None: break
            metin = kapsayici.get_text(" ", strip=True)
            eslesme = re.search(r"([^\n]{3,80}[.]pdf)", metin, re.I)
            if eslesme:
                ad = eslesme.group(1).strip()
                if len(ad) < 100:
                    return ad
            kapsayici = kapsayici.parent
    except Exception:
        pass
    dosya = href.split("/")[-1].split("?")[0]
    try:
        dosya = unquote(dosya)
    except Exception:
        pass
    return dosya or "Belge"

def ilan_icerik_cek(url):
    session = get_session()
    try:
        resp = session.get(url, verify=False, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Tüm linkler (debug)
        tum_linkler = []
        for a in soup.find_all("a", href=True):
            metin = a.get_text(strip=True)
            href  = a["href"]
            if href and href not in ("#","javascript:void(0)"):
                tum_linkler.append({
                    "metin": metin[:60],
                    "href" : href[:120],
                    "tam"  : urljoin(url, href)[:150],
                })

        # Nav/footer temizle
        for tag in soup(["nav","header","footer","script","style"]):
            tag.decompose()

        # PDF / dosya linkleri
        pdf_listesi = []
        gorulen = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if not href or href.startswith(("javascript:","mailto:","tel:")):
                continue
            if not dosya_linki_mi(href, url):
                continue
            tam_url = urljoin(url, href)
            if tam_url in gorulen:
                continue
            gorulen.add(tam_url)
            ad     = pdf_ad_bul(a, href)
            icerik = pdf_icerigi_cek(tam_url, session)
            pdf_listesi.append({"ad": ad, "url": tam_url, "icerik": icerik})

        satirlar = [s for s in soup.get_text("\n", strip=True).splitlines() if s.strip()]
        metin = "\n".join(satirlar[:400])

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
1. Metinde geçen TÜM sayısal ve spesifik bilgileri yaz: ölçüler, adetler, saatler, tarihler, adresler, banka adları, form adları vb.
2. Listeler varsa (örn: istenen belgeler, aranan nitelikler) HER maddeyi ayrı satırda numaralı yaz.
3. Metinde OLMAYAN hiçbir bilgiyi uydurma.
4. Yanıtını Türkçe ver.

Şu başlıkları kullan (bilgi yoksa o başlığı atla):

📋 **İlan Özeti**
🏛️ **Kurum**
🎯 **Aranan Pozisyon(lar)**
🔢 **Alınacak Kişi Sayısı**
📚 **Aranan Şartlar / Nitelikler**
📋 **İstenen Belgeler**
📅 **Önemli Tarihler**
📝 **Başvuru Bilgileri**
⚠️ **Dikkat Edilmesi Gerekenler**
⬇️ **Ekli Dosyalar** (varsa)"""

        ek_metin = ""
        if pdf_listesi:
            ek_metin = "\n\n--- EKLİ DOSYALAR ---\n"
            for p in pdf_listesi:
                ek_metin += f"\nDosya: {p['ad']}\nURL: {p['url']}\n"
                if p["icerik"]:
                    ek_metin += f"İçerik:\n{p['icerik'][:1500]}\n"

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
    favs = st.session_state.setdefault("kamu_favoriler", set())
    if link in favs:
        favs.discard(link)
    else:
        favs.add(link)

def favori_mi(link):
    return link in st.session_state.get("kamu_favoriler", set())

# ─────────────────────────────────────────────
# AKILLI ARAMA
# ─────────────────────────────────────────────
def arama_eslesiyor(arama_metni, ilan):
    if not arama_metni:
        return True
    hedef = normalize(ilan["baslik"] + " " + ilan.get("kurum",""))
    kelimeler = normalize(arama_metni).split()
    return all(k in hedef for k in kelimeler)

# ─────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────
CSS = """
<style>
.kamu-kart {
    background: #1a1d2e;
    border-left: 4px solid #7c3aed;
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 4px;
}
.kamu-baslik {
    font-size: 15px;
    font-weight: 600;
    color: #e8eaf0;
    margin-bottom: 4px;
    line-height: 1.4;
}
.kamu-meta {
    font-size: 12px;
    color: #9aa0b4;
    margin-top: 3px;
}
.kamu-tarih {
    font-size: 12px;
    color: #f59e0b;
    font-weight: 500;
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
    fav      = favori_mi(d["link"])
    fav_ikon = "⭐" if fav else "☆"

    tarih_str = ""
    if d.get("basvuru_tarihi"):
        tarih_str = f"📅 {d['basvuru_tarihi']}"

    kurum_str = f"🏛️ {d['kurum']}  " if d.get("kurum") else ""

    st.markdown(f"""
    <div class="kamu-kart">
        <div class="kamu-baslik">{d['baslik']}</div>
        <div class="kamu-meta">{kurum_str}<span class="kamu-tarih">{tarih_str}</span></div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        st.link_button("🔗 İlana Git", url=d["link"], use_container_width=True)

    anahtar   = f"kamu_ozet_{idx}"
    pdf_key   = f"kamu_pdf_{idx}"
    link_key  = f"kamu_lnk_{idx}"

    with col2:
        if st.button("🤖 AI Özet", key=f"kamu_btn_{idx}", use_container_width=True):
            with st.spinner("📖 İlan okunuyor..."):
                icerik, pdf_listesi, tum_linkler = ilan_icerik_cek(d["link"])
                st.session_state[pdf_key]  = pdf_listesi
                st.session_state[link_key] = tum_linkler
            with st.spinner("🤖 AI özetleniyor..."):
                ozet = groq_ozet(d["baslik"], icerik, pdf_listesi)
                st.session_state[anahtar] = ozet

    with col3:
        if st.button(f"{fav_ikon} Favori", key=f"kamu_fav_{idx}", use_container_width=True):
            favori_toggle(d["link"])
            st.rerun()

    if anahtar in st.session_state:
        with st.expander("📄 AI Özeti", expanded=True):
            st.markdown(st.session_state[anahtar])

        # PDF butonları
        pdf_listesi = st.session_state.get(pdf_key, [])
        if pdf_listesi:
            st.markdown("**📎 Ekli Belgeler — İndir:**")
            for pdf in pdf_listesi:
                col_ad, col_btn = st.columns([4, 1])
                with col_ad:
                    st.markdown(
                        f"<div style='padding:5px 0;font-size:14px;'>📄 {pdf['ad']}</div>",
                        unsafe_allow_html=True,
                    )
                with col_btn:
                    st.link_button("⬇️ İndir", url=pdf["url"], use_container_width=True)
            st.markdown("")
        else:
            tum_linkler = st.session_state.get(link_key, [])
            if tum_linkler:
                with st.expander("🔍 Sayfadaki Tüm Linkler (debug — PDF bulunamadı)", expanded=False):
                    for lnk in tum_linkler:
                        st.markdown(f"**Metin:** `{lnk['metin']}` | **href:** `{lnk['href']}`")

        if st.button("✖️ Kapat", key=f"kamu_kapat_{idx}"):
            for k in [anahtar, pdf_key, link_key]:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()

    st.divider()

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
def sidebar_filtre():
    st.sidebar.title("📋 Kamu Personel\nAlım İlanları")
    st.sidebar.markdown("---")

    st.sidebar.subheader("🔤 Akıllı Arama")
    arama = st.sidebar.text_input(
        "Kurum veya ilan başlığında ara:",
        placeholder="örn: sahil güvenlik, mühendis",
        key="kamu_arama",
    )
    st.sidebar.markdown(
        "<div class='arama-ipucu'>💡 Birden fazla kelime yazabilirsin. "
        "Türkçe karakter fark etmez.</div>",
        unsafe_allow_html=True,
    )

    st.sidebar.markdown("---")
    sadece_favori = st.sidebar.checkbox(
        f"⭐ Sadece Favoriler ({len(st.session_state.get('kamu_favoriler', set()))})",
        key="kamu_sadece_favori",
    )

    # Kullanma Kılavuzu
    st.sidebar.markdown("---")
    with st.sidebar.expander("📖 Nasıl Kullanılır?", expanded=False):
        st.sidebar.markdown("""
**🔄 Verileri Güncelle**
Siteyi anlık tarar, yeni ilanları çeker.
Her gün otomatik güncellenir.

---

**🔤 Akıllı Arama**
Kurum adı veya ilan başlığında arama yapar.
Birden fazla kelime yazabilirsin — hepsi
eşleşmeli. Türkçe karakter takılmaz.

---

**⭐ Favoriler**
☆ Favori butonuna basınca ilan yıldızlanır.
"Sadece Favoriler" ile sadece onları görürsün.
Favoriler sayfanın üstünde her zaman görünür.

---

**🤖 AI Özet**
İlanı otomatik okuyup özetler:
pozisyon, şartlar, tarihler, belgeler.
Varsa ekli PDF'leri de indirme butonu ile gösterir.
        """)

    return {
        "arama"        : arama.strip(),
        "sadece_favori": sadece_favori,
    }

# ─────────────────────────────────────────────
# FİLTRELE
# ─────────────────────────────────────────────
def ilan_filtrele(ilanlar, filtre):
    sonuc = ilanlar
    if filtre["sadece_favori"]:
        favs  = st.session_state.get("kamu_favoriler", set())
        sonuc = [d for d in sonuc if d["link"] in favs]
    if filtre["arama"]:
        sonuc = [d for d in sonuc if arama_eslesiyor(filtre["arama"], d)]
    return sonuc

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

    for k, v in [("son_groq_istegi", 0), ("kamu_favoriler", set())]:
        if k not in st.session_state:
            st.session_state[k] = v

    if not PDF_DESTEKLI:
        st.info("ℹ️ PDF içerikleri için `pip install PyPDF2` kurabilirsin.")

    # Başlık + Güncelle
    col_b, col_btn = st.columns([5, 1])
    with col_b:
        st.title("📋 Kamu Personeli Alım İlanları")
    with col_btn:
        st.write("")
        if st.button("🔄 Verileri Güncelle", use_container_width=True):
            st.cache_data.clear()
            veri_guncelle()
            st.success("Güncellendi!")

    ilanlar = veri_yukle()

    son = st.session_state.get("son_guncelleme")
    if son:
        st.caption(f"📡 Kaynak: kamuilan.sbb.gov.tr · Son güncelleme: {son.strftime('%d.%m.%Y %H:%M')}")

    # Varsayılan görünüm butonu
    if st.button("🏠 Varsayılan Görünüme Dön", use_container_width=True):
        for k in ["kamu_arama", "kamu_sadece_favori"]:
            if k in st.session_state:
                del st.session_state[k]
        st.rerun()

    if not ilanlar:
        st.error("İlanlar yüklenemedi. Lütfen 'Verileri Güncelle' butonuna tıklayın.")
        return

    filtre   = sidebar_filtre()
    filtreli = ilan_filtrele(ilanlar, filtre)

    # İstatistik
    c1, c2, c3 = st.columns(3)
    c1.metric("📋 Toplam İlan", len(ilanlar))
    c2.metric("🔍 Gösterilen",  len(filtreli))
    c3.metric("⭐ Favoriler",   len(st.session_state.get("kamu_favoriler", set())))

    st.markdown("---")

    if not filtreli:
        st.info("Seçilen filtrelere uygun ilan bulunamadı.")
        return

    # ── Favoriler — her zaman üstte ──
    favs = st.session_state.get("kamu_favoriler", set())
    favori_ilanlar = [d for d in ilanlar if d["link"] in favs]
    if favori_ilanlar:
        with st.expander(f"⭐ Favorilerim — {len(favori_ilanlar)} ilan", expanded=True):
            for d in favori_ilanlar:
                ilan_karti_goster(d, hash(d["link"] + "_fav"))
        st.markdown("---")

    # ── Tüm ilanlar (tarih gruplama YOK — site zaten güncel ilanlar) ──
    with st.expander(f"📋 Güncel İlanlar — {len(filtreli)} ilan", expanded=True):
        for d in filtreli:
            ilan_karti_goster(d, hash(d["link"]))

if __name__ == "__main__":
    main()
