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

PLATFORM_ETIKET = {
    "pc"                  : "🖥️ PC",
    "steam"               : "🟦 Steam",
    "epic-games-store"    : "⚫ Epic",
    "gog"                 : "🟣 GOG",
    "itch.io"             : "🎮 Itch.io",
    "ps4"                 : "🔵 PS4",
    "ps5"                 : "🔵 PS5",
    "xbox-one"            : "🟢 Xbox One",
    "xbox-series-xs"      : "🟢 Xbox Series",
    "switch"              : "🔴 Switch",
    "android"             : "🤖 Android",
    "ios"                 : "🍎 iOS",
    "vr"                  : "👓 VR",
    "battlenet"           : "🔷 Battle.net",
    "ubisoft"             : "🟠 Ubisoft",
    "origin"              : "🟠 Origin",
    "drm-free"            : "🆓 DRM-Free",
    "multiple-platforms"  : "🌐 Çoklu Platform",
}

TUR_ETIKET = {
    "game": "🎮 Oyun",
    "loot": "🎁 Loot",
    "beta": "🧪 Beta",
}

# ─────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;600;700&family=Inter:wght@300;400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

h1, h2, h3 {
    font-family: 'Rajdhani', sans-serif !important;
    letter-spacing: 1px;
}

.gp-kart {
    background: linear-gradient(135deg, #0f1923 0%, #162030 100%);
    border: 1px solid #1e3a52;
    border-radius: 12px;
    overflow: hidden;
    margin-bottom: 12px;
    transition: border-color 0.2s;
}
.gp-kart:hover { border-color: #00c2ff44; }

.gp-kart-ust {
    display: flex;
    gap: 14px;
    padding: 14px;
}

.gp-gorsel {
    width: 110px;
    min-width: 110px;
    height: 65px;
    object-fit: cover;
    border-radius: 6px;
    background: #0a0f16;
}

.gp-bilgi { flex: 1; min-width: 0; }

.gp-baslik {
    font-family: 'Rajdhani', sans-serif;
    font-size: 16px;
    font-weight: 700;
    color: #e8f4ff;
    line-height: 1.2;
    margin-bottom: 5px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.gp-meta {
    font-size: 12px;
    color: #5a7a9a;
    margin-bottom: 6px;
}

.gp-etiketler { display: flex; flex-wrap: wrap; gap: 5px; }

.gp-etiket {
    font-size: 11px;
    font-weight: 500;
    padding: 2px 8px;
    border-radius: 20px;
    background: #0a1a2a;
    border: 1px solid #1e3a52;
    color: #7ab8d8;
}

.gp-etiket-tur {
    background: #0d2010;
    border-color: #1a4020;
    color: #5dba70;
}

.gp-deger {
    font-family: 'Rajdhani', sans-serif;
    font-size: 18px;
    font-weight: 700;
    color: #00c2ff;
    text-align: right;
    white-space: nowrap;
}

.gp-deger-bos { color: #2a4a6a; font-size: 13px; }

.gp-aciklama {
    font-size: 13px;
    color: #7a9ab8;
    line-height: 1.6;
    padding: 10px 14px;
    border-top: 1px solid #1e3a52;
    background: #0a1420;
}

.gp-bitis {
    font-size: 11px;
    color: #e05a5a;
    margin-top: 4px;
}

.worth-kutu {
    background: linear-gradient(135deg, #0a1f0a, #0d2a1a);
    border: 1px solid #1a5030;
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 16px;
    text-align: center;
}

.worth-sayi {
    font-family: 'Rajdhani', sans-serif;
    font-size: 38px;
    font-weight: 700;
    color: #00e676;
    line-height: 1;
}

.worth-alt {
    font-size: 13px;
    color: #4a8a6a;
    margin-top: 4px;
}

.ceviriliyor {
    font-size: 12px;
    color: #4a7a9a;
    font-style: italic;
    padding: 6px 14px 10px;
    background: #0a1420;
}
</style>
"""

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
# GROQ — TÜRKÇE ÇEVİRİ
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
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Sen bir oyun haberleri çevirmenisin. "
                        "Verilen İngilizce metni sade, akıcı Türkçeye çevir. "
                        "Oyun jargonunu koru (örn: loot, beta, DLC). "
                        "Sadece çeviriyi döndür, açıklama ekleme."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Oyun adı: {baslik}\n\nAçıklama:\n{metin[:1500]}",
                },
            ],
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
# KART GÖSTER
# ─────────────────────────────────────────────
def ilan_karti_goster(ilan: dict, idx: int):
    baslik      = ilan.get("title","")
    aciklama_en = ilan.get("description","")
    platform    = ilan.get("platforms","")
    tur         = ilan.get("type","")
    deger       = deger_formatla(str(ilan.get("worth","0")))
    gorsel      = ilan.get("image","")
    link        = ilan.get("open_giveaway_url","") or ilan.get("open_giveaway","")
    bitis       = bitis_formatla(ilan.get("end_date",""))
    aciklama_key = f"aciklama_{idx}"

    platformlar = [p.strip() for p in platform.split(",") if p.strip()]
    etiket_html = "".join(
        f'<span class="gp-etiket">{platform_etiket(p)}</span>'
        for p in platformlar
    )
    if tur:
        etiket_html += f'<span class="gp-etiket gp-etiket-tur">{tur_etiket(tur)}</span>'

    deger_html = (
        f'<div class="gp-deger">{deger}</div>'
        if deger else
        '<div class="gp-deger gp-deger-bos">Ücretsiz</div>'
    )

    gorsel_html = (
        f'<img class="gp-gorsel" src="{gorsel}" alt="">'
        if gorsel else
        '<div class="gp-gorsel"></div>'
    )

    st.markdown(f"""
    <div class="gp-kart">
        <div class="gp-kart-ust">
            {gorsel_html}
            <div class="gp-bilgi">
                <div class="gp-baslik" title="{baslik}">{baslik}</div>
                <div class="gp-etiketler">{etiket_html}</div>
                {f'<div class="gp-bitis">{bitis}</div>' if bitis else ""}
            </div>
            {deger_html}
        </div>
    </div>
    """, unsafe_allow_html=True)

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
        ilan_id = str(ilan.get("id",""))
        fav_ikon = "⭐" if ilan_id in favs else "☆"
        if st.button(fav_ikon, key=f"fav_{idx}", width="stretch"):
            if ilan_id in favs:
                favs.discard(ilan_id)
            else:
                favs.add(ilan_id)
            st.rerun()

    if aciklama_key in st.session_state:
        st.markdown(
            f'<div class="gp-aciklama">{st.session_state[aciklama_key]}</div>',
            unsafe_allow_html=True,
        )

    st.divider()

# ─────────────────────────────────────────────
# WORTH KUTUSU
# ─────────────────────────────────────────────
def worth_goster():
    with st.spinner("📊 Anlık değer hesaplanıyor..."):
        veri = worth_getir()

    if not veri:
        return

    toplam_deger  = veri.get("worth_estimation_usd","?")
    aktif_sayi    = veri.get("active_giveaways_number","?")

    st.markdown(f"""
    <div class="worth-kutu">
        <div class="worth-sayi">${toplam_deger}</div>
        <div class="worth-alt">
            Şu an aktif <b>{aktif_sayi}</b> ücretsiz fırsatın toplam tahmini değeri
        </div>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
def sidebar_filtre() -> dict:
    st.sidebar.markdown("""
    <div style="font-family:'Rajdhani',sans-serif;font-size:22px;font-weight:700;
         color:#00c2ff;letter-spacing:2px;margin-bottom:4px">
    🎮 GAMERPOWER
    </div>
    <div style="font-size:12px;color:#4a7a9a;margin-bottom:16px">
    Ücretsiz Oyun & Loot Takibi
    </div>
    """, unsafe_allow_html=True)

    st.sidebar.markdown("---")
    st.sidebar.subheader("🕹️ Platform")
    platform = st.sidebar.selectbox(
        "Platform:", PLATFORM_SECENEKLERI, key="gp_platform"
    )

    st.sidebar.markdown("---")
    st.sidebar.subheader("🎁 Tür")
    tur = st.sidebar.radio(
        "Tür:", TUR_SECENEKLERI, key="gp_tur"
    )

    st.sidebar.markdown("---")
    st.sidebar.subheader("📊 Sıralama")
    siralama_label = st.sidebar.radio(
        "Sırala:", list(SIRALAMA_SECENEKLERI.keys()), key="gp_siralama"
    )

    st.sidebar.markdown("---")
    sadece_favori = st.sidebar.checkbox(
        f"⭐ Sadece Favoriler ({len(st.session_state.get('gp_favoriler', set()))})",
        key="gp_favori",
    )

    st.sidebar.markdown("---")
    st.sidebar.caption(
        "📡 Kaynak: gamerpower.com\n\n"
        "🤖 Çeviri: Groq llama-3.3-70b\n\n"
        "⏱️ Cache: 5 dakika"
    )

    return {
        "platform"     : platform,
        "tur"          : tur,
        "siralama"     : SIRALAMA_SECENEKLERI[siralama_label],
        "sadece_favori": sadece_favori,
    }

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    st.set_page_config(
        page_title="GamerPower TR — Ücretsiz Oyunlar",
        page_icon="🎮",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(CSS, unsafe_allow_html=True)

    if "son_groq_istegi" not in st.session_state:
        st.session_state["son_groq_istegi"] = 0
    if "gp_favoriler" not in st.session_state:
        st.session_state["gp_favoriler"] = set()

    st.markdown("""
    <h1 style="font-family:'Rajdhani',sans-serif;font-size:36px;font-weight:700;
         color:#e8f4ff;letter-spacing:2px;margin-bottom:4px">
    🎮 ÜCRETSİZ OYUN & LOOT TAKİBİ
    </h1>
    <p style="color:#4a7a9a;font-size:14px;margin-top:0">
    GamerPower — anlık fırsatlar, Groq ile Türkçe açıklamalar
    </p>
    """, unsafe_allow_html=True)

    worth_goster()

    filtre = sidebar_filtre()

    with st.spinner("🎮 İlanlar yükleniyor..."):
        ilanlar = ilanlar_getir(
            filtre["platform"],
            filtre["tur"],
            filtre["siralama"],
        )

    if filtre["sadece_favori"]:
        favs = st.session_state.get("gp_favoriler", set())
        ilanlar = [d for d in ilanlar if str(d.get("id","")) in favs]

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

    for i, ilan in enumerate(ilanlar):
        ilan_karti_goster(ilan, i)


if __name__ == "__main__":
    main()