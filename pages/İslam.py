"""
🕌 İslami Zaman — Namaz Vakitleri & İslami Asistan
Ana Kaynak   : ezanvakti.imsakiyem.com (daha temiz API, search desteği)
Yedek Kaynak : ezanvakti.emushaf.net
Diğer        : Ramadan API + Al-Quran Cloud (tr.diyanet) + Groq AI
"""

import streamlit as st
import requests
from datetime import datetime, timedelta
import pytz
import random

# ─────────────────────────────────────────────────────────────
# SAYFA AYARLARI
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="🕌 İslami Zaman",
    page_icon="🕌",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Amiri:ital,wght@0,400;0,700;1,400&family=Tajawal:wght@300;400;500;700&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

.stApp {
    background: #080e1a;
    color: #ddd0b8;
    font-family: 'Tajawal', sans-serif;
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0a1220 0%, #080e1a 100%) !important;
    border-right: 1px solid #1a2e48;
}
[data-testid="stSidebarNav"] { display: none; }

/* ── HERO ── */
.hero {
    background: linear-gradient(135deg, #0b1829 0%, #0f2040 50%, #0b1829 100%);
    border: 1px solid #1e3d64;
    border-radius: 24px;
    padding: 28px 36px;
    text-align: center;
    margin-bottom: 24px;
    position: relative;
    overflow: hidden;
}
.hero::before {
    content: '';
    position: absolute;
    top: 0; left: 10%; right: 10%;
    height: 2px;
    background: linear-gradient(90deg, transparent, #c8a84b, #ffe066, #c8a84b, transparent);
}
.hero-arabic {
    font-family: 'Amiri', serif;
    font-size: 1.6em;
    color: #c8a84b;
    letter-spacing: 4px;
    opacity: 0.85;
    margin-bottom: 4px;
}
.hero-clock {
    font-family: 'Tajawal', monospace;
    font-size: 4.2em;
    font-weight: 700;
    color: #e8d5a3;
    letter-spacing: 6px;
    line-height: 1;
    margin: 8px 0;
    text-shadow: 0 0 40px rgba(200,168,75,0.3);
}
.hero-miladi { font-size: 1em; color: #7a9dbd; letter-spacing: 2px; margin-bottom: 2px; }
.hero-hijri  { font-family: 'Amiri', serif; font-size: 1.15em; color: #c8a84b; margin-top: 4px; }
.hero-location { font-size: 0.85em; color: #4a7a9b; margin-top: 8px; letter-spacing: 1px; }
.hero-kaynak {
    font-size: 0.68em; color: #2a5070; margin-top: 6px; letter-spacing: 0.5px;
    display: flex; align-items: center; justify-content: center; gap: 6px;
}
.kaynak-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 20px;
    font-size: 0.9em;
}
.kaynak-imsakiyem { background: #0a2a10; border: 1px solid #1a5020; color: #4caf6a; }
.kaynak-emushaf   { background: #2a1a05; border: 1px solid #5a3010; color: #ff9800; }

/* ── VAKİT KARTLARI ── */
.vakit-card {
    background: linear-gradient(160deg, #0c1c2e 0%, #0f2340 100%);
    border: 1px solid #1a3050;
    border-radius: 16px;
    padding: 18px 8px;
    text-align: center;
    position: relative;
    height: 130px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
}
.vakit-card.aktif {
    background: linear-gradient(160deg, #162840 0%, #1e3c5a 100%);
    border-color: #c8a84b;
    box-shadow: 0 0 24px rgba(200,168,75,0.15);
}
.vakit-card.aktif::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, #c8a84b, transparent);
    border-radius: 16px 16px 0 0;
}
.vakit-ikon  { font-size: 1.7em; margin-bottom: 6px; }
.vakit-adi   { font-size: 0.72em; color: #5a8aaa; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 5px; }
.vakit-saat  { font-size: 1.45em; font-weight: 700; color: #ddd0b8; }
.vakit-card.aktif .vakit-saat { color: #c8a84b; }
.vakit-etiket { font-size: 0.65em; color: #c8a84b; margin-top: 4px; letter-spacing: 1px; }

/* ── GERİ SAYIM ── */
.geri-sayim {
    background: linear-gradient(135deg, #0c1e10 0%, #0a180c 100%);
    border: 1px solid #1e4a28;
    border-radius: 20px;
    padding: 22px 28px;
    text-align: center;
}
.geri-sayim.ramazan {
    background: linear-gradient(135deg, #1e1205 0%, #160e04 100%);
    border-color: #6a4010;
}
.gs-ust     { font-size: 0.78em; color: #5a8a6a; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 6px; }
.gs-namaz   { font-family: 'Amiri', serif; font-size: 1.4em; color: #a8d8b8; margin-bottom: 10px; }
.gs-zaman   { font-family: 'Tajawal', monospace; font-size: 3em; font-weight: 700; color: #4caf6a;
               letter-spacing: 4px; text-shadow: 0 0 20px rgba(76,175,80,0.3); }

/* ── BÖLüM BAŞLIK ── */
.bolum-baslik {
    font-family: 'Amiri', serif;
    font-size: 1.3em;
    color: #c8a84b;
    padding: 14px 0 10px;
    border-bottom: 1px solid #1a3050;
    margin: 20px 0 14px;
}

/* ── BİLGİ KUTU ── */
.bilgi-kutu {
    background: #0c1c2e;
    border: 1px solid #1a3050;
    border-radius: 14px;
    padding: 18px;
    text-align: center;
    height: 110px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
}
.bilgi-deger  { font-size: 1.7em; font-weight: 700; color: #c8a84b; font-family: 'Amiri', serif; }
.bilgi-etiket { font-size: 0.72em; color: #4a7a9b; text-transform: uppercase; letter-spacing: 1px; margin-top: 4px; }

/* ── AYET KUTU ── */
.ayet-kutu {
    background: linear-gradient(160deg, #0c1c2e 0%, #0f2340 100%);
    border: 1px solid #1e3d64;
    border-radius: 18px;
    padding: 26px 30px;
    margin: 12px 0;
}
.ayet-arapca  { font-family: 'Amiri', serif; font-size: 2em; color: #c8a84b; text-align: right;
                direction: rtl; line-height: 2; margin-bottom: 18px; padding-bottom: 16px; border-bottom: 1px solid #1e3d64; }
.ayet-turkce  { font-size: 1.05em; color: #a8c8e0; line-height: 1.85; font-style: italic; margin-bottom: 12px; }
.ayet-kaynak  { font-size: 0.75em; color: #3a6080; text-align: right; }

/* ── RAMAZAN PANKART ── */
.ramazan-pankart {
    background: linear-gradient(135deg, #1e1005 0%, #2a1808 60%, #1e1005 100%);
    border: 1px solid #8a5820;
    border-radius: 22px;
    padding: 28px;
    text-align: center;
    position: relative;
    overflow: hidden;
}
.ramazan-pankart::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, transparent, #ff9800, #ffd54f, #ff9800, transparent);
}
.ramazan-baslik { font-family: 'Amiri', serif; font-size: 2.2em; color: #ffc107; }

/* ── CHAT ── */
.sohbet-kutu {
    background: #0c1c2e;
    border: 1px solid #1a3050;
    border-radius: 14px;
    padding: 16px 20px;
    margin: 6px 0;
    color: #a8c8e0;
    line-height: 1.7;
}
.sohbet-kutu.kullanici {
    background: linear-gradient(135deg, #0f2010 0%, #0c180c 100%);
    border-color: #1e4a28;
    color: #a8d8b8;
    text-align: right;
}
.sohbet-rol { font-size: 0.7em; color: #3a6080; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; }
.sohbet-kutu.kullanici .sohbet-rol { color: #3a6a40; }

/* ── UYARI ── */
.uyari-not {
    background: #1a1205;
    border: 1px solid #4a3010;
    border-left: 3px solid #c8a84b;
    border-radius: 0 10px 10px 0;
    padding: 12px 16px;
    margin: 10px 0;
    font-size: 0.82em;
    color: #8a7840;
    line-height: 1.6;
}

/* ── HAFTALIK TABLO ── */
.haftalik-satir {
    display: grid;
    grid-template-columns: 2.2fr 1fr 1fr 1fr 1fr 1fr 1fr;
    gap: 4px;
    padding: 8px 12px;
    border-radius: 8px;
    margin: 3px 0;
    background: #0a1420;
    border: 1px solid #0f2030;
    font-size: 0.84em;
    align-items: center;
}
.haftalik-satir.bugun { background: #0f2035; border-color: #1e4060; }
.haftalik-satir.baslik {
    background: transparent;
    border-color: transparent;
    color: #c8a84b;
    font-size: 0.75em;
    text-transform: uppercase;
    letter-spacing: 1px;
}

/* ── STREAMLİT OVERRIDE ── */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stDecoration"] { display: none; }
.stButton > button {
    background: linear-gradient(135deg, #0f2040, #162c50) !important;
    color: #c8d8e8 !important;
    border: 1px solid #1e3d64 !important;
    border-radius: 10px !important;
    font-family: 'Tajawal', sans-serif !important;
    font-size: 0.9em !important;
    transition: all 0.25s !important;
}
.stButton > button:hover { border-color: #c8a84b !important; color: #c8a84b !important; }
.stSelectbox > div > div {
    background: #0c1c2e !important; border-color: #1a3050 !important; color: #ddd0b8 !important;
}
.stTextInput > div > div > input, .stTextArea > div > div > textarea {
    background: #0c1c2e !important; border-color: #1a3050 !important;
    color: #ddd0b8 !important; border-radius: 10px !important;
    font-family: 'Tajawal', sans-serif !important;
}
label { color: #7a9dbd !important; font-family: 'Tajawal', sans-serif !important; }
.stTabs [data-baseweb="tab"]             { color: #5a8aaa !important; font-family: 'Tajawal', sans-serif !important; }
.stTabs [aria-selected="true"]           { color: #c8a84b !important; }
.stTabs [data-baseweb="tab-highlight"]   { background-color: #c8a84b !important; }
p, li { color: #a0b8cc; }
h1, h2, h3 { font-family: 'Amiri', serif !important; color: #c8a84b !important; }
.stNumberInput > div > div > input { background: #0c1c2e !important; border-color: #1a3050 !important; color: #ddd0b8 !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# SABITLER
# ─────────────────────────────────────────────────────────────
IMSAKIYEM   = "https://ezanvakti.imsakiyem.com"   # ANA KAYNAK
EMUSHAF     = "https://ezanvakti.emushaf.net"      # YEDEK KAYNAK
RAMADAN_URL = "https://ramadan.munafio.com/api/check"
QURAN_URL   = "https://api.alquran.cloud/v1"
DIYANET_URL = "https://t061.diyanet.gov.tr/apigateway/acikkaynakkuran"
EVERYAYAH   = "https://everyayah.com/data"
# Sesli okuma kari seçenekleri (everyayah.com klasör adları)
KARILER = {
    "Abdulbasit Abdussamed (Murattal)": "Abdul_Basit_Murattal_64kbps",
    "Mishary Rashid Alafasy":           "Mishary_Rashid_Alafasy_128kbps",
    "Mahmoud Khalil al-Hussary":        "Husary_128kbps",
    "Saad Al-Ghamdi":                   "Saad_Al-Ghamdee_128kbps",
    "Muhammad Siddiq Al-Minshawi":      "Minshawi_Murattal_128kbps",
}
NOMINATIM   = "https://nominatim.openstreetmap.org"
TR_TZ       = pytz.timezone("Europe/Istanbul")

VAKIT_IKONLARI = {
    "imsak": "🌙", "gunes": "🌅", "ogle": "☀️",
    "ikindi": "🌤️", "aksam": "🌇", "yatsi": "🌃"
}
VAKIT_ADLARI = {
    "imsak": "İmsak", "gunes": "Güneş", "ogle": "Öğle",
    "ikindi": "İkindi", "aksam": "Akşam", "yatsi": "Yatsı"
}
GUN_ADLARI = {
    "Monday": "Pazartesi", "Tuesday": "Salı", "Wednesday": "Çarşamba",
    "Thursday": "Perşembe", "Friday": "Cuma", "Saturday": "Cumartesi", "Sunday": "Pazar"
}
AY_ADLARI = {
    "January": "Ocak", "February": "Şubat", "March": "Mart", "April": "Nisan",
    "May": "Mayıs", "June": "Haziran", "July": "Temmuz", "August": "Ağustos",
    "September": "Eylül", "October": "Ekim", "November": "Kasım", "December": "Aralık"
}

# ─────────────────────────────────────────────────────────────
# YARDIMCI FONKSİYONLAR
# ─────────────────────────────────────────────────────────────
def normalize_eslesme(metin: str) -> str:
    donusum = str.maketrans("çÇğĞıİöÖşŞüÜ", "cCgGiIoOsSuU")
    return metin.translate(donusum).upper().strip()

def adi_duzenle(adi: str) -> str:
    """TÜMÜYLE BÜYÜK HARF → Title Case (emushaf.net hatası için)"""
    if not adi:
        return adi
    kelimeler = adi.strip().split()
    sonuc = []
    for k in kelimeler:
        if not k:
            continue
        ilk = "İ" if k[0] == "I" else k[0].upper()
        kalan = k[1:].lower()
        sonuc.append(ilk + kalan)
    return " ".join(sonuc)

def zaman_parse(saat_str: str, tarih=None):
    if tarih is None:
        tarih = datetime.now(TR_TZ).date()
    try:
        s, d = saat_str.strip().split(":")
        naive = datetime.combine(tarih, datetime.min.time().replace(hour=int(s), minute=int(d)))
        return TR_TZ.localize(naive)
    except:
        return None

def geri_sayim_str(hedef_dt) -> str:
    now = datetime.now(TR_TZ)
    fark = hedef_dt - now
    if fark.total_seconds() <= 0:
        return "00:00:00"
    toplam = int(fark.total_seconds())
    s, kalan = divmod(toplam, 3600)
    d, sn = divmod(kalan, 60)
    return f"{s:02d}:{d:02d}:{sn:02d}"

def tr_tarih_format(dt) -> str:
    gun = GUN_ADLARI.get(dt.strftime("%A"), dt.strftime("%A"))
    ay  = AY_ADLARI.get(dt.strftime("%B"), dt.strftime("%B"))
    return f"{gun}, {dt.day} {ay} {dt.year}"

def canlı_gs_js(element_id: str, hedef_dt) -> str:
    """Canlı geri sayım JS kodu"""
    ts = int(hedef_dt.timestamp() * 1000)
    return f"""
    <script>
    (function f() {{
        var el = window.parent.document.getElementById('{element_id}');
        if (el) {{
            var k = Math.max(0, {ts} - Date.now());
            var s  = Math.floor(k / 3600000);
            var d  = Math.floor((k % 3600000) / 60000);
            var sn = Math.floor((k % 60000) / 1000);
            el.textContent = String(s).padStart(2,'0') + ':' + String(d).padStart(2,'0') + ':' + String(sn).padStart(2,'0');
        }}
        setTimeout(f, 1000);
    }})();
    </script>
    """

# ─────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────
defaults = {
    "sohbet": [],
    "ilce_id": None,
    "ilce_id_emushaf": None,          # fallback için
    "konum_adi": "",
    "kaynak": "imsakiyem",             # "imsakiyem" | "emushaf"
    "geo_denendi": False,
    "ayet_tohumu": random.randint(1, 9999),
    "ramazan_dua": None,
    "groq_api_key_input": "",          # kullanıcı girişi
    "manuel_konum_ac": False,          # manuel konum paneli
    "im_secili_ulke_idx": 0,
    "im_secili_eyalet_idx": 0,
    "im_secili_ilce_idx": 0,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ─────────────────────────────────────────────────────────────
# GEOLOCATION → QUERY PARAMS
# ─────────────────────────────────────────────────────────────
params   = st.query_params
geo_lat  = params.get("lat",     None)
geo_lng  = params.get("lng",     None)
geo_red  = params.get("geo_red", None)

# Geolocation Streamlit Cloud sandbox'ta çalışmıyor — tamamen kaldırıldı
# Konum seçimi ana panel expander'ından yapılıyor (varsayılan: Samsun/Atakum)
st.session_state.geo_denendi = True

# ─────────────────────────────────────────────────────────────
# ═══════════════  İMSAKİYEM API FONKSİYONLARI  ═══════════════
# ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=86400)
def im_ulkeler():
    try:
        r = requests.get(f"{IMSAKIYEM}/api/locations/countries", timeout=10)
        return r.json().get("data", []) if r.ok else []
    except:
        return []

@st.cache_data(ttl=86400)
def im_eyaletler(country_id: str):
    try:
        r = requests.get(f"{IMSAKIYEM}/api/locations/states", params={"countryId": country_id}, timeout=10)
        return r.json().get("data", []) if r.ok else []
    except:
        return []

@st.cache_data(ttl=86400)
def im_ilceler(state_id: str):
    try:
        r = requests.get(f"{IMSAKIYEM}/api/locations/districts", params={"stateId": state_id}, timeout=10)
        return r.json().get("data", []) if r.ok else []
    except:
        return []

def im_ara(tip: str, sorgu: str):
    """tip: countries | states | districts — cache yok, her sorguda taze sonuç"""
    try:
        r = requests.get(
            f"{IMSAKIYEM}/api/locations/search/{tip}",
            params={"q": sorgu},
            timeout=8,
            headers={"Accept": "application/json"},
        )
        if r.ok:
            veri = r.json()
            if isinstance(veri, list):
                return veri
            return veri.get("data", veri.get("results", []))
        return []
    except Exception:
        return []

@st.cache_data(ttl=600)
def im_vakitler(district_id: str, period: str = "weekly"):
    try:
        r = requests.get(f"{IMSAKIYEM}/api/prayer-times/{district_id}/{period}", timeout=12)
        if not r.ok:
            return []
        veri = r.json()
        if isinstance(veri, list):
            return veri
        if isinstance(veri, dict):
            for key in ("data", "prayer_times", "prayerTimes", "times", "results"):
                if isinstance(veri.get(key), list):
                    return veri[key]
        return []
    except Exception:
        return []

@st.cache_data(ttl=86400)
def varsayilan_konum_yukle():
    """Samsun / Atakum ilçesini imsakiyem'den bul, _id döndür"""
    try:
        sonuclar = im_ara("districts", "Atakum")
        for s in sonuclar:
            if "atakum" in s.get("name", "").lower():
                sehir = ""
                if isinstance(s.get("state_id"), dict):
                    sehir = s["state_id"].get("name", "")
                return s["_id"], f"📍 {sehir} / {s['name']}" if sehir else f"📍 {s['name']}"
        # Bulamazsa Samsun merkez dene
        sonuclar2 = im_ara("districts", "Samsun")
        if sonuclar2:
            s = sonuclar2[0]
            sehir = s["state_id"].get("name", "") if isinstance(s.get("state_id"), dict) else ""
            return s["_id"], f"📍 {sehir} / {s['name']}" if sehir else f"📍 {s['name']}"
    except Exception:
        pass
    return None, None

# ─────────────────────────────────────────────────────────────
# ═══════════════  EMUSHAF YEDEK API  ═══════════════
# ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=86400)
def em_ulkeler():
    try:
        r = requests.get(f"{EMUSHAF}/ulkeler", timeout=10)
        return r.json() if r.ok else []
    except:
        return []

@st.cache_data(ttl=86400)
def em_sehirler(ulke_id):
    try:
        r = requests.get(f"{EMUSHAF}/sehirler/{ulke_id}", timeout=10)
        return r.json() if r.ok else []
    except:
        return []

@st.cache_data(ttl=86400)
def em_ilceler(sehir_id):
    try:
        r = requests.get(f"{EMUSHAF}/ilceler/{sehir_id}", timeout=10)
        return r.json() if r.ok else []
    except:
        return []

@st.cache_data(ttl=600)
def em_vakitler(ilce_id):
    try:
        r = requests.get(f"{EMUSHAF}/vakitler/{ilce_id}", timeout=10)
        if not r.ok:
            return []
        veri = r.json()
        # API bazen dict, bazen list döner
        if isinstance(veri, list):
            return veri
        if isinstance(veri, dict):
            for key in ("data", "vakitler", "times", "results"):
                if isinstance(veri.get(key), list):
                    return veri[key]
            return [veri]  # tek kayıt
        return []
    except Exception:
        return []

# ─────────────────────────────────────────────────────────────
# GENEL API'LER
# ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def ramazan_kontrol(tarih_str: str):
    try:
        r = requests.get(RAMADAN_URL, params={"date": tarih_str}, timeout=8)
        return r.json() if r.ok else None
    except:
        return None

@st.cache_data(ttl=3600)
def hicri_tarih_getir(tarih_iso: str) -> str:
    """Aladdin API'den Hicri tarihi çek (YYYY-MM-DD → Hicri string)"""
    try:
        r = requests.get(
            f"https://api.aladhan.com/v1/gToH/{tarih_iso.replace('-', '-')}",
            timeout=6
        )
        if r.ok:
            d = r.json().get("data", {}).get("hijri", {})
            gun  = d.get("day", "")
            ay   = d.get("month", {}).get("ar", "") or d.get("month", {}).get("en", "")
            yil  = d.get("year", "")
            if gun and yil:
                return f"{gun} {ay} {yil}"
    except Exception:
        pass
    return ""

@st.cache_data(ttl=86400)
def sure_listesi_getir():
    try:
        r = requests.get(f"{QURAN_URL}/surah", timeout=10)
        return r.json().get("data", []) if r.ok else []
    except:
        return []

@st.cache_data(ttl=86400)
def sureyi_getir(sure_no: int):
    try:
        r = requests.get(f"{QURAN_URL}/surah/{sure_no}/tr.diyanet", timeout=15)
        return r.json().get("data", None) if r.ok else None
    except:
        return None

@st.cache_data(ttl=86400)
def ayet_getir(ayet_no: int):
    try:
        r1 = requests.get(f"{QURAN_URL}/ayah/{ayet_no}", timeout=8)
        r2 = requests.get(f"{QURAN_URL}/ayah/{ayet_no}/tr.diyanet", timeout=8)
        return {
            "ar": r1.json().get("data", {}) if r1.ok else {},
            "tr": r2.json().get("data", {}) if r2.ok else {},
        }
    except:
        return None

@st.cache_data(ttl=86400)
def cuz_getir(cuz_no: int):
    try:
        r = requests.get(f"{QURAN_URL}/juz/{cuz_no}/tr.diyanet", timeout=15)
        return r.json().get("data", None) if r.ok else None
    except:
        return None

# ─────────────────────────────────────────────────────────────
# DİYANET OPEN SOURCE KURAN API
# ─────────────────────────────────────────────────────────────
def diyanet_baslik():
    """Diyanet API icin Authorization header — resmi isimler: DIB_KURAN_API_TOKEN, DIB_KURAN_API_BASE_URL"""
    key = ""
    base_url_override = ""
    try:
        # Resmi env ismi: DIB_KURAN_API_TOKEN
        if "DIB_KURAN_API_TOKEN" in st.secrets:
            key = str(st.secrets["DIB_KURAN_API_TOKEN"]).strip()
        # Eski isim fallback
        elif "DIYANET_API_KEY" in st.secrets:
            key = str(st.secrets["DIYANET_API_KEY"]).strip()
        # Resmi base URL override
        if "DIB_KURAN_API_BASE_URL" in st.secrets:
            base_url_override = str(st.secrets["DIB_KURAN_API_BASE_URL"]).strip()
    except Exception:
        pass
    if not key:
        key = str(st.session_state.get("diyanet_api_key_input", "")).strip()
    if base_url_override:
        # Session'a kaydet ki fonksiyonlar kullansın
        st.session_state["_diy_base_url"] = base_url_override.rstrip("/")
    return {"Authorization": f"Bearer {key}", "Accept": "application/json"} if key else None

def diyanet_aktif():
    return diyanet_baslik() is not None

def diyanet_key() -> str:
    """Diyanet API token'ini döndür"""
    h = diyanet_baslik()
    if not h:
        return ""
    auth = h.get("Authorization", "")
    return auth.replace("Bearer ", "").strip()

def diyanet_base_url() -> str:
    """Aktif Diyanet base URL (secrets'tan veya default)"""
    # Önce session state'e kaydedilmiş override'a bak
    override = st.session_state.get("_diy_base_url", "")
    if override:
        return override
    # secrets'tan direkt oku
    try:
        if "DIB_KURAN_API_BASE_URL" in st.secrets:
            return str(st.secrets["DIB_KURAN_API_BASE_URL"]).strip().rstrip("/")
    except Exception:
        pass
    return DIYANET_URL

# ─── Diyanet API response formatları (schema'ya göre):
# GET /api/v1/chapters          → {"data": [ChapterResource], "meta": {...}}
# GET /api/v1/chapters/{id}     → [VerseResource]  (direkt array, wrapper YOK)
# GET /api/v1/juz/{id}          → [VerseResource]  (direkt array, wrapper YOK)
# GET /api/v1/verses/page/{n}   → {"data": [VerseResource], "meta": {...}, "success": bool}
#
# ChapterResource: id, name_turkish, name_arabic, verse_count, revelation_order, first_page
# VerseResource:   id, surah_number, verse_number, text, arabic_text,
#                  juz_number, page_number, surah_name_turkish, surah_name_arabic

@st.cache_data(ttl=86400)
def diy_sureler(api_key: str, base_url: str = DIYANET_URL):
    """GET /api/v1/chapters → {data: [ChapterResource]}"""
    if not api_key:
        return []
    h = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    try:
        r = requests.get(
            f"{base_url}/api/v1/chapters",
            headers=h, params={"language": "tr"}, timeout=10
        )
        if r.ok:
            # Response: {"data": [...], "meta": {...}}
            veri = r.json()
            lst = veri.get("data", []) if isinstance(veri, dict) else veri
            return lst if isinstance(lst, list) else []
    except Exception:
        pass
    return []

@st.cache_data(ttl=86400)
def diy_sure_getir(chapter_id: int, api_key: str, base_url: str = DIYANET_URL):
    """GET /api/v1/chapters/{chapter_id} → [VerseResource] (direkt array)"""
    if not api_key:
        return None
    h = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    try:
        r = requests.get(
            f"{base_url}/api/v1/chapters/{chapter_id}",
            headers=h,
            params={"language_id": 1, "arabic_text_group_id": 1},
            timeout=15
        )
        if r.ok:
            veri = r.json()
            # Direkt array döner, wrapper yok
            if isinstance(veri, list):
                return veri
            # Yine de dict gelirse data'ya bak
            if isinstance(veri, dict):
                return veri.get("data", [])
    except Exception:
        pass
    return None

@st.cache_data(ttl=86400)
def diy_cuz_getir(juz_id: int, api_key: str, base_url: str = DIYANET_URL):
    """GET /api/v1/juz/{juz_id} → [VerseResource] (direkt array)"""
    if not api_key:
        return None
    h = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    try:
        r = requests.get(
            f"{base_url}/api/v1/juz/{juz_id}",
            headers=h, params={"language_id": 1}, timeout=15
        )
        if r.ok:
            veri = r.json()
            # Direkt array döner
            if isinstance(veri, list):
                return veri
            if isinstance(veri, dict):
                return veri.get("data", [])
    except Exception:
        pass
    return None

@st.cache_data(ttl=86400)
def diy_sayfa_getir(sayfa: int, api_key: str, base_url: str = DIYANET_URL):
    """GET /api/v1/verses/page/{page_number} → {data: [VerseResource], meta, success}"""
    if not api_key:
        return None
    h = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    try:
        r = requests.get(
            f"{base_url}/api/v1/verses/page/{sayfa}",
            headers=h,
            params={"language_id": 1, "arabic_text_group_id": 1},
            timeout=12
        )
        if r.ok:
            veri = r.json()
            # Response: {"data": [...], "meta": {...}, "success": true}
            if isinstance(veri, dict):
                return veri.get("data", [])
            if isinstance(veri, list):
                return veri
    except Exception:
        pass
    return None

def everyayah_url(sure_no: int, ayet_no: int, kari_klasor: str) -> str:
    return f"{EVERYAYAH}/{kari_klasor}/{sure_no:03d}{ayet_no:03d}.mp3"

@st.cache_data(ttl=3600)
def ters_geocode(lat: float, lng: float):
    try:
        r = requests.get(
            f"{NOMINATIM}/reverse",
            params={"lat": lat, "lon": lng, "format": "json", "accept-language": "tr"},
            headers={"User-Agent": "IslamilZaman/2.0 (open-source)"},
            timeout=8,
        )
        return r.json() if r.ok else None
    except:
        return None
@st.cache_data(ttl=86400)
def kible_acisi_hesapla(lat: float, lng: float) -> float:
    """Kabe koordinatlarına göre kıble açısını hesapla (derece, kuzeyden saat yönünde)"""
    import math
    kabe_lat = math.radians(21.4225)
    kabe_lng = math.radians(39.8262)
    lat_r    = math.radians(lat)
    dlng     = kabe_lng - math.radians(lng)
    x = math.sin(dlng) * math.cos(kabe_lat)
    y = math.cos(lat_r) * math.sin(kabe_lat) - math.sin(lat_r) * math.cos(kabe_lat) * math.cos(dlng)
    aci = math.degrees(math.atan2(x, y))
    return (aci + 360) % 360



def groq_api_key_al() -> str:
    """API anahtarını sırayla: secrets → session_state → boş döndür"""
    # st.secrets.get() bazen çalışmıyor — bracket erişimi daha güvenilir
    try:
        if "GROQ_API_KEY" in st.secrets:
            key = st.secrets["GROQ_API_KEY"]
            if key and str(key).strip():
                return str(key).strip()
    except Exception:
        pass
    return str(st.session_state.get("groq_api_key_input", "")).strip()

def groq_sor(mesajlar: list, sistem: str = None) -> str:
    api_key = groq_api_key_al()
    if not api_key:
        return "🔑 Groq API anahtarı girilmedi. Sol panelin altından anahtarınızı ekleyin."
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        msgs = []
        if sistem:
            msgs.append({"role": "system", "content": sistem})
        msgs.extend(mesajlar)
        yanit = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=msgs,
            max_tokens=1200,
            temperature=0.65,
        )
        return yanit.choices[0].message.content
    except Exception as e:
        hata = str(e)
        if "api_key" in hata.lower() or "authentication" in hata.lower() or "invalid" in hata.lower():
            return "🔑 Groq API anahtarı geçersiz. Sol panelden doğru anahtarı girin."
        return f"⚠️ Yapay zeka hatası: {hata}"

def groq_cevir(metin: str) -> str:
    return groq_sor(
        [{"role": "user", "content": f"Sadece Türkçeye çevir, başka hiçbir şey yazma: {metin}"}],
        sistem="Sen bir çevirmensin. Sadece çeviriyi ver, hiçbir açıklama ekleme.",
    )

# ─────────────────────────────────────────────────────────────
# VAKİT VERİSİ NORMALIZASYON
# İmsakiyem → standart dict: {imsak, gunes, ogle, ikindi, aksam, yatsi, tarih, hicri, gun_adi}
# Emushaf   → aynı standart dict
# ─────────────────────────────────────────────────────────────
def im_vakit_normalize(v: dict) -> dict:
    """İmsakiyem verisini standart formata çevir — birden fazla alan adı formatını destekler"""
    # times alt nesnesi varsa kullan, yoksa direkt v'den al
    times = v.get("times") or v.get("prayerTimes") or v.get("prayer_times") or v

    def _saat(alan_adlari):
        for ad in alan_adlari:
            val = times.get(ad)
            if val and val != "00:00":
                return val
            # Büyük harf versiyonu
            val = v.get(ad)
            if val and val != "00:00":
                return val
        return "—"

    tarih_iso = (
        v.get("date") or v.get("Date") or
        v.get("gregorian_date") or v.get("gregorianDate") or ""
    )
    hicri = v.get("hijri_date") or v.get("hijriDate") or v.get("hijri") or {}

    try:
        # Eğer "2026-02-25T00:00:00.000Z" gibi uzun ISO geliyorsa T'den öncesini al (Y-m-d)
        safe_iso = tarih_iso.split("T")[0] if "T" in tarih_iso else tarih_iso
        dt = datetime.strptime(safe_iso, "%Y-%m-%d")
        tarih_kisa = dt.strftime("%d.%m.%Y")
        gun_adi = GUN_ADLARI.get(dt.strftime("%A"), dt.strftime("%A"))
    except Exception:
        tarih_kisa = tarih_iso
        gun_adi = ""

    if isinstance(hicri, dict):
        hicri_str = (
            hicri.get("full_date") or hicri.get("fullDate") or
            f"{hicri.get('day','?')} {hicri.get('month_name') or hicri.get('monthName','?')} {hicri.get('year','?')}"
        )
    elif isinstance(hicri, str) and hicri:
        # ISO string gibi "2026-02-25T00:00:00.000Z" gelirse temizle
        hicri_str = hicri.split("T")[0] if "T" in hicri else hicri
    else:
        hicri_str = ""

    # ISO tarih formatı, sadece sayı/tire, veya çok kısa ise temizle
    if hicri_str and (
        "T" in hicri_str or
        "Z" in hicri_str or
        (len(hicri_str) <= 10 and hicri_str.count("-") >= 2)
    ):
        hicri_str = ""

    return {
        "imsak":      _saat(["imsak", "Imsak", "fajr", "Fajr"]),
        "gunes":      _saat(["gunes", "Gunes", "sunrise", "Sunrise", "shuruk"]),
        "ogle":       _saat(["ogle", "Ogle", "dhuhr", "Dhuhr", "zuhr"]),
        "ikindi":     _saat(["ikindi", "Ikindi", "asr", "Asr"]),
        "aksam":      _saat(["aksam", "Aksam", "maghrib", "Maghrib"]),
        "yatsi":      _saat(["yatsi", "Yatsi", "isha", "Isha"]),
        "tarih_kisa": tarih_kisa,
        "tarih_iso":  tarih_iso,
        "hicri_str":  hicri_str,
        "gun_adi":    gun_adi,
        "kiblesaati":  v.get("qibla_time") or v.get("qiblaTime") or "—",
        "gunesdogus":  _saat(["sunrise", "gunes", "Gunes"]),
        "gunesbatis":  _saat(["sunset", "aksam", "Aksam"]),
        "gmt":         "+3",
    }

def em_vakit_normalize(v: dict) -> dict:
    """Emushaf verisini standart formata çevir"""
    tarih_kisa = v.get("MiladiTarihKisa", "").strip()
    try:
        dt = datetime.strptime(tarih_kisa, "%d.%m.%Y")
        tarih_iso = dt.strftime("%Y-%m-%d")
        gun_adi   = GUN_ADLARI.get(dt.strftime("%A"), dt.strftime("%A"))
    except:
        tarih_iso = ""
        gun_adi   = ""

    return {
        "imsak":      v.get("Imsak",      "—"),
        "gunes":      v.get("Gunes",      "—"),
        "ogle":       v.get("Ogle",       "—"),
        "ikindi":     v.get("Ikindi",     "—"),
        "aksam":      v.get("Aksam",      "—"),
        "yatsi":      v.get("Yatsi",      "—"),
        "tarih_kisa": tarih_kisa,
        "tarih_iso":  tarih_iso,
        "hicri_str":  v.get("HicriTarihUzun", ""),
        "gun_adi":    gun_adi,
        "kiblesaati": v.get("KibleSaati",  "—"),
        "gunesdogus": v.get("GunesDogus",  "—"),
        "gunesbatis": v.get("GunesBatis",  "—"),
        "gmt":        str(v.get("GreenwichOrtalamaZamani", "+3")),
    }

# ─────────────────────────────────────────────────────────────
# SONRAKI NAMAZ & AKTİF VAKİT
# ─────────────────────────────────────────────────────────────
VAKIT_SIRA = ["imsak", "gunes", "ogle", "ikindi", "aksam", "yatsi"]

def aktif_vakit_bul(vakit: dict):
    now = datetime.now(TR_TZ)
    bugun = now.date()
    aktif = None
    for key in VAKIT_SIRA:
        dt = zaman_parse(vakit[key], bugun)
        if dt and dt <= now:
            aktif = key
    return aktif

def sonraki_namaz_bul(vakit: dict, yarin_vakit: dict = None):
    now = datetime.now(TR_TZ)
    bugun = now.date()
    for key in VAKIT_SIRA:
        dt = zaman_parse(vakit[key], bugun)
        if dt and dt > now:
            return VAKIT_ADLARI[key], VAKIT_IKONLARI[key], dt, vakit[key]
    # Gece sonrası → yarının imsakı
    if yarin_vakit:
        yarin = bugun + timedelta(days=1)
        dt = zaman_parse(yarin_vakit["imsak"], yarin)
        if dt:
            return "İmsak (Yarın)", "🌙", dt, yarin_vakit["imsak"]
    return "İmsak", "🌙", None, "—"

# ─────────────────────────────────────────────────────────────
# OTOMATİK KONUM EŞLEŞTİRME
# İmsakiyem'in search endpointi sayesinde çok daha doğru
# ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def konum_eslestir_imsakiyem(lat: float, lng: float):
    """
    1) Nominatim'den şehir/ilçe adını al
    2) İmsakiyem search/districts endpoint'i ile eşleştir
    3) Bulamazsa states içinde ara, sonra countries
    """
    geo = ters_geocode(lat, lng)
    if not geo:
        return None, None

    adres = geo.get("address", {})
    # Sırayla dene: ilçe → şehir → il
    sorgu_adaylari = list(filter(None, [
        adres.get("suburb"),
        adres.get("district"),
        adres.get("county"),
        adres.get("city"),
        adres.get("town"),
        adres.get("province"),
        adres.get("state"),
    ]))

    for sorgu in sorgu_adaylari[:4]:
        sonuclar = im_ara("districts", sorgu)
        if sonuclar:
            ilce = sonuclar[0]
            ilce_adi  = ilce.get("name", "")
            sehir_adi = ilce.get("state_id", {}).get("name", "") if isinstance(ilce.get("state_id"), dict) else ""
            konum_goster = f"📍 {sehir_adi} / {ilce_adi}" if sehir_adi else f"📍 {ilce_adi}"
            return ilce.get("_id"), konum_goster

    # İmsakiyem eşleşmezse Nominatim adresini dön
    sehir = adres.get("city") or adres.get("town") or adres.get("province") or ""
    return None, f"📍 {sehir}"

@st.cache_data(ttl=3600)
def konum_eslestir_emushaf(lat: float, lng: float):
    """Emushaf için fallback konum eşleştirme"""
    geo = ters_geocode(lat, lng)
    if not geo:
        return None, None, None

    adres = geo.get("address", {})
    sehir_hammadde = (adres.get("city") or adres.get("town") or adres.get("province") or "").upper()
    ilce_hammadde  = (adres.get("suburb") or adres.get("district") or sehir_hammadde).upper()
    is_turkey = any(x in adres.get("country", "").upper() for x in ["TURKEY", "TÜRKIYE", "TURKIYE"])

    ulkeler = em_ulkeler()
    if not ulkeler:
        return None, None, None

    eslesme_ulke = None
    if is_turkey:
        eslesme_ulke = next(
            (u for u in ulkeler if "TURKIYE" in normalize_eslesme(u["UlkeAdi"])), None
        )
    else:
        n_ulke = normalize_eslesme(adres.get("country", ""))
        for u in ulkeler:
            n_a = normalize_eslesme(u["UlkeAdi"])
            if n_ulke and (n_ulke in n_a or n_a in n_ulke):
                eslesme_ulke = u
                break

    if not eslesme_ulke:
        return None, None, None

    sehirler = em_sehirler(eslesme_ulke["UlkeID"])
    eslesme_sehir = None
    n_sehir = normalize_eslesme(sehir_hammadde)
    for s in sehirler:
        if n_sehir and n_sehir in normalize_eslesme(s["SehirAdi"]):
            eslesme_sehir = s
            break
    if not eslesme_sehir and sehirler:
        eslesme_sehir = sehirler[0]

    if not eslesme_sehir:
        return None, None, None

    ilceler = em_ilceler(eslesme_sehir["SehirID"])
    eslesme_ilce = None
    n_ilce = normalize_eslesme(ilce_hammadde)
    for i in ilceler:
        if n_ilce and n_ilce in normalize_eslesme(i["IlceAdi"]):
            eslesme_ilce = i
            break
    if not eslesme_ilce and ilceler:
        eslesme_ilce = ilceler[0]

    return (
        eslesme_ulke,
        eslesme_sehir,
        eslesme_ilce,
    )

# ─────────────────────────────────────────────────────────────
# İLK AÇILIŞTA VARSAYILAN KONUM: SAMSUN / ATAKUM
# ─────────────────────────────────────────────────────────────
if not st.session_state.konum_adi and not st.session_state.ilce_id:
    _def_id, _def_adi = varsayilan_konum_yukle()
    if _def_id:
        st.session_state.ilce_id   = _def_id
        st.session_state.konum_adi = _def_adi
        st.session_state.kaynak    = "imsakiyem"

# ─────────────────────────────────────────────────────────────
# GEO KOORDİNATLARINDAN OTOMATİK KONUM BELİRLE
# ─────────────────────────────────────────────────────────────
otomatik_im_ulke = otomatik_im_sehir = otomatik_im_ilce = None
otomatik_em_ulke = otomatik_em_sehir = otomatik_em_ilce = None

if geo_lat and geo_lng:
    try:
        lat_f = float(geo_lat)
        lng_f = float(geo_lng)

        # İmsakiyem ile dene
        im_id, im_konum_adi = konum_eslestir_imsakiyem(lat_f, lng_f)
        if im_id:
            st.session_state.ilce_id  = im_id
            st.session_state.kaynak   = "imsakiyem"
            st.session_state.konum_adi = im_konum_adi
        else:
            # Emushaf fallback
            em_res = konum_eslestir_emushaf(lat_f, lng_f)
            if em_res and em_res[2]:
                otomatik_em_ulke, otomatik_em_sehir, otomatik_em_ilce = em_res
                st.session_state.ilce_id_emushaf = otomatik_em_ilce["IlceID"]
                st.session_state.kaynak = "emushaf"
                em_sehir_g = adi_duzenle(otomatik_em_sehir["SehirAdi"]) if otomatik_em_sehir else ""
                em_ilce_g  = adi_duzenle(otomatik_em_ilce["IlceAdi"])
                st.session_state.konum_adi = f"📍 {em_sehir_g} / {em_ilce_g}"
    except:
        pass

# ─────────────────────────────────────────────────────────────
# ════════════════════  SIDEBAR  ════════════════════
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='text-align:center;padding:16px 0 8px;font-family:Amiri,serif;
                font-size:1.4em;color:#c8a84b;letter-spacing:2px;'>☪️ İslami Zaman</div>
    <div style='text-align:center;font-size:0.72em;color:#3a6080;
                padding-bottom:12px;letter-spacing:1px;'>Namaz Vakitleri & Kuran</div>
    """, unsafe_allow_html=True)
    st.divider()

    # Konum durum kutusu
    if st.session_state.konum_adi:
        kaynak_badge = (
            '<span class="kaynak-badge kaynak-imsakiyem">imsakiyem.com ✓</span>'
            if st.session_state.kaynak == "imsakiyem"
            else '<span class="kaynak-badge kaynak-emushaf">emushaf.net ↩</span>'
        )
        durum_renk = "#0c1e10" if st.session_state.kaynak == "imsakiyem" else "#1a1205"
        durum_border = "#1e4a28" if st.session_state.kaynak == "imsakiyem" else "#4a3010"
        st.markdown(f"""
        <div style='background:{durum_renk};border:1px solid {durum_border};border-radius:12px;
                    padding:12px 16px;margin-bottom:12px;text-align:center;'>
            <div style='font-size:0.68em;color:#3a6a40;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;'>
                ✅ Konum Tespit Edildi
            </div>
            <div style='color:#a8d8b8;font-size:0.88em;margin-bottom:6px;'>{st.session_state.konum_adi}</div>
            {kaynak_badge}
        </div>
        """, unsafe_allow_html=True)
        konumu_degistir = st.checkbox("🔄 Konumu Değiştir", key="konum_degistir_cb")
    elif geo_red:
        st.markdown("""
        <div style='background:#1a1005;border:1px solid #4a3010;border-radius:12px;
                    padding:12px 16px;margin-bottom:12px;text-align:center;'>
            <div style='font-size:0.68em;color:#6a4020;text-transform:uppercase;letter-spacing:1px;'>
                ⚠️ Konum İzni Reddedildi
            </div>
            <div style='color:#8a6040;font-size:0.82em;margin-top:4px;'>Aşağıdan manuel seçin</div>
        </div>
        """, unsafe_allow_html=True)
        konumu_degistir = True
    else:
        konumu_degistir = True

    # ── KAYNAK SEÇİMİ ──
    st.markdown('<p style="font-size:0.78em;color:#4a6a8a;margin-bottom:4px;">⚡ Veri Kaynağı</p>', unsafe_allow_html=True)
    kaynak_secim = st.radio(
        "Kaynak",
        ["🟢 imsakiyem.com (Önerilen)", "🟡 emushaf.net (Yedek)"],
        index=0 if st.session_state.kaynak == "imsakiyem" else 1,
        label_visibility="collapsed",
        horizontal=True,
    )
    st.session_state.kaynak = "imsakiyem" if "imsakiyem" in kaynak_secim else "emushaf"

    st.markdown("---")

    # ── MANUEL KONUM SEÇİMİ ──
    if konumu_degistir or not st.session_state.konum_adi:

        if st.session_state.kaynak == "imsakiyem":
            # İmsakiyem: ülke → eyalet → ilçe
            ulkeler_im = im_ulkeler()
            if ulkeler_im:
                ulke_display = [u.get("name", "") for u in ulkeler_im]
                try:
                    varsayilan_ulke = next(i for i, u in enumerate(ulkeler_im)
                                           if "Türkiye" in u.get("name", "") or "Turkey" in u.get("name_en", ""))
                except Exception:
                    varsayilan_ulke = 0

                st.markdown('<p style="font-size:0.8em;color:#5a8aaa;margin-bottom:2px;">🌍 Ülke</p>', unsafe_allow_html=True)
                s_ulke = st.selectbox("Ülke", ulke_display, index=varsayilan_ulke, label_visibility="collapsed", key="im_ulke_sb")
                secili_ulke_im = next((u for u in ulkeler_im if u.get("name") == s_ulke), None)

                if secili_ulke_im:
                    eyaletler = im_eyaletler(secili_ulke_im["_id"])
                    if eyaletler:
                        eyalet_display = [e.get("name", "") for e in eyaletler]
                        try:
                            v_eyalet = next(i for i, e in enumerate(eyaletler)
                                            if "Ankara" in e.get("name", ""))
                        except Exception:
                            v_eyalet = 0

                        st.markdown('<p style="font-size:0.8em;color:#5a8aaa;margin:8px 0 2px;">🏙️ Şehir / Eyalet</p>', unsafe_allow_html=True)
                        s_eyalet = st.selectbox("Eyalet", eyalet_display, index=v_eyalet, label_visibility="collapsed", key="im_eyalet_sb")
                        secili_eyalet_im = next((e for e in eyaletler if e.get("name") == s_eyalet), None)

                        if secili_eyalet_im:
                            ilceler_im = im_ilceler(secili_eyalet_im["_id"])
                            if ilceler_im:
                                ilce_display = [i.get("name", "") for i in ilceler_im]
                                st.markdown('<p style="font-size:0.8em;color:#5a8aaa;margin:8px 0 2px;">📍 İlçe</p>', unsafe_allow_html=True)
                                s_ilce = st.selectbox("İlçe", ilce_display, index=0, label_visibility="collapsed", key="im_ilce_sb")
                                secili_ilce_im = next((i for i in ilceler_im if i.get("name") == s_ilce), None)

                                if st.button("✅ Konumu Uygula", use_container_width=True, key="im_uygula"):
                                    if secili_ilce_im:
                                        st.session_state.ilce_id   = secili_ilce_im["_id"]
                                        st.session_state.konum_adi = f"📍 {s_eyalet} / {s_ilce}"
                                        st.session_state.kaynak    = "imsakiyem"
                                        im_vakitler.clear()
                                        st.rerun()
                            else:
                                st.warning("Bu eyalet için ilçe bulunamadı.")
                    else:
                        st.warning("Ülke için şehir bulunamadı.")
            else:
                st.error("⚠️ İmsakiyem ülke listesi yüklenemedi.")

        else:
            # Emushaf: ülke → şehir → ilçe
            ulkeler_em = em_ulkeler()
            if ulkeler_em:
                ulke_display = [adi_duzenle(u["UlkeAdi"]) for u in ulkeler_em]
                try:
                    v_ulke = next(i for i, u in enumerate(ulkeler_em)
                                  if "TURKIYE" in normalize_eslesme(u["UlkeAdi"]))
                except Exception:
                    v_ulke = 0

                st.markdown('<p style="font-size:0.8em;color:#5a8aaa;margin-bottom:2px;">🌍 Ülke</p>', unsafe_allow_html=True)
                s_ulke = st.selectbox("Ülke", ulke_display, index=v_ulke, label_visibility="collapsed", key="em_ulke_sb")
                secili_ulke_em = ulkeler_em[ulke_display.index(s_ulke)]

                sehirler_em = em_sehirler(secili_ulke_em["UlkeID"])
                if sehirler_em:
                    sehir_display = [adi_duzenle(s["SehirAdi"]) for s in sehirler_em]
                    try:
                        v_sehir = next(i for i, s in enumerate(sehirler_em)
                                       if "ANKARA" in s["SehirAdi"].upper())
                    except Exception:
                        v_sehir = 0

                    st.markdown('<p style="font-size:0.8em;color:#5a8aaa;margin:8px 0 2px;">🏙️ Şehir</p>', unsafe_allow_html=True)
                    s_sehir = st.selectbox("Şehir", sehir_display, index=v_sehir, label_visibility="collapsed", key="em_sehir_sb")
                    secili_sehir_em = sehirler_em[sehir_display.index(s_sehir)]

                    ilceler_em = em_ilceler(secili_sehir_em["SehirID"])
                    if ilceler_em:
                        ilce_display = [adi_duzenle(i["IlceAdi"]) for i in ilceler_em]
                        st.markdown('<p style="font-size:0.8em;color:#5a8aaa;margin:8px 0 2px;">📍 İlçe</p>', unsafe_allow_html=True)
                        s_ilce = st.selectbox("İlçe", ilce_display, index=0, label_visibility="collapsed", key="em_ilce_sb")
                        secili_ilce_em = ilceler_em[ilce_display.index(s_ilce)]

                        if st.button("✅ Konumu Uygula", use_container_width=True, key="em_uygula"):
                            st.session_state.ilce_id_emushaf = secili_ilce_em["IlceID"]
                            st.session_state.konum_adi = f"📍 {s_sehir} / {s_ilce}"
                            st.session_state.kaynak = "emushaf"
                            em_vakitler.clear()
                            st.rerun()
                    else:
                        st.warning("Bu şehir için ilçe bulunamadı.")
                else:
                    st.error("⚠️ Emushaf şehir listesi yüklenemedi.")

    st.divider()

    # Arama butonu (imsakiyem search)
    if st.session_state.kaynak == "imsakiyem":
        ara_sorgu = st.text_input("🔍 İlçe Ara", placeholder="Örn: Beşiktaş, Berlin…", key="ara_input")
        if ara_sorgu.strip():
            sonuclar = im_ara("districts", ara_sorgu.strip())
            if sonuclar:
                s_display = [
                    f"{r.get('name','')} — "
                    f"{r.get('state_id',{}).get('name','') if isinstance(r.get('state_id'),dict) else ''}"
                    for r in sonuclar[:10]
                ]
                secim = st.selectbox("Sonuçlar", s_display, key="ara_secim")
                if st.button("✅ Seç", use_container_width=True):
                    idx = s_display.index(secim)
                    secili = sonuclar[idx]
                    st.session_state.ilce_id = secili["_id"]
                    st.session_state.konum_adi = f"📍 {secim}"
                    st.rerun()
            else:
                st.caption("Sonuç bulunamadı")
        st.markdown("---")

    col_b1, col_b2 = st.columns(2)
    with col_b1:
        if st.button("🔄 Yenile", use_container_width=True):
            im_vakitler.clear()
            em_vakitler.clear()
            st.rerun()
    with col_b2:
        if st.button("🎲 Ayet", use_container_width=True):
            st.session_state.ayet_tohumu = random.randint(1, 9999)
            for k in list(st.session_state.keys()):
                if k.startswith("tefsir_") or k.startswith("sure_anlam_"):
                    del st.session_state[k]
            st.rerun()

    if geo_red:
        if st.button("📍 Konumu Tekrar Dene", use_container_width=True):
            st.query_params.clear()
            st.session_state.geo_denendi = False
            st.rerun()

    st.divider()
    st.markdown("""
    <div style='font-size:0.68em;color:#2a4a6a;line-height:1.8;'>
    <strong style="color:#3a5a7a">⚠️ Sorumluluk Reddi:</strong><br>
    Vakitler Diyanet İşleri Başkanlığı verilerine dayanır.
    Türkiye dışında zaman dilimi sapmaları oluşabilir.
    Ramazan bilgisi tahminidir.
    Kesin bilgi için din görevlisine başvurun.
    </div>
    """, unsafe_allow_html=True)

    # ── DİYANET API ANAHTARI ──
    st.divider()
    with st.expander("📖 DIB_KURAN_API_TOKEN", expanded=not bool(diyanet_aktif())):
        st.markdown('<p style="font-size:0.78em;color:#4a6a8a;">Resmi Diyanet Kuran API icin JWT token. <a href="https://t061.diyanet.gov.tr" target="_blank" style="color:#c8a84b;">Portal -></a></p>', unsafe_allow_html=True)
        _dkey = st.text_input(
            "Diyanet API Key",
            type="password",
            value=st.session_state.get("diyanet_api_key_input", ""),
            key="diyanet_api_key_widget",
            placeholder="eyJ...",
            label_visibility="collapsed",
        )
        if _dkey != st.session_state.get("diyanet_api_key_input", ""):
            st.session_state.diyanet_api_key_input = _dkey
            # Diyanet cache'i temizle
            diy_sureler.clear()
            st.rerun()
        if diyanet_aktif():
            st.success("✅ Diyanet API aktif")
        else:
            st.caption("⚠️ Girilmezse alquran.cloud fallback kullanılır.")

    # ── GROQ API ANAHTARI ──
    with st.expander("🤖 Groq AI Anahtarı", expanded=not bool(groq_api_key_al())):
        st.markdown('<p style="font-size:0.78em;color:#4a6a8a;">Yapay zeka asistanı için gerekli. <a href="https://console.groq.com/keys" target="_blank" style="color:#c8a84b;">Buradan alın →</a></p>', unsafe_allow_html=True)
        _key = st.text_input(
            "API Anahtarı",
            type="password",
            value=st.session_state.groq_api_key_input,
            key="groq_api_key_widget",
            placeholder="gsk_...",
            label_visibility="collapsed",
        )
        if _key != st.session_state.groq_api_key_input:
            st.session_state.groq_api_key_input = _key
            st.rerun()
        if groq_api_key_al():
            st.success("✅ API anahtarı aktif")

# ─────────────────────────────────────────────────────────────
# AKTİF VAKİT VERİSİ ÇEK
# ─────────────────────────────────────────────────────────────
now_tr     = datetime.now(TR_TZ)
bugun_kisa = now_tr.strftime("%d.%m.%Y")
bugun_iso  = now_tr.strftime("%Y-%m-%d")
bugun_api  = now_tr.strftime("%d-%m-%Y")

vakitler_norm = []   # normalize edilmiş standart dict listesi
bugun_vakit   = None
yarin_vakit   = None
kaynak_aktif  = st.session_state.kaynak

if kaynak_aktif == "imsakiyem" and st.session_state.ilce_id:
    ham_liste = im_vakitler(st.session_state.ilce_id, "weekly")
    if ham_liste:
        vakitler_norm = [im_vakit_normalize(v) for v in ham_liste]
    else:
        # İmsakiyem boş → emushaf fallback
        kaynak_aktif = "emushaf_fallback"

if kaynak_aktif == "emushaf" and st.session_state.ilce_id_emushaf:
    ham_liste = em_vakitler(st.session_state.ilce_id_emushaf)
    if ham_liste:
        vakitler_norm = [em_vakit_normalize(v) for v in ham_liste]

if kaynak_aktif == "emushaf_fallback" and st.session_state.ilce_id_emushaf:
    ham_liste = em_vakitler(st.session_state.ilce_id_emushaf)
    if ham_liste:
        vakitler_norm = [em_vakit_normalize(v) for v in ham_liste]
        kaynak_aktif  = "emushaf_fallback"

if vakitler_norm:
    bugun_vakit = next(
        (v for v in vakitler_norm if v["tarih_kisa"] == bugun_kisa),
        vakitler_norm[0]
    )
    # Yarının verisi
    bugun_idx = vakitler_norm.index(bugun_vakit)
    if bugun_idx + 1 < len(vakitler_norm):
        yarin_vakit = vakitler_norm[bugun_idx + 1]

ramazan_veri = ramazan_kontrol(bugun_api)
ramazan_mi   = (
    ramazan_veri is not None
    and ramazan_veri.get("status") == "success"
    and ramazan_veri["data"].get("isRamadan", False)
)

# ─────────────────────────────────────────────────────────────
# HERO
# ─────────────────────────────────────────────────────────────
hicri_str = ""
if bugun_vakit:
    _raw_hicri = bugun_vakit.get("hicri_str", "")
    # ISO string, salt tarih ya da boşsa temizle
    _bozuk = (
        not _raw_hicri or
        "T" in _raw_hicri or
        "Z" in _raw_hicri or
        (len(_raw_hicri) <= 10 and _raw_hicri.count("-") >= 2)
    )
    if not _bozuk:
        hicri_str = _raw_hicri
    else:
        # Aladhan API'den çek
        _h_iso = bugun_vakit.get("tarih_iso") or bugun_iso
        hicri_str = hicri_tarih_getir(_h_iso)

# Hâlâ boşsa Miladi tarihi Türkçe göster
if not hicri_str or hicri_str == "—":
    hicri_str = tr_tarih_format(now_tr)
miladi_str = tr_tarih_format(now_tr)
saat_str   = now_tr.strftime("%H:%M:%S")

kaynak_badge_html = ""
if vakitler_norm:
    if "fallback" in kaynak_aktif:
        kaynak_badge_html = '<span class="kaynak-badge kaynak-emushaf">⚡ emushaf.net (yedek)</span>'
    elif kaynak_aktif == "emushaf":
        kaynak_badge_html = '<span class="kaynak-badge kaynak-emushaf">emushaf.net</span>'
    else:
        kaynak_badge_html = '<span class="kaynak-badge kaynak-imsakiyem">imsakiyem.com ✓</span>'

st.markdown(f"""
<div class="hero">
    <div class="hero-arabic">
        {"رَمَضَانُ الْمُبَارَك" if ramazan_mi else "بِسْمِ اللهِ الرَّحْمَنِ الرَّحِيم"}
    </div>
    <div class="hero-clock" id="tr-saat">{saat_str}</div>
    <div class="hero-miladi">{miladi_str}</div>
    <div class="hero-hijri">{hicri_str}</div>
    <div class="hero-location">{st.session_state.konum_adi or "📍 Konum seçilmedi"}</div>
    <div class="hero-kaynak">Veri Kaynağı: {kaynak_badge_html}</div>
</div>
""", unsafe_allow_html=True)

# Canlı saat
st.components.v1.html("""
<script>
(function tick() {
    var el = window.parent.document.getElementById('tr-saat');
    if (el) {
        el.textContent = new Date().toLocaleTimeString('tr-TR', {
            timeZone: 'Europe/Istanbul', hour12: false,
            hour: '2-digit', minute: '2-digit', second: '2-digit'
        });
    }
    setTimeout(tick, 1000);
})();
</script>
""", height=0)

# ─────────────────────────────────────────────────────────────
# TABLAR
# ─────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "🕌 Namaz Vakitleri", "🌙 Ramazan", "📖 Kuran-ı Kerim", "🤖 Dini Asistan"
])

# ══════════════════════════════════════════════════════════════
# TAB 1 — NAMAZ VAKİTLERİ
# ══════════════════════════════════════════════════════════════
with tab1:

    # ── ANA PANEL KONUm DEĞİŞTİRME ──
    with st.expander("📍 Konum Seç / Değiştir", expanded=not bool(st.session_state.konum_adi)):
        st.markdown('<p style="font-size:0.82em;color:#5a8aaa;margin-bottom:6px;">Şehir veya ilçe adını yazarak arayın:</p>', unsafe_allow_html=True)
        ara_col, btn_col = st.columns([3, 1])
        with ara_col:
            konum_ara = st.text_input("İlçe Ara", placeholder="Örn: Atakum, Kadıköy, Konya…",
                                       key="tab1_ara", label_visibility="collapsed")
        with btn_col:
            ara_btn = st.button("🔍 Ara", key="tab1_ara_btn", use_container_width=True)

        # Arama: sadece buton basıldığında çalış, sonucu session'a kaydet
        if ara_btn and konum_ara.strip():
            with st.spinner("Aranıyor…"):
                _res = im_ara("districts", konum_ara.strip())
            st.session_state["ara_sonuclari"] = _res
            st.session_state["ara_sorgu_son"] = konum_ara.strip()

        sonuclar_ara = st.session_state.get("ara_sonuclari", [])
        ara_sorgu_son = st.session_state.get("ara_sorgu_son", "")

        if ara_sorgu_son:
            if sonuclar_ara:
                s_display_ara = [
                    f"{r.get('name','')}  —  {r.get('state_id',{}).get('name','') if isinstance(r.get('state_id'),dict) else ''}"
                    for r in sonuclar_ara[:12]
                ]
                secim_ara = st.selectbox("Sonuç Seç", s_display_ara, key="tab1_secim", label_visibility="collapsed")
                if st.button("✅ Bu Konumu Kullan", key="tab1_uygula", use_container_width=True):
                    idx_ara = s_display_ara.index(secim_ara)
                    sec = sonuclar_ara[idx_ara]
                    st.session_state.ilce_id   = sec["_id"]
                    st.session_state.konum_adi = f"📍 {secim_ara.replace('  —  ', ' / ')}"
                    st.session_state.kaynak    = "imsakiyem"
                    st.session_state["ara_sonuclari"] = []
                    st.session_state["ara_sorgu_son"] = ""
                    im_vakitler.clear()
                    st.rerun()
            else:
                st.caption(f"⚠️ '{ara_sorgu_son}' için sonuç bulunamadı. İngilizce veya farklı yazımı deneyin (örn: Atakum, Besiktas).")

        st.markdown('<hr style="border-color:#1a3050;margin:10px 0">', unsafe_allow_html=True)
        st.markdown('<p style="font-size:0.78em;color:#3a5a70;">Ya da listeden seçin:</p>', unsafe_allow_html=True)
        ulkeler_exp = im_ulkeler()
        if ulkeler_exp:
            ulke_disp_exp = [u.get("name","") for u in ulkeler_exp]
            try:
                v_ulke_exp = next(i for i, u in enumerate(ulkeler_exp)
                                   if "Türkiye" in u.get("name","") or "Turkey" in u.get("name_en",""))
            except Exception:
                v_ulke_exp = 0
            ec1, ec2, ec3 = st.columns(3)
            with ec1:
                s_ulke_exp = st.selectbox("Ülke", ulke_disp_exp, index=v_ulke_exp,
                                           key="exp_ulke", label_visibility="visible")
                sec_ulke_exp = next((u for u in ulkeler_exp if u.get("name")==s_ulke_exp), None)
            with ec2:
                eyaletler_exp = im_eyaletler(sec_ulke_exp["_id"]) if sec_ulke_exp else []
                eyalet_disp_exp = [e.get("name","") for e in eyaletler_exp]
                try:
                    v_eyalet_exp = next(i for i, e in enumerate(eyaletler_exp)
                                         if "Samsun" in e.get("name",""))
                except Exception:
                    v_eyalet_exp = 0
                s_eyalet_exp = st.selectbox("Şehir", eyalet_disp_exp, index=v_eyalet_exp,
                                             key="exp_eyalet", label_visibility="visible")
                sec_eyalet_exp = next((e for e in eyaletler_exp if e.get("name")==s_eyalet_exp), None)
            with ec3:
                ilceler_exp = im_ilceler(sec_eyalet_exp["_id"]) if sec_eyalet_exp else []
                ilce_disp_exp = [i.get("name","") for i in ilceler_exp]
                try:
                    v_ilce_exp = next(i for i, x in enumerate(ilceler_exp)
                                       if "Atakum" in x.get("name",""))
                except Exception:
                    v_ilce_exp = 0
                s_ilce_exp = st.selectbox("İlçe", ilce_disp_exp, index=v_ilce_exp,
                                           key="exp_ilce", label_visibility="visible")
                sec_ilce_exp = next((i for i in ilceler_exp if i.get("name")==s_ilce_exp), None)

            if st.button("✅ Seçilen Konumu Uygula", key="exp_uygula", use_container_width=True):
                if sec_ilce_exp:
                    st.session_state.ilce_id   = sec_ilce_exp["_id"]
                    st.session_state.konum_adi = f"📍 {s_eyalet_exp} / {s_ilce_exp}"
                    st.session_state.kaynak    = "imsakiyem"
                    im_vakitler.clear()
                    st.rerun()

    if not bugun_vakit:
        st.warning("⏳ Vakitler yükleniyor ya da konum bulunamadı. Lütfen yukarıdan konum seçin.")

    else:
        # Geri sayım
        snr_ad, snr_ikon, snr_dt, snr_saat = sonraki_namaz_bul(bugun_vakit, yarin_vakit)
        gs = geri_sayim_str(snr_dt) if snr_dt else "—"

        c_a, c_b, c_c = st.columns([1, 2, 1])
        with c_b:
            st.markdown(f"""
            <div class="geri-sayim">
                <div class="gs-ust">⏱ Sonraki Namaza Kalan Süre</div>
                <div class="gs-namaz">{snr_ikon} {snr_ad} — {snr_saat}</div>
                <div class="gs-zaman" id="gs-main">{gs}</div>
            </div>
            """, unsafe_allow_html=True)
        if snr_dt:
            st.components.v1.html(canlı_gs_js("gs-main", snr_dt), height=0)

        # Vakit kartları
        st.markdown('<div class="bolum-baslik">📅 Bugünün Namaz Vakitleri</div>', unsafe_allow_html=True)
        aktif_key = aktif_vakit_bul(bugun_vakit)
        cols = st.columns(6)
        for i, key in enumerate(VAKIT_SIRA):
            is_aktif = key == aktif_key
            saat = bugun_vakit[key]
            with cols[i]:
                st.markdown(f"""
                <div class="vakit-card {'aktif' if is_aktif else ''}">
                    <div class="vakit-ikon">{VAKIT_IKONLARI[key]}</div>
                    <div class="vakit-adi">{VAKIT_ADLARI[key]}</div>
                    <div class="vakit-saat">{saat}</div>
                    {'<div class="vakit-etiket">● Şu An</div>' if is_aktif else ''}
                </div>
                """, unsafe_allow_html=True)

        # Ek bilgiler
        st.markdown('<div class="bolum-baslik">ℹ️ Günün Ek Bilgileri</div>', unsafe_allow_html=True)

        # Kıble açısını konum koordinatlarından hesapla
        _kible_aci = None
        _kible_lat = None
        _kible_lng = None
        if geo_lat and geo_lng:
            try:
                _kible_lat, _kible_lng = float(geo_lat), float(geo_lng)
            except Exception:
                pass
        # geo yoksa Samsun/Atakum koordinatları (varsayılan)
        if _kible_lat is None:
            _kible_lat, _kible_lng = 41.3240, 36.2527
        _kible_aci = kible_acisi_hesapla(_kible_lat, _kible_lng)

        gunesdogus = bugun_vakit.get("gunesdogus", "—")
        gunesbatis = bugun_vakit.get("gunesbatis", "—")
        gmt        = bugun_vakit.get("gmt", "+3")

        # Güneş vakitleri emushaf'tan geliyor, imsakiyem için güneş/imsak saatlerini kullan
        if gunesdogus == "—":
            gunesdogus = bugun_vakit.get("gunes", "—")
        if gunesbatis == "—":
            gunesbatis = bugun_vakit.get("aksam", "—")

        c1, c2, c3, c4 = st.columns(4)

        # Kıble pusulası — st.markdown + CSS transform (iframe yok, taşma yok)
        with c1:
            aci_str = f"{_kible_aci:.1f}"
            st.markdown(f"""
            <div class="bilgi-kutu" style="height:110px;padding:10px 6px;">
                <div style="position:relative;width:52px;height:52px;flex-shrink:0;">
                    <div style="position:absolute;inset:0;border-radius:50%;
                                background:#0a1628;border:1.5px solid #1e3d64;"></div>
                    <div style="position:absolute;top:1px;left:50%;transform:translateX(-50%);
                                font-size:8px;color:#4a7a9b;line-height:1;">K</div>
                    <div style="position:absolute;bottom:1px;left:50%;transform:translateX(-50%);
                                font-size:8px;color:#2a4a6a;line-height:1;">G</div>
                    <div style="position:absolute;left:1px;top:50%;transform:translateY(-50%);
                                font-size:8px;color:#2a4a6a;line-height:1;">B</div>
                    <div style="position:absolute;right:1px;top:50%;transform:translateY(-50%);
                                font-size:8px;color:#2a4a6a;line-height:1;">D</div>
                    <div style="position:absolute;inset:0;display:flex;align-items:center;
                                justify-content:center;">
                        <div style="width:4px;height:40px;transform:rotate({aci_str}deg);
                                    transform-origin:center center;display:flex;
                                    flex-direction:column;align-items:center;">
                            <div style="width:0;height:0;
                                        border-left:4px solid transparent;
                                        border-right:4px solid transparent;
                                        border-bottom:20px solid #c8a84b;"></div>
                            <div style="width:0;height:0;
                                        border-left:4px solid transparent;
                                        border-right:4px solid transparent;
                                        border-top:20px solid #2a4060;"></div>
                        </div>
                    </div>
                </div>
                <div style="font-size:0.78em;color:#c8a84b;margin-top:4px;line-height:1;font-weight:700;">{aci_str}°</div>
                <div class="bilgi-etiket">Kıble</div>
            </div>
            """, unsafe_allow_html=True)

        for col, ikon, deger, etiket in [
            (c2, "🌄", gunesdogus, "Güneş Doğumu"),
            (c3, "🌅", gunesbatis, "Güneş Batımı"),
            (c4, "🌐", f"GMT+{gmt}" if not str(gmt).startswith("+") else f"GMT{gmt}", "Zaman Dilimi"),
        ]:
            with col:
                st.markdown(f"""
                <div class="bilgi-kutu">
                    <div style="font-size:1.6em;margin-bottom:6px;">{ikon}</div>
                    <div class="bilgi-deger">{deger}</div>
                    <div class="bilgi-etiket">{etiket}</div>
                </div>
                """, unsafe_allow_html=True)

        # Haftalık tablo
        st.markdown('<div class="bolum-baslik">📆 Haftalık Namaz Vakitleri</div>', unsafe_allow_html=True)
        if vakitler_norm:
            st.markdown("""
            <div class="haftalik-satir baslik">
                <div>Tarih</div>
                <div style="text-align:center">İmsak</div>
                <div style="text-align:center">Güneş</div>
                <div style="text-align:center">Öğle</div>
                <div style="text-align:center">İkindi</div>
                <div style="text-align:center">Akşam</div>
                <div style="text-align:center">Yatsı</div>
            </div>
            """, unsafe_allow_html=True)

            for v in vakitler_norm[:7]:
                tarih = v["tarih_kisa"]
                bugun_mu = tarih == bugun_kisa
                gun_adi_kisa = v["gun_adi"][:3] if v["gun_adi"] else ""
                tarih_goster = f"{gun_adi_kisa} {tarih}"
                saatler_html = "".join([
                    f'<div style="text-align:center;color:{"#c8a84b" if bugun_mu else "#8aadcc"};">{v[k]}</div>'
                    for k in ["imsak", "gunes", "ogle", "ikindi", "aksam", "yatsi"]
                ])
                st.markdown(f"""
                <div class="haftalik-satir {'bugun' if bugun_mu else ''}">
                    <div style="color:{'#c8a84b' if bugun_mu else '#5a8aaa'};
                                font-weight:{'600' if bugun_mu else '400'};">
                        {tarih_goster} {'◀' if bugun_mu else ''}
                    </div>
                    {saatler_html}
                </div>
                """, unsafe_allow_html=True)

        st.markdown("""
        <div class="uyari-not">
        ℹ️ Ana kaynak: <strong>imsakiyem.com</strong> (Diyanet İşleri Başkanlığı verileri, Türkçe düzeltilmiş).
        Türkiye dışında zaman dilimi sapmaları oluşabilir — bu Diyanet API'sinin bilinen bir sınırlamasıdır.
        </div>
        """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# TAB 2 — RAMAZAN
# ══════════════════════════════════════════════════════════════
with tab2:
    if not ramazan_veri or ramazan_veri.get("status") != "success":
        st.error("⚠️ Ramazan bilgisi alınamadı.")
    elif ramazan_mi:
        rv   = ramazan_veri["data"]
        hicri = rv.get("hijriDate", {})
        gun_no = hicri.get("day", {}).get("number", "?")

        st.markdown(f"""
        <div class="ramazan-pankart">
            <div class="ramazan-baslik">🌙 Ramazan Mübârek Olsun 🌙</div>
            <div style="color:#ffd54f;font-size:1.1em;margin-top:12px;">
                Hicri {hicri.get('year','?')} — {gun_no}. Gün
            </div>
            <div style="color:#ffb74d;font-size:0.9em;margin-top:4px;font-family:Amiri,serif;">
                شَهْرُ رَمَضَانَ الَّذِي أُنزِلَ فِيهِ الْقُرْآنُ
            </div>
        </div>
        """, unsafe_allow_html=True)

        if bugun_vakit:
            c1, c2 = st.columns(2)
            bugun = now_tr.date()

            # İFTAR
            with c1:
                iftar_dt = zaman_parse(bugun_vakit["aksam"], bugun)
                if iftar_dt and now_tr < iftar_dt:
                    iftar_gs = geri_sayim_str(iftar_dt)
                    st.markdown(f"""
                    <div class="geri-sayim ramazan">
                        <div class="gs-ust" style="color:#8a6030;">🍽️ İftara Kalan Süre</div>
                        <div class="gs-namaz" style="color:#d8a870;">Akşam Ezanı — {bugun_vakit['aksam']}</div>
                        <div class="gs-zaman" id="iftar-gs" style="color:#ff9800;text-shadow:0 0 20px rgba(255,152,0,0.3);">{iftar_gs}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    st.components.v1.html(canlı_gs_js("iftar-gs", iftar_dt), height=0)
                else:
                    st.markdown("""
                    <div class="geri-sayim ramazan" style="padding:32px;">
                        <div class="gs-ust" style="color:#8a6030;">🍽️ İftar</div>
                        <div style="font-size:2.5em;margin:8px 0;">✅</div>
                        <div style="color:#4caf6a;font-family:Amiri,serif;font-size:1.1em;">Hayırlı İftarlar! 🌙</div>
                    </div>
                    """, unsafe_allow_html=True)

            # İMSAK / SAHUR
            with c2:
                yarin = bugun + timedelta(days=1)
                if yarin_vakit:
                    imsak_dt     = zaman_parse(yarin_vakit["imsak"], yarin)
                    imsak_etiket = f"Yarın İmsak — {yarin_vakit['imsak']}"
                else:
                    imsak_dt     = zaman_parse(bugun_vakit["imsak"], bugun)
                    imsak_etiket = f"Bugün İmsak — {bugun_vakit['imsak']}"

                if imsak_dt:
                    imsak_gs = geri_sayim_str(imsak_dt)
                    st.markdown(f"""
                    <div class="geri-sayim ramazan">
                        <div class="gs-ust" style="color:#8a6030;">🌙 Sahura (İmsak) Kalan Süre</div>
                        <div class="gs-namaz" style="color:#d8a870;">{imsak_etiket}</div>
                        <div class="gs-zaman" id="imsak-gs" style="color:#ff9800;text-shadow:0 0 20px rgba(255,152,0,0.3);">{imsak_gs}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    st.components.v1.html(canlı_gs_js("imsak-gs", imsak_dt), height=0)

        # Günlük dua (Groq)
        st.markdown('<div class="bolum-baslik">🤲 Günlük Ramazan Duası</div>', unsafe_allow_html=True)
        if not st.session_state.ramazan_dua:
            with st.spinner("Dua hazırlanıyor…"):
                st.session_state.ramazan_dua = groq_sor(
                    [{"role": "user", "content": f"Ramazanın {gun_no}. günü için güzel bir iftar duası yaz. Arapça orijinalini, Türkçe okunuşunu ve Türkçe anlamını ver. Kısa ve samimi olsun."}],
                    sistem="Sen İslami bilgiye hakim, Türkçe konuşan saygılı bir din asistanısın.",
                )
        st.markdown(f'<div class="ayet-kutu"><div class="ayet-turkce" style="font-style:normal;">{st.session_state.ramazan_dua}</div></div>', unsafe_allow_html=True)
        if st.button("🔄 Dua Yenile"):
            st.session_state.ramazan_dua = None
            st.rerun()

    else:
        rv = ramazan_veri["data"]
        gelecek     = rv.get("nextRamadan", {})
        tarih_gel   = gelecek.get("date", "?")
        kalan_en    = gelecek.get("timeLeft", "?")

        tl_key = f"tl_{kalan_en}"
        if tl_key not in st.session_state and kalan_en != "?":
            st.session_state[tl_key] = groq_cevir(kalan_en)
        kalan_tr = st.session_state.get(tl_key, kalan_en)

        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#0c1c2e,#0f2340);border:1px solid #1e3d64;
                    border-radius:22px;padding:48px;text-align:center;margin:16px 0;">
            <div style="font-size:3.5em;margin-bottom:16px;">🌙</div>
            <div style="font-family:Amiri,serif;font-size:2em;color:#7a9dbd;">Şu An Ramazan Değil</div>
            <div style="color:#3a6080;margin:10px 0 30px;font-size:0.82em;">
                Bu bilgi tahmine dayalıdır. Kesin bilgi için yetkili dini kaynaklara başvurun.
            </div>
            <div style="background:#0a1420;border:1px solid #1a3050;border-radius:16px;
                        padding:24px;display:inline-block;min-width:320px;">
                <div style="color:#3a6080;font-size:0.75em;text-transform:uppercase;letter-spacing:2px;margin-bottom:8px;">
                    📅 Bir Sonraki Ramazan
                </div>
                <div style="font-family:Amiri,serif;font-size:2em;color:#c8a84b;margin:8px 0;">{tarih_gel}</div>
                <div style="color:#ff9800;font-size:1.1em;">{kalan_tr}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if bugun_vakit:
            st.markdown(f"""
            <div class="bilgi-kutu" style="margin-top:16px;">
                <div style="font-family:Amiri,serif;font-size:1.6em;color:#c8a84b;">{bugun_vakit.get('hicri_str','')}</div>
                <div class="bilgi-etiket">Bugünün Hicri Tarihi</div>
            </div>
            """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# TAB 3 — KURAN-I KERİM  (Ana: Diyanet API → Fallback: alquran.cloud)
# ══════════════════════════════════════════════════════════════
with tab3:

    # Kaynak durumu
    _diy = diyanet_aktif()
    if _diy:
        st.markdown('<div class="uyari-not">🟢 <strong>Diyanet Açık Kaynak Kuran API</strong> aktif — Resmi Türkçe çeviri + Arapça metin kullanılıyor.</div>', unsafe_allow_html=True)
        # Debug: gerçek API key isimlerini göster (sure listesi yüklendikten sonra görünür)
        if "diy_sure_ornek" in st.session_state:
            st.caption(f"📋 Diyanet API sure key'leri: `{st.session_state['diy_sure_ornek']}`")
    else:
        st.markdown('<div class="uyari-not">🟡 Diyanet API anahtarı girilmedi — <strong>alquran.cloud</strong> yedek kaynağı kullanılıyor. Sol panelden Diyanet API anahtarı ekleyebilirsiniz.</div>', unsafe_allow_html=True)

    # Kari seçimi (sesli okuma için)
    kari_adi = st.selectbox("🎧 Kari Seç (Sesli Okuma)", list(KARILER.keys()), key="kari_secim")
    kari_klasor = KARILER[kari_adi]

    st.markdown("---")
    col_sol, col_sag = st.columns([1, 2])

    # ── GÜNÜN AYETİ ──
    with col_sol:
        st.markdown('<div class="bolum-baslik">✨ Günün Ayeti</div>', unsafe_allow_html=True)
        random.seed(st.session_state.ayet_tohumu)

        _arapca = _turkce = _sure_adi_ar = _sure_adi_tr = ""
        _sure_no = _ayet_no = 0

        if _diy:
            # Diyanet: rastgele sayfa → ilk ayet
            _rand_sayfa = random.randint(1, 604)
            _sayfa_ayetler = diy_sayfa_getir(_rand_sayfa, diyanet_key(), diyanet_base_url())
            if _sayfa_ayetler and isinstance(_sayfa_ayetler, list) and len(_sayfa_ayetler) > 0:
                _idx = random.randint(0, min(5, len(_sayfa_ayetler)-1))
                _a = _sayfa_ayetler[_idx]
                _arapca    = _a.get("arabic_text", "")
                _turkce    = _a.get("text", "")
                _sure_adi_tr = _a.get("surah_name_turkish", "")
                _sure_adi_ar = _a.get("surah_name_arabic", "")
                _sure_no   = _a.get("surah_number", 0)
                _ayet_no   = _a.get("verse_number", 0)

        if not _turkce:
            # Fallback: alquran.cloud
            _rand_no = random.randint(1, 6236)
            _av = ayet_getir(_rand_no)
            if _av:
                _arapca  = _av.get("ar", {}).get("text", "")
                _turkce  = _av.get("tr", {}).get("text", "")
                _sinf    = _av.get("tr", {}).get("surah", {})
                _sure_adi_ar = _sinf.get("name", "")
                _sure_no = _sinf.get("number", 0)
                _ayet_no = _av.get("tr", {}).get("numberInSurah", 0)
                _sure_adi_tr = groq_cevir(_sinf.get("englishName", "")) if _sinf.get("englishName") else ""

        if _turkce:
            st.markdown(f"""
            <div class="ayet-kutu">
                <div class="ayet-arapca">{_arapca}</div>
                <div class="ayet-turkce">"{_turkce}"</div>
                <div class="ayet-kaynak">
                    📖 {_sure_adi_ar} — {_sure_adi_tr}<br>
                    {_sure_no}. Sure, {_ayet_no}. Ayet
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Sesli okuma
            if _sure_no and _ayet_no:
                audio_url = everyayah_url(_sure_no, _ayet_no, kari_klasor)
                st.markdown(f'<div style="font-size:0.75em;color:#4a7a9b;margin:6px 0 2px;">🎧 {kari_adi}</div>', unsafe_allow_html=True)
                st.audio(audio_url, format="audio/mp3")

            # Tefsir
            _tefsir_key = f"tefsir_{_sure_no}_{_ayet_no}"
            if _tefsir_key not in st.session_state and groq_api_key_al():
                with st.spinner("Açıklama hazırlanıyor…"):
                    st.session_state[_tefsir_key] = groq_sor(
                        [{"role": "user", "content": f"{_sure_no}. sure ({_sure_adi_ar}), {_ayet_no}. ayet hakkında kısa ve anlaşılır bir açıklama yaz. 3-4 cümle."}],
                        sistem="Sen İslami bilgiye hakim, Türkçe konuşan bir din asistanısın.",
                    )
            if _tefsir_key in st.session_state:
                st.markdown('<div class="bolum-baslik">📝 Açıklama</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="sohbet-kutu">{st.session_state[_tefsir_key]}</div>', unsafe_allow_html=True)
        else:
            st.warning("Ayet yüklenemedi, 'Yeni Ayet' butonuna basın.")

    # ── SAĞ KOLON ──
    with col_sag:

        kuran_sekme = st.tabs(["📚 Sure Okuyucu", "📋 Cüz Okuyucu", "📄 Sayfa Okuyucu"])

        # ── SURE OKUYUCU ──
        with kuran_sekme[0]:
            # Diyanet sure listesi
            _dkey = diyanet_key()
            _diy_base = diyanet_base_url()
            _diy_sureler = diy_sureler(_dkey, _diy_base) if _diy else []
            if _diy_sureler:
                # İlk öğeyi debug için kaydet (gerçek key isimlerini görmek için)
                if _diy_sureler and "diy_sure_ornek" not in st.session_state:
                    st.session_state["diy_sure_ornek"] = list(_diy_sureler[0].keys())

                # Olası key isimleri: id/number/surah_id, name_turkish/name_tr/turkish_name, name_arabic/arabic_name
                def _sure_id(s):
                    return s.get("SureId") or s.get("id") or s.get("number") or s.get("surah_id") or s.get("chapter_id", 0)
                def _sure_tr(s):
                    return s.get("SureNameTurkish") or s.get("name_turkish") or s.get("name_tr") or s.get("turkish_name") or s.get("name", "?")
                def _sure_ar(s):
                    return s.get("SureNameArabic") or s.get("name_arabic") or s.get("arabic_name") or s.get("name_ar") or ""
                def _sure_ayet(s):
                    return s.get("AyetCount") or s.get("verse_count") or s.get("ayah_count") or s.get("verses_count") or "?"

                sure_sec_d = {
                    f"{_sure_id(s):>3}. {_sure_tr(s)}  {_sure_ar(s)}  — {_sure_ayet(s)} ayet": _sure_id(s)
                    for s in _diy_sureler if _sure_id(s)
                }
                _secili_sure_str = st.selectbox("Sure Seç", list(sure_sec_d.keys()), index=0, key="diy_sure_sb")
                _secili_sure_no = sure_sec_d.get(_secili_sure_str)
                if _secili_sure_no is None:
                    _secili_sure_no = list(sure_sec_d.values())[0] if sure_sec_d else 1
            else:
                # Fallback: alquran.cloud sure listesi
                _fb_sureler = sure_listesi_getir()
                if _fb_sureler:
                    sure_sec_d = {
                        f"{s['number']:>3}. {s.get('name','')}  —  {s.get('englishName','')}": s["number"]
                        for s in _fb_sureler
                    }
                    _secili_sure_str = st.selectbox("Sure Seç", list(sure_sec_d.keys()), index=0, key="fb_sure_sb")
                    _secili_sure_no = sure_sec_d.get(_secili_sure_str)
                    if _secili_sure_no is None:
                        _secili_sure_no = list(sure_sec_d.values())[0] if sure_sec_d else 1
                else:
                    _secili_sure_no = 1

            _sure_key = f"sure_d_{_secili_sure_no}"
            if st.button("📖 Sureyi Yükle", use_container_width=True, key="sure_yukle_btn"):
                with st.spinner("Sure yükleniyor…"):
                    if _diy:
                        st.session_state[_sure_key] = diy_sure_getir(_secili_sure_no, diyanet_key(), diyanet_base_url())
                    else:
                        st.session_state[_sure_key] = sureyi_getir(_secili_sure_no)

            _sure_icerik = st.session_state.get(_sure_key)
            if _sure_icerik:
                if _diy and isinstance(_sure_icerik, list):
                    # Diyanet formatı: [VerseResource, ...]
                    # VerseResource: surah_name_turkish, surah_name_arabic, verse_number, surah_number
                    if _sure_icerik:
                        _s_info = _sure_icerik[0].get("surah_info", {})
                        _sure_adi_goster = _s_info.get("name_turkish") or _sure_icerik[0].get("surah_name_turkish", "")
                        _sure_adi_ar_g   = _sure_icerik[0].get("surah_name_arabic", "")
                    else:
                        _sure_adi_goster = ""
                        _sure_adi_ar_g = ""
                    _vahiy_bilgi = ""
                    st.markdown(f"""
                    <div style="background:#0c1c2e;border:1px solid #1e3d64;border-radius:14px;
                                padding:16px;text-align:center;margin:10px 0;">
                        <div style="font-family:Amiri,serif;font-size:1.7em;color:#c8a84b;">{_sure_adi_ar_g}</div>
                        <div style="color:#5a8aaa;font-size:1em;margin-top:4px;">{_sure_adi_goster}</div>
                        <div style="color:#3a6080;font-size:0.82em;margin-top:2px;">{len(_sure_icerik)} Ayet • Sayfa {_sure_icerik[0].get('page_number','?') if _sure_icerik else '?'} • Cüz {_sure_icerik[0].get('juz_number','?') if _sure_icerik else '?'}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    _goster = st.slider("Gösterilecek Ayet Sayısı", 1, len(_sure_icerik), len(_sure_icerik), key="diy_sure_sl")
                    
                    # ── TDV İSLÂM ANSİKLOPEDİSİ ──
                    if _sure_adi_goster:
                        with st.expander(f"📚 TDV İslâm Ansiklopedisi: {_sure_adi_goster} Suresi"):
                            try:
                                import requests
                                from bs4 import BeautifulSoup
                                
                                # Turkish characters replace
                                tr_map = str.maketrans("çğıöşüâî", "cgiosuai")
                                raw_slug = _sure_adi_goster.split(" ")[0].lower() # e.g. "Bakara Suresi" -> "bakara"
                                slug = raw_slug.translate(tr_map).replace(" ", "-")
                                
                                tdv_url = f"https://islamansiklopedisi.org.tr/{slug}-suresi"
                                r_tdv = requests.get(tdv_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=3)
                                if r_tdv.ok:
                                    soup = BeautifulSoup(r_tdv.text, "html.parser")
                                    # Select all meaningful paragraphs from the article body
                                    pars = soup.select(".article-body p") or soup.select("p")
                                    tdv_text = "\n\n".join([p.text.strip() for p in pars if len(p.text.strip()) > 50][:4])
                                    
                                    if tdv_text:
                                        st.markdown(f"<div style='font-size:0.9em;color:#a0c0d8;line-height:1.6;'>{tdv_text}...<br><br><a href='{tdv_url}' target='_blank' style='color:#c8a84b;'>Devamını TDV'de Oku ↗</a></div>", unsafe_allow_html=True)
                                    else:
                                        st.warning("TDV Ansiklopedisinde bu sureye ait metin bulunamadı.")
                                else:
                                    st.error("TDV Ansiklopedisi'ne ulaşılamadı.")
                            except Exception as e:
                                st.error(f"TDV bağlantısı sırasında bir hata oluştu: {e}")

                    for _av in _sure_icerik[:_goster]:
                        # VerseResource kesin alanlar
                        _sno   = _av.get("surah_id") or _av.get("surah_number", _secili_sure_no)
                        _ano   = _av.get("verse_id_in_surah") or _av.get("verse_number", 0)
                        
                        _t_dict = _av.get("translation")
                        _metin = _t_dict.get("text", "") if isinstance(_t_dict, dict) else _av.get("text", "")
                        
                        _a_dict = _av.get("arabic_script")
                        _arapc = _a_dict.get("text", "") if isinstance(_a_dict, dict) else _av.get("arabic_text", "")
                        
                        # API'de ayet bazında cüz bilgisi gelmediğinden sure bazındaki bilgiyi (veya fallback) kullanıyoruz
                        _juz   = _s_info.get("Cuz", "?") if "_s_info" in locals() and isinstance(_s_info, dict) and "Cuz" in _s_info else _av.get("juz_number", "?")
                        _sayfa = _av.get("page_number", "?")
                        _audio = everyayah_url(_sno, _ano, kari_klasor)
                        st.markdown(f"""
                        <div style="background:#080e1a;border:1px solid #1a3050;border-radius:10px;
                                    padding:14px 18px;margin:5px 0;">
                            <div style="font-size:0.7em;color:#2a5a70;margin-bottom:6px;">
                                {_ano}. Ayet &nbsp;•&nbsp; Cüz {_juz} &nbsp;•&nbsp; Sayfa {_sayfa}
                            </div>
                            {"<div style='font-family:Amiri,serif;font-size:1.7em;color:#c8a84b;direction:rtl;text-align:right;line-height:2;margin-bottom:10px;'>" + _arapc + "</div>" if _arapc else ""}
                            <div style="color:#a0c0d8;font-size:0.9em;line-height:1.8;">{_metin}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        if _sno and _ano:
                            st.audio(_audio, format="audio/mp3")
                else:
                    # alquran.cloud formatı
                    _ayetler = _sure_icerik.get("ayahs", []) if isinstance(_sure_icerik, dict) else []
                    _vahiy   = _sure_icerik.get("revelationType","") if isinstance(_sure_icerik, dict) else ""
                    _vahiy_tr= "Mekke'de İnen" if _vahiy=="Meccan" else "Medine'de İnen" if _vahiy=="Medinan" else _vahiy
                    st.markdown(f"""
                    <div style="background:#0c1c2e;border:1px solid #1e3d64;border-radius:14px;
                                padding:16px;text-align:center;margin:10px 0;">
                        <div style="font-family:Amiri,serif;font-size:1.7em;color:#c8a84b;">{_sure_icerik.get('name','') if isinstance(_sure_icerik,dict) else ''}</div>
                        <div style="color:#3a6080;font-size:0.85em;margin-top:4px;">{_sure_icerik.get('numberOfAyahs','?') if isinstance(_sure_icerik,dict) else '?'} Ayet • {_vahiy_tr}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    _goster = st.slider("Gösterilecek Ayet Sayısı", 1, len(_ayetler), len(_ayetler), key="fb_sure_sl")
                    for _av in _ayetler[:_goster]:
                        _ano = _av.get("numberInSurah", 0)
                        _audio = everyayah_url(_secili_sure_no, _ano, kari_klasor)
                        st.markdown(f"""
                        <div style="background:#080e1a;border:1px solid #1a3050;border-radius:10px;
                                    padding:14px 18px;margin:5px 0;">
                            <div style="font-size:0.7em;color:#2a5a70;margin-bottom:6px;">{_ano}. Ayet</div>
                            <div style="color:#a0c0d8;font-size:0.9em;line-height:1.75;">{_av.get('text','')}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        st.audio(_audio, format="audio/mp3")

        # ── CÜZ OKUYUCU ──
        with kuran_sekme[1]:
            ca, cb = st.columns([2, 1])
            with ca:
                cuz_no = st.number_input("Cüz Numarası (1–30)", 1, 30, 1, key="cuz_no_inp")
            with cb:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("📋 Getir", use_container_width=True, key="cuz_getir_btn"):
                    ck = f"cuz_d_{cuz_no}"
                    with st.spinner(f"{cuz_no}. Cüz yükleniyor…"):
                        if _diy:
                            st.session_state[ck] = diy_cuz_getir(cuz_no, diyanet_key(), diyanet_base_url())
                        else:
                            _fb = cuz_getir(cuz_no)
                            st.session_state[ck] = _fb.get("ayahs", []) if _fb else []

            cuz_ic = st.session_state.get(f"cuz_d_{cuz_no}")
            if cuz_ic:
                _cuz_ayetler = cuz_ic if isinstance(cuz_ic, list) else cuz_ic.get("ayahs", [])
                st.success(f"✅ {cuz_no}. Cüz — {len(_cuz_ayetler)} ayet")
                _goster_c = st.slider("Gösterilecek Ayet", 5, min(20, len(_cuz_ayetler)), 5, key="cuz_sl")
                for _cav in _cuz_ayetler[:_goster_c]:
                    # Diyanet & alquran.cloud uyumlu alan isimleri
                    _s_info = _cav.get("surah_info", {})
                    _c_sure_adi = _s_info.get("name_turkish") or _cav.get("surah_name_turkish") or _cav.get("surah", {}).get("name", "")
                    _c_sno = _cav.get("surah_id") or _cav.get("surah_number") or (_cav.get("surah", {}).get("number", 0))
                    _c_ano = _cav.get("verse_id_in_surah") or _cav.get("verse_number") or _cav.get("numberInSurah", 0)
                    
                    _c_a_dict = _cav.get("arabic_script")
                    _c_arapca = _c_a_dict.get("text", "") if isinstance(_c_a_dict, dict) else _cav.get("arabic_text", "")
                    
                    _c_t_dict = _cav.get("translation")
                    _c_turkce = _c_t_dict.get("text", "") if isinstance(_c_t_dict, dict) else _cav.get("text", "")
                    _c_audio  = everyayah_url(_c_sno, _c_ano, kari_klasor)
                    st.markdown(f"""
                    <div style="background:#080e1a;border:1px solid #1a3050;border-radius:10px;
                                padding:12px 16px;margin:4px 0;">
                        <div style="font-size:0.7em;color:#2a5a70;">{_c_sure_adi} — {_c_ano}. Ayet</div>
                        {"<div style='font-family:Amiri,serif;font-size:1.4em;color:#c8a84b;direction:rtl;text-align:right;line-height:2;margin:6px 0;'>" + _c_arapca + "</div>" if _c_arapca else ""}
                        <div style="color:#a0c0d8;font-size:0.88em;line-height:1.7;margin-top:4px;">{_c_turkce}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    if _c_sno and _c_ano:
                        st.audio(_c_audio, format="audio/mp3")

        # ── SAYFA OKUYUCU (Sadece Diyanet API'de) ──
        with kuran_sekme[2]:
            if not _diy:
                st.info("📖 Sayfa okuyucu yalnızca Diyanet API anahtarı ile kullanılabilir. Sol panelden ekleyin.")
            else:
                sayfa_col1, sayfa_col2 = st.columns([2, 1])
                with sayfa_col1:
                    sayfa_no = st.number_input("Sayfa Numarası (1–604)", 1, 604, 1, key="sayfa_no_inp")
                with sayfa_col2:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("📄 Getir", use_container_width=True, key="sayfa_getir_btn"):
                        _sk = f"sayfa_{sayfa_no}"
                        with st.spinner(f"{sayfa_no}. Sayfa yükleniyor…"):
                            st.session_state[_sk] = diy_sayfa_getir(sayfa_no, diyanet_key(), diyanet_base_url())

                _sayfa_ic = st.session_state.get(f"sayfa_{sayfa_no}")
                if _sayfa_ic and isinstance(_sayfa_ic, list):
                    st.success(f"✅ {sayfa_no}. Sayfa — {len(_sayfa_ic)} ayet")
                    for _sav in _sayfa_ic:
                        _s_sno = _sav.get("surah_id") or _sav.get("surah_number", 0)
                        _s_ano = _sav.get("verse_id_in_surah") or _sav.get("verse_number", 0)
                        
                        _s_info = _sav.get("surah_info", {})
                        _s_sadi = _s_info.get("name_turkish") or _sav.get("surah_name_turkish", "")
                        _s_audio = everyayah_url(_s_sno, _s_ano, kari_klasor)
                        
                        _s_a_dict = _sav.get("arabic_script")
                        _s_arapca = _s_a_dict.get("text", "") if isinstance(_s_a_dict, dict) else _sav.get("arabic_text", "")
                        
                        _s_t_dict = _sav.get("translation")
                        _s_turkce = _s_t_dict.get("text", "") if isinstance(_s_t_dict, dict) else _sav.get("text", "")
                        
                        st.markdown(f"""
                        <div style="background:#080e1a;border:1px solid #1a3050;border-radius:10px;
                                    padding:12px 16px;margin:4px 0;">
                            <div style="font-size:0.7em;color:#2a5a70;">{_s_sadi} — {_s_ano}. Ayet  •  Cüz {_sav.get('juz_number','?')}</div>
                            <div style="font-family:Amiri,serif;font-size:1.5em;color:#c8a84b;direction:rtl;text-align:right;line-height:2;margin:6px 0;">{_s_arapca}</div>
                            <div style="color:#a0c0d8;font-size:0.88em;line-height:1.7;">{_s_turkce}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        if _s_sno and _s_ano:
                            st.audio(_s_audio, format="audio/mp3")

# ══════════════════════════════════════════════════════════════
# TAB 4 — DİNİ ASİSTAN
# ══════════════════════════════════════════════════════════════
with tab4:
    st.markdown("""
    <div style="background:linear-gradient(135deg,#0c1c2e,#0f2340);border:1px solid #1e3d64;
                border-radius:18px;padding:20px;text-align:center;margin-bottom:16px;">
        <div style="font-family:Amiri,serif;font-size:1.6em;color:#c8a84b;margin-bottom:6px;">
            🤖 İslami Dini Asistan
        </div>
        <div style="color:#3a6080;font-size:0.82em;">
            Namaz, ibadet, Kuran, hadis ve dini konular hakkında Türkçe sorabilirsiniz.<br>
            <span style="color:#2a5070;">Groq AI (Llama 3.3 70B) • Bilgiler tavsiye niteliğindedir</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Hızlı sorular
    st.markdown('<div class="bolum-baslik">⚡ Hızlı Sorular</div>', unsafe_allow_html=True)
    h_cols = st.columns(3)
    hizli_sorular = [
        ("🌅", "Sabah namazı kaç rekattır?"),
        ("📖", "Fatiha Suresi'nin anlamı nedir?"),
        ("🌙", "Ramazanda oruç nasıl tutulur?"),
        ("🕋", "Hacca kimler gitmeli?"),
        ("💰", "Zekat hesabı nasıl yapılır?"),
        ("🤲", "Kunut duası nedir ve nasıl okunur?"),
    ]
    SISTEM_PROMPT = """Sen Türkiye Diyanet İşleri Başkanlığı'nın resmi görüşlerini esas alan, Hanefi mezhebi çerçevesinde Türkçe cevaplar veren bir dini bilgi asistanısın.

KURALLAR:
- Tüm yanıtlarını yalnızca Türkçe yaz.
- Sadece Kuran-ı Kerim, Sahih Hadisler ve Diyanet İşleri Başkanlığı'nın resmi fetvalarına dayanan bilgi ver.
- Diyanet görüşüne aykırı, tartışmalı veya farklı mezhep yorumlarına girme.
- Arapça terimleri kullanırken parantez içinde Türkçe karşılığını yaz.
- Cevaplarını kısa ve anlaşılır tut (3-5 cümle yeterli).
- Siyasi, sosyal veya tartışmalı konularda yorum yapma.
- Her yanıtının sonuna şunu ekle: "📌 Kesin hüküm için Diyanet İşleri Başkanlığı'na veya yetkili bir din görevlisine başvurun."
- Dini bilgi dışındaki sorulara (siyaset, kişisel tavsiye, tıp vb.) cevap verme, nazikçe kapsam dışı olduğunu belirt."""

    for i, (ikon, soru) in enumerate(hizli_sorular):
        with h_cols[i % 3]:
            if st.button(f"{ikon} {soru}", key=f"hs_{i}", use_container_width=True):
                st.session_state.sohbet.append({"rol": "kullanici", "icerik": soru})
                with st.spinner("Yanıt hazırlanıyor…"):
                    yanit = groq_sor(
                        [{"role": "user" if m["rol"] == "kullanici" else "assistant", "content": m["icerik"]}
                         for m in st.session_state.sohbet[-8:]],
                        sistem=SISTEM_PROMPT,
                    )
                    st.session_state.sohbet.append({"rol": "asistan", "icerik": yanit})
                st.rerun()

    # Sohbet geçmişi
    if st.session_state.sohbet:
        st.markdown('<div class="bolum-baslik">💬 Sohbet</div>', unsafe_allow_html=True)
        for mesaj in st.session_state.sohbet:
            css = "kullanici" if mesaj["rol"] == "kullanici" else ""
            rol_adi = "Siz" if mesaj["rol"] == "kullanici" else "🤖 Asistan"
            st.markdown(f"""
            <div class="sohbet-kutu {css}">
                <div class="sohbet-rol">{rol_adi}</div>
                {mesaj["icerik"]}
            </div>
            """, unsafe_allow_html=True)

    # Giriş alanı
    st.markdown("---")
    gi_col, go_col = st.columns([5, 1])
    with gi_col:
        kullanici_girisi = st.text_input(
            "Soru", key="sohbet_gir",
            placeholder="Örn: Cuma namazı kaç rekattır? / Abdest nasıl alınır?",
            label_visibility="collapsed",
        )
    with go_col:
        gonder = st.button("📨 Gönder", use_container_width=True)

    if (gonder or kullanici_girisi) and kullanici_girisi.strip():
        st.session_state.sohbet.append({"rol": "kullanici", "icerik": kullanici_girisi.strip()})
        with st.spinner("Yanıt hazırlanıyor…"):
            yanit = groq_sor(
                [{"role": "user" if m["rol"] == "kullanici" else "assistant", "content": m["icerik"]}
                 for m in st.session_state.sohbet[-10:]],
                sistem=SISTEM_PROMPT,
            )
            st.session_state.sohbet.append({"rol": "asistan", "icerik": yanit})
        st.rerun()

    if st.session_state.sohbet:
        c_t, _ = st.columns([1, 4])
        with c_t:
            if st.button("🗑️ Temizle"):
                st.session_state.sohbet = []
                st.rerun()
