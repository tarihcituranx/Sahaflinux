import streamlit as st
import requests
import time
import os
import json as _json
from datetime import datetime
import zoneinfo

st.set_page_config(
    page_title="Altin Fiyatlari | Canli",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Streamlit chrome'unu gizle
st.markdown("""
<style>
#MainMenu, header, footer, .stAppDeployButton { display: none !important; }
.block-container { padding: 0 !important; margin: 0 !important; max-width: 100% !important; }
.stApp { background: #070608 !important; }
section[data-testid="stSidebar"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

# ─── SABİTLER ─────────────────────────────────────────────────────────────────
API_URL    = "https://goldprice.today/api.php?data=live"
RATE_FILE  = "/tmp/finans_rate.json"
RATE_LIMIT = 20
RATE_WINDOW = 60

CURRENCIES = {
    "TRY": ("Türk Lirası",      "₺"),
    "USD": ("Amerikan Doları",  "$"),
    "EUR": ("Euro",             "€"),
    "GBP": ("İngiliz Sterlini", "£"),
    "CHF": ("İsviçre Frangı",   "Fr"),
    "SAR": ("Suudi Riyali",     "SR"),
    "AED": ("BAE Dirhemi",      "AED"),
    "JPY": ("Japon Yeni",       "¥"),
    "AUD": ("Avustralya Doları","A$"),
    "CAD": ("Kanada Doları",    "C$"),
    "RUB": ("Rus Rublesi",      "RUB"),
    "CNY": ("Çin Yuanı",        "CNY"),
    "QAR": ("Katar Riyali",     "QAR"),
    "KWD": ("Kuveyt Dinarı",    "KWD"),
    "EGP": ("Mısır Lirası",     "EGP"),
    "PKR": ("Pakistan Rupisi",  "PKR"),
    "INR": ("Hindistan Rupisi", "INR"),
    "BRL": ("Brezilya Reali",   "R$"),
    "NOK": ("Norveç Kronu",     "NOK"),
    "SEK": ("İsveç Kronu",      "SEK"),
}

TICKER_CODES = ["TRY","USD","EUR","GBP","CHF","SAR","AED","JPY","AUD","RUB","INR","CNY","QAR","KWD","EGP","PKR"]


# ─── RATE LIMIT ───────────────────────────────────────────────────────────────
def check_rate() -> bool:
    now = time.time()
    try:
        rl = {}
        if os.path.exists(RATE_FILE):
            with open(RATE_FILE) as f: rl = _json.load(f)
        hits = [t for t in rl.get("hits", []) if now - t < RATE_WINDOW]
        if len(hits) >= RATE_LIMIT: return False
        hits.append(now)
        with open(RATE_FILE, "w") as f: _json.dump({"hits": hits}, f)
        return True
    except: return True


# ─── VERİ ÇEK ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def fetch_prices():
    if not check_rate(): return None
    try:
        r = requests.get(API_URL, timeout=10)
        return r.json()
    except: return {}

def nf(v: float) -> str:
    """Sayı formatla — nokta binlik, virgül ondalık (TR formatı)."""
    if v >= 1_000_000: s = f"{v:,.0f}"
    elif v >= 100:     s = f"{v:,.2f}"
    else:              s = f"{v:,.3f}"
    # Python formatı: 1,234.56 → TR: 1.234,56
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


# ─── HTML SAYFA ŞABLONu ───────────────────────────────────────────────────────
def build_page(data: dict, sel: str) -> str:
    sel_name, sel_sym = CURRENCIES.get(sel, ("", sel))

    gold = data.get(sel, data.get("USD", {}))
    gram_p  = float(gold.get("gram",  0))
    ounce_p = float(gold.get("ounce", 0))
    tola_p  = float(gold.get("tola",  0))

    # Gümüş
    xag_ratio = float(data.get("XAG", {}).get("ounce", 59.4))
    gold_usd  = float(data.get("USD", {}).get("gram", 166.3))
    sel_gram  = gram_p
    conv      = sel_gram / gold_usd if gold_usd > 0 else 1
    silver_gram  = (float(data.get("USD",{}).get("gram",166.3)) / xag_ratio) * conv
    silver_oz    = silver_gram * 31.1035

    # Türk altın tipleri
    half_g     = gram_p * 3.508
    quarter_g  = gram_p * 1.754
    republic_g = gram_p * 7.216

    try:
        tz_tr = zoneinfo.ZoneInfo("Europe/Istanbul")
    except Exception:
        tz_tr = None
    now_tr = datetime.now(tz_tr) if tz_tr else datetime.now()
    now_str = now_tr.strftime("%d.%m.%Y %H:%M") + " (TR)"

    # ── Ticker içeriği
    ticker_items = ""
    for code in TICKER_CODES:
        d  = data.get(code, {})
        gv = float(d.get("gram", 0))
        sym = CURRENCIES.get(code, ("", code))[1]
        if gv > 0:
            ticker_items += f"""
            <span class="ti">
                <span class="ti-code">ALTIN/{code}</span>
                <span class="ti-dot">◆</span>
                <span class="ti-val">{sym}&nbsp;{nf(gv)}/gr</span>
            </span>"""

    # ── Kur tablosu satırları
    rate_rows = ""
    for code, (name, sym) in CURRENCIES.items():
        d  = data.get(code, {})
        gv = float(d.get("gram", 0))
        if gv <= 0: continue
        active = ' style="border-color:rgba(212,168,71,0.7);background:rgba(212,168,71,0.07);"' if code == sel else ""
        rate_rows += f"""
        <div class="rr"{active}>
            <div>
                <div class="rr-code">{code}</div>
                <div class="rr-name">{name}</div>
            </div>
            <div class="rr-right">
                <div class="rr-val">{sym} {nf(gv)}</div>
                <div class="rr-unit">/gram</div>
            </div>
        </div>"""

    # ── TRY özel kartlar
    try_cards = ""
    if sel == "TRY":
        try_cards = f"""
        <div class="section-title">Anlık Altın Fiyatı — Türkiye</div>
        <div class="sub-grid four">
            <div class="hero-card primary">
                <div class="hc-unit">Gram Altın</div>
                <div class="hc-price sm">{sel_sym} {nf(gram_p)}</div>
                <div class="hc-label">1 gram · 24 ayar saf</div>
            </div>
            <div class="hero-card">
                <div class="hc-unit">Yarım Altın</div>
                <div class="hc-price sm">{sel_sym} {nf(half_g)}</div>
                <div class="hc-label">~3.50 gram · 21 ayar</div>
            </div>
            <div class="hero-card">
                <div class="hc-unit">Çeyrek Altın</div>
                <div class="hc-price sm">{sel_sym} {nf(quarter_g)}</div>
                <div class="hc-label">~1.75 gram · 21 ayar</div>
            </div>
            <div class="hero-card">
                <div class="hc-unit">Cumhuriyet Altını</div>
                <div class="hc-price sm">{sel_sym} {nf(republic_g)}</div>
                <div class="hc-label">~7.22 gram · 22 ayar</div>
            </div>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700;900&family=DM+Mono:wght@300;400;500&family=DM+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
:root {{
    --gold: #d4a847; --gold2: #f0c96a; --gold3: #fff1c4;
    --dark: #070608; --dark2: #0e0d10; --dark3: #141318; --dark4: #1c1a22;
    --border: rgba(212,168,71,0.18); --border2: rgba(212,168,71,0.38);
    --muted: rgba(255,255,255,0.35); --green: #4cb97a; --red: #e05050;
    --silver: rgba(180,190,210,0.8);
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html {{ font-size: 16px; }}
body {{
    background: var(--dark);
    color: #e8dfc8;
    font-family: 'DM Sans', sans-serif;
    -webkit-font-smoothing: antialiased;
    overflow-x: hidden;
}}

/* ── TICKER ── */
.ticker-wrap {{
    position: sticky; top: 0; z-index: 100;
    background: linear-gradient(90deg, #0a0800, #181000, #0a0800);
    border-bottom: 1px solid var(--border2);
    height: 36px; overflow: hidden;
    display: flex; align-items: center;
}}
.ticker-track {{
    display: flex; white-space: nowrap;
    animation: scroll-left 60s linear infinite;
}}
.ticker-track:hover {{ animation-play-state: paused; }}
.ti {{
    display: inline-flex; align-items: center; gap: 7px;
    padding: 0 24px; border-right: 1px solid rgba(212,168,71,0.12);
    font-family: 'DM Mono', monospace; font-size: 0.68rem;
}}
.ti-code {{ color: var(--gold); letter-spacing: 0.1em; font-size: 0.62rem; }}
.ti-dot  {{ color: rgba(212,168,71,0.3); font-size: 0.5rem; }}
.ti-val  {{ color: #f0e8d0; }}
@keyframes scroll-left {{
    0%   {{ transform: translateX(0); }}
    100% {{ transform: translateX(-50%); }}
}}

/* ── LAYOUT ── */
.page {{
    max-width: 1100px;
    margin: 0 auto;
    padding: 0 16px 40px;
}}

/* ── HEADER ── */
.header {{
    text-align: center;
    padding: 32px 16px 24px;
}}
.logo {{
    font-family: 'Playfair Display', serif;
    font-size: clamp(1.8rem, 5vw, 3rem);
    font-weight: 900;
    letter-spacing: 0.04em;
    background: linear-gradient(135deg, #8a6010 0%, #d4a847 30%, #f0c96a 50%, #d4a847 70%, #8a6010 100%);
    background-size: 300% 100%;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    animation: gold-sheen 5s ease infinite;
    line-height: 1.1;
}}
.sub {{
    font-family: 'DM Mono', monospace;
    font-size: 0.65rem;
    letter-spacing: 0.3em;
    color: var(--muted);
    text-transform: uppercase;
    margin-top: 8px;
}}
.live-dot {{
    display: inline-block;
    width: 7px; height: 7px; border-radius: 50%;
    background: var(--green);
    box-shadow: 0 0 8px var(--green);
    animation: blink 1.4s ease infinite;
    margin-right: 6px;
    vertical-align: middle;
}}
.divider {{
    width: 70px; height: 1px; margin: 16px auto 0;
    background: linear-gradient(90deg, transparent, var(--gold), transparent);
}}
@keyframes gold-sheen {{
    0%  {{ background-position:0% 50%; }}
    50% {{ background-position:100% 50%; }}
    100%{{ background-position:0% 50%; }}
}}
@keyframes blink {{ 0%,100%{{opacity:1}} 50%{{opacity:0.25}} }}

/* ── SEÇİCİ ── */
.selector-wrap {{
    margin: 20px 0 8px;
}}
.selector-label {{
    font-family: 'DM Mono', monospace;
    font-size: 0.6rem; letter-spacing: 0.3em;
    color: var(--gold); text-transform: uppercase;
    margin-bottom: 8px;
}}
.selector {{
    width: 100%;
    background: var(--dark4);
    border: 1px solid var(--border2);
    border-radius: 10px;
    color: #e8dfc8;
    font-family: 'DM Mono', monospace;
    font-size: 0.85rem;
    padding: 10px 14px;
    outline: none;
    -webkit-appearance: none;
    cursor: pointer;
}}
.selector:focus {{ border-color: var(--gold); }}
.selector option {{ background: #141318; }}

/* ── BÖLÜM BAŞLIĞI ── */
.section-title {{
    font-family: 'DM Mono', monospace;
    font-size: 0.6rem; letter-spacing: 0.3em;
    color: var(--gold); text-transform: uppercase;
    margin: 24px 0 12px;
}}

/* ── HERO GRID ── */
.hero-grid {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
    margin-top: 20px;
}}
@media (max-width: 600px) {{
    .hero-grid {{ grid-template-columns: 1fr; gap: 10px; }}
    .sub-grid  {{ grid-template-columns: 1fr !important; }}
}}
@media (min-width: 601px) and (max-width: 850px) {{
    .hero-grid {{ grid-template-columns: repeat(2, 1fr); }}
}}

/* ── KARTLAR ── */
.hero-card {{
    background: var(--dark4);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 22px 18px;
    position: relative;
    overflow: hidden;
    transition: border-color 0.25s, box-shadow 0.25s;
}}
.hero-card:hover {{
    border-color: var(--border2);
    box-shadow: 0 0 30px rgba(212,168,71,0.09);
}}
.hero-card.primary {{
    background: linear-gradient(145deg, #100d06, #1a1508);
    border-color: rgba(212,168,71,0.45);
    box-shadow: 0 0 50px rgba(212,168,71,0.07);
}}
.hero-card::after {{
    content: '';
    position: absolute; bottom: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, transparent, var(--gold), transparent);
    opacity: 0.35;
}}
.hc-unit {{
    font-family: 'DM Mono', monospace;
    font-size: 0.6rem; letter-spacing: 0.25em;
    color: var(--gold); text-transform: uppercase; margin-bottom: 10px;
}}
.hc-price {{
    font-family: 'Playfair Display', serif;
    font-weight: 700;
    font-size: clamp(1.5rem, 3vw, 2.2rem);
    color: #f0e8d0; line-height: 1.1;
    word-break: break-all;
}}
.hc-price.big {{
    font-size: clamp(1.8rem, 4vw, 2.8rem);
}}
.hc-price.sm {{
    font-size: clamp(1.3rem, 2.5vw, 1.8rem);
}}
.hc-label {{
    font-size: 0.68rem; color: var(--muted); margin-top: 6px;
}}

/* ── SUB GRID (TRY) ── */
.sub-grid {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 10px;
    margin-bottom: 4px;
}}

/* ── SILVER BAND ── */
.silver-card {{
    background: linear-gradient(135deg, rgba(160,175,195,0.06), rgba(90,100,115,0.04));
    border: 1px solid rgba(180,190,210,0.14);
    border-radius: 12px;
    padding: 16px 20px;
    display: flex; flex-wrap: wrap; gap: 16px; align-items: center;
    margin-top: 4px;
}}
.sc-item {{ display: flex; flex-direction: column; gap: 3px; }}
.sc-label {{ font-family: 'DM Mono', monospace; font-size: 0.58rem; letter-spacing: 0.25em; color: rgba(180,190,210,0.5); text-transform: uppercase; }}
.sc-val   {{ font-family: 'Playfair Display', serif; font-size: 1.15rem; font-weight: 700; color: var(--silver); }}

/* ── 4'lü sub-grid ── */
.sub-grid.four {{
    grid-template-columns: repeat(4, 1fr);
}}
@media (max-width: 700px) {{
    .sub-grid.four {{ grid-template-columns: repeat(2, 1fr); }}
}}
@media (max-width: 380px) {{
    .sub-grid.four {{ grid-template-columns: 1fr; }}
}}

/* ── OKUNABİLİRLİK İYİLEŞTİRMELERİ ── */
body {{
    background: var(--dark);
    color: #f0e8d4;
    font-family: 'DM Sans', sans-serif;
    -webkit-font-smoothing: antialiased;
    overflow-x: hidden;
    line-height: 1.5;
}}
.hc-unit {{
    font-family: 'DM Mono', monospace;
    font-size: 0.65rem; letter-spacing: 0.2em;
    color: #c8a050; text-transform: uppercase; margin-bottom: 10px;
    font-weight: 500;
}}
.hc-price {{
    font-family: 'Playfair Display', serif;
    font-weight: 700;
    font-size: clamp(1.5rem, 3vw, 2.2rem);
    color: #fff8ee; line-height: 1.15;
    word-break: break-all;
    text-shadow: 0 1px 4px rgba(0,0,0,0.4);
}}
.hc-price.big {{
    font-size: clamp(1.8rem, 4vw, 2.8rem);
}}
.hc-price.sm {{
    font-size: clamp(1.2rem, 2.5vw, 1.7rem);
}}
.hc-label {{
    font-size: 0.72rem; color: rgba(255,255,255,0.5); margin-top: 6px;
    font-weight: 400; letter-spacing: 0.02em;
}}
.section-title {{
    font-family: 'DM Mono', monospace;
    font-size: 0.62rem; letter-spacing: 0.28em;
    color: #c8a050; text-transform: uppercase;
    margin: 24px 0 12px;
    font-weight: 500;
    opacity: 0.9;
}}
.rr-code {{ font-family: 'DM Mono', monospace; font-size: 0.72rem; color: #c8a050; letter-spacing: 0.12em; font-weight: 600; }}
.rr-name {{ font-size: 0.65rem; color: rgba(255,255,255,0.45); margin-top: 2px; }}
.rr-val  {{ font-family: 'DM Mono', monospace; font-size: 0.88rem; color: #f0e8d4; font-weight: 500; }}
.rr-unit {{ font-size: 0.6rem; color: rgba(255,255,255,0.3); margin-top: 2px; }}
.ti-code {{ color: #c8a050; letter-spacing: 0.1em; font-size: 0.63rem; font-weight: 500; }}
.ti-val  {{ color: #f0e8d0; font-size: 0.7rem; }}
.sc-label {{ font-family: 'DM Mono', monospace; font-size: 0.6rem; letter-spacing: 0.22em; color: rgba(180,195,215,0.6); text-transform: uppercase; }}
.sc-val   {{ font-family: 'Playfair Display', serif; font-size: 1.2rem; font-weight: 700; color: rgba(210,225,240,0.95); }}
.logo {{
    font-family: 'Playfair Display', serif;
    font-size: clamp(1.8rem, 5vw, 3rem);
    font-weight: 900;
    letter-spacing: 0.04em;
    background: linear-gradient(135deg, #8a6010 0%, #d4a847 30%, #f0c96a 50%, #d4a847 70%, #8a6010 100%);
    background-size: 300% 100%;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    animation: gold-sheen 5s ease infinite;
    line-height: 1.1;
}}
.sub {{
    font-family: 'DM Mono', monospace;
    font-size: 0.67rem;
    letter-spacing: 0.25em;
    color: rgba(255,255,255,0.45);
    text-transform: uppercase;
    margin-top: 8px;
}}
.footer {{
    text-align: center; padding: 20px 16px;
    font-family: 'DM Mono', monospace; font-size: 0.6rem;
    color: rgba(200,160,80,0.35); letter-spacing: 0.18em;
    border-top: 1px solid var(--border);
    margin-top: 32px;
}}
.sc-sep   {{ color: rgba(180,190,210,0.15); font-size: 1.4rem; align-self: center; }}

/* ── KUR TABLOSU ── */
.rate-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 8px;
    margin-top: 4px;
}}
@media (max-width: 480px) {{
    .rate-grid {{ grid-template-columns: repeat(2, 1fr); gap: 6px; }}
}}
.rr {{
    background: var(--dark4);
    border: 1px solid var(--border);
    border-radius: 9px; padding: 12px 14px;
    display: flex; justify-content: space-between; align-items: center;
    transition: all 0.2s; cursor: default;
}}
.rr:hover {{ border-color: var(--border2); background: var(--dark3); }}
.rr-code {{ font-family: 'DM Mono', monospace; font-size: 0.7rem; color: var(--gold); letter-spacing: 0.12em; }}
.rr-name {{ font-size: 0.62rem; color: var(--muted); margin-top: 2px; }}
.rr-right {{ text-align: right; }}
.rr-val  {{ font-family: 'DM Mono', monospace; font-size: 0.85rem; color: #e8dfc8; font-weight: 500; }}
.rr-unit {{ font-size: 0.58rem; color: var(--muted); margin-top: 1px; }}

/* ── FOOTER ── */
.footer {{
    text-align: center; padding: 20px 16px;
    font-family: 'DM Mono', monospace; font-size: 0.58rem;
    color: rgba(212,168,71,0.3); letter-spacing: 0.2em;
    border-top: 1px solid var(--border);
    margin-top: 32px;
}}
</style>
</head>
<body>

<!-- TICKER -->
<div class="ticker-wrap">
  <div class="ticker-track">
    {ticker_items}
    {ticker_items}
  </div>
</div>

<!-- SAYFA -->
<div class="page">

  <!-- BAŞLIK -->
  <div class="header">
    <div class="logo">ALTIN BORSASI</div>
    <div class="sub">
      <span class="live-dot"></span>
      Canlı Fiyatlar &nbsp;·&nbsp; {now_str}
    </div>
    <div class="divider"></div>
  </div>

  <!-- PARA BİRİMİ SEÇİCİ -->
  <div class="selector-wrap">
    <div class="selector-label">Para Birimi Seç</div>
    <select class="selector" onchange="setCurrency(this.value)">
      {build_options(sel)}
    </select>
  </div>

  <!-- TRY ÖZEL KARTLAR (üstte) -->
  {try_cards}

  <!-- HERO KARTLAR -->
  <div class="section-title">Uluslararası Birimler</div>
  <div class="hero-grid">
    <div class="hero-card primary">
      <div class="hc-unit">Gram Altın</div>
      <div class="hc-price big">{sel_sym} {nf(gram_p)}</div>
      <div class="hc-label">{sel_name} / Gram</div>
    </div>
    <div class="hero-card">
      <div class="hc-unit">Ons Altın</div>
      <div class="hc-price">{sel_sym} {nf(ounce_p)}</div>
      <div class="hc-label">{sel_name} / Troy Ons (31.10 gr)</div>
    </div>
    <div class="hero-card">
      <div class="hc-unit">Tola Altın</div>
      <div class="hc-price">{sel_sym} {nf(tola_p)}</div>
      <div class="hc-label">{sel_name} / Tola (11.66 gr)</div>
    </div>
  </div>

  <!-- GÜMÜŞ -->
  <div class="section-title">Gümüş</div>
  <div class="silver-card">
    <div class="sc-item">
      <div class="sc-label">Gram Gümüş</div>
      <div class="sc-val">{sel_sym} {nf(silver_gram)}</div>
    </div>
    <div class="sc-sep">|</div>
    <div class="sc-item">
      <div class="sc-label">Ons Gümüş</div>
      <div class="sc-val">{sel_sym} {nf(silver_oz)}</div>
    </div>
    <div class="sc-sep">|</div>
    <div class="sc-item">
      <div class="sc-label">Altın/Gümüş Oranı</div>
      <div class="sc-val">{xag_ratio:.1f} : 1</div>
    </div>
  </div>

  <!-- KUR TABLOSU -->
  <div class="section-title">Dünya Para Birimlerinde Gram Altın</div>
  <div class="rate-grid">
    {rate_rows}
  </div>

  <!-- FOOTER -->
  <div class="footer">
    ◆ &nbsp; Kaynak: goldprice.today &nbsp; ◆ &nbsp; {now_str} &nbsp; ◆ &nbsp; Her 60 saniyede güncellenir &nbsp; ◆
  </div>

</div>

<script>
function setCurrency(val) {{
    // Streamlit ile iletişim — query param üzerinden
    const url = new URL(window.location.href);
    // Parent frame'e mesaj gönder
    window.parent.postMessage({{type: 'streamlit:setComponentValue', value: val}}, '*');
}}
</script>

</body>
</html>"""


def build_options(sel: str) -> str:
    opts = ""
    for code, (name, sym) in CURRENCIES.items():
        selected = "selected" if code == sel else ""
        opts += f'<option value="{code}" {selected}>{code} — {name} ({sym})</option>\n'
    return opts


# ─── ANA UYGULAMA ─────────────────────────────────────────────────────────────

# Para birimi seçimi — query params üzerinden
if "currency" not in st.session_state:
    st.session_state["currency"] = "TRY"

# Veri çek
data = fetch_prices()

if data is None:
    st.components.v1.html("""
    <html><body style="background:#070608;display:flex;justify-content:center;align-items:center;height:100vh;flex-direction:column;font-family:monospace;">
    <div style="color:#d4a847;font-size:1.5rem;margin-bottom:12px;">⏳</div>
    <div style="color:#d4a847;font-size:0.8rem;letter-spacing:0.2em;">RATE LIMIT</div>
    <div style="color:rgba(255,255,255,0.3);font-size:0.7rem;margin-top:8px;">1 dakika sonra tekrar deneyin</div>
    </body></html>""", height=300)
    st.stop()

if not data:
    st.error("API bağlantısı kurulamadı.")
    st.stop()

# Para birimi seçici (streamlit native — değişimi yakala)
_, col, _ = st.columns([0.5, 3, 0.5])
with col:
    cur_list = list(CURRENCIES.keys())
    idx = cur_list.index(st.session_state["currency"]) if st.session_state["currency"] in cur_list else 0
    chosen = st.selectbox(
        "Para Birimi",
        options=cur_list,
        format_func=lambda c: f"{c}  —  {CURRENCIES[c][0]}  ({CURRENCIES[c][1]})",
        index=idx,
        key="cur_selector",
        label_visibility="collapsed",
    )
    if chosen != st.session_state["currency"]:
        st.session_state["currency"] = chosen
        st.rerun()

# Tüm sayfayı HTML olarak render et
html = build_page(data, st.session_state["currency"])
st.components.v1.html(html, height=2400, scrolling=True)

# 60s'de otomatik güncelle
time.sleep(60)
st.cache_data.clear()
st.rerun()
