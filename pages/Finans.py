import streamlit as st
import requests
import time
import os
import json as _json
from datetime import datetime
import zoneinfo
import math

st.set_page_config(
    page_title="Finans Takip | Canlı",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
#MainMenu, header, footer, .stAppDeployButton { display: none !important; }
.block-container { padding: 0 !important; margin: 0 !important; max-width: 100% !important; }
.stApp { background: #070608 !important; }
section[data-testid="stSidebar"] { display: none !important; }
div[data-testid="stSelectbox"] label { display: none !important; }
div[data-testid="stSelectbox"] > div > div {
    background: #1c1a22 !important; color: #e8dfc8 !important;
    font-family: 'Courier New', monospace !important; font-size: 0.85rem !important;
    border: 1px solid rgba(212,168,71,0.4) !important; border-radius: 10px !important;
}
</style>
""", unsafe_allow_html=True)

# ─── SABİTLER ─────────────────────────────────────────────────────────────────
TRUNCGIL_API  = "https://finance.truncgil.com/api/today.json"
GOLDPRICE_API = "https://goldprice.today/api.php?data=live"
RATE_FILE     = "/tmp/finans_rate.json"
RATE_LIMIT    = 20
RATE_WINDOW   = 60

CURRENCIES = {
    "TRY": ("Türk Lirası",         "₺"),
    "USD": ("Amerikan Doları",     "$"),
    "EUR": ("Euro",                "€"),
    "GBP": ("İngiliz Sterlini",    "£"),
    "CHF": ("İsviçre Frangı",      "Fr"),
    "SAR": ("Suudi Riyali",        "SR"),
    "AED": ("BAE Dirhemi",         "AED"),
    "JPY": ("Japon Yeni (100)",    "¥"),
    "AUD": ("Avustralya Doları",   "A$"),
    "CAD": ("Kanada Doları",       "C$"),
    "RUB": ("Rus Rublesi",         "₽"),
    "CNY": ("Çin Yuanı",           "¥"),
    "QAR": ("Katar Riyali",        "QAR"),
    "KWD": ("Kuveyt Dinarı",       "KD"),
    "EGP": ("Mısır Lirası",        "E£"),
    "PKR": ("Pakistan Rupisi",     "₨"),
    "INR": ("Hindistan Rupisi",    "₹"),
    "BRL": ("Brezilya Reali",      "R$"),
    "NOK": ("Norveç Kronu",        "kr"),
    "SEK": ("İsveç Kronu",         "kr"),
    "SGD": ("Singapur Doları",     "S$"),
    "HKD": ("Hong Kong Doları",    "HK$"),
    "DKK": ("Danimarka Kronu",     "kr"),
    "NZD": ("Yeni Zelanda Doları", "NZ$"),
    "PLN": ("Polonya Zlotisi",     "zł"),
    "AZN": ("Azerbaycan Manatı",   "₼"),
    "KZT": ("Kazak Tengesi",       "₸"),
    "UAH": ("Ukrayna Grivnası",    "₴"),
    "BGN": ("Bulgar Levası",       "лв"),
    "RON": ("Romanya Leyi",        "lei"),
    "ZAR": ("Güney Afrika Randı",  "R"),
    "BHD": ("Bahreyn Dinarı",      "BD"),
    "IQD": ("Irak Dinarı",         "IQD"),
    "ILS": ("İsrail Şekeli",       "₪"),
    "HUF": ("Macar Forinti",       "Ft"),
    "CZK": ("Çek Korunası",        "Kč"),
    "MXN": ("Meksika Pesosu",      "$"),
    "MYR": ("Malezya Ringgiti",    "RM"),
    "IDR": ("Endonezya Rupiahi",   "Rp"),
    "THB": ("Tayland Bahtı",       "฿"),
    "KRW": ("Güney Kore Wonu",     "₩"),
    "TWD": ("Yeni Tayvan Doları",  "NT$"),
    "LKR": ("Sri Lanka Rupisi",    "₨"),
    "MAD": ("Fas Dirhemi",         "MAD"),
    "TND": ("Tunus Dinarı",        "DT"),
    "JOD": ("Ürdün Dinarı",        "JD"),
    "OMR": ("Umman Riyali",        "OMR"),
    "CLP": ("Şili Pesosu",         "$"),
    "ARS": ("Arjantin Pesosu",     "$"),
    "GEL": ("Gürcistan Larisi",    "₾"),
    "DZD": ("Cezayir Dinarı",      "DZD"),
    "LYD": ("Libya Dinarı",        "LD"),
    "BAM": ("Bosna-Hersek Markı",  "KM"),
    "ALL": ("Arnavutluk Leki",     "L"),
    "MDL": ("Moldovya Leusu",      "MDL"),
    "MKD": ("Makedon Dinarı",      "MKD"),
    "RSD": ("Sırbistan Dinarı",    "din"),
    "LBP": ("Lübnan Lirası",       "L£"),
    "SYP": ("Suriye Lirası",       "S£"),
    "IRR": ("İran Riyali",         "Rls"),
    "UYU": ("Uruguay Pesosu",      "$U"),
    "COP": ("Kolombiya Pesosu",    "$"),
    "PEN": ("Peru İnti",           "S/"),
    "CRC": ("Kostarika Kolonu",    "₡"),
    "ISK": ("İzlanda Kronası",     "kr"),
    "PHP": ("Filipinler Pesosu",   "₱"),
    "BRL": ("Brezilya Reali",      "R$"),
}

TICKER_CODES = [
    "USD","EUR","GBP","CHF","SAR","AED","JPY",
    "AUD","RUB","INR","QAR","KWD","EGP","CAD","CNY",
]

# İlk 15 kripto (piyasa değerine göre en önemliler)
TOP_CRYPTOS_15 = [
    "BTC","ETH","XRP","SOL","BNB","DOGE","ADA",
    "AVAX","LINK","DOT","LTC","UNI","AAVE","APT","NEAR",
]
# Tüm kriptolar (API'deki sırayla)
ALL_CRYPTOS = [
    "BTC","ETH","XRP","USDT","SOL","BNB","DOGE","USDC","ADA","STETH",
    "TRX","LINK","AVAX","SUI","WBTC","XLM","WSTETH","HBAR","TON","SHIB",
    "DOT","WETH","LTC","LEO","BCH","BGB","TRUMP","UNI","HYPE","PEPE",
    "WEETH","USDS","NEAR","USDE","AAVE","APT","ICP","ONDO","ETC","WBT",
    "VET","XMR","POL","CRO","RENDER","ALGO","MNT","OKB","OM","DAI",
]

# Truncgil altın kodları → (görünüm adı, alt açıklama, öncelik)
GOLD_MAP = {
    "GRA": ("Gram Altın",          "24 ayar saf altın",        1),
    "HAS": ("Gram Has Altın",      "Saf has altın",            2),
    "CEY": ("Çeyrek Altın",        "1,754 gr · 22 ayar",       3),
    "YAR": ("Yarım Altın",         "3,508 gr · 22 ayar",       4),
    "TAM": ("Tam Altın",           "7,016 gr · 22 ayar",       5),
    "CUM": ("Cumhuriyet Altını",   "7,216 gr · 22 ayar",       6),
    "ATA": ("Ata Altın",           "7,216 gr · 22 ayar",       7),
    "RES": ("Reşat Altın",         "7,216 gr · 22 ayar",       8),
    "HAM": ("Hamit Altın",         "7,216 gr · 22 ayar",       9),
    "IKI": ("2,5 Liralık Altın",   "~17,54 gr · 22 ayar",      10),
    "BES": ("5 Liralık Altın",     "~35,08 gr · 22 ayar",      11),
    "GRE": ("Gremse Altın",        "~35,08 gr · 22 ayar",      12),
    "OSA": ("18 Ayar Altın",       "18 ayar / gram",           13),
    "ODA": ("14 Ayar Altın",       "14 ayar / gram",           14),
    "YIA": ("22 Ayar Bilezik",     "22 ayar / gram",           15),
    "GUM": ("Gram Gümüş",          "999 saflık",               16),
    "GPL": ("Gram Platin",         "999 saflık",               17),
}

# İlk 9 altın tipi default gösterilecek
TOP_GOLD_CODES = ["CEY","YAR","TAM","CUM","ATA","OSA","ODA","YIA","HAS"]

# İlk 15 döviz default
TOP_CURRENCY_CODES = [
    "USD","EUR","GBP","CHF","SAR","AED","JPY","AUD",
    "CAD","RUB","CNY","KWD","QAR","INR","EGP",
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
def fetch_truncgil():
    try:
        r = requests.get(TRUNCGIL_API, timeout=10)
        return r.json()
    except:
        return {}

@st.cache_data(ttl=60)
def fetch_goldprice():
    if not check_rate():
        return None
    try:
        r = requests.get(GOLDPRICE_API, timeout=10)
        return r.json()
    except:
        return {}


# ─── YARDIMCILAR ──────────────────────────────────────────────────────────────
def nf(v: float) -> str:
    if v == 0:
        return "0"
    if v >= 100_000:
        s = f"{v:,.0f}"
    elif v >= 1_000:
        s = f"{v:,.2f}"
    elif v >= 1:
        s = f"{v:,.3f}"
    else:
        mag  = -int(math.floor(math.log10(abs(v))))
        prec = max(4, mag + 3)
        s    = f"{v:,.{prec}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def badge(chg_pct: float) -> str:
    if abs(chg_pct) < 0.001:
        return ""
    arrow = "&#9650;" if chg_pct > 0 else "&#9660;"
    col   = "#4cb97a" if chg_pct > 0 else "#e05050"
    bg    = "rgba(76,185,122,0.13)" if chg_pct > 0 else "rgba(224,80,80,0.13)"
    brd   = "rgba(76,185,122,0.3)"  if chg_pct > 0 else "rgba(224,80,80,0.3)"
    p     = f"{abs(chg_pct):.2f}".replace(".", ",")
    return (f'<span class="badge" style="color:{col};background:{bg};'
            f'border:1px solid {brd};">{arrow} {p}%</span>')

def chg_color(c: float) -> str:
    return "#4cb97a" if c >= 0 else "#e05050"

def chg_arrow(c: float) -> str:
    return "▲" if c >= 0 else "▼"


# ─── HTML ŞABLONU ─────────────────────────────────────────────────────────────
def build_page(tc: dict, gp: dict, sel: str, prev_tc: dict) -> str:
    sel_name, sel_sym = CURRENCIES.get(sel, ("", sel))
    r_tc   = tc.get("Rates", {})
    r_prev = prev_tc.get("Rates", {}) if prev_tc else {}

    def tv(code, field="Buying"):
        return float(r_tc.get(code, {}).get(field, 0))
    def pv(code, field="Buying"):
        return float(r_prev.get(code, {}).get(field, 0))
    def tch(code):
        return float(r_tc.get(code, {}).get("Change", 0))

    # ── Saat
    try:
        tz_tr = zoneinfo.ZoneInfo("Europe/Istanbul")
    except Exception:
        tz_tr = None
    now_tr  = datetime.now(tz_tr) if tz_tr else datetime.now()
    now_str = now_tr.strftime("%d.%m.%Y %H:%M") + " (TR)"

    # ── Ticker
    ticker_items = ""
    for code in TICKER_CODES:
        d   = r_tc.get(code, {})
        if d.get("Type") != "Currency":
            continue
        buy = float(d.get("Buying", 0))
        if buy <= 0:
            continue
        c = float(d.get("Change", 0))
        ticker_items += f"""
        <span class="ti">
            <span class="ti-code">{code}/TRY</span>
            <span class="ti-dot">◆</span>
            <span class="ti-val">₺ {nf(buy)}</span>
            <span style="color:{chg_color(c)};font-size:0.58rem;">{chg_arrow(c)}{abs(c):.2f}%</span>
        </span>"""
    # BTC ticker
    btc = r_tc.get("BTC", {})
    if btc.get("TRY_Price"):
        c = float(btc.get("Change", 0))
        ticker_items += f"""
        <span class="ti">
            <span class="ti-code" style="color:#f7931a;">BTC</span>
            <span class="ti-dot">◆</span>
            <span class="ti-val">₺ {nf(float(btc['TRY_Price']))}</span>
            <span style="color:{chg_color(c)};font-size:0.58rem;">{chg_arrow(c)}{abs(c):.2f}%</span>
        </span>"""
    # Gram altın ticker
    gra = r_tc.get("GRA", {})
    if gra.get("Buying"):
        c = float(gra.get("Change", 0))
        ticker_items += f"""
        <span class="ti">
            <span class="ti-code" style="color:#d4a847;">ALTIN</span>
            <span class="ti-dot">◆</span>
            <span class="ti-val">₺ {nf(float(gra['Buying']))}/gr</span>
            <span style="color:{chg_color(c)};font-size:0.58rem;">{chg_arrow(c)}{abs(c):.2f}%</span>
        </span>"""

    # ── Spot bant (GRA / GUM / GPL)
    def spot_item(code, title, sub=""):
        b = tv(code, "Buying"); s = tv(code, "Selling")
        c = tch(code)
        if b <= 0:
            return ""
        return f"""
        <div class="spot-item">
            <div class="spot-label">{title}</div>
            <div class="spot-price">₺ {nf(b)}</div>
            <div class="spot-sell">Alış: ₺ {nf(b)} &nbsp;·&nbsp; Satış: ₺ {nf(s)}{f"<br><small style='color:rgba(255,255,255,0.2)'>{sub}</small>" if sub else ""}</div>
            <div class="spot-chg">{badge(c)}</div>
        </div>"""

    # ── Altın kartı
    def gold_card(code, big=False, primary=False, hidden=False):
        info = GOLD_MAP.get(code)
        if not info:
            return ""
        label, sub, _ = info
        b = tv(code, "Buying"); s = tv(code, "Selling")
        c = tch(code)
        if b <= 0:
            return ""
        spread   = s - b
        p_cls    = "hc-price big" if big else "hc-price sm"
        card_cls = "hero-card" + (" primary" if primary else "") + (" hidden-card" if hidden else "")
        return f"""
        <div class="{card_cls}">
            <div class="hc-unit">{label}</div>
            <div class="{p_cls}">₺ {nf(b)}</div>
            <div class="hc-label">{sub} · Satış: ₺ {nf(s)}</div>
            <div class="hc-spread">Spread: ₺ {nf(spread)}</div>
            <div class="hc-change">{badge(c)}</div>
        </div>"""

    # ── Tüm altın kartlarını oluştur
    top_gold_html  = ""
    extra_gold_html = ""
    for code, (label, sub, priority) in GOLD_MAP.items():
        b = tv(code, "Buying")
        if b <= 0:
            continue
        if code in TOP_GOLD_CODES:
            big     = (code == "TAM")
            primary = (code == "TAM")
            top_gold_html += gold_card(code, big=big, primary=primary)
        else:
            extra_gold_html += gold_card(code)

    # ── Kripto kartı
    def crypto_card(code, hidden=False):
        d = r_tc.get(code, {})
        if d.get("Type") != "CryptoCurrency":
            return ""
        usd_p  = float(d.get("USD_Price", 0))
        try_p  = float(d.get("TRY_Price", 0))
        c      = float(d.get("Change",    0))
        name_c = d.get("Name", code)
        if usd_p <= 0:
            return ""
        hidden_cls = " hidden-card" if hidden else ""
        return f"""
        <div class="crypto-card{hidden_cls}">
            <div class="cc-left">
                <div class="cc-code">{code}</div>
                <div class="cc-name">{name_c}</div>
            </div>
            <div class="cc-right">
                <div class="cc-usd">$ {nf(usd_p)}</div>
                <div class="cc-try">₺ {nf(try_p)}</div>
                <div style="color:{chg_color(c)};font-size:0.6rem;margin-top:2px;">{chg_arrow(c)} {abs(c):.2f}%</div>
            </div>
        </div>"""

    top_crypto_html   = "".join(crypto_card(c) for c in TOP_CRYPTOS_15)
    extra_crypto_html = "".join(
        crypto_card(c, hidden=True)
        for c in ALL_CRYPTOS
        if c not in TOP_CRYPTOS_15
    )

    # ── Döviz satırı
    def rate_row(code, hidden=False):
        info = CURRENCIES.get(code)
        if not info:
            return ""
        name, sym = info
        if code == "TRY":
            return ""
        d = r_tc.get(code, {})
        if d.get("Type") != "Currency":
            return ""
        buy  = float(d.get("Buying",  0))
        sell = float(d.get("Selling", 0))
        c    = float(d.get("Change",  0))
        if buy <= 0:
            return ""
        active     = ' style="border-color:rgba(212,168,71,0.7);background:rgba(212,168,71,0.07);"' if code == sel else ""
        hidden_cls = " hidden-card" if hidden else ""
        return f"""
        <div class="rr{hidden_cls}"{active}>
            <div>
                <div class="rr-code">{code}</div>
                <div class="rr-name">{name}</div>
            </div>
            <div class="rr-right">
                <div class="rr-val">₺ {nf(buy)}</div>
                <div class="rr-sell">Satış: ₺ {nf(sell)}</div>
                <div style="color:{chg_color(c)};font-size:0.6rem;margin-top:2px;">{chg_arrow(c)} {abs(c):.2f}%</div>
            </div>
        </div>"""

    top_rate_html   = "".join(rate_row(c) for c in TOP_CURRENCY_CODES)
    extra_rate_html = "".join(
        rate_row(c, hidden=True)
        for c in CURRENCIES
        if c not in TOP_CURRENCY_CODES and c != "TRY"
    )

    # ── Uluslararası altın (goldprice.today)
    gp_sel  = gp.get(sel, gp.get("USD", {})) if gp else {}
    gram_p  = float(gp_sel.get("gram",  0))
    ounce_p = float(gp_sel.get("ounce", 0))
    tola_p  = float(gp_sel.get("tola",  0))
    intl_section = ""
    if gram_p > 0:
        intl_section = f"""
        <div class="section-title">Uluslararası Birimler — {sel_name} <span class="src-tag">goldprice.today</span></div>
        <div class="hero-grid">
            <div class="hero-card primary">
                <div class="hc-unit">Gram Altın</div>
                <div class="hc-price big">{sel_sym} {nf(gram_p)}</div>
                <div class="hc-label">{sel_name} / 24 Ayar Gram</div>
            </div>
            <div class="hero-card">
                <div class="hc-unit">Ons Altın</div>
                <div class="hc-price">{sel_sym} {nf(ounce_p)}</div>
                <div class="hc-label">{sel_name} / Troy Ons (31,10 gr)</div>
            </div>
            <div class="hero-card">
                <div class="hc-unit">Tola Altın</div>
                <div class="hc-price">{sel_sym} {nf(tola_p)}</div>
                <div class="hc-label">{sel_name} / Tola (11,66 gr)</div>
            </div>
        </div>"""

    # ── Ana döviz sepet
    usd_b = tv("USD","Buying"); usd_s = tv("USD","Selling")
    eur_b = tv("EUR","Buying"); eur_s = tv("EUR","Selling")
    gbp_b = tv("GBP","Buying"); gbp_s = tv("GBP","Selling")

    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=DM+Mono:wght@400;500&family=DM+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{{
    --gold:#d4a847;--gold2:#f0c96a;
    --dark:#070608;--dark3:#141318;--dark4:#1c1a22;
    --border:rgba(212,168,71,0.18);--border2:rgba(212,168,71,0.38);
    --muted:rgba(255,255,255,0.4);--green:#4cb97a;--red:#e05050;
}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--dark);color:#f0e8d4;font-family:'DM Sans',sans-serif;-webkit-font-smoothing:antialiased;overflow-x:hidden;line-height:1.5}}

/* TICKER */
.ticker-wrap{{position:sticky;top:0;z-index:100;background:linear-gradient(90deg,#0a0800,#181000,#0a0800);border-bottom:1px solid var(--border2);height:36px;overflow:hidden;display:flex;align-items:center}}
.ticker-track{{display:flex;white-space:nowrap;animation:scroll-left 90s linear infinite}}
.ticker-track:hover{{animation-play-state:paused}}
.ti{{display:inline-flex;align-items:center;gap:6px;padding:0 18px;border-right:1px solid rgba(212,168,71,0.1);font-family:'DM Mono',monospace;font-size:0.68rem}}
.ti-code{{color:#c8a050;letter-spacing:0.08em;font-size:0.62rem;font-weight:500}}
.ti-dot{{color:rgba(212,168,71,0.25);font-size:0.5rem}}
.ti-val{{color:#f0e8d0}}
@keyframes scroll-left{{0%{{transform:translateX(0)}}100%{{transform:translateX(-50%)}}}}

.clockbar{{background:linear-gradient(90deg,#0a0800,#100e00,#0a0800);border-bottom:1px solid rgba(212,168,71,0.1);padding:6px 20px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;font-family:'DM Mono',monospace}}
.page{{max-width:1160px;margin:0 auto;padding:0 16px 60px}}
.header{{text-align:center;padding:28px 16px 18px}}
.logo{{font-family:'Playfair Display',serif;font-size:clamp(1.8rem,5vw,3rem);font-weight:900;letter-spacing:0.04em;background:linear-gradient(135deg,#8a6010 0%,#d4a847 30%,#f0c96a 50%,#d4a847 70%,#8a6010 100%);background-size:300% 100%;-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;animation:gold-sheen 5s ease infinite}}
.logo-sub{{font-size:0.62rem;letter-spacing:0.25em;color:rgba(255,255,255,0.3);text-transform:uppercase;margin-top:5px;font-family:'DM Mono',monospace}}
.live-dot{{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--green);box-shadow:0 0 8px var(--green);animation:blink 1.4s ease infinite;margin-right:6px;vertical-align:middle}}
.divider{{width:60px;height:1px;margin:14px auto 0;background:linear-gradient(90deg,transparent,var(--gold),transparent)}}
@keyframes gold-sheen{{0%{{background-position:0% 50%}}50%{{background-position:100% 50%}}100%{{background-position:0% 50%}}}}
@keyframes blink{{0%,100%{{opacity:1}}50%{{opacity:0.2}}}}

.section-title{{font-family:'DM Mono',monospace;font-size:0.62rem;letter-spacing:0.25em;color:#c8a050;text-transform:uppercase;margin:28px 0 12px;font-weight:500;display:flex;align-items:center;gap:10px}}
.section-title::after{{content:'';flex:1;height:1px;background:linear-gradient(90deg,rgba(212,168,71,0.15),transparent)}}
.src-tag{{font-size:0.5rem;letter-spacing:0.06em;color:rgba(255,255,255,0.2);border:1px solid rgba(255,255,255,0.08);border-radius:3px;padding:1px 5px;text-transform:uppercase;vertical-align:middle;font-weight:400}}

/* TOGGLE BUTTON */
.toggle-btn{{
    display:inline-flex;align-items:center;gap:6px;
    font-family:'DM Mono',monospace;font-size:0.6rem;letter-spacing:0.12em;
    color:rgba(212,168,71,0.7);text-transform:uppercase;
    background:rgba(212,168,71,0.06);border:1px solid rgba(212,168,71,0.2);
    border-radius:6px;padding:5px 14px;cursor:pointer;
    transition:all 0.2s;user-select:none;margin-top:12px;
}}
.toggle-btn:hover{{background:rgba(212,168,71,0.12);border-color:rgba(212,168,71,0.35);color:var(--gold)}}
.toggle-btn .arrow{{transition:transform 0.3s;display:inline-block}}
.toggle-btn.open .arrow{{transform:rotate(180deg)}}

/* HIDDEN CARDS */
.hidden-card{{display:none}}

/* GRID layouts */
.hero-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:4px}}
.gold-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:10px;margin-top:4px}}
.fx-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}}
.rate-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(205px,1fr));gap:8px;margin-top:4px}}
.crypto-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(185px,1fr));gap:8px;margin-top:4px}}

/* CARDS */
.hero-card{{background:var(--dark4);border:1px solid var(--border);border-radius:14px;padding:20px 18px;position:relative;overflow:hidden;transition:border-color 0.25s,box-shadow 0.25s}}
.hero-card:hover{{border-color:var(--border2);box-shadow:0 0 25px rgba(212,168,71,0.08)}}
.hero-card.primary{{background:linear-gradient(145deg,#100d06,#1a1508);border-color:rgba(212,168,71,0.42);box-shadow:0 0 45px rgba(212,168,71,0.06)}}
.hero-card::after{{content:'';position:absolute;bottom:0;left:0;right:0;height:2px;background:linear-gradient(90deg,transparent,var(--gold),transparent);opacity:0.3}}
.hc-unit{{font-family:'DM Mono',monospace;font-size:0.6rem;letter-spacing:0.16em;color:#c8a050;text-transform:uppercase;margin-bottom:10px;font-weight:500}}
.hc-price{{font-family:'Playfair Display',serif;font-weight:700;font-size:clamp(1.3rem,2.6vw,1.85rem);color:#fff8ee;line-height:1.15;word-break:break-all}}
.hc-price.big{{font-size:clamp(1.5rem,3.5vw,2.4rem)}}
.hc-price.sm{{font-size:clamp(1.1rem,2.2vw,1.55rem)}}
.hc-label{{font-size:0.65rem;color:rgba(255,255,255,0.38);margin-top:5px}}
.hc-spread{{font-size:0.59rem;color:rgba(255,255,255,0.22);margin-top:2px}}
.hc-change{{margin-top:7px;min-height:22px}}
.badge{{display:inline-flex;align-items:center;gap:3px;font-family:'DM Mono',monospace;font-size:0.62rem;font-weight:600;padding:2px 8px;border-radius:20px;line-height:1.4;white-space:nowrap}}

/* SPOT BAND */
.spot-band{{display:flex;flex-wrap:wrap;background:var(--dark4);border:1px solid var(--border);border-radius:14px;overflow:hidden;margin-top:4px}}
.spot-item{{flex:1;min-width:180px;padding:18px 20px;border-right:1px solid var(--border)}}
.spot-item:last-child{{border-right:none}}
.spot-label{{font-family:'DM Mono',monospace;font-size:0.56rem;letter-spacing:0.18em;color:#c8a050;text-transform:uppercase;margin-bottom:6px}}
.spot-price{{font-family:'Playfair Display',serif;font-size:1.4rem;font-weight:700;color:#fff8ee}}
.spot-sell{{font-size:0.62rem;color:rgba(255,255,255,0.28);margin-top:3px}}
.spot-chg{{margin-top:5px}}

/* FX SEPET */
.fx-card{{background:var(--dark4);border:1px solid var(--border);border-radius:12px;padding:16px 18px;transition:all 0.2s}}
.fx-card:hover{{border-color:var(--border2)}}
.fx-code{{font-family:'DM Mono',monospace;font-size:0.6rem;letter-spacing:0.16em;color:#c8a050;font-weight:500}}
.fx-buy{{font-family:'Playfair Display',serif;font-size:1.5rem;font-weight:700;color:#fff8ee;margin-top:7px}}
.fx-sell{{font-size:0.62rem;color:rgba(255,255,255,0.28);margin-top:3px}}

/* KUR TABLOSU */
.rr{{background:var(--dark4);border:1px solid var(--border);border-radius:9px;padding:12px 14px;display:flex;justify-content:space-between;align-items:center;transition:all 0.2s}}
.rr:hover{{border-color:var(--border2);background:var(--dark3)}}
.rr-code{{font-family:'DM Mono',monospace;font-size:0.7rem;color:#c8a050;letter-spacing:0.1em;font-weight:600}}
.rr-name{{font-size:0.6rem;color:rgba(255,255,255,0.35);margin-top:2px}}
.rr-right{{text-align:right}}
.rr-val{{font-family:'DM Mono',monospace;font-size:0.86rem;color:#f0e8d4;font-weight:500}}
.rr-sell{{font-size:0.58rem;color:rgba(255,255,255,0.25);margin-top:1px}}

/* KRİPTO */
.crypto-card{{background:var(--dark4);border:1px solid var(--border);border-radius:9px;padding:12px 14px;display:flex;justify-content:space-between;align-items:center;transition:all 0.2s}}
.crypto-card:hover{{border-color:rgba(247,147,26,0.28);background:var(--dark3)}}
.cc-code{{font-family:'DM Mono',monospace;font-size:0.7rem;color:#f7931a;letter-spacing:0.08em;font-weight:600}}
.cc-name{{font-size:0.58rem;color:rgba(255,255,255,0.32);margin-top:2px}}
.cc-right{{text-align:right}}
.cc-usd{{font-family:'DM Mono',monospace;font-size:0.72rem;color:rgba(255,255,255,0.42)}}
.cc-try{{font-family:'DM Mono',monospace;font-size:0.86rem;color:#f0e8d4;font-weight:500;margin-top:1px}}

/* SORUMLULUK REDDİ */
.disclaimer{{
    display:flex;align-items:flex-start;gap:14px;
    background:linear-gradient(135deg,rgba(212,168,71,0.06),rgba(212,168,71,0.03));
    border:1px solid rgba(212,168,71,0.22);
    border-left:3px solid rgba(212,168,71,0.55);
    border-radius:10px;padding:16px 20px;margin-top:20px;
}}
.disc-icon{{font-size:1.1rem;margin-top:1px;flex-shrink:0}}
.disc-title{{
    font-family:'DM Mono',monospace;font-size:0.62rem;letter-spacing:0.18em;
    color:#c8a050;text-transform:uppercase;font-weight:600;margin-bottom:7px;
}}
.disc-text{{
    font-size:0.7rem;color:rgba(255,255,255,0.42);line-height:1.65;
}}
.disc-text strong{{color:rgba(255,255,255,0.62);font-weight:600}}

/* BİLDİRİM */
#notif{{display:none;position:fixed;top:68px;right:16px;z-index:999;background:rgba(76,185,122,0.15);border:1px solid rgba(76,185,122,0.4);border-radius:10px;padding:10px 18px;font-family:'DM Mono',monospace;font-size:0.7rem;color:#4cb97a;letter-spacing:0.1em;box-shadow:0 4px 20px rgba(0,0,0,0.4);animation:fadeIn 0.3s ease}}
@keyframes fadeIn{{from{{opacity:0;transform:translateY(-8px)}}to{{opacity:1;transform:translateY(0)}}}}

/* FOOTER */
.footer{{text-align:center;padding:20px 16px;font-family:'DM Mono',monospace;font-size:0.56rem;color:rgba(212,168,71,0.25);letter-spacing:0.18em;border-top:1px solid var(--border);margin-top:40px}}

/* RESPONSIVE */
@media(max-width:720px){{
    .hero-grid,.fx-grid{{grid-template-columns:1fr}}
    .spot-band{{flex-direction:column}}
    .spot-item{{border-right:none;border-bottom:1px solid var(--border)}}
    .spot-item:last-child{{border-bottom:none}}
}}
@media(max-width:480px){{
    .rate-grid,.crypto-grid,.gold-grid{{grid-template-columns:repeat(2,1fr)}}
}}
</style>
</head>
<body>
<div id="notif">✓ &nbsp;VERİ GÜNCELLENDİ</div>

<!-- TICKER -->
<div class="ticker-wrap">
  <div class="ticker-track">{ticker_items}{ticker_items}</div>
</div>

<!-- CLOCK BAR -->
<div class="clockbar">
    <div style="display:flex;align-items:center;gap:14px;">
        <span style="color:rgba(212,168,71,0.4);letter-spacing:0.1em;font-size:0.56rem;">TR SAATİ</span>
        <span id="clock-time" style="color:#f0e8d0;letter-spacing:0.08em;font-size:0.82rem;font-weight:500;">--:--:--</span>
        <span id="clock-date" style="color:rgba(255,255,255,0.25);font-size:0.6rem;"></span>
    </div>
    <div style="display:flex;align-items:center;gap:10px;">
        <span id="upd-lbl" style="color:rgba(212,168,71,0.38);font-size:0.55rem;letter-spacing:0.08em;"></span>
        <div style="width:100px;height:3px;background:rgba(255,255,255,0.06);border-radius:4px;overflow:hidden;">
            <div id="cbar" style="height:100%;background:linear-gradient(90deg,#d4a847,#f0c96a);border-radius:4px;transition:width 1s linear;width:100%;"></div>
        </div>
        <span id="csec" style="color:#d4a847;font-size:0.68rem;min-width:24px;text-align:right;"></span>
    </div>
</div>

<div class="page">

  <!-- BAŞLIK -->
  <div class="header">
    <div class="logo">FİNANS TAKİP</div>
    <div class="logo-sub">
        <span class="live-dot"></span>Canlı &nbsp;·&nbsp; Altın &nbsp;·&nbsp; Döviz &nbsp;·&nbsp; Kripto &nbsp;·&nbsp; {now_str}
    </div>
    <div class="divider"></div>
  </div>

  <!-- SORUMLULUK REDDİ -->
  <div class="disclaimer">
    <div class="disc-icon">⚠️</div>
    <div class="disc-body">
      <div class="disc-title">Sorumluluk Reddi &amp; Bilgilendirme</div>
      <div class="disc-text">
        Bu platform <strong>yalnızca bilgilendirme amaçlıdır</strong> ve yatırım tavsiyesi niteliği taşımaz.
        Gösterilen fiyatlar <strong>gerçek zamanlı piyasa verileri</strong> değil; truncgil.com ve goldprice.today 
        kaynaklı referans fiyatlardır. Gerçek alım-satım fiyatları yetkili aracı kurumlar, bankalar ve 
        kuyumculara göre farklılık gösterebilir. <strong>YTD (Yılbaşından Bu Yana)</strong> değişim 
        oranları ve günlük yüzde değişimler, önceki güne ait kapanış fiyatına göre hesaplanmış 
        yaklaşık değerler olup kesinlik garantisi verilmemektedir. Herhangi bir finansal karar 
        vermeden önce <strong>lisanslı bir yatırım danışmanına</strong> başvurmanız tavsiye edilir.
      </div>
    </div>
  </div>

  <!-- SPOT BANT -->
  <div class="section-title">Anlık Spot Fiyatlar <span class="src-tag">truncgil</span></div>
  <div class="spot-band">
    {spot_item("GRA","Gram Altın (24 Ayar)")}
    {spot_item("GUM","Gram Gümüş","999 saflık")}
    {spot_item("GPL","Gram Platin","999 saflık")}
  </div>

  <!-- TRY ALTIN -->
  <div class="section-title">Türk Altın Çeşitleri <span class="src-tag">truncgil</span></div>
  <div class="gold-grid" id="gold-grid">
    {top_gold_html}
    {extra_gold_html}
  </div>
  <div style="text-align:center;">
    <button class="toggle-btn" id="btn-gold" onclick="toggleSection('gold-grid','btn-gold','altın çeşidi')">
        <span class="arrow">▼</span>&nbsp; Tümünü Göster
    </button>
  </div>

  <!-- ANA DÖVİZ SEPET -->
  <div class="section-title">Ana Döviz Kurları <span class="src-tag">truncgil</span></div>
  <div class="fx-grid">
    <div class="fx-card">
        <div class="fx-code">USD / TRY &nbsp; {badge(tch("USD"))}</div>
        <div class="fx-buy">₺ {nf(usd_b)}</div>
        <div class="fx-sell">Satış: ₺ {nf(usd_s)}</div>
    </div>
    <div class="fx-card">
        <div class="fx-code">EUR / TRY &nbsp; {badge(tch("EUR"))}</div>
        <div class="fx-buy">₺ {nf(eur_b)}</div>
        <div class="fx-sell">Satış: ₺ {nf(eur_s)}</div>
    </div>
    <div class="fx-card">
        <div class="fx-code">GBP / TRY &nbsp; {badge(tch("GBP"))}</div>
        <div class="fx-buy">₺ {nf(gbp_b)}</div>
        <div class="fx-sell">Satış: ₺ {nf(gbp_s)}</div>
    </div>
  </div>

  <!-- ULUSLARARASI -->
  {intl_section}

  <!-- KRİPTO -->
  <div class="section-title">Kripto Para Piyasası <span class="src-tag">truncgil</span></div>
  <div class="crypto-grid" id="crypto-grid">
    {top_crypto_html}
    {extra_crypto_html}
  </div>
  <div style="text-align:center;">
    <button class="toggle-btn" id="btn-crypto" onclick="toggleSection('crypto-grid','btn-crypto','kripto')">
        <span class="arrow">▼</span>&nbsp; Tümünü Göster
    </button>
  </div>

  <!-- TÜM DÖVİZ TABLOSU -->
  <div class="section-title">Dünya Döviz Kurları (TRY Alış / Satış) <span class="src-tag">truncgil</span></div>
  <div class="rate-grid" id="rate-grid">
    {top_rate_html}
    {extra_rate_html}
  </div>
  <div style="text-align:center;">
    <button class="toggle-btn" id="btn-rate" onclick="toggleSection('rate-grid','btn-rate','kur')">
        <span class="arrow">▼</span>&nbsp; Tümünü Göster
    </button>
  </div>

  <div class="footer">
    ◆ &nbsp; Kaynak: truncgil.com &amp; goldprice.today &nbsp; ◆ &nbsp; {now_str} &nbsp; ◆ &nbsp; Her 60 saniyede güncellenir &nbsp; ◆
  </div>
</div>

<script>
// ── Toggle fonksiyonu
function toggleSection(gridId, btnId, label) {{
    var grid = document.getElementById(gridId);
    var btn  = document.getElementById(btnId);
    var hidden = grid.querySelectorAll('.hidden-card');
    var isOpen = btn.classList.contains('open');

    if (!isOpen) {{
        // Aç
        hidden.forEach(function(el) {{ el.style.display = ''; }});
        btn.classList.add('open');
        btn.innerHTML = '<span class="arrow">▲</span>&nbsp; Daha Az Göster';
    }} else {{
        // Kapat
        hidden.forEach(function(el) {{ el.style.display = 'none'; }});
        btn.classList.remove('open');
        btn.innerHTML = '<span class="arrow">▼</span>&nbsp; Tümünü Göster';
    }}
}}

// ── Saat & countdown
(function() {{
    var RSEC = 60, t0 = Date.now();
    var first = !sessionStorage.getItem('fp');
    if (!first) {{
        var n = document.getElementById('notif');
        if (n) {{ n.style.display = 'block'; setTimeout(function() {{ n.style.display = 'none'; }}, 3500); }}
    }}
    sessionStorage.setItem('fp', '1');

    function tick() {{
        var now = new Date();
        var tr = new Intl.DateTimeFormat('tr-TR', {{
            timeZone: 'Europe/Istanbul', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false
        }}).format(now);
        var td = new Intl.DateTimeFormat('tr-TR', {{
            timeZone: 'Europe/Istanbul', day: '2-digit', month: '2-digit', year: 'numeric', weekday: 'short'
        }}).format(now);
        var ct = document.getElementById('clock-time');
        var cd = document.getElementById('clock-date');
        if (ct) ct.textContent = tr;
        if (cd) cd.textContent = td;

        var el  = Math.floor((Date.now() - t0) / 1000);
        var rem = Math.max(0, RSEC - (el % RSEC));
        var pct = (rem / RSEC) * 100;
        var bar = document.getElementById('cbar');
        var sec = document.getElementById('csec');
        var lbl = document.getElementById('upd-lbl');
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
</body>
</html>"""


# ─── ANA UYGULAMA ─────────────────────────────────────────────────────────────
if "currency" not in st.session_state:
    st.session_state["currency"] = "TRY"
if "prev_tc" not in st.session_state:
    st.session_state["prev_tc"] = {}

# Para birimi seçici
cur_list = list(CURRENCIES.keys())
_, col_c, _ = st.columns([0.3, 4, 0.3])
with col_c:
    idx = cur_list.index(st.session_state["currency"]) if st.session_state["currency"] in cur_list else 0
    chosen = st.selectbox(
        "Para Birimi",
        options=cur_list,
        format_func=lambda c: f"{c}  —  {CURRENCIES[c][0]}  ({CURRENCIES[c][1]})",
        index=idx,
        key="cur_sel",
        label_visibility="collapsed",
    )
    if chosen != st.session_state["currency"]:
        st.session_state["currency"] = chosen
        st.rerun()

# Veri çek
tc = fetch_truncgil()
gp = fetch_goldprice() or {}

if not tc:
    st.components.v1.html("""
    <html><body style="background:#070608;display:flex;justify-content:center;
    align-items:center;height:100vh;flex-direction:column;font-family:monospace;">
    <div style="color:#d4a847;font-size:1.5rem;margin-bottom:12px;">⚠️</div>
    <div style="color:#d4a847;font-size:0.85rem;letter-spacing:0.2em;">API BAĞLANTI HATASI</div>
    <div style="color:rgba(255,255,255,0.3);font-size:0.7rem;margin-top:10px;">Sayfayı yenileyin</div>
    </body></html>""", height=300)
    st.stop()

html = build_page(tc, gp, st.session_state["currency"], st.session_state["prev_tc"])
st.components.v1.html(html, height=4400, scrolling=True)

time.sleep(60)
st.session_state["prev_tc"] = dict(tc)
st.cache_data.clear()
st.rerun()
