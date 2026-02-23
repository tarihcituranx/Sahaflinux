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
API_URL     = "https://goldprice.today/api.php?data=live"
RATE_FILE   = "/tmp/finans_rate.json"
RATE_LIMIT  = 20
RATE_WINDOW = 60

CURRENCIES = {
    "TRY": ("Türk Lirası",       "₺"),
    "USD": ("Amerikan Doları",   "$"),
    "EUR": ("Euro",              "€"),
    "GBP": ("İngiliz Sterlini",  "£"),
    "CHF": ("İsviçre Frangı",    "Fr"),
    "SAR": ("Suudi Riyali",      "SR"),
    "AED": ("BAE Dirhemi",       "AED"),
    "JPY": ("Japon Yeni",        "¥"),
    "AUD": ("Avustralya Doları", "A$"),
    "CAD": ("Kanada Doları",     "C$"),
    "RUB": ("Rus Rublesi",       "₽"),
    "CNY": ("Çin Yuanı",         "¥CN"),
    "QAR": ("Katar Riyali",      "QAR"),
    "KWD": ("Kuveyt Dinarı",     "KD"),
    "EGP": ("Mısır Lirası",      "E£"),
    "PKR": ("Pakistan Rupisi",   "₨"),
    "INR": ("Hindistan Rupisi",  "₹"),
    "BRL": ("Brezilya Reali",    "R$"),
    "NOK": ("Norveç Kronu",      "kr"),
    "SEK": ("İsveç Kronu",       "kr"),
}

TICKER_CODES = [
    "TRY", "USD", "EUR", "GBP", "CHF",
    "SAR", "AED", "JPY", "AUD", "RUB",
    "INR", "CNY", "QAR", "KWD", "EGP", "PKR",
]


# ─── RATE LIMIT ───────────────────────────────────────────────────────────────
def check_rate() -> bool:
    now = time.time()
    try:
        rl = {}
        if os.path.exists(RATE_FILE):
            with open(RATE_FILE) as f:
                rl = _json.load(f)
        hits = [t for t in rl.get("hits", []) if now - t < RATE_WINDOW]
        if len(hits) >= RATE_LIMIT:
            return False
        hits.append(now)
        with open(RATE_FILE, "w") as f:
            _json.dump({"hits": hits}, f)
        return True
    except:
        return True


# ─── VERİ ÇEK ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def fetch_prices():
    if not check_rate():
        return None
    try:
        r = requests.get(API_URL, timeout=10)
        return r.json()
    except:
        return {}


def nf(v: float) -> str:
    """Sayı formatla — nokta binlik, virgül ondalık (TR formatı)."""
    if v >= 1_000_000:
        s = f"{v:,.0f}"
    elif v >= 100:
        s = f"{v:,.2f}"
    else:
        s = f"{v:,.3f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


# ─── HTML SAYFA ŞABLONU ────────────────────────────────────────────────────────
def build_page(data: dict, sel: str, prev_data: dict = None) -> str:
    sel_name, sel_sym = CURRENCIES.get(sel, ("", sel))

    gold    = data.get(sel, data.get("USD", {}))
    gram_p  = float(gold.get("gram",  0))
    ounce_p = float(gold.get("ounce", 0))
    tola_p  = float(gold.get("tola",  0))

    # ── Gümüş
    xag_ratio = float(data.get("XAG", {}).get("ounce", 59.4))
    gold_usd  = float(data.get("USD", {}).get("gram",  166.3))
    conv      = (gram_p / gold_usd) if gold_usd > 0 else 1
    silver_gram = (gold_usd / max(xag_ratio, 0.001)) * conv
    silver_oz   = silver_gram * 31.1035

    # ── Türk altın tipleri (22 ayar ziynet)
    # API 24 ayar saf altın gram fiyatı veriyor.
    # Fiyat = gram_p (saf fiyat/gr) × toplam_ağırlık × (22/24)
    AYAR22     = 22 / 24
    quarter_g  = gram_p * 1.754  * AYAR22  # Çeyrek:      1,754 gr toplam  → 1,608 gr has
    half_g     = gram_p * 3.508  * AYAR22  # Yarım:       3,508 gr toplam  → 3,216 gr has
    full_g     = gram_p * 7.016  * AYAR22  # Tam:         7,016 gr toplam  → 6,431 gr has
    republic_g = gram_p * 7.216  * AYAR22  # Cumhuriyet:  7,216 gr toplam  → 6,615 gr has

    # ── Önceki fiyatlar
    prev_data = prev_data or {}
    prev_gold       = prev_data.get(sel, prev_data.get("USD", {}))
    prev_gram_p     = float(prev_gold.get("gram",  0))
    prev_ounce_p    = float(prev_gold.get("ounce", 0))
    prev_tola_p     = float(prev_gold.get("tola",  0))
    prev_quarter_g  = prev_gram_p * 1.754  * AYAR22
    prev_half_g     = prev_gram_p * 3.508  * AYAR22
    prev_full_g     = prev_gram_p * 7.016  * AYAR22
    prev_republic_g = prev_gram_p * 7.216  * AYAR22
    _prev_usd_gram  = float(prev_data.get("USD", {}).get("gram", 0))
    _prev_xag       = float(prev_data.get("XAG", {}).get("ounce", 59.4))
    prev_silver_g   = (
        (_prev_usd_gram / max(_prev_xag, 0.001)) *
        (prev_gram_p / max(_prev_usd_gram, 0.001))
    ) if (_prev_usd_gram > 0 and prev_gram_p > 0) else 0

    def chg(curr: float, prev: float) -> str:
        if prev <= 0 or curr <= 0 or abs(curr - prev) < 0.0001:
            return ""
        diff  = curr - prev
        pct   = diff / prev * 100
        arrow = "&#9650;" if diff > 0 else "&#9660;"
        col   = "#4cb97a" if diff > 0 else "#e05050"
        bg    = "rgba(76,185,122,0.13)"  if diff > 0 else "rgba(224,80,80,0.13)"
        brd   = "rgba(76,185,122,0.3)"   if diff > 0 else "rgba(224,80,80,0.3)"
        pct_s = f"{abs(pct):.2f}".replace(".", ",")
        dif_s = nf(abs(diff))
        return (
            f'<span class="badge" style="color:{col};background:{bg};'
            f'border:1px solid {brd};">{arrow} {dif_s} ({pct_s}%)</span>'
        )

    try:
        tz_tr = zoneinfo.ZoneInfo("Europe/Istanbul")
    except Exception:
        tz_tr = None
    now_tr  = datetime.now(tz_tr) if tz_tr else datetime.now()
    now_str = now_tr.strftime("%d.%m.%Y %H:%M") + " (TR)"

    # ── Ticker
    ticker_items = ""
    for code in TICKER_CODES:
        d   = data.get(code, {})
        gv  = float(d.get("gram", 0))
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
        if gv <= 0:
            continue
        prev_gv = float(prev_data.get(code, {}).get("gram", 0))
        active  = ' style="border-color:rgba(212,168,71,0.7);background:rgba(212,168,71,0.07);"' if code == sel else ""
        rate_rows += f"""
        <div class="rr"{active}>
            <div>
                <div class="rr-code">{code}</div>
                <div class="rr-name">{name}</div>
            </div>
            <div class="rr-right">
                <div class="rr-val">{sym} {nf(gv)}</div>
                <div class="rr-unit">/gram</div>
                <div class="rr-change">{chg(gv, prev_gv)}</div>
            </div>
        </div>"""

    # ── TRY özel kartlar
    try_cards = ""
    if sel == "TRY":
        try_cards = f"""
        <div class="section-title">Anlık Altın Fiyatı — Türkiye</div>
        <div class="sub-grid four">
            <div class="hero-card">
                <div class="hc-unit">Çeyrek Altın</div>
                <div class="hc-price sm">{sel_sym} {nf(quarter_g)}</div>
                <div class="hc-label">1,754 gr toplam · 22 ayar · 1,608 gr has</div>
                <div class="hc-change">{chg(quarter_g, prev_quarter_g)}</div>
            </div>
            <div class="hero-card">
                <div class="hc-unit">Yarım Altın</div>
                <div class="hc-price sm">{sel_sym} {nf(half_g)}</div>
                <div class="hc-label">3,508 gr toplam · 22 ayar · 3,216 gr has</div>
                <div class="hc-change">{chg(half_g, prev_half_g)}</div>
            </div>
            <div class="hero-card primary">
                <div class="hc-unit">Tam Altın</div>
                <div class="hc-price sm">{sel_sym} {nf(full_g)}</div>
                <div class="hc-label">7,016 gr toplam · 22 ayar · 6,431 gr has</div>
                <div class="hc-change">{chg(full_g, prev_full_g)}</div>
            </div>
            <div class="hero-card">
                <div class="hc-unit">Cumhuriyet Altını</div>
                <div class="hc-price sm">{sel_sym} {nf(republic_g)}</div>
                <div class="hc-label">7,216 gr toplam · 22 ayar · 6,615 gr has</div>
                <div class="hc-change">{chg(republic_g, prev_republic_g)}</div>
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
    --muted: rgba(255,255,255,0.4); --green: #4cb97a; --red: #e05050;
    --silver: rgba(200,218,235,0.92);
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html {{ font-size: 16px; }}
body {{
    background: var(--dark);
    color: #f0e8d4;
    font-family: 'DM Sans', sans-serif;
    -webkit-font-smoothing: antialiased;
    overflow-x: hidden;
    line-height: 1.5;
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
.ti-code {{ color: #c8a050; letter-spacing: 0.1em; font-size: 0.63rem; font-weight: 500; }}
.ti-dot  {{ color: rgba(212,168,71,0.3); font-size: 0.5rem; }}
.ti-val  {{ color: #f0e8d0; font-size: 0.7rem; }}
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
    font-size: 0.67rem;
    letter-spacing: 0.25em;
    color: rgba(255,255,255,0.45);
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
    0%  {{ background-position: 0% 50%; }}
    50% {{ background-position: 100% 50%; }}
    100%{{ background-position: 0% 50%; }}
}}
@keyframes blink {{ 0%,100%{{opacity:1}} 50%{{opacity:0.25}} }}

/* ── SEÇİCİ ── */
.selector-wrap {{ margin: 20px 0 8px; }}
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
    font-size: 0.62rem; letter-spacing: 0.28em;
    color: #c8a050; text-transform: uppercase;
    margin: 24px 0 12px;
    font-weight: 500; opacity: 0.9;
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
.badge {{
    display: inline-flex; align-items: center; gap: 3px;
    font-family: 'DM Mono', monospace;
    font-size: 0.63rem; font-weight: 600;
    padding: 3px 8px; border-radius: 20px;
    margin-top: 6px; letter-spacing: 0.02em;
    white-space: nowrap; line-height: 1;
}}
.hc-change {{ margin-top: 4px; min-height: 24px; }}
.rr-change .badge {{ font-size: 0.57rem; padding: 2px 5px; margin-top: 2px; }}
.hc-unit {{
    font-family: 'DM Mono', monospace;
    font-size: 0.65rem; letter-spacing: 0.2em;
    color: #c8a050; text-transform: uppercase;
    margin-bottom: 10px; font-weight: 500;
}}
.hc-price {{
    font-family: 'Playfair Display', serif;
    font-weight: 700;
    font-size: clamp(1.5rem, 3vw, 2.2rem);
    color: #fff8ee; line-height: 1.15;
    word-break: break-all;
    text-shadow: 0 1px 4px rgba(0,0,0,0.4);
}}
.hc-price.big {{ font-size: clamp(1.8rem, 4vw, 2.8rem); }}
.hc-price.sm  {{ font-size: clamp(1.2rem, 2.5vw, 1.7rem); }}
.hc-label {{
    font-size: 0.72rem; color: rgba(255,255,255,0.5);
    margin-top: 6px; font-weight: 400; letter-spacing: 0.02em;
}}

/* ── SUB GRID (TRY) ── */
.sub-grid {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 10px;
    margin-bottom: 4px;
}}
.sub-grid.four {{ grid-template-columns: repeat(4, 1fr); }}
@media (max-width: 700px) {{
    .sub-grid.four {{ grid-template-columns: repeat(2, 1fr); }}
}}
@media (max-width: 380px) {{
    .sub-grid.four {{ grid-template-columns: 1fr; }}
}}

/* ── GÜMÜŞ BANDI ── */
.silver-card {{
    background: linear-gradient(135deg, rgba(160,175,195,0.06), rgba(90,100,115,0.04));
    border: 1px solid rgba(180,190,210,0.14);
    border-radius: 12px;
    padding: 16px 20px;
    display: flex; flex-wrap: wrap; gap: 16px; align-items: center;
    margin-top: 4px;
}}
.sc-item {{ display: flex; flex-direction: column; gap: 3px; }}
.sc-label {{
    font-family: 'DM Mono', monospace; font-size: 0.6rem;
    letter-spacing: 0.22em; color: rgba(180,195,215,0.6); text-transform: uppercase;
}}
.sc-val {{
    font-family: 'Playfair Display', serif;
    font-size: 1.2rem; font-weight: 700; color: var(--silver);
}}
.sc-sep {{ color: rgba(180,190,210,0.15); font-size: 1.4rem; align-self: center; }}

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
.rr-code  {{ font-family: 'DM Mono', monospace; font-size: 0.72rem; color: #c8a050; letter-spacing: 0.12em; font-weight: 600; }}
.rr-name  {{ font-size: 0.65rem; color: rgba(255,255,255,0.45); margin-top: 2px; }}
.rr-right {{ text-align: right; }}
.rr-val   {{ font-family: 'DM Mono', monospace; font-size: 0.88rem; color: #f0e8d4; font-weight: 500; }}
.rr-unit  {{ font-size: 0.6rem; color: rgba(255,255,255,0.3); margin-top: 1px; }}

/* ── FOOTER ── */
.footer {{
    text-align: center; padding: 20px 16px;
    font-family: 'DM Mono', monospace; font-size: 0.6rem;
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

<!-- CANLI SAAT + COUNTDOWN BAR -->
<div id="clockbar" style="
    background: linear-gradient(90deg,#0a0800,#100e00,#0a0800);
    border-bottom: 1px solid rgba(212,168,71,0.12);
    padding: 6px 20px;
    display: flex; align-items: center; justify-content: space-between;
    flex-wrap: wrap; gap: 8px;
    font-family: 'DM Mono', monospace; font-size: 0.68rem;
">
    <div style="display:flex;align-items:center;gap:16px;">
        <span style="color:rgba(212,168,71,0.5);letter-spacing:0.15em;font-size:0.58rem;">TR SAATİ</span>
        <span id="clock-time" style="color:#f0e8d0;letter-spacing:0.08em;font-size:0.82rem;font-weight:500;">--:--:--</span>
        <span id="clock-date" style="color:rgba(255,255,255,0.3);font-size:0.62rem;"></span>
    </div>
    <div style="display:flex;align-items:center;gap:10px;">
        <span id="update-label" style="color:rgba(212,168,71,0.5);font-size:0.6rem;letter-spacing:0.12em;"></span>
        <div style="width:120px;height:4px;background:rgba(255,255,255,0.06);border-radius:4px;overflow:hidden;">
            <div id="countdown-bar" style="height:100%;background:linear-gradient(90deg,#d4a847,#f0c96a);border-radius:4px;transition:width 1s linear;width:100%;"></div>
        </div>
        <span id="countdown-sec" style="color:#d4a847;font-size:0.7rem;min-width:28px;text-align:right;"></span>
    </div>
</div>

<!-- BİLDİRİM -->
<div id="notif" style="
    display:none; position:fixed; top:74px; right:16px; z-index:999;
    background:rgba(76,185,122,0.15); border:1px solid rgba(76,185,122,0.4);
    border-radius:10px; padding:10px 18px;
    font-family:'DM Mono',monospace; font-size:0.72rem;
    color:#4cb97a; letter-spacing:0.1em;
    box-shadow:0 4px 20px rgba(0,0,0,0.4);
    animation: fadeIn 0.3s ease;
">✓ &nbsp;VERİ GÜNCELLENDİ</div>

<style>
@keyframes fadeIn {{ from{{opacity:0;transform:translateY(-8px)}} to{{opacity:1;transform:translateY(0)}} }}
</style>

<script>
(function() {{
    var REFRESH_SEC = 60;
    var loadTime = Date.now();
    var firstLoad = !sessionStorage.getItem('finans_loaded');
    if (!firstLoad) {{
        var n = document.getElementById('notif');
        if (n) {{
            n.style.display = 'block';
            setTimeout(function(){{ n.style.display='none'; }}, 3500);
        }}
    }}
    sessionStorage.setItem('finans_loaded', '1');

    function tick() {{
        var now = new Date();
        var tr = new Intl.DateTimeFormat('tr-TR', {{
            timeZone: 'Europe/Istanbul',
            hour: '2-digit', minute: '2-digit', second: '2-digit',
            hour12: false
        }}).format(now);
        var trDate = new Intl.DateTimeFormat('tr-TR', {{
            timeZone: 'Europe/Istanbul',
            day: '2-digit', month: '2-digit', year: 'numeric', weekday: 'short'
        }}).format(now);

        var ct = document.getElementById('clock-time');
        var cd = document.getElementById('clock-date');
        if (ct) ct.textContent = tr;
        if (cd) cd.textContent = trDate;

        var elapsed = Math.floor((Date.now() - loadTime) / 1000);
        var rem = Math.max(0, REFRESH_SEC - (elapsed % REFRESH_SEC));
        var pct = (rem / REFRESH_SEC) * 100;

        var bar = document.getElementById('countdown-bar');
        var sec = document.getElementById('countdown-sec');
        var lbl = document.getElementById('update-label');
        if (bar) {{
            bar.style.width = pct + '%';
            bar.style.background = rem < 10
                ? 'linear-gradient(90deg,#e05050,#ff8080)'
                : 'linear-gradient(90deg,#d4a847,#f0c96a)';
        }}
        if (sec) sec.textContent = rem + 's';
        if (lbl) lbl.textContent = rem === 0 ? 'GÜNCELLENİYOR...' : 'SONRA GÜNCELLENİR';
    }}

    tick();
    setInterval(tick, 1000);
}})();
</script>

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

  <!-- PARA BİRİMİ SEÇİCİ (HTML — görsel amaçlı) -->
  <div class="selector-wrap">
    <div class="selector-label">Para Birimi Seç</div>
    <select class="selector" onchange="setCurrency(this.value)">
      {build_options(sel)}
    </select>
  </div>

  <!-- TRY ÖZEL KARTLAR -->
  {try_cards}

  <!-- HERO KARTLAR -->
  <div class="section-title">Uluslararası Birimler</div>
  <div class="hero-grid">
    <div class="hero-card primary">
      <div class="hc-unit">Gram Altın</div>
      <div class="hc-price big">{sel_sym} {nf(gram_p)}</div>
      <div class="hc-label">{sel_name} / Gram</div>
      <div class="hc-change">{chg(gram_p, prev_gram_p)}</div>
    </div>
    <div class="hero-card">
      <div class="hc-unit">Ons Altın</div>
      <div class="hc-price">{sel_sym} {nf(ounce_p)}</div>
      <div class="hc-label">{sel_name} / Troy Ons (31,10 gr)</div>
      <div class="hc-change">{chg(ounce_p, prev_ounce_p)}</div>
    </div>
    <div class="hero-card">
      <div class="hc-unit">Tola Altın</div>
      <div class="hc-price">{sel_sym} {nf(tola_p)}</div>
      <div class="hc-label">{sel_name} / Tola (11,66 gr)</div>
      <div class="hc-change">{chg(tola_p, prev_tola_p)}</div>
    </div>
  </div>

  <!-- GÜMÜŞ -->
  <div class="section-title">Gümüş</div>
  <div class="silver-card">
    <div class="sc-item">
      <div class="sc-label">Gram Gümüş</div>
      <div class="sc-val">{sel_sym} {nf(silver_gram)}</div>
      <div class="rr-change">{chg(silver_gram, prev_silver_g)}</div>
    </div>
    <div class="sc-sep">|</div>
    <div class="sc-item">
      <div class="sc-label">Ons Gümüş</div>
      <div class="sc-val">{sel_sym} {nf(silver_oz)}</div>
    </div>
    <div class="sc-sep">|</div>
    <div class="sc-item">
      <div class="sc-label">Altın / Gümüş Oranı</div>
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
    // Streamlit selectbox ile senkronize etmek için parent frame'e mesaj gönder
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

if "currency" not in st.session_state:
    st.session_state["currency"] = "TRY"
if "prev_data" not in st.session_state:
    st.session_state["prev_data"] = {}

# Veri çek
data = fetch_prices()

if data is None:
    st.components.v1.html("""
    <html><body style="background:#070608;display:flex;justify-content:center;
    align-items:center;height:100vh;flex-direction:column;font-family:monospace;">
    <div style="color:#d4a847;font-size:1.5rem;margin-bottom:12px;">⏳</div>
    <div style="color:#d4a847;font-size:0.8rem;letter-spacing:0.2em;">RATE LIMIT</div>
    <div style="color:rgba(255,255,255,0.3);font-size:0.7rem;margin-top:8px;">1 dakika sonra tekrar deneyin</div>
    </body></html>""", height=300)
    st.stop()

if not data:
    st.error("API bağlantısı kurulamadı.")
    st.stop()

# Para birimi seçici (Streamlit native)
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

# Tam sayfayı render et
html = build_page(data, st.session_state["currency"], st.session_state["prev_data"])
st.components.v1.html(html, height=2400, scrolling=True)

# 60 saniyede bir otomatik güncelle
time.sleep(60)
st.session_state["prev_data"] = dict(data)
st.cache_data.clear()
st.rerun()
