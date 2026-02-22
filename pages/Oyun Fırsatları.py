"""
GamerPower Ücretsiz Oyun & Loot Takibi
Streamlit + Groq (Türkçe çeviri) + GamerPower API
"""

import time
from datetime import datetime, timezone, timedelta

import requests
import streamlit as st
from groq import Groq

# ─────────────────────────────────────────────
# AYARLAR
# ─────────────────────────────────────────────
BASE_URL          = "https://www.gamerpower.com/api"
GROQ_MODEL        = "llama-3.3-70b-versatile"
RATE_LIMIT_SANIYE = 16
TZ_TR             = timezone(timedelta(hours=3))

PLATFORM_SECENEKLERI = [
    "Tümü", "pc", "steam", "epic-games-store", "gog",
    "itch.io", "ps4", "ps5", "xbox-one", "xbox-series-xs",
    "switch", "android", "ios", "vr", "battlenet",
    "ubisoft", "origin", "drm-free",
]

TUR_SECENEKLERI = ["Tümü", "game", "loot", "beta"]

SIRALAMA_SECENEKLERI = {
    "Tarihe göre (yeni→eski)": "date",
    "Değere göre (pahalı→ucuz)": "value",
    "Popülerliğe göre": "popularity",
}

PLATFORM_ETIKET = { ... }  # (orijinal kodundaki aynı)
TUR_ETIKET = { ... }       # (orijinal kodundaki aynı)

# ─────────────────────────────────────────────
# CSS (değişmedi)
# ─────────────────────────────────────────────
CSS = """ ... """   # (orijinal CSS tamamen aynı, buraya yapıştır)

# ─────────────────────────────────────────────
# GAMERPOWER API
# ─────────────────────────────────────────────
def gp_getir(endpoint: str, params: dict = None) -> dict | list | None:
    try:
        r = requests.get(f"{BASE_URL}/{endpoint}", params=params, timeout=15)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.HTTPError as e:
        if r.status_code == 404:
            return []
        st.error(f"API hatası: {e}")
        return None
    except Exception as e:
        st.error(f"Bağlantı hatası: {e}")
        return None

@st.cache_data(ttl=300)
def worth_getir() -> dict | None:
    return gp_getir("worth")

@st.cache_data(ttl=300)
def ilanlar_getir(platform: str, tur: str, siralama: str) -> list:
    params = {}
    if platform and platform != "Tümü":
        params["platform"] = platform
    if tur and tur != "Tümü":
        params["type"] = tur
    if siralama:
        params["sort-by"] = siralama

    sonuc = gp_getir("giveaways", params)
    return sonuc if isinstance(sonuc, list) else []

# ─────────────────────────────────────────────
# GROQ — TÜRKÇE ÇEVİRİ (değişmedi)
# ─────────────────────────────────────────────
def groq_cevir(metin: str, baslik: str = "") -> str:
    if not metin or not metin.strip():
        return ""

    son_istek = st.session_state.get("son_groq_istegi", 0)
    bekleme = RATE_LIMIT_SANIYE - (time.time() - son_istek)
    if bekleme > 0:
        time.sleep(bekleme)

    try:
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
        yanit = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[ ... ],   # orijinal mesajlar aynı
            temperature=0.2,
            max_tokens=800,
        )
        st.session_state["son_groq_istegi"] = time.time()
        return yanit.choices[0].message.content.strip()
    except Exception as e:
        hata = str(e)
        if "rate_limit" in hata.lower():
            return "⏳ Rate limit — otomatik bekleniyor..."
        return f"(Çeviri hatası: {hata})"

# ─────────────────────────────────────────────
# YARDIMCI FONKSİYONLAR
# ─────────────────────────────────────────────
def worth_to_float(worth) -> float:
    """'$5.99' gibi değerleri güvenli float'a çevirir"""
    if not worth or str(worth).lower() in ("n/a", "0.0", "0", ""):
        return 0.0
    clean = str(worth).replace('$', '').replace(',', '').strip()
    try:
        return float(clean)
    except:
        return 0.0

def platform_etiket(p: str) -> str:
    return PLATFORM_ETIKET.get(p.lower().replace(" ", "-"), f"🎮 {p}")

def tur_etiket(t: str) -> str:
    return TUR_ETIKET.get(t.lower(), f"🎮 {t}")

def bitis_formatla(tarih_str: str) -> str:
    if not tarih_str or tarih_str.lower() == "n/a":
        return ""
    return f"⏰ Bitiş: {tarih_str}"

def deger_formatla(deger: str) -> str:
    if not deger or deger == "0.0" or deger.lower() == "n/a":
        return ""
    try:
        return f"${float(deger):.2f}"
    except Exception:
        return deger

# ─────────────────────────────────────────────
# KART GÖSTER (sadece butonlar değişti)
# ─────────────────────────────────────────────
def ilan_karti_goster(ilan: dict, idx: int):
    # ... (üst kısım tamamen aynı)

    st.markdown(f""" ... """, unsafe_allow_html=True)  # kart HTML aynı

    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        if link:
            st.link_button("🎮 Hemen Al", url=link, width="stretch")

    with col2:
        btn_label = "📄 Açıklamayı Gizle" if aciklama_key in st.session_state else "🌐 Türkçe Açıkla"
        if st.button(btn_label, key=f"btn_{idx}", width="stretch"):
            if aciklama_key in st.session_state:
                st.session_state.pop(aciklama_key)
                st.rerun()
            else:
                with st.spinner("🤖 Türkçeye çevriliyor..."):
                    ceviri = groq_cevir(aciklama_en, baslik)
                    st.session_state[aciklama_key] = ceviri

    with col3:
        favs = st.session_state.setdefault("gp_favoriler", set())
        ilan_id = str(ilan.get("id", ""))
        fav_ikon = "⭐" if ilan_id in favs else "☆"
        if st.button(fav_ikon, key=f"fav_{idx}", width="stretch"):
            if ilan_id in favs:
                favs.discard(ilan_id)
            else:
                favs.add(ilan_id)
            st.rerun()

    if aciklama_key in st.session_state:
        st.markdown(f'<div class="gp-aciklama">{st.session_state[aciklama_key]}</div>', unsafe_allow_html=True)

    st.divider()

# ─────────────────────────────────────────────
# WORTH KUTUSU (değişmedi)
# ─────────────────────────────────────────────
def worth_goster():
    # ... aynı

# ─────────────────────────────────────────────
# SIDEBAR (değişmedi)
# ─────────────────────────────────────────────
def sidebar_filtre() -> dict:
    # ... aynı

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    st.set_page_config(page_title="GamerPower TR — Ücretsiz Oyunlar", page_icon="🎮", layout="wide", initial_sidebar_state="expanded")
    st.markdown(CSS, unsafe_allow_html=True)

    if "son_groq_istegi" not in st.session_state:
        st.session_state["son_groq_istegi"] = 0
    if "gp_favoriler" not in st.session_state:
        st.session_state["gp_favoriler"] = set()

    st.markdown(""" ... """, unsafe_allow_html=True)  # başlık aynı

    worth_goster()

    filtre = sidebar_filtre()

    with st.spinner("🎮 İlanlar yükleniyor..."):
        ilanlar = ilanlar_getir(filtre["platform"], filtre["tur"], filtre["siralama"])

    if filtre["sadece_favori"]:
        favs = st.session_state.get("gp_favoriler", set())
        ilanlar = [d for d in ilanlar if str(d.get("id", "")) in favs]

    # ── İstatistik (burası düzeltildi!)
    col1, col2, col3 = st.columns(3)
    col1.metric("🎮 Toplam Fırsat", len(ilanlar))
    col2.metric(
        "💰 Toplam Değer",
        f"${sum(worth_to_float(d.get('worth')) for d in ilanlar):.0f}",
    )
    col3.metric("⭐ Favoriler", len(st.session_state.get("gp_favoriler", set())))

    st.markdown("---")

    if not ilanlar:
        st.info("Bu filtrelere uygun ilan bulunamadı.")
        return

    # ── İlanları listele
    for i, ilan in enumerate(ilanlar):
        ilan_karti_goster(ilan, i)


if __name__ == "__main__":
    main()