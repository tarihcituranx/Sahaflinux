import streamlit as st
import requests
import time
import random
from datetime import datetime

st.set_page_config(
    page_title="Altin Fiyatlari | Canli",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── SABITLER ─────────────────────────────────────────────────────────────────
API_URL = "https://goldprice.today/api.php?data=live"

CURRENCIES = {
    "TRY": ("Türk Lirası",    "₺"),
    "USD": ("Amerikan Doları","$"),
    "EUR": ("Euro",           "€"),
    "GBP": ("İngiliz Sterlini","£"),
    "CHF": ("İsviçre Frangı", "Fr"),
    "SAR": ("Suudi Riyali",   "﷼"),
    "AED": ("BAE Dirhemi",    "د.إ"),
    "JPY": ("Japon Yeni",     "¥"),
    "AUD": ("Avustralya Doları","A$"),
    "CAD": ("Kanada Doları",  "C$"),
    "RUB": ("Rus Rublesi",    "₽"),
    "CNY": ("Çin Yuanı",      "¥"),
    "QAR": ("Katar Riyali",   "ر.ق"),
    "KWD": ("Kuveyt Dinarı",  "د.ك"),
    "EGP": ("Mısır Lirası",   "£"),
    "PKR": ("Pakistan Rupisi","₨"),
    "INR": ("Hindistan Rupisi","₹"),
    "BRL": ("Brezilya Reali", "R$"),
    "NOK": ("Norveç Kronu",   "kr"),
    "SEK": ("İsveç Kronu",    "kr"),
}

SHOWCASE_CURRENCIES = ["TRY","USD","EUR","GBP","CHF","SAR","AED","JPY","AUD","RUB","INR","CNY","QAR","KWD"]

# ─── CSS / TASARIM ────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700;900&family=DM+Mono:wght@300;400;500&family=DM+Sans:wght@300;400;500;600&display=swap');

:root {
  --gold:    #d4a847;
  --gold2:   #f0c96a;
  --gold3:   #ffe9a0;
  --dark:    #070608;
  --dark2:   #0e0d10;
  --dark3:   #141318;
  --dark4:   #1c1a22;
  --panel:   rgba(20,19,26,0.97);
  --border:  rgba(212,168,71,0.18);
  --border2: rgba(212,168,71,0.35);
  --red:     #e05050;
  --green:   #4cb97a;
  --muted:   rgba(255,255,255,0.35);
}

html, body, .stApp { background: var(--dark) !important; color: #e8dfc8 !important; font-family: 'DM Sans', sans-serif !important; }

/* Tüm streamlit padding'leri sıfırla */
.stApp > header { display: none !important; }
.block-container { padding: 0 !important; max-width: 100% !important; }
section[data-testid="stSidebar"] { display: none; }

/* ── TICKER BANT ── */
.ticker-wrap {
  position: fixed; top: 0; left: 0; right: 0; z-index: 999;
  background: linear-gradient(90deg, #0a0800, #1a1200, #0a0800);
  border-bottom: 1px solid var(--border2);
  height: 38px; overflow: hidden;
  display: flex; align-items: center;
}
.ticker-track {
  display: flex; gap: 0; white-space: nowrap;
  animation: ticker-scroll 55s linear infinite;
  will-change: transform;
}
.ticker-track:hover { animation-play-state: paused; }
.ticker-item {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 0 28px;
  font-family: 'DM Mono', monospace; font-size: 0.72rem; font-weight: 500;
  border-right: 1px solid rgba(212,168,71,0.15);
}
.ticker-label { color: var(--gold); letter-spacing: 0.12em; font-size: 0.65rem; }
.ticker-val   { color: #f0e8d0; }
.ticker-sep   { color: rgba(212,168,71,0.4); font-size: 0.6rem; }
@keyframes ticker-scroll {
  from { transform: translateX(0); }
  to   { transform: translateX(-50%); }
}

/* ── SAYFA GÖVDE ── */
.fin-root {
  padding: 54px 0 40px 0;
  background:
    radial-gradient(ellipse 70% 40% at 20% 10%, rgba(180,130,30,0.07) 0%, transparent 65%),
    radial-gradient(ellipse 50% 30% at 80% 80%, rgba(100,80,20,0.05) 0%, transparent 60%),
    var(--dark);
  min-height: 100vh;
}

/* ── BASLIK ── */
.fin-header {
  text-align: center; padding: 36px 20px 20px 20px;
  position: relative;
}
.fin-header::after {
  content: '';
  display: block; margin: 18px auto 0; width: 80px; height: 1px;
  background: linear-gradient(90deg, transparent, var(--gold), transparent);
}
.fin-logo {
  font-family: 'Playfair Display', serif;
  font-size: clamp(1.8rem, 4vw, 3rem); font-weight: 900;
  background: linear-gradient(135deg, #a07820, #d4a847, #f0c96a, #d4a847, #a07820);
  background-size: 300% 100%; animation: gold-sheen 6s ease infinite;
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
  letter-spacing: 0.04em; line-height: 1;
}
.fin-sub {
  font-family: 'DM Mono', monospace; font-size: 0.7rem; letter-spacing: 0.35em;
  color: var(--muted); text-transform: uppercase; margin-top: 8px;
}
.live-dot {
  display: inline-block; width: 7px; height: 7px; border-radius: 50%;
  background: var(--green); margin-right: 6px;
  box-shadow: 0 0 8px var(--green);
  animation: blink 1.4s ease infinite;
}
@keyframes blink { 0%,100%{opacity:1;} 50%{opacity:0.3;} }
@keyframes gold-sheen {
  0%  { background-position: 0%   50%; }
  50% { background-position: 100% 50%; }
  100%{ background-position: 0%   50%; }
}

/* ── HERO KARTLAR ── */
.hero-grid {
  display: grid; grid-template-columns: repeat(3, 1fr);
  gap: 16px; padding: 24px 32px 8px;
  max-width: 1100px; margin: 0 auto;
}
@media(max-width:700px){ .hero-grid { grid-template-columns:1fr; } }

.hero-card {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 16px; padding: 28px 24px;
  position: relative; overflow: hidden;
  transition: border-color 0.3s, box-shadow 0.3s;
}
.hero-card::before {
  content:''; position:absolute; inset:0;
  background: linear-gradient(135deg, rgba(212,168,71,0.04) 0%, transparent 60%);
  pointer-events:none;
}
.hero-card:hover {
  border-color: var(--border2);
  box-shadow: 0 0 40px rgba(212,168,71,0.1), 0 8px 32px rgba(0,0,0,0.4);
}
.hero-card.primary {
  background: linear-gradient(145deg, #120f08, #1c1608);
  border-color: rgba(212,168,71,0.4);
  box-shadow: 0 0 60px rgba(212,168,71,0.08);
}
.hc-unit {
  font-family: 'DM Mono', monospace; font-size: 0.65rem; letter-spacing: 0.3em;
  color: var(--gold); text-transform: uppercase; margin-bottom: 10px;
}
.hc-symbol { font-size: 0.9rem; margin-right: 4px; opacity: 0.7; }
.hc-price {
  font-family: 'Playfair Display', serif; font-weight: 700;
  font-size: clamp(1.6rem, 3vw, 2.4rem); color: #f0e8d0;
  letter-spacing: -0.01em; line-height: 1.1;
}
.hc-price.big { font-size: clamp(2rem,4vw,3.2rem); }
.hc-label { font-size: 0.72rem; color: var(--muted); margin-top: 6px; }
.hc-accent {
  position:absolute; bottom:0; left:0; right:0; height:3px;
  background: linear-gradient(90deg, transparent, var(--gold), transparent);
  opacity: 0.4;
}

/* ── SILVER BAND ── */
.silver-band {
  max-width:1100px; margin: 16px auto; padding: 0 32px;
}
.silver-card {
  background: linear-gradient(135deg, rgba(180,190,200,0.06), rgba(100,110,120,0.04));
  border: 1px solid rgba(180,190,210,0.15);
  border-radius: 12px; padding: 16px 24px;
  display: flex; align-items: center; gap: 20px; flex-wrap: wrap;
}
.silver-lbl { font-family:'DM Mono',monospace; font-size:0.62rem; letter-spacing:0.3em; color:rgba(180,190,210,0.6); text-transform:uppercase; }
.silver-val { font-family:'Playfair Display',serif; font-size:1.2rem; color:rgba(200,210,220,0.9); font-weight:700; }
.silver-sep { color:rgba(180,190,210,0.2); font-size:1.2rem; }

/* ── KURU SECİCİ ── */
.selector-wrap {
  max-width: 1100px; margin: 28px auto 0; padding: 0 32px;
}
.selector-title {
  font-family:'DM Mono',monospace; font-size:0.62rem; letter-spacing:0.3em;
  color:var(--gold); text-transform:uppercase; margin-bottom:12px;
}

/* ── KUR TABLOSU ── */
.rate-table {
  max-width: 1100px; margin: 8px auto 0; padding: 0 32px 32px;
}
.rate-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 10px;
}
.rate-row {
  background: var(--dark4); border: 1px solid var(--border);
  border-radius: 10px; padding: 14px 16px;
  display: flex; justify-content: space-between; align-items: center;
  transition: all 0.25s; cursor: default;
}
.rate-row:hover { background: var(--dark3); border-color: var(--border2); transform:translateY(-1px); }
.rate-row.active { border-color: var(--gold); background: rgba(212,168,71,0.06); }
.rr-left {}
.rr-code { font-family:'DM Mono',monospace; font-size:0.72rem; color:var(--gold); letter-spacing:0.15em; }
.rr-name { font-size:0.7rem; color:var(--muted); margin-top:2px; }
.rr-right { text-align:right; }
.rr-val  { font-family:'DM Mono',monospace; font-size:0.9rem; color:#e8dfc8; font-weight:500; }
.rr-unit { font-size:0.62rem; color:var(--muted); margin-top:1px; }

/* ── GÜNCELLEME ── */
.update-bar {
  text-align:center; padding:16px;
  font-family:'DM Mono',monospace; font-size:0.65rem; color:rgba(212,168,71,0.4);
  letter-spacing:0.2em;
}

/* Streamlit widget override */
div[data-testid="stSelectbox"] > div > div {
  background: var(--dark4) !important; border: 1px solid var(--border2) !important;
  color: #e8dfc8 !important; border-radius: 8px !important;
  font-family: 'DM Mono', monospace !important;
}
label { color: var(--gold) !important; font-family:'DM Mono',monospace !important;
  font-size:0.65rem !important; letter-spacing:0.2em !important; text-transform:uppercase !important; }
</style>
""", unsafe_allow_html=True)


# ─── VERİ ÇEK ─────────────────────────────────────────────────────────────────
import os, json as _json

RATE_FILE  = "/tmp/finans_rate.json"
RATE_LIMIT = 20          # dakikada max istek (tüm kullanıcılar toplamda)
RATE_WINDOW = 60         # saniye

def _check_rate() -> bool:
    """Basit sunucu-geneli rate limit. True = izin var."""
    now = time.time()
    try:
        data_rl = {}
        if os.path.exists(RATE_FILE):
            with open(RATE_FILE) as f:
                data_rl = _json.load(f)
        # Pencere dışındaki kayıtları temizle
        hits = [t for t in data_rl.get("hits", []) if now - t < RATE_WINDOW]
        if len(hits) >= RATE_LIMIT:
            return False
        hits.append(now)
        with open(RATE_FILE, "w") as f:
            _json.dump({"hits": hits}, f)
        return True
    except:
        return True   # hata varsa izin ver

@st.cache_data(ttl=60)
def fetch_prices():
    if not _check_rate():
        return None   # rate limit aşıldı
    try:
        r = requests.get(API_URL, timeout=10)
        return r.json()
    except:
        return {}

# Para sembolü → HTML entity (Streamlit render güvenliği)
SYM_ENTITY = {
    "₺": "&#8378;",  # TRY
    "£": "&pound;",
    "€": "&euro;",
    "¥": "&yen;",
    "₽": "&#8381;",  # RUB
    "₹": "&#8377;",  # INR
    "₨": "&#8360;",  # PKR
    "﷼": "&#65020;", # SAR/QAR
    "د.إ": "&#x62F;.&#x625;",
    "د.ك": "&#x62F;.&#x643;",
    "ر.ق": "&#x631;.&#x642;",
    "$": "$", "A$": "A$", "C$": "C$", "R$": "R$", "Fr": "Fr",
    "kr": "kr", "＄": "$",
}

def safe_sym(sym: str) -> str:
    """Sembolü HTML-güvenli entity'e çevirir."""
    return SYM_ENTITY.get(sym, sym)

def fmt_price(val: float, symbol: str, decimals: int = 2) -> str:
    if val >= 1_000_000:
        return f"{symbol}{val:,.0f}"
    elif val >= 1_000:
        return f"{symbol}{val:,.2f}"
    else:
        return f"{symbol}{val:,.{decimals}f}"

def num_fmt(val: float) -> str:
    """Sayıyı güzel formatla."""
    if val >= 1_000_000: return f"{val:,.0f}"
    if val >= 10_000:    return f"{val:,.2f}"
    if val >= 1_000:     return f"{val:,.2f}"
    if val >= 100:       return f"{val:,.2f}"
    return f"{val:,.3f}"


# ─── SESSION STATE ─────────────────────────────────────────────────────────────
if "selected_currency" not in st.session_state:
    st.session_state["selected_currency"] = "TRY"
if "last_fetch" not in st.session_state:
    st.session_state["last_fetch"] = 0


# ─── VERİYİ YÜKLE ─────────────────────────────────────────────────────────────
data = fetch_prices()

if data is None:
    st.markdown("""
    <div style='text-align:center;padding:80px 20px;font-family:DM Mono,monospace;'>
        <div style='font-size:2rem;color:#d4a847;margin-bottom:12px;'>&#9203;</div>
        <div style='color:#d4a847;font-size:0.85rem;letter-spacing:0.2em;'>RATE LIMIT</div>
        <div style='color:rgba(255,255,255,0.4);font-size:0.75rem;margin-top:8px;'>
            Cok fazla istek. 1 dakika sonra tekrar deneyin.
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

if not data:
    st.error("API bağlantısı kurulamadı.")
    st.stop()

sel = st.session_state["selected_currency"]
sel_info = CURRENCIES.get(sel, ("", sel))
sel_sym  = sel_info[1]
sel_name = sel_info[0]

gold_data   = data.get(sel, data.get("USD", {}))
gram_price  = float(gold_data.get("gram",  0))
ounce_price = float(gold_data.get("ounce", 0))
tola_price  = float(gold_data.get("tola",  0))

# Gümüş: XAG oransalı kullanarak seçili para birimine dönüştür
xag_usd  = float(data.get("XAG", {}).get("ounce", 59.39))   # ons gümüş / ons altın
gold_usd = float(data.get("USD", {}).get("ounce", 5172))
silver_usd_oz = gold_usd / xag_usd
# Seçili para birimine çevir
usd_gram = float(data.get("USD", {}).get("gram", 166.29))
sel_gram = gram_price
conv = sel_gram / usd_gram if usd_gram > 0 else 1
silver_gram = (silver_usd_oz / 31.1035) * conv

# Yarım ve çeyrek altın (Türk geleneği — 22 ayar ≈ 6.7g)
half_gr  = gram_price * 3.508   # ~3.508g
quarter_gr = gram_price * 1.754  # ~1.754g
republic_gr = gram_price * 7.216 # ~7.216g cumhuriyet altını


# ─── TICKER VERİSİ ────────────────────────────────────────────────────────────
ticker_items = []
for code in SHOWCASE_CURRENCIES:
    d = data.get(code, {})
    gram_v = float(d.get("gram", 0))
    sym = CURRENCIES.get(code, ("", code))[1]
    if gram_v > 0:
        ticker_items.append((code, sym, gram_v))

# Ticker HTML — iki kopya ile sonsuz döngü
ticker_html_items = ""
for code, sym, gram_v in ticker_items:
    formatted = num_fmt(gram_v)
    ticker_html_items += f"""
    <span class="ticker-item">
        <span class="ticker-label">ALTIN/{code}</span>
        <span class="ticker-sep">◆</span>
        <span class="ticker-val">{safe_sym(sym)}{formatted} /gr</span>
    </span>"""

ticker_html = f"""
<div class="ticker-wrap">
  <div class="ticker-track">
    {ticker_html_items}
    {ticker_html_items}
  </div>
</div>
"""


# ─── TICKER ───────────────────────────────────────────────────────────────────
st.components.v1.html(ticker_html, height=38)

# ─── ANA GÖVDE ────────────────────────────────────────────────────────────────
st.markdown('<div class="fin-root">', unsafe_allow_html=True)

# Başlık
now_str = datetime.now().strftime("%d.%m.%Y %H:%M")
st.markdown(f"""
<div class="fin-header">
    <div class="fin-logo">ALTIN BORSASI</div>
    <div class="fin-sub">
        <span class="live-dot"></span>
        Canlı Fiyatlar &nbsp;·&nbsp; {now_str}
    </div>
</div>
""", unsafe_allow_html=True)

# ─── PARA BİRİMİ SEÇİCİ ───────────────────────────────────────────────────────
st.markdown('<div class="selector-wrap"><div class="selector-title">Para Birimi</div>', unsafe_allow_html=True)
currency_options = list(CURRENCIES.keys())
cur_idx = currency_options.index(sel) if sel in currency_options else 0
chosen = st.selectbox(" ", options=currency_options,
    format_func=lambda c: f"{c}  —  {CURRENCIES[c][0]}  ({CURRENCIES[c][1]})",
    index=cur_idx, label_visibility="collapsed", key="cur_select")
if chosen != sel:
    st.session_state["selected_currency"] = chosen
    st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

# ─── HERO KARTLAR ─────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="hero-grid">

  <div class="hero-card primary">
    <div class="hc-unit">Gram Altın</div>
    <div class="hc-price big"><span class="hc-symbol">{safe_sym(sel_sym)}</span>{num_fmt(gram_price)}</div>
    <div class="hc-label">{sel_name} / Gram</div>
    <div class="hc-accent"></div>
  </div>

  <div class="hero-card">
    <div class="hc-unit">Ons Altın</div>
    <div class="hc-price"><span class="hc-symbol">{safe_sym(sel_sym)}</span>{num_fmt(ounce_price)}</div>
    <div class="hc-label">{sel_name} / Troy Ons (31.10 gr)</div>
    <div class="hc-accent"></div>
  </div>

  <div class="hero-card">
    <div class="hc-unit">Tola Altın</div>
    <div class="hc-price"><span class="hc-symbol">{safe_sym(sel_sym)}</span>{num_fmt(tola_price)}</div>
    <div class="hc-label">{sel_name} / Tola (11.66 gr)</div>
    <div class="hc-accent"></div>
  </div>

</div>
""", unsafe_allow_html=True)

# ─── TÜRK ALTIN TIPLERI (sadece TRY'de göster) ────────────────────────────────
if sel == "TRY":
    _sym = safe_sym(sel_sym)
    st.markdown(f"""
    <div style='max-width:1100px;margin:16px auto;padding:0 32px;'>
        <div style='display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px;'>

          <div class="hero-card">
            <div class="hc-unit">Yarim Altin</div>
            <div class="hc-price" style="font-size:1.5rem;">
              <span class="hc-symbol">{_sym}</span>{num_fmt(half_gr)}
            </div>
            <div class="hc-label">~3.50 gram - 21 ayar</div>
          </div>

          <div class="hero-card">
            <div class="hc-unit">Ceyrek Altin</div>
            <div class="hc-price" style="font-size:1.5rem;">
              <span class="hc-symbol">{_sym}</span>{num_fmt(quarter_gr)}
            </div>
            <div class="hc-label">~1.75 gram - 21 ayar</div>
          </div>

          <div class="hero-card">
            <div class="hc-unit">Cumhuriyet Altini</div>
            <div class="hc-price" style="font-size:1.5rem;">
              <span class="hc-symbol">{_sym}</span>{num_fmt(republic_gr)}
            </div>
            <div class="hc-label">~7.22 gram - 22 ayar</div>
          </div>

        </div>
    </div>
    """, unsafe_allow_html=True)

# ─── GÜMÜŞ ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="silver-band">
  <div class="silver-card">
    <div>
      <div class="silver-lbl">Gram Gümüş</div>
      <div class="silver-val">{safe_sym(sel_sym)}{num_fmt(silver_gram)}</div>
    </div>
    <div class="silver-sep">|</div>
    <div>
      <div class="silver-lbl">Ons Gümüş</div>
      <div class="silver-val">{safe_sym(sel_sym)}{num_fmt(silver_gram * 31.1035)}</div>
    </div>
    <div class="silver-sep">|</div>
    <div>
      <div class="silver-lbl">Altın/Gümüş Oranı</div>
      <div class="silver-val">{xag_usd:.1f} : 1</div>
    </div>
    <div style="margin-left:auto;">
      <div class="silver-lbl">Kıymetli Metal</div>
      <div style="font-size:0.7rem;color:rgba(180,190,210,0.5);margin-top:2px;">Ag · Gümüş</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ─── TÜM KURLAR TABLOSU ───────────────────────────────────────────────────────
st.markdown("""
<div class="rate-table">
  <div style="font-family:'DM Mono',monospace;font-size:0.62rem;letter-spacing:0.3em;
              color:rgba(212,168,71,0.6);text-transform:uppercase;margin-bottom:14px;">
    Dünya Para Birimlerinde Gram Altın Fiyatı
  </div>
  <div class="rate-grid">
""", unsafe_allow_html=True)

rate_rows = ""
for code, (name, sym) in CURRENCIES.items():
    d = data.get(code, {})
    gram_v = float(d.get("gram", 0))
    if gram_v <= 0:
        continue
    active_cls = " active" if code == sel else ""
    rate_rows += f"""
    <div class="rate-row{active_cls}">
      <div class="rr-left">
        <div class="rr-code">{code}</div>
        <div class="rr-name">{name}</div>
      </div>
      <div class="rr-right">
        <div class="rr-val">{safe_sym(sym)}{num_fmt(gram_v)}</div>
        <div class="rr-unit">/gram</div>
      </div>
    </div>"""

st.markdown(rate_rows + "</div></div>", unsafe_allow_html=True)

# ─── GÜNCELLEME ZAMANI ────────────────────────────────────────────────────────
st.markdown(f"""
<div class="update-bar">
    ◆ &nbsp; VERİ KAYNAĞI: GOLDPRICE.TODAY &nbsp; ◆ &nbsp; SON GÜNCELLEME: {now_str} &nbsp; ◆ &nbsp; HER 60 SANİYEDE GÜNCELLENIR &nbsp; ◆
</div>
""", unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)  # fin-root

# ─── OTOMATİK YENİLE (60s) ────────────────────────────────────────────────────
time.sleep(60)
st.cache_data.clear()
st.rerun()
