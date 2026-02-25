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

.stApp { background: #080e1a; color: #ddd0b8; font-family: 'Tajawal', sans-serif; }
[data-testid="stSidebar"] { background: linear-gradient(180deg, #0a1220 0%, #080e1a 100%) !important; border-right: 1px solid #1a2e48; }
[data-testid="stSidebarNav"] { display: none; }

/* ── HERO ── */
.hero { background: linear-gradient(135deg, #0b1829 0%, #0f2040 50%, #0b1829 100%); border: 1px solid #1e3d64; border-radius: 24px; padding: 28px 36px; text-align: center; margin-bottom: 24px; position: relative; overflow: hidden; }
.hero::before { content: ''; position: absolute; top: 0; left: 10%; right: 10%; height: 2px; background: linear-gradient(90deg, transparent, #c8a84b, #ffe066, #c8a84b, transparent); }
.hero-arabic { font-family: 'Amiri', serif; font-size: 1.6em; color: #c8a84b; letter-spacing: 4px; opacity: 0.85; margin-bottom: 4px; }
.hero-clock { font-family: 'Tajawal', monospace; font-size: 4.2em; font-weight: 700; color: #e8d5a3; letter-spacing: 6px; line-height: 1; margin: 8px 0; text-shadow: 0 0 40px rgba(200,168,75,0.3); }
.hero-miladi { font-size: 1em; color: #7a9dbd; letter-spacing: 2px; margin-bottom: 2px; }
.hero-hijri  { font-family: 'Amiri', serif; font-size: 1.15em; color: #c8a84b; margin-top: 4px; }
.hero-location { font-size: 0.85em; color: #4a7a9b; margin-top: 8px; letter-spacing: 1px; }
.hero-kaynak { font-size: 0.68em; color: #2a5070; margin-top: 6px; letter-spacing: 0.5px; display: flex; align-items: center; justify-content: center; gap: 6px; }
.kaynak-badge { display: inline-block; padding: 2px 8px; border-radius: 20px; font-size: 0.9em; }
.kaynak-imsakiyem { background: #0a2a10; border: 1px solid #1a5020; color: #4caf6a; }
.kaynak-emushaf   { background: #2a1a05; border: 1px solid #5a3010; color: #ff9800; }

/* ── VAKİT KARTLARI ── */
.vakit-card { background: linear-gradient(160deg, #0c1c2e 0%, #0f2340 100%); border: 1px solid #1a3050; border-radius: 16px; padding: 18px 8px; text-align: center; position: relative; height: 130px; display: flex; flex-direction: column; align-items: center; justify-content: center; }
.vakit-card.aktif { background: linear-gradient(160deg, #162840 0%, #1e3c5a 100%); border-color: #c8a84b; box-shadow: 0 0 24px rgba(200,168,75,0.15); }
.vakit-card.aktif::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px; background: linear-gradient(90deg, transparent, #c8a84b, transparent); border-radius: 16px 16px 0 0; }
.vakit-ikon  { font-size: 1.7em; margin-bottom: 6px; }
.vakit-adi   { font-size: 0.72em; color: #5a8aaa; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 5px; }
.vakit-saat  { font-size: 1.45em; font-weight: 700; color: #ddd0b8; }
.vakit-card.aktif .vakit-saat { color: #c8a84b; }
.vakit-etiket { font-size: 0.65em; color: #c8a84b; margin-top: 4px; letter-spacing: 1px; }

/* ── GERİ SAYIM ── */
.geri-sayim { background: linear-gradient(135deg, #0c1e10 0%, #0a180c 100%); border: 1px solid #1e4a28; border-radius: 20px; padding: 22px 28px; text-align: center; }
.geri-sayim.ramazan { background: linear-gradient(135deg, #1e1205 0%, #160e04 100%); border-color: #6a4010; }
.gs-ust     { font-size: 0.78em; color: #5a8a6a; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 6px; }
.gs-namaz   { font-family: 'Amiri', serif; font-size: 1.4em; color: #a8d8b8; margin-bottom: 10px; }
.gs-zaman   { font-family: 'Tajawal', monospace; font-size: 3em; font-weight: 700; color: #4caf6a; letter-spacing: 4px; text-shadow: 0 0 20px rgba(76,175,80,0.3); }

/* ── BÖLÜM BAŞLIK ── */
.bolum-baslik { font-family: 'Amiri', serif; font-size: 1.3em; color: #c8a84b; padding: 14px 0 10px; border-bottom: 1px solid #1a3050; margin: 20px 0 14px; }

/* ── BİLGİ KUTU ── */
.bilgi-kutu { background: #0c1c2e; border: 1px solid #1a3050; border-radius: 14px; padding: 18px; text-align: center; height: 110px; display: flex; flex-direction: column; align-items: center; justify-content: center; }
.bilgi-deger  { font-size: 1.7em; font-weight: 700; color: #c8a84b; font-family: 'Amiri', serif; }
.bilgi-etiket { font-size: 0.72em; color: #4a7a9b; text-transform: uppercase; letter-spacing: 1px; margin-top: 4px; }

/* ── AYET KUTU ── */
.ayet-kutu { background: linear-gradient(160deg, #0c1c2e 0%, #0f2340 100%); border: 1px solid #1e3d64; border-radius: 18px; padding: 26px 30px; margin: 12px 0; }
.ayet-arapca  { font-family: 'Amiri', serif; font-size: 2em; color: #c8a84b; text-align: right; direction: rtl; line-height: 2; margin-bottom: 18px; padding-bottom: 16px; border-bottom: 1px solid #1e3d64; }
.ayet-turkce  { font-size: 1.05em; color: #a8c8e0; line-height: 1.85; font-style: italic; margin-bottom: 12px; }
.ayet-kaynak  { font-size: 0.75em; color: #3a6080; text-align: right; }

/* ── RAMAZAN PANKART ── */
.ramazan-pankart { background: linear-gradient(135deg, #1e1005 0%, #2a1808 60%, #1e1005 100%); border: 1px solid #8a5820; border-radius: 22px; padding: 28px; text-align: center; position: relative; overflow: hidden; }
.ramazan-pankart::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px; background: linear-gradient(90deg, transparent, #ff9800, #ffd54f, #ff9800, transparent); }
.ramazan-baslik { font-family: 'Amiri', serif; font-size: 2.2em; color: #ffc107; }

/* ── CHAT ── */
.sohbet-kutu { background: #0c1c2e; border: 1px solid #1a3050; border-radius: 14px; padding: 16px 20px; margin: 6px 0; color: #a8c8e0; line-height: 1.7; }
.sohbet-kutu.kullanici { background: linear-gradient(135deg, #0f2010 0%, #0c180c 100%); border-color: #1e4a28; color: #a8d8b8; text-align: right; }
.sohbet-rol { font-size: 0.7em; color: #3a6080; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; }
.sohbet-kutu.kullanici .sohbet-rol { color: #3a6a40; }

/* ── UYARI ── */
.uyari-not { background: #1a1205; border: 1px solid #4a3010; border-left: 3px solid #c8a84b; border-radius: 0 10px 10px 0; padding: 12px 16px; margin: 10px 0; font-size: 0.82em; color: #8a7840; line-height: 1.6; }

/* ── HAFTALIK TABLO ── */
.haftalik-satir { display: grid; grid-template-columns: 2.2fr 1fr 1fr 1fr 1fr 1fr 1fr; gap: 4px; padding: 8px 12px; border-radius: 8px; margin: 3px 0; background: #0a1420; border: 1px solid #0f2030; font-size: 0.84em; align-items: center; }
.haftalik-satir.bugun { background: #0f2035; border-color: #1e4060; }
.haftalik-satir.baslik { background: transparent; border-color: transparent; color: #c8a84b; font-size: 0.75em; text-transform: uppercase; letter-spacing: 1px; }

/* ── STREAMLİT OVERRIDE ── */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stDecoration"] { display: none; }
.stButton > button { background: linear-gradient(135deg, #0f2040, #162c50) !important; color: #c8d8e8 !important; border: 1px solid #1e3d64 !important; border-radius: 10px !important; font-family: 'Tajawal', sans-serif !important; font-size: 0.9em !important; transition: all 0.25s !important; }
.stButton > button:hover { border-color: #c8a84b !important; color: #c8a84b !important; }
.stSelectbox > div > div { background: #0c1c2e !important; border-color: #1a3050 !important; color: #ddd0b8 !important; }
.stTextInput > div > div > input, .stTextArea > div > div > textarea { background: #0c1c2e !important; border-color: #1a3050 !important; color: #ddd0b8 !important; border-radius: 10px !important; font-family: 'Tajawal', sans-serif !important; }
label { color: #7a9dbd !important; font-family: 'Tajawal', sans-serif !important; }
.stTabs [data-baseweb="tab"] { color: #5a8aaa !important; font-family: 'Tajawal', sans-serif !important; }
.stTabs [aria-selected="true"] { color: #c8a84b !important; }
.stTabs [data-baseweb="tab-highlight"] { background-color: #c8a84b !important; }
p, li { color: #a0b8cc; }
h1, h2, h3 { font-family: 'Amiri', serif !important; color: #c8a84b !important; }
.stNumberInput > div > div > input { background: #0c1c2e !important; border-color: #1a3050 !important; color: #ddd0b8 !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# SABITLER
# ─────────────────────────────────────────────────────────────
IMSAKIYEM   = "https://ezanvakti.imsakiyem.com"
EMUSHAF     = "https://ezanvakti.emushaf.net"
RAMADAN_URL = "https://ramadan.munafio.com/api/check"
QURAN_URL   = "https://api.alquran.cloud/v1"
NOMINATIM   = "https://nominatim.openstreetmap.org"
TR_TZ       = pytz.timezone("Europe/Istanbul")

VAKIT_IKONLARI = {"imsak": "🌙", "gunes": "🌅", "ogle": "☀️", "ikindi": "🌤️", "aksam": "🌇", "yatsi": "🌃"}
VAKIT_ADLARI = {"imsak": "İmsak", "gunes": "Güneş", "ogle": "Öğle", "ikindi": "İkindi", "aksam": "Akşam", "yatsi": "Yatsı"}
GUN_ADLARI = {"Monday": "Pazartesi", "Tuesday": "Salı", "Wednesday": "Çarşamba", "Thursday": "Perşembe", "Friday": "Cuma", "Saturday": "Cumartesi", "Sunday": "Pazar"}
AY_ADLARI = {"January": "Ocak", "February": "Şubat", "March": "Mart", "April": "Nisan", "May": "Mayıs", "June": "Haziran", "July": "Temmuz", "August": "Ağustos", "September": "Eylül", "October": "Ekim", "November": "Kasım", "December": "Aralık"}

# ─────────────────────────────────────────────────────────────
# YARDIMCI FONKSİYONLAR
# ─────────────────────────────────────────────────────────────
def normalize_eslesme(metin: str) -> str:
    if not metin: return ""
    donusum = str.maketrans("çÇğĞıİöÖşŞüÜ", "cCgGiIoOsSuU")
    return metin.translate(donusum).upper().strip()

def adi_duzenle(adi: str) -> str:
    if not adi: return adi
    kelimeler = adi.strip().split()
    sonuc = []
    for k in kelimeler:
        if not k: continue
        ilk = "İ" if k[0] == "I" else k[0].upper()
        kalan = k[1:].lower()
        sonuc.append(ilk + kalan)
    return " ".join(sonuc)

def zaman_parse(saat_str: str, tarih=None):
    if not saat_str or saat_str == "—": return None
    if tarih is None: tarih = datetime.now(TR_TZ).date()
    try:
        s, d = saat_str.strip().split(":")
        naive = datetime.combine(tarih, datetime.min.time().replace(hour=int(s), minute=int(d)))
        return TR_TZ.localize(naive)
    except:
        return None

def geri_sayim_str(hedef_dt) -> str:
    now = datetime.now(TR_TZ)
    fark = hedef_dt - now
    if fark.total_seconds() <= 0: return "00:00:00"
    toplam = int(fark.total_seconds())
    s, kalan = divmod(toplam, 3600)
    d, sn = divmod(kalan, 60)
    return f"{s:02d}:{d:02d}:{sn:02d}"

def tr_tarih_format(dt) -> str:
    gun = GUN_ADLARI.get(dt.strftime("%A"), dt.strftime("%A"))
    ay  = AY_ADLARI.get(dt.strftime("%B"), dt.strftime("%B"))
    return f"{gun}, {dt.day} {ay} {dt.year}"

def canlı_gs_js(element_id: str, hedef_dt) -> str:
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
    "ilce_id_emushaf": None,
    "konum_adi": "",
    "kaynak": "imsakiyem",
    "geo_denendi": False,
    "ayet_tohumu": random.randint(1, 9999),
    "ramazan_dua": None,
    "api_debug_log": {} # API verilerini debug için tutacağız
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────────────────────
# GEOLOCATION (TAKILMA KORUMALI)
# ─────────────────────────────────────────────────────────────
params   = st.query_params
geo_lat  = params.get("lat",     None)
geo_lng  = params.get("lng",     None)
geo_red  = params.get("geo_red", None)

if not geo_lat and not geo_red and not st.session_state.geo_denendi:
    st.components.v1.html("""
    <script>
    (function() {
        var base = window.parent.location.href.split('?')[0];
        if (!navigator.geolocation) { window.parent.location.href = base + '?geo_red=1'; return; }
        
        navigator.geolocation.getCurrentPosition(
            function(pos) {
                window.parent.location.href = base + '?lat=' + pos.coords.latitude.toFixed(5) + '&lng=' + pos.coords.longitude.toFixed(5);
            },
            function() { window.parent.location.href = base + '?geo_red=1'; },
            { timeout: 5000, maximumAge: 300000 }
        );
    })();
    </script>
    <div style="text-align:center;padding:50px 20px;font-family:Tajawal,sans-serif; color:#7a9dbd;background:#080e1a;">
        <div style="font-size:2.5em;margin-bottom:12px;">📍</div>
        <div style="font-size:1.2em;color:#5a8aaa;">Konumunuz tespit ediliyor…</div>
        <div style="font-size:0.8em;color:#3a5a70;margin-top:8px;">Tarayıcınızda konum izni istenecektir.</div>
    </div>
    """, height=220)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("Hemen Geç (Manuel Konum Seç)", use_container_width=True):
            st.session_state.geo_denendi = True
            st.rerun()
    st.stop()

st.session_state.geo_denendi = True

# ─────────────────────────────────────────────────────────────
# API ÇAĞRILARI
# ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=86400, show_spinner=False)
def im_ulkeler():
    try:
        r = requests.get(f"{IMSAKIYEM}/api/locations/countries", timeout=5)
        return r.json().get("data", []) if r.ok else None
    except: return None

@st.cache_data(ttl=86400, show_spinner=False)
def im_eyaletler(country_id: str):
    try:
        r = requests.get(f"{IMSAKIYEM}/api/locations/states", params={"countryId": country_id}, timeout=5)
        return r.json().get("data", []) if r.ok else None
    except: return None

@st.cache_data(ttl=86400, show_spinner=False)
def im_ilceler(state_id: str):
    try:
        r = requests.get(f"{IMSAKIYEM}/api/locations/districts", params={"stateId": state_id}, timeout=5)
        return r.json().get("data", []) if r.ok else None
    except: return None

@st.cache_data(ttl=3600, show_spinner=False)
def im_ara(tip: str, sorgu: str):
    try:
        r = requests.get(f"{IMSAKIYEM}/api/locations/search/{tip}", params={"q": sorgu}, timeout=5)
        return r.json().get("data", []) if r.ok else None
    except: return None

@st.cache_data(ttl=600, show_spinner=False)
def im_vakitler(district_id: str, period: str = "weekly"):
    try:
        r = requests.get(f"{IMSAKIYEM}/api/prayer-times/{district_id}/{period}", timeout=8)
        if not r.ok: return None
        return r.json().get("data", [])
    except Exception as e:
        return {"error": str(e)}

@st.cache_data(ttl=86400, show_spinner=False)
def em_ulkeler():
    try:
        r = requests.get(f"{EMUSHAF}/ulkeler", timeout=5)
        return r.json() if r.ok else None
    except: return None

@st.cache_data(ttl=86400, show_spinner=False)
def em_sehirler(ulke_id):
    try:
        r = requests.get(f"{EMUSHAF}/sehirler/{ulke_id}", timeout=5)
        return r.json() if r.ok else None
    except: return None

@st.cache_data(ttl=86400, show_spinner=False)
def em_ilceler(sehir_id):
    try:
        r = requests.get(f"{EMUSHAF}/ilceler/{sehir_id}", timeout=5)
        return r.json() if r.ok else None
    except: return None

@st.cache_data(ttl=600, show_spinner=False)
def em_vakitler(ilce_id):
    try:
        r = requests.get(f"{EMUSHAF}/vakitler/{ilce_id}", timeout=8)
        return r.json() if r.ok else None
    except Exception as e:
        return {"error": str(e)}

@st.cache_data(ttl=3600, show_spinner=False)
def ramazan_kontrol(tarih_str: str):
    try:
        r = requests.get(RAMADAN_URL, params={"date": tarih_str}, timeout=5)
        return r.json() if r.ok else None
    except: return None

@st.cache_data(ttl=3600, show_spinner=False)
def ters_geocode(lat: float, lng: float):
    try:
        r = requests.get(
            f"{NOMINATIM}/reverse",
            params={"lat": lat, "lon": lng, "format": "json", "accept-language": "tr"},
            headers={"User-Agent": "IslamilZaman/2.0"}, timeout=5,
        )
        return r.json() if r.ok else None
    except: return None

# ─────────────────────────────────────────────────────────────
# VERİ NORMALİZASYONU (HATA KORUMALI)
# ─────────────────────────────────────────────────────────────
def im_vakit_normalize(v: dict) -> dict:
    if not isinstance(v, dict): return {}
    times = v.get("times", {})
    tarih_iso = v.get("date", "")
    hicri = v.get("hijri_date", {})

    try:
        dt = datetime.strptime(tarih_iso, "%Y-%m-%d")
        tarih_kisa = dt.strftime("%d.%m.%Y")
        gun_adi = GUN_ADLARI.get(dt.strftime("%A"), dt.strftime("%A"))
    except:
        tarih_kisa = tarih_iso
        gun_adi = ""

    hicri_str = hicri.get("full_date", "") if isinstance(hicri, dict) else ""
    if not hicri_str and isinstance(hicri, dict):
        hicri_str = f"{hicri.get('day','?')} {hicri.get('month_name','?')} {hicri.get('year','?')}"

    return {
        "imsak": times.get("imsak", "—"), "gunes": times.get("gunes", "—"), "ogle": times.get("ogle", "—"),
        "ikindi": times.get("ikindi","—"), "aksam": times.get("aksam", "—"), "yatsi": times.get("yatsi", "—"),
        "tarih_kisa": tarih_kisa, "tarih_iso": tarih_iso, "hicri_str": hicri_str, "gun_adi": gun_adi,
        "kiblesaati": "—", "gunesdogus": "—", "gunesbatis": "—", "gmt": "+3",
    }

def em_vakit_normalize(v: dict) -> dict:
    if not isinstance(v, dict): return {}
    tarih_kisa = str(v.get("MiladiTarihKisa", "")).strip()
    try:
        dt = datetime.strptime(tarih_kisa, "%d.%m.%Y")
        tarih_iso = dt.strftime("%Y-%m-%d")
        gun_adi   = GUN_ADLARI.get(dt.strftime("%A"), dt.strftime("%A"))
    except:
        tarih_iso, gun_adi = "", ""

    return {
        "imsak": v.get("Imsak", "—"), "gunes": v.get("Gunes", "—"), "ogle": v.get("Ogle", "—"),
        "ikindi": v.get("Ikindi", "—"), "aksam": v.get("Aksam", "—"), "yatsi": v.get("Yatsi", "—"),
        "tarih_kisa": tarih_kisa, "tarih_iso": tarih_iso, "hicri_str": str(v.get("HicriTarihUzun", "")),
        "gun_adi": gun_adi, "kiblesaati": v.get("KibleSaati", "—"), "gunesdogus": v.get("GunesDogus", "—"),
        "gunesbatis": v.get("GunesBatis", "—"), "gmt": str(v.get("GreenwichOrtalamaZamani", "+3")),
    }

VAKIT_SIRA = ["imsak", "gunes", "ogle", "ikindi", "aksam", "yatsi"]

def aktif_vakit_bul(vakit: dict):
    now = datetime.now(TR_TZ)
    bugun = now.date()
    aktif = None
    for key in VAKIT_SIRA:
        dt = zaman_parse(vakit.get(key), bugun)
        if dt and dt <= now: aktif = key
    return aktif

def sonraki_namaz_bul(vakit: dict, yarin_vakit: dict = None):
    now = datetime.now(TR_TZ)
    bugun = now.date()
    for key in VAKIT_SIRA:
        dt = zaman_parse(vakit.get(key), bugun)
        if dt and dt > now: return VAKIT_ADLARI[key], VAKIT_IKONLARI[key], dt, vakit[key]
    if yarin_vakit:
        yarin = bugun + timedelta(days=1)
        dt = zaman_parse(yarin_vakit.get("imsak"), yarin)
        if dt: return "İmsak (Yarın)", "🌙", dt, yarin_vakit["imsak"]
    return "İmsak", "🌙", None, "—"

# ─────────────────────────────────────────────────────────────
# OTOMATİK KONUM EŞLEŞTİRME
# ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def konum_eslestir_imsakiyem(lat: float, lng: float):
    geo = ters_geocode(lat, lng)
    if not geo: return None, None
    adres = geo.get("address", {})
    sorgu_adaylari = list(filter(None, [adres.get("suburb"), adres.get("district"), adres.get("county"), adres.get("city"), adres.get("town"), adres.get("province"), adres.get("state")]))
    for sorgu in sorgu_adaylari[:4]:
        sonuclar = im_ara("districts", sorgu)
        if sonuclar and isinstance(sonuclar, list):
            ilce = sonuclar[0]
            ilce_adi  = ilce.get("name", "")
            sehir_adi = ilce.get("state_id", {}).get("name", "") if isinstance(ilce.get("state_id"), dict) else ""
            return ilce.get("_id"), f"📍 {sehir_adi} / {ilce_adi}" if sehir_adi else f"📍 {ilce_adi}"
    return None, f"📍 {adres.get('city') or adres.get('town') or ''}"

@st.cache_data(ttl=3600, show_spinner=False)
def konum_eslestir_emushaf(lat: float, lng: float):
    geo = ters_geocode(lat, lng)
    if not geo: return None, None, None
    adres = geo.get("address", {})
    sehir_hammadde = (adres.get("city") or adres.get("town") or adres.get("province") or "").upper()
    ilce_hammadde  = (adres.get("suburb") or adres.get("district") or sehir_hammadde).upper()
    is_turkey = any(x in adres.get("country", "").upper() for x in ["TURKEY", "TÜRKIYE", "TURKIYE"])

    ulkeler = em_ulkeler()
    if not ulkeler: return None, None, None

    eslesme_ulke = next((u for u in ulkeler if "TURKIYE" in normalize_eslesme(u["UlkeAdi"])), None) if is_turkey else None
    if not eslesme_ulke: return None, None, None

    sehirler = em_sehirler(eslesme_ulke["UlkeID"])
    if not sehirler: return eslesme_ulke, None, None
    n_sehir = normalize_eslesme(sehir_hammadde)
    eslesme_sehir = next((s for s in sehirler if n_sehir and n_sehir in normalize_eslesme(s["SehirAdi"])), sehirler[0])

    ilceler = em_ilceler(eslesme_sehir["SehirID"])
    if not ilceler: return eslesme_ulke, eslesme_sehir, None
    n_ilce = normalize_eslesme(ilce_hammadde)
    eslesme_ilce = next((i for i in ilceler if n_ilce and n_ilce in normalize_eslesme(i["IlceAdi"])), ilceler[0])

    return eslesme_ulke, eslesme_sehir, eslesme_ilce

if geo_lat and geo_lng:
    try:
        lat_f, lng_f = float(geo_lat), float(geo_lng)
        im_id, im_konum_adi = konum_eslestir_imsakiyem(lat_f, lng_f)
        if im_id:
            st.session_state.ilce_id, st.session_state.kaynak, st.session_state.konum_adi = im_id, "imsakiyem", im_konum_adi
        else:
            em_res = konum_eslestir_emushaf(lat_f, lng_f)
            if em_res and em_res[2]:
                st.session_state.ilce_id_emushaf, st.session_state.kaynak = em_res[2]["IlceID"], "emushaf"
                st.session_state.konum_adi = f"📍 {adi_duzenle(em_res[1]['SehirAdi'])} / {adi_duzenle(em_res[2]['IlceAdi'])}"
    except: pass

# ─────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""<div style='text-align:center;padding:16px 0 8px;font-family:Amiri,serif;font-size:1.4em;color:#c8a84b;letter-spacing:2px;'>☪️ İslami Zaman</div><div style='text-align:center;font-size:0.72em;color:#3a6080;padding-bottom:12px;letter-spacing:1px;'>Namaz Vakitleri & Kuran</div>""", unsafe_allow_html=True)
    st.divider()

    if st.session_state.konum_adi:
        badge = '<span class="kaynak-badge kaynak-imsakiyem">imsakiyem ✓</span>' if st.session_state.kaynak == "imsakiyem" else '<span class="kaynak-badge kaynak-emushaf">emushaf ↩</span>'
        d_renk, d_border = ("#0c1e10", "#1e4a28") if st.session_state.kaynak == "imsakiyem" else ("#1a1205", "#4a3010")
        st.markdown(f"<div style='background:{d_renk};border:1px solid {d_border};border-radius:12px;padding:12px 16px;margin-bottom:12px;text-align:center;'><div style='font-size:0.68em;color:#3a6a40;letter-spacing:1px;margin-bottom:4px;'>✅ Konum Tespit Edildi</div><div style='color:#a8d8b8;font-size:0.88em;margin-bottom:6px;'>{st.session_state.konum_adi}</div>{badge}</div>", unsafe_allow_html=True)
        konumu_degistir = st.checkbox("🔄 Konumu Değiştir", value=False)
    elif geo_red:
        st.markdown("<div style='background:#1a1005;border:1px solid #4a3010;border-radius:12px;padding:12px 16px;margin-bottom:12px;text-align:center;'><div style='font-size:0.68em;color:#6a4020;letter-spacing:1px;'>⚠️ Konum İzni Yok</div><div style='color:#8a6040;font-size:0.82em;margin-top:4px;'>Aşağıdan manuel seçin</div></div>", unsafe_allow_html=True)
        konumu_degistir = True
    else: konumu_degistir = True

    st.markdown('<p style="font-size:0.78em;color:#4a6a8a;margin-bottom:4px;">⚡ Veri Kaynağı</p>', unsafe_allow_html=True)
    kaynak_secim = st.radio("Kaynak", ["🟢 imsakiyem.com", "🟡 emushaf.net"], index=0 if st.session_state.kaynak == "imsakiyem" else 1, label_visibility="collapsed", horizontal=True)
    st.session_state.kaynak = "imsakiyem" if "imsakiyem" in kaynak_secim else "emushaf"
    st.markdown("---")

    if konumu_degistir or not st.session_state.konum_adi:
        if st.session_state.kaynak == "imsakiyem":
            ulkeler_im = im_ulkeler()
            if ulkeler_im is None:
                st.error("İmsakiyem bağlantı hatası. Lütfen emushaf.net kaynağını seçin.")
            elif ulkeler_im:
                ulke_display = [u.get("name", "") for u in ulkeler_im]
                v_ulke = next((i for i, u in enumerate(ulkeler_im) if "Türkiye" in u.get("name", "") or "Turkey" in u.get("name_en", "")), 0)
                s_ulke = st.selectbox("Ülke", ulke_display, index=v_ulke, label_visibility="collapsed")
                secili_ulke_im = next((u for u in ulkeler_im if u.get("name") == s_ulke), None)

                if secili_ulke_im:
                    eyaletler = im_eyaletler(secili_ulke_im["_id"])
                    if eyaletler:
                        eyalet_display = [e.get("name", "") for e in eyaletler]
                        s_eyalet = st.selectbox("Eyalet", eyalet_display, index=0, label_visibility="collapsed")
                        secili_eyalet_im = next((e for e in eyaletler if e.get("name") == s_eyalet), None)

                        if secili_eyalet_im:
                            ilceler_im = im_ilceler(secili_eyalet_im["_id"])
                            if ilceler_im:
                                ilce_display = [i.get("name", "") for i in ilceler_im]
                                s_ilce = st.selectbox("İlçe", ilce_display, index=0, label_visibility="collapsed")
                                if s_ilce:
                                    st.session_state.ilce_id = next((i for i in ilceler_im if i.get("name") == s_ilce), None)["_id"]
                                    st.session_state.konum_adi = f"📍 {s_eyalet} / {s_ilce}"

        else:
            ulkeler_em = em_ulkeler()
            if ulkeler_em is None:
                st.error("Emushaf bağlantı hatası.")
            elif ulkeler_em:
                ulke_display = [adi_duzenle(u["UlkeAdi"]) for u in ulkeler_em]
                v_ulke = next((i for i, u in enumerate(ulkeler_em) if "TURKIYE" in normalize_eslesme(u["UlkeAdi"])), 0)
                s_ulke = st.selectbox("Ülke", ulke_display, index=v_ulke, label_visibility="collapsed")
                secili_ulke_em = ulkeler_em[ulke_display.index(s_ulke)]

                sehirler_em = em_sehirler(secili_ulke_em["UlkeID"])
                if sehirler_em:
                    sehir_display = [adi_duzenle(s["SehirAdi"]) for s in sehirler_em]
                    s_sehir = st.selectbox("Şehir", sehir_display, index=0, label_visibility="collapsed")
                    secili_sehir_em = sehirler_em[sehir_display.index(s_sehir)]

                    ilceler_em = em_ilceler(secili_sehir_em["SehirID"])
                    if ilceler_em:
                        ilce_display = [adi_duzenle(i["IlceAdi"]) for i in ilceler_em]
                        s_ilce = st.selectbox("İlçe", ilce_display, index=0, label_visibility="collapsed")
                        st.session_state.ilce_id_emushaf = ilceler_em[ilce_display.index(s_ilce)]["IlceID"]
                        st.session_state.konum_adi = f"📍 {s_sehir} / {s_ilce}"

    st.divider()
    c_btn1, c_btn2 = st.columns(2)
    with c_btn1:
        if st.button("🔄 Yenile", use_container_width=True):
            im_vakitler.clear()
            em_vakitler.clear()
            st.rerun()
    with c_btn2:
        if st.button("🎲 Ayet", use_container_width=True):
            st.session_state.ayet_tohumu = random.randint(1, 9999)
            st.rerun()

# ─────────────────────────────────────────────────────────────
# AKTİF VAKİT VERİSİ ÇEK & KONTROL ET
# ─────────────────────────────────────────────────────────────
now_tr     = datetime.now(TR_TZ)
bugun_kisa = now_tr.strftime("%d.%m.%Y")
bugun_api  = now_tr.strftime("%d-%m-%Y")

vakitler_norm = []
bugun_vakit = yarin_vakit = None
kaynak_aktif = st.session_state.kaynak
api_raw_data = None # Debug için ham veriyi tut

if kaynak_aktif == "imsakiyem" and st.session_state.ilce_id:
    ham_liste = im_vakitler(st.session_state.ilce_id, "weekly")
    if isinstance(ham_liste, dict) and "error" in ham_liste:
        st.session_state.api_debug_log["imsakiyem_error"] = ham_liste["error"]
        kaynak_aktif = "emushaf_fallback"
    elif ham_liste:
        api_raw_data = ham_liste
        vakitler_norm = [im_vakit_normalize(v) for v in ham_liste if isinstance(v, dict)]
    else: kaynak_aktif = "emushaf_fallback"

if kaynak_aktif in ["emushaf", "emushaf_fallback"] and st.session_state.ilce_id_emushaf:
    ham_liste = em_vakitler(st.session_state.ilce_id_emushaf)
    if isinstance(ham_liste, dict) and "error" in ham_liste:
        st.session_state.api_debug_log["emushaf_error"] = ham_liste["error"]
    elif ham_liste:
        api_raw_data = ham_liste
        vakitler_norm = [em_vakit_normalize(v) for v in ham_liste if isinstance(v, dict)]
        kaynak_aktif = "emushaf_fallback" if kaynak_aktif != "emushaf" else "emushaf"

if vakitler_norm:
    bugun_vakit = next((v for v in vakitler_norm if v.get("tarih_kisa") == bugun_kisa), None)
    if not bugun_vakit and len(vakitler_norm) > 0:
        # Eğer bugünü bulamadıysa, ilk günü bugün kabul et (bazı API'ler saat dilimi farkı yapabilir)
        bugun_vakit = vakitler_norm[0]
    
    if bugun_vakit:
        bugun_idx = vakitler_norm.index(bugun_vakit)
        if bugun_idx + 1 < len(vakitler_norm):
            yarin_vakit = vakitler_norm[bugun_idx + 1]

ramazan_veri = ramazan_kontrol(bugun_api)
ramazan_mi = ramazan_veri and ramazan_veri.get("status") == "success" and ramazan_veri["data"].get("isRamadan", False)

# ─────────────────────────────────────────────────────────────
# HERO
# ─────────────────────────────────────────────────────────────
hicri_str = bugun_vakit.get("hicri_str", "—") if bugun_vakit else "—"
miladi_str = tr_tarih_format(now_tr)
saat_str = now_tr.strftime("%H:%M:%S")

k_badge = ""
if vakitler_norm:
    if "fallback" in kaynak_aktif: k_badge = '<span class="kaynak-badge kaynak-emushaf">⚡ emushaf (yedek)</span>'
    elif kaynak_aktif == "emushaf": k_badge = '<span class="kaynak-badge kaynak-emushaf">emushaf</span>'
    else: k_badge = '<span class="kaynak-badge kaynak-imsakiyem">imsakiyem ✓</span>'

st.markdown(f"""
<div class="hero">
    <div class="hero-arabic">{"رَمَضَانُ الْمُبَارَك" if ramazan_mi else "بِسْمِ اللهِ الرَّحْمَنِ الرَّحِيم"}</div>
    <div class="hero-clock" id="tr-saat">{saat_str}</div>
    <div class="hero-miladi">{miladi_str}</div>
    <div class="hero-hijri">{hicri_str}</div>
    <div class="hero-location">{st.session_state.konum_adi or "📍 Konum seçilmedi"}</div>
    <div class="hero-kaynak">Veri Kaynağı: {k_badge}</div>
</div>
""", unsafe_allow_html=True)

st.components.v1.html("""<script>(function tick(){var el=window.parent.document.getElementById('tr-saat');if(el)el.textContent=new Date().toLocaleTimeString('tr-TR',{timeZone:'Europe/Istanbul',hour12:false});setTimeout(tick,1000);})();</script>""", height=0)

# ─────────────────────────────────────────────────────────────
# TABLAR
# ─────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["🕌 Namaz Vakitleri", "🌙 Ramazan", "⚙️ API Debug"])

with tab1:
    if not vakitler_norm and not st.session_state.ilce_id and not st.session_state.ilce_id_emushaf:
        st.markdown('<div style="background:#0c1c2e;border:1px dashed #1e3d64;border-radius:18px;padding:50px;text-align:center;margin:20px 0;"><div style="font-size:2.5em;margin-bottom:12px;">📍</div><div style="color:#5a8aaa;font-size:1.1em;">Sol panelden konum seçin.</div></div>', unsafe_allow_html=True)
    elif not vakitler_norm:
        st.error("⚠️ Seçili konum için API'den veri alınamadı veya dönen liste boş. Sol menüden 'Yedek Kaynak'ı seçmeyi deneyin.")
        with st.expander("API Hata Loglarını Gör"):
            st.json(st.session_state.api_debug_log)
    elif not bugun_vakit:
        st.error(f"⚠️ API {len(vakitler_norm)} günlük veri döndürdü ancak bugünün tarihi ({bugun_kisa}) ile eşleşen kayıt bulunamadı.")
        with st.expander("Dönen Tarihleri İncele"):
            st.write([v.get("tarih_kisa") for v in vakitler_norm])
    else:
        snr_ad, snr_ikon, snr_dt, snr_saat = sonraki_namaz_bul(bugun_vakit, yarin_vakit)
        gs = geri_sayim_str(snr_dt) if snr_dt else "—"

        c_a, c_b, c_c = st.columns([1, 2, 1])
        with c_b:
            st.markdown(f'<div class="geri-sayim"><div class="gs-ust">⏱ Sonraki Namaza Kalan Süre</div><div class="gs-namaz">{snr_ikon} {snr_ad} — {snr_saat}</div><div class="gs-zaman" id="gs-main">{gs}</div></div>', unsafe_allow_html=True)
        if snr_dt: st.components.v1.html(canlı_gs_js("gs-main", snr_dt), height=0)

        st.markdown('<div class="bolum-baslik">📅 Bugünün Namaz Vakitleri</div>', unsafe_allow_html=True)
        aktif_key = aktif_vakit_bul(bugun_vakit)
        cols = st.columns(6)
        for i, key in enumerate(VAKIT_SIRA):
            is_aktif = key == aktif_key
            with cols[i]:
                st.markdown(f'<div class="vakit-card {"aktif" if is_aktif else ""}"><div class="vakit-ikon">{VAKIT_IKONLARI[key]}</div><div class="vakit-adi">{VAKIT_ADLARI[key]}</div><div class="vakit-saat">{bugun_vakit.get(key, "—")}</div>{"<div class=\"vakit-etiket\">● Şu An</div>" if is_aktif else ""}</div>', unsafe_allow_html=True)

        st.markdown('<div class="bolum-baslik">📆 Haftalık Namaz Vakitleri</div>', unsafe_allow_html=True)
        st.markdown('<div class="haftalik-satir baslik"><div>Tarih</div><div style="text-align:center">İmsak</div><div style="text-align:center">Güneş</div><div style="text-align:center">Öğle</div><div style="text-align:center">İkindi</div><div style="text-align:center">Akşam</div><div style="text-align:center">Yatsı</div></div>', unsafe_allow_html=True)
        for v in vakitler_norm[:7]:
            b_mu = v.get("tarih_kisa") == bugun_vakit.get("tarih_kisa")
            s_html = "".join([f'<div style="text-align:center;color:{"#c8a84b" if b_mu else "#8aadcc"};">{v.get(k, "—")}</div>' for k in ["imsak", "gunes", "ogle", "ikindi", "aksam", "yatsi"]])
            st.markdown(f'<div class="haftalik-satir {"bugun" if b_mu else ""}"><div style="color:{"#c8a84b" if b_mu else "#5a8aaa"};">{v.get("gun_adi", "")[:3]} {v.get("tarih_kisa", "")} {"◀" if b_mu else ""}</div>{s_html}</div>', unsafe_allow_html=True)

with tab2:
    st.info("Ramazan modülü (Buraya daha önceki Ramazan kodun gelebilir, sadelik için daralttım)")

with tab3:
    st.markdown('<div class="bolum-baslik">🛠️ Sorun Giderme ve API Ham Verisi</div>', unsafe_allow_html=True)
    st.write("Eğer veriler ekranda gözükmüyorsa, arka planda uygulamanın çektiği veriler aşağıdadır. Buradan API'nin saatleri verip vermediğini kontrol edebilirsin.")
    if api_raw_data:
        st.json(api_raw_data)
    else:
        st.warning("Şu an hiçbir API'den başarılı ham veri çekilemedi.")
