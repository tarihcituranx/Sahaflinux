import streamlit as st
import requests
import html
import random
import json
import time

# ─── Sayfa Ayarları ───────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Kim Turanyoner Olmak Ister",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS Tasarım ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700;900&family=Rajdhani:wght@300;400;600;700&display=swap');

*, *::before, *::after { box-sizing: border-box; }

html, body, .stApp {
    background: #000814 !important;
    color: #e2c97e !important;
    font-family: 'Rajdhani', sans-serif !important;
}

/* Genel arka plan dokusu */
.stApp::before {
    content: '';
    position: fixed;
    inset: 0;
    background:
        radial-gradient(ellipse 80% 50% at 50% 0%, rgba(14,58,120,0.35) 0%, transparent 70%),
        radial-gradient(ellipse 60% 40% at 50% 100%, rgba(100,20,20,0.2) 0%, transparent 70%);
    pointer-events: none;
    z-index: 0;
}

/* Başlık */
.show-title {
    font-family: 'Cinzel', serif;
    font-size: clamp(1.4rem, 4vw, 2.8rem);
    font-weight: 900;
    text-align: center;
    background: linear-gradient(135deg, #ffe066, #e2c97e, #f5b800, #fff1a8, #e2c97e);
    background-size: 300% 300%;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    animation: shimmer 4s ease infinite;
    text-shadow: none;
    letter-spacing: 0.05em;
    margin-bottom: 0.1rem;
    line-height: 1.1;
}

.host-name {
    font-family: 'Rajdhani', sans-serif;
    font-size: 1rem;
    color: #90afd4;
    text-align: center;
    letter-spacing: 0.3em;
    text-transform: uppercase;
    margin-bottom: 1rem;
}

@keyframes shimmer {
    0%   { background-position: 0% 50%; }
    50%  { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

/* Soru kutusu */
.question-box {
    background: linear-gradient(145deg, rgba(10,30,70,0.95), rgba(5,15,40,0.98));
    border: 1px solid rgba(226,201,126,0.3);
    border-radius: 16px;
    padding: 2rem 2.5rem;
    text-align: center;
    font-family: 'Rajdhani', sans-serif;
    font-size: clamp(1rem, 2.5vw, 1.4rem);
    font-weight: 600;
    color: #ffffff;
    line-height: 1.5;
    box-shadow:
        0 0 40px rgba(14,58,120,0.4),
        0 0 0 1px rgba(226,201,126,0.1),
        inset 0 1px 0 rgba(255,255,255,0.05);
    margin-bottom: 1.5rem;
    position: relative;
    overflow: hidden;
}

.question-box::before {
    content: '';
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: conic-gradient(from 0deg at 50% 50%, transparent 340deg, rgba(226,201,126,0.06) 350deg, transparent 360deg);
    animation: rotate 8s linear infinite;
}

@keyframes rotate {
    from { transform: rotate(0deg); }
    to   { transform: rotate(360deg); }
}

.question-number-badge {
    display: inline-block;
    background: linear-gradient(135deg, #f5b800, #e2c97e);
    color: #000;
    font-family: 'Cinzel', serif;
    font-weight: 700;
    font-size: 0.75rem;
    padding: 0.25rem 0.9rem;
    border-radius: 20px;
    letter-spacing: 0.1em;
    margin-bottom: 0.8rem;
}

/* Cevap butonları */
.stButton > button {
    width: 100% !important;
    background: linear-gradient(145deg, rgba(10,30,80,0.9), rgba(5,15,50,0.95)) !important;
    color: #e2c97e !important;
    border: 1px solid rgba(226,201,126,0.35) !important;
    border-radius: 10px !important;
    font-family: 'Rajdhani', sans-serif !important;
    font-size: 1rem !important;
    font-weight: 600 !important;
    padding: 0.7rem 1.2rem !important;
    transition: all 0.2s ease !important;
    letter-spacing: 0.03em !important;
    text-align: left !important;
}

.stButton > button:hover {
    background: linear-gradient(145deg, rgba(30,70,160,0.95), rgba(15,40,100,0.98)) !important;
    border-color: rgba(226,201,126,0.7) !important;
    box-shadow: 0 0 18px rgba(226,201,126,0.25), 0 0 40px rgba(14,58,120,0.3) !important;
    transform: translateY(-1px) !important;
}

/* Joker butonları */
.joker-btn > button {
    background: linear-gradient(145deg, rgba(60,20,5,0.9), rgba(40,10,2,0.95)) !important;
    border-color: rgba(200,80,20,0.5) !important;
    color: #ff9966 !important;
    font-size: 0.85rem !important;
}
.joker-btn > button:hover {
    background: linear-gradient(145deg, rgba(120,40,10,0.95), rgba(80,20,5,0.98)) !important;
    border-color: rgba(255,120,50,0.8) !important;
    box-shadow: 0 0 18px rgba(200,80,20,0.35) !important;
}
.joker-btn > button:disabled {
    opacity: 0.3 !important;
    cursor: not-allowed !important;
}

/* Ödül merdiveni sidebar */
.prize-item {
    font-family: 'Rajdhani', sans-serif;
    font-size: 0.9rem;
    font-weight: 600;
    padding: 0.25rem 0.7rem;
    border-radius: 6px;
    margin: 2px 0;
    display: flex;
    justify-content: space-between;
    transition: all 0.3s;
    color: #90afd4;
}
.prize-item.current {
    background: linear-gradient(90deg, rgba(226,201,126,0.2), rgba(245,184,0,0.1));
    color: #ffe066;
    border-left: 3px solid #f5b800;
    font-size: 1rem;
    font-weight: 700;
}
.prize-item.earned {
    color: #4caf50;
    text-decoration: none;
}
.prize-item.guaranteed {
    color: #ff9966;
    font-weight: 700;
}
.prize-item.guaranteed.earned {
    color: #4caf50;
}

/* Mesaj kutuları */
.info-box {
    background: rgba(10,30,80,0.7);
    border: 1px solid rgba(226,201,126,0.2);
    border-radius: 10px;
    padding: 1rem 1.5rem;
    margin: 0.8rem 0;
    font-family: 'Rajdhani', sans-serif;
    font-size: 1rem;
    color: #c8daf5;
    line-height: 1.5;
}

.correct-box {
    background: rgba(20,80,20,0.7);
    border: 1px solid rgba(100,200,100,0.4);
    border-radius: 10px;
    padding: 1rem 1.5rem;
    margin: 0.8rem 0;
    color: #a8ffb0;
    font-family: 'Rajdhani', sans-serif;
    font-size: 1.1rem;
    font-weight: 700;
    text-align: center;
}

.wrong-box {
    background: rgba(80,10,10,0.7);
    border: 1px solid rgba(200,60,60,0.4);
    border-radius: 10px;
    padding: 1rem 1.5rem;
    margin: 0.8rem 0;
    color: #ffaaaa;
    font-family: 'Rajdhani', sans-serif;
    font-size: 1.1rem;
    font-weight: 700;
    text-align: center;
}

.prize-box {
    background: linear-gradient(135deg, rgba(40,30,5,0.9), rgba(20,15,2,0.95));
    border: 2px solid rgba(226,201,126,0.5);
    border-radius: 16px;
    padding: 2rem;
    text-align: center;
    margin: 1rem 0;
}

.big-prize {
    font-family: 'Cinzel', serif;
    font-size: clamp(2rem, 6vw, 4rem);
    font-weight: 900;
    background: linear-gradient(135deg, #ffe066, #f5b800, #fff1a8);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

/* Kategori / zorluk seçici stilleri */
div[data-testid="stSelectbox"] > div > div {
    background: rgba(10,30,70,0.9) !important;
    border: 1px solid rgba(226,201,126,0.3) !important;
    color: #e2c97e !important;
    border-radius: 8px !important;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: rgba(3,8,20,0.97) !important;
    border-right: 1px solid rgba(226,201,126,0.15) !important;
}

section[data-testid="stSidebar"] .stMarkdown {
    color: #e2c97e;
}

/* Divider */
hr {
    border-color: rgba(226,201,126,0.15) !important;
    margin: 1rem 0 !important;
}

/* Streamlit label rengi */
label, .stSelectbox label {
    color: #90afd4 !important;
    font-family: 'Rajdhani', sans-serif !important;
    font-weight: 600 !important;
    letter-spacing: 0.05em !important;
}

/* Number input */
div[data-testid="stNumberInput"] input {
    background: rgba(10,30,70,0.9) !important;
    color: #e2c97e !important;
    border: 1px solid rgba(226,201,126,0.3) !important;
}

/* Text input */
div[data-testid="stTextInput"] input {
    background: rgba(10,30,70,0.9) !important;
    color: #e2c97e !important;
    border: 1px solid rgba(226,201,126,0.3) !important;
    border-radius: 8px !important;
}

/* Spinner */
div[data-testid="stSpinner"] {
    color: #e2c97e !important;
}

/* Audio yoksa ses efekti için hidden component */
.audio-hidden {
    display: none;
}

/* Lifeline seçildi işareti */
.used-tag {
    display: inline-block;
    background: rgba(80,20,20,0.8);
    color: #ff6666;
    font-size: 0.7rem;
    padding: 1px 6px;
    border-radius: 4px;
    margin-left: 4px;
    vertical-align: middle;
}

</style>
""", unsafe_allow_html=True)


# ─── Sabitler ─────────────────────────────────────────────────────────────────
PRIZE_AMOUNTS = [
    1_000, 2_000, 3_000, 5_000, 10_000,
    20_000, 40_000, 75_000, 150_000, 300_000,
    500_000, 1_000_000, 2_000_000, 3_000_000, 5_000_000
]

GUARANTEED_LEVELS = {2: 3_000, 6: 20_000, 10: 500_000}  # 0-tabanlı index

CATEGORIES = {
    "Rastgele": None,
    "Genel Bilgi": 9,
    "Kitaplar": 10,
    "Film": 11,
    "Muzik": 12,
    "Televizyon": 14,
    "Video Oyunlari": 15,
    "Bilim & Doga": 17,
    "Bilgisayar": 18,
    "Matematik": 19,
    "Mitoloji": 20,
    "Spor": 21,
    "Cografya": 22,
    "Tarih": 23,
    "Sanat": 25,
    "Hayvanlar": 27,
}

DIFFICULTY_MAP = {
    "Kolay": "easy",
    "Orta": "medium",
    "Zor": "hard",
    "Karisik": None,
}

HOST_COMMENTS_CORRECT = [
    "Bravo! Turan Kaya gülümsüyor! Kesinlikle dogru!",
    "Harikasiniz! Turan size hayran kaldi!",
    "Dogru cevap! Turan Kaya: 'Bunu bilecektinizi hissediyordum!'",
    "Mukemmel! Stüdyo sizin icin ayaga kalkmak istiyor!",
    "Evet, evet, evet! Dogru! Turan Kaya tebrik ediyor!",
]

HOST_COMMENTS_WRONG = [
    "Maalesef... Turan Kaya derin bir ic cekis cekiyor.",
    "Ah... Yaninizda olsaydim kulaginiza fisildardim dogrusunu.",
    "Uzgünüm... Turan Kaya: 'Her zaman bir sonrakine!'",
    "Ne yazik ki yanlis. Ama bu yolculuk inanilmazdi!",
]

HOST_COMMENTS_LIFELINE = [
    "Joker kullaniyor! Turan Kaya merakla bekliyor...",
    "Zekice bir hamle! Turan Kaya onayliyor!",
    "Joker zamani! Her seyi kullanmak isteyebilirsiniz!",
]

FIFTY_FIFTY_COMMENTS = [
    "Elli - Elli! Bilgisayar iki yanlis seçenegi eledi. Simdi ne diyorsunuz?",
    "Yarisi gitti! Turan Kaya: 'Simdi daha mi kolay?'",
]

PHONE_COMMENTS = [
    "Bir arkadasa soruyorsunuz! Turan Kaya: 'Umuyorum ki arayacaginiz kisi bunu biliyor...'",
    "Telefon jokerini kullandınız! Bakalim arkadasiniz ne diyecek...",
]

AUDIENCE_COMMENTS = [
    "Seyirci yoklaması! Turan Kaya: 'Stüdyo ne diyecek acaba?'",
    "Seyirciler oyladi! Turan Kaya: 'Kitlenin bilgeligine guveniyor musunuz?'",
]


# ─── Yardımcı Fonksiyonlar ───────────────────────────────────────────────────
def format_prize(amount: int) -> str:
    return f"{amount:,} TL".replace(",", ".")


def get_guaranteed_prize(current_index: int) -> str:
    earned = 0
    for lvl, amt in GUARANTEED_LEVELS.items():
        if current_index > lvl:
            earned = amt
    if earned == 0:
        return "0 TL"
    return format_prize(earned)


def fetch_questions(amount=15, category=None, difficulty=None):
    params = {"amount": amount, "type": "multiple"}
    if category:
        params["category"] = category
    if difficulty:
        params["difficulty"] = difficulty
    try:
        r = requests.get("https://opentdb.com/api.php", params=params, timeout=10)
        data = r.json()
        if data["response_code"] != 0:
            return []
        questions = []
        for q in data["results"]:
            correct = html.unescape(q["correct_answer"])
            wrongs = [html.unescape(w) for w in q["incorrect_answers"]]
            options = wrongs + [correct]
            random.shuffle(options)
            questions.append({
                "question": html.unescape(q["question"]),
                "correct": correct,
                "options": options,
                "difficulty": q["difficulty"],
                "category": html.unescape(q["category"]),
            })
        return questions
    except Exception as e:
        st.error(f"Soru yuklenirken hata: {e}")
        return []


def groq_phone_friend(question: str, options: list, api_key: str) -> str:
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        opts_text = "\n".join([f"{chr(65+i)}) {o}" for i, o in enumerate(options)])
        prompt = (
            f"Sen bir bilgi yarismasi uzmanısın. Asagidaki soruyu ve seçenekleri incele, "
            f"en dogru cevabi ver. Sadece hangi seçenegi sectini ve kısa bir aciklama yap.\n\n"
            f"Soru: {question}\n\n{opts_text}"
        )
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Arkadasiniza ulasılamadi: {e}"


def audience_poll(options: list, correct: str) -> dict:
    """Seyirci oylamasi - dogru seçenege agirlik verir."""
    n = len(options)
    base = [random.randint(3, 12) for _ in range(n)]
    correct_idx = options.index(correct)
    base[correct_idx] += random.randint(35, 55)
    total = sum(base)
    return {opt: round(v / total * 100, 1) for opt, v in zip(options, base)}


def play_sound_js(sound_type: str):
    """Web Audio API ile basit ses efekti."""
    if sound_type == "correct":
        freq, duration, wave = 880, 0.4, "sine"
        notes = "[[0,660,0.15],[0.15,880,0.25]]"
    elif sound_type == "wrong":
        freq, duration, wave = 200, 0.6, "sawtooth"
        notes = "[[0,300,0.2],[0.2,200,0.4]]"
    elif sound_type == "tick":
        freq, duration, wave = 440, 0.08, "square"
        notes = f"[[0,{freq},0.08]]"
    else:
        return
    js = f"""
    <script>
    (function() {{
        var ctx = new (window.AudioContext || window.webkitAudioContext)();
        var notes = {notes};
        notes.forEach(function(n) {{
            var osc = ctx.createOscillator();
            var gain = ctx.createGain();
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.type = '{wave}';
            osc.frequency.value = n[1];
            gain.gain.setValueAtTime(0.2, ctx.currentTime + n[0]);
            gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + n[0] + n[2]);
            osc.start(ctx.currentTime + n[0]);
            osc.stop(ctx.currentTime + n[0] + n[2] + 0.05);
        }});
    }})();
    </script>
    """
    st.components.v1.html(js, height=0)


# ─── Session State Baslangici ─────────────────────────────────────────────────
def init_state():
    defaults = {
        "phase": "setup",          # setup | playing | result
        "questions": [],
        "q_index": 0,
        "score_index": -1,
        "lifelines": {
            "fifty_fifty": True,
            "phone": True,
            "audience": True,
        },
        "eliminated_options": [],
        "last_result": None,       # "correct" | "wrong"
        "host_message": "",
        "poll_result": None,
        "phone_result": None,
        "fifty_used_this_q": False,
        "audience_used_this_q": False,
        "phone_used_this_q": False,
        "groq_key": "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_state()
ss = st.session_state


# ─── Ödül Merdiveni Sidebar ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='font-family:Cinzel,serif; font-size:1.1rem; font-weight:700; 
                color:#e2c97e; text-align:center; letter-spacing:0.05em; margin-bottom:0.5rem;'>
        ODUL MERDIVENI
    </div>
    """, unsafe_allow_html=True)

    prize_html = ""
    for i in range(len(PRIZE_AMOUNTS) - 1, -1, -1):
        amt = PRIZE_AMOUNTS[i]
        classes = "prize-item"
        prefix = ""
        if i in GUARANTEED_LEVELS:
            classes += " guaranteed"
            prefix = "&#9733; "

        if ss["phase"] == "playing":
            if i == ss["q_index"]:
                classes += " current"
            elif i < ss["q_index"]:
                classes += " earned"

        prize_html += f"""
        <div class='{classes}'>
            <span>{prefix}{i+1}. Soru</span>
            <span>{format_prize(amt)}</span>
        </div>
        """

    st.markdown(prize_html, unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)

    if ss["phase"] in ["playing", "result"]:
        earned_prize = get_guaranteed_prize(ss["q_index"])
        st.markdown(f"""
        <div style='text-align:center; padding:0.5rem;'>
            <div style='color:#90afd4; font-size:0.75rem; letter-spacing:0.2em; font-family:Rajdhani,sans-serif;'>
                GARANTILI KAZANINIZ
            </div>
            <div style='color:#ff9966; font-family:Cinzel,serif; font-size:1.1rem; font-weight:700;'>
                {earned_prize}
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("""
    <div style='color:#555; font-size:0.7rem; text-align:center; 
                font-family:Rajdhani,sans-serif; letter-spacing:0.1em;'>
        SUNUCU: TURAN KAYA<br>
        <span style='color:#333;'>Kim Turanyoner Olmak Ister</span>
    </div>
    """, unsafe_allow_html=True)


# ─── Ana Başlık ───────────────────────────────────────────────────────────────
st.markdown("""
<div style='text-align:center; padding:1rem 0 0.5rem 0;'>
    <div class='show-title'>KIM TURANYONER OLMAK ISTER</div>
    <div class='host-name'>Sunucu: Turan Kaya</div>
</div>
""", unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)


# ─── SETUP EKRANI ─────────────────────────────────────────────────────────────
if ss["phase"] == "setup":
    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        st.markdown("""
        <div class='info-box' style='text-align:center; margin-bottom:1.5rem;'>
            <div style='font-family:Cinzel,serif; font-size:1.2rem; color:#e2c97e; margin-bottom:0.5rem;'>
                Buyuk Odule Hazir Misiniz?
            </div>
            <div style='color:#90afd4;'>
                15 soruda 5.000.000 TL kazanabilirsiniz!<br>
                3 joker hakkınız var. Iyi sanslar!
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Groq key secrets'tan otomatik okunuyor
        ss["groq_key"] = st.secrets.get("GROQ_API_KEY", "")

        cat_choice = st.selectbox("Kategori Secin", list(CATEGORIES.keys()))
        diff_choice = st.selectbox("Zorluk Secin", list(DIFFICULTY_MAP.keys()))

        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("YARISMAYA BASLA", use_container_width=True):
            with st.spinner("Sorular hazirlaniyor..."):
                questions = fetch_questions(
                    amount=15,
                    category=CATEGORIES[cat_choice],
                    difficulty=DIFFICULTY_MAP[diff_choice],
                )
            if len(questions) < 5:
                st.error("Yeterli soru yuklenemedi. Lutfen farkli bir kategori veya zorluk secin.")
            else:
                ss["questions"] = questions[:15]
                ss["phase"] = "playing"
                ss["q_index"] = 0
                ss["score_index"] = -1
                ss["lifelines"] = {"fifty_fifty": True, "phone": True, "audience": True}
                ss["eliminated_options"] = []
                ss["last_result"] = None
                ss["host_message"] = "Hos geldiniz! Turan Kaya stüdyoda sizi bekliyor! Ilk soruyla baslayalim..."
                ss["poll_result"] = None
                ss["phone_result"] = None
                ss["fifty_used_this_q"] = False
                ss["audience_used_this_q"] = False
                ss["phone_used_this_q"] = False
                st.rerun()

        st.markdown("""
        <div style='margin-top:2rem;'>
        <div class='info-box'>
            <div style='font-family:Cinzel,serif; color:#e2c97e; margin-bottom:0.5rem;'>JOKER HAKLARI</div>
            <b style='color:#ff9966;'>50:50</b> — Bilgisayar iki yanlis seçenegi eler<br>
            <b style='color:#ff9966;'>Bir Arkadasa Sor</b> — Groq Yapay Zekasi yorumlar<br>
            <b style='color:#ff9966;'>Seyirci Oylamasi</b> — Stüdyo oyluyor
        </div>
        <div class='info-box'>
            <div style='font-family:Cinzel,serif; color:#e2c97e; margin-bottom:0.5rem;'>GARANTI ODULLERI</div>
            3. soruda <b style='color:#ff9966;'>3.000 TL</b> garanti<br>
            7. soruda <b style='color:#ff9966;'>20.000 TL</b> garanti<br>
            11. soruda <b style='color:#ff9966;'>500.000 TL</b> garanti
        </div>
        </div>
        """, unsafe_allow_html=True)


# ─── OYUN EKRANI ──────────────────────────────────────────────────────────────
elif ss["phase"] == "playing":
    q_data = ss["questions"][ss["q_index"]]
    current_options = q_data["options"][:]

    # ── Sunucu Mesaji
    if ss["host_message"]:
        st.markdown(f"""
        <div class='info-box'>
            <span style='color:#e2c97e; font-weight:700;'>Turan Kaya:</span> 
            {ss['host_message']}
        </div>
        """, unsafe_allow_html=True)

    # ── Joker Butonları
    j1, j2, j3, j4 = st.columns([1, 1, 1, 0.5])

    with j1:
        with st.container():
            st.markdown('<div class="joker-btn">', unsafe_allow_html=True)
            fifty_label = "50 : 50" + ("  [KULLANILDI]" if not ss["lifelines"]["fifty_fifty"] else "")
            if st.button(fifty_label, disabled=not ss["lifelines"]["fifty_fifty"], key="btn_fifty"):
                ss["lifelines"]["fifty_fifty"] = False
                # Yanlis seçeneklerden 2 tanesini ele
                wrongs = [o for o in current_options if o != q_data["correct"]]
                to_remove = random.sample(wrongs, min(2, len(wrongs)))
                ss["eliminated_options"] = to_remove
                ss["fifty_used_this_q"] = True
                ss["host_message"] = random.choice(FIFTY_FIFTY_COMMENTS)
                ss["poll_result"] = None
                ss["phone_result"] = None
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    with j2:
        with st.container():
            st.markdown('<div class="joker-btn">', unsafe_allow_html=True)
            phone_label = "Arkadasa Sor" + ("  [KULLANILDI]" if not ss["lifelines"]["phone"] else "")
            if st.button(phone_label, disabled=not ss["lifelines"]["phone"], key="btn_phone"):
                if not ss["groq_key"]:
                    st.warning("Groq API anahtari bulunamadi! secrets.toml dosyasina GROQ_API_KEY ekleyin.")
                else:
                    ss["lifelines"]["phone"] = False
                    ss["phone_used_this_q"] = True
                    visible_opts = [o for o in current_options if o not in ss["eliminated_options"]]
                    with st.spinner("Arkadasiniz dusünüyor..."):
                        answer = groq_phone_friend(q_data["question"], visible_opts, ss["groq_key"])
                    ss["phone_result"] = answer
                    ss["host_message"] = random.choice(PHONE_COMMENTS)
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    with j3:
        with st.container():
            st.markdown('<div class="joker-btn">', unsafe_allow_html=True)
            aud_label = "Seyirci Sor" + ("  [KULLANILDI]" if not ss["lifelines"]["audience"] else "")
            if st.button(aud_label, disabled=not ss["lifelines"]["audience"], key="btn_audience"):
                ss["lifelines"]["audience"] = False
                ss["audience_used_this_q"] = True
                visible_opts = [o for o in current_options if o not in ss["eliminated_options"]]
                poll = audience_poll(visible_opts, q_data["correct"])
                ss["poll_result"] = poll
                ss["host_message"] = random.choice(AUDIENCE_COMMENTS)
                ss["phone_result"] = None
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    with j4:
        with st.container():
            st.markdown('<div class="joker-btn">', unsafe_allow_html=True)
            if st.button("Cekil", key="btn_quit"):
                earned = get_guaranteed_prize(ss["q_index"])
                ss["last_result"] = "quit"
                ss["phase"] = "result"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Soru Kutusu
    diff_color = {"easy": "#4caf50", "medium": "#ff9800", "hard": "#f44336"}.get(q_data["difficulty"], "#90afd4")
    diff_label = {"easy": "KOLAY", "medium": "ORTA", "hard": "ZOR"}.get(q_data["difficulty"], "")

    st.markdown(f"""
    <div class='question-box'>
        <div>
            <span class='question-number-badge'>SORU {ss['q_index']+1} / 15</span>
            &nbsp;
            <span style='font-size:0.7rem; color:{diff_color}; font-family:Rajdhani,sans-serif; 
                         font-weight:700; letter-spacing:0.2em;'>{diff_label}</span>
        </div>
        <div style='margin-top:0.5rem; position:relative; z-index:1;'>
            {q_data['question']}
        </div>
        <div style='font-size:0.72rem; color:#445; margin-top:0.5rem; font-family:Rajdhani,sans-serif;'>
            {q_data['category']}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Joker Sonuclari
    if ss["phone_result"]:
        st.markdown(f"""
        <div class='info-box'>
            <b style='color:#e2c97e;'>Arkadasiniz diyor ki:</b><br>
            {ss['phone_result']}
        </div>
        """, unsafe_allow_html=True)

    if ss["poll_result"]:
        st.markdown("<div style='margin: 0.5rem 0;'>", unsafe_allow_html=True)
        poll_html = "<div class='info-box'><b style='color:#e2c97e;'>Seyirci Oylamasi:</b><br>"
        for opt, pct in sorted(ss["poll_result"].items(), key=lambda x: -x[1]):
            bar_w = int(pct)
            poll_html += f"""
            <div style='margin:4px 0; font-family:Rajdhani,sans-serif;'>
                <span style='color:#c8daf5; display:inline-block; width:45%; 
                             overflow:hidden; text-overflow:ellipsis; white-space:nowrap; 
                             vertical-align:middle; font-size:0.85rem;'>{opt}</span>
                <div style='display:inline-block; width:50%; vertical-align:middle; 
                            background:rgba(255,255,255,0.05); border-radius:4px; height:14px;'>
                    <div style='width:{min(bar_w,100)}%; background:linear-gradient(90deg,#1565c0,#42a5f5); 
                                height:100%; border-radius:4px;'></div>
                </div>
                <span style='color:#ffe066; font-weight:700; font-size:0.85rem; margin-left:6px;'>{pct}%</span>
            </div>
            """
        poll_html += "</div>"
        st.markdown(poll_html, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Cevap Butonları (2x2 grid)
    visible_opts = [o for o in current_options if o not in ss["eliminated_options"]]
    letters = ["A", "B", "C", "D"]

    all_opts_with_letter = [(letters[i], o) for i, o in enumerate(current_options)]
    
    rows = [all_opts_with_letter[:2], all_opts_with_letter[2:]]
    for row in rows:
        cols = st.columns(len(row))
        for ci, (col, (letter, option)) in enumerate(zip(cols, row)):
            with col:
                if option in ss["eliminated_options"]:
                    st.markdown(f"""
                    <div style='background:rgba(5,10,30,0.5); border:1px solid rgba(50,50,80,0.3);
                                border-radius:10px; padding:0.7rem 1.2rem; color:rgba(100,100,130,0.4);
                                font-family:Rajdhani,sans-serif; font-size:1rem; text-align:left;
                                min-height:3rem; display:flex; align-items:center;'>
                        <b style='margin-right:0.5rem;'>{letter})</b> — — —
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    if st.button(f"{letter})  {option}", key=f"ans_{ss['q_index']}_{ci}_{option[:10]}",
                                  use_container_width=True):
                        if option == q_data["correct"]:
                            ss["score_index"] = ss["q_index"]
                            ss["host_message"] = random.choice(HOST_COMMENTS_CORRECT)
                            ss["last_result"] = "correct"
                            play_sound_js("correct")
                            if ss["q_index"] == 14:
                                ss["phase"] = "result"
                            else:
                                ss["q_index"] += 1
                                ss["eliminated_options"] = []
                                ss["poll_result"] = None
                                ss["phone_result"] = None
                                ss["fifty_used_this_q"] = False
                                ss["audience_used_this_q"] = False
                                ss["phone_used_this_q"] = False
                        else:
                            ss["last_result"] = "wrong"
                            ss["host_message"] = random.choice(HOST_COMMENTS_WRONG)
                            ss["correct_answer_reveal"] = q_data["correct"]
                            play_sound_js("wrong")
                            ss["phase"] = "result"
                        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Mevcut Ödül
    st.markdown(f"""
    <div style='text-align:center; font-family:Rajdhani,sans-serif;'>
        <span style='color:#666; font-size:0.8rem; letter-spacing:0.2em;'>BU SORUNUN ODULU</span><br>
        <span style='color:#ffe066; font-family:Cinzel,serif; font-size:1.5rem; font-weight:700;'>
            {format_prize(PRIZE_AMOUNTS[ss['q_index']])}
        </span>
    </div>
    """, unsafe_allow_html=True)


# ─── SONUC EKRANI ─────────────────────────────────────────────────────────────
elif ss["phase"] == "result":

    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:

        if ss["last_result"] == "correct" and ss["score_index"] == 14:
            # BUYUK KAZANAN!
            st.markdown("""
            <div style='text-align:center; margin:1rem 0;'>
                <div style='font-family:Cinzel,serif; font-size:1.5rem; color:#ffe066; 
                            letter-spacing:0.1em; margin-bottom:1rem;'>
                    MUHTESEM! INANILMAZ!
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown(f"""
            <div class='prize-box'>
                <div style='color:#90afd4; font-family:Rajdhani,sans-serif; 
                            font-size:1rem; letter-spacing:0.2em; margin-bottom:0.5rem;'>
                    KAZANDINIZ
                </div>
                <div class='big-prize'>{format_prize(PRIZE_AMOUNTS[14])}</div>
                <div style='color:#ff9966; font-family:Cinzel,serif; margin-top:0.5rem;'>
                    BUYUK ODUL!
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("""
            <div class='correct-box'>
                Tebrikler! Turanyoner oldunuz!<br>
                Turan Kaya: "Bu tarihi bir an! Stüdyoyu yikiniz!"
            </div>
            """, unsafe_allow_html=True)
            play_sound_js("correct")

        elif ss["last_result"] == "wrong":
            guaranteed = get_guaranteed_prize(ss["q_index"])
            reveal = ss.get("correct_answer_reveal", "")
            st.markdown(f"""
            <div class='wrong-box'>
                Yanlis cevap! Uzgunuz...<br>
                <span style='font-size:0.85rem; color:#ccc;'>Dogru cevap: {reveal}</span>
            </div>
            """, unsafe_allow_html=True)

            earned_idx = -1
            for lvl in sorted(GUARANTEED_LEVELS.keys(), reverse=True):
                if ss["q_index"] > lvl:
                    earned_idx = lvl
                    break

            earned_amount = PRIZE_AMOUNTS[earned_idx] if earned_idx >= 0 else 0

            st.markdown(f"""
            <div class='prize-box'>
                <div style='color:#90afd4; font-family:Rajdhani,sans-serif; 
                            font-size:1rem; letter-spacing:0.2em; margin-bottom:0.5rem;'>
                    KAZANDINIZ
                </div>
                <div class='big-prize'>{format_prize(earned_amount)}</div>
                <div style='color:#90afd4; font-family:Rajdhani,sans-serif; margin-top:0.5rem;'>
                    Garanti ödülünüz
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown(f"""
            <div class='info-box'>
                Turan Kaya: "{random.choice(HOST_COMMENTS_WRONG)}"
            </div>
            """, unsafe_allow_html=True)

        elif ss["last_result"] == "quit":
            if ss["score_index"] >= 0:
                earned_amount = PRIZE_AMOUNTS[ss["score_index"]]
            else:
                earned_amount = 0

            for lvl in sorted(GUARANTEED_LEVELS.keys(), reverse=True):
                if ss["q_index"] > lvl:
                    earned_amount = max(earned_amount, PRIZE_AMOUNTS[lvl])
                    break

            st.markdown(f"""
            <div class='prize-box'>
                <div style='color:#90afd4; font-family:Rajdhani,sans-serif; 
                            font-size:1rem; letter-spacing:0.2em; margin-bottom:0.5rem;'>
                    CEKILDINIZ — KAZANDINIZ
                </div>
                <div class='big-prize'>{format_prize(earned_amount)}</div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("""
            <div class='info-box'>
                Turan Kaya: "Cesur bir karar! Kazancınız emin ellerde. Tekrar bekleriz!"
            </div>
            """, unsafe_allow_html=True)

        elif ss["last_result"] == "correct":
            # Aslında buraya 14. soru dogru cevaplanınca gelir - zaten yukarıda hallettik
            pass

        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("YENIDEN OYNA", use_container_width=True):
            for k in ["phase", "questions", "q_index", "score_index", "lifelines",
                      "eliminated_options", "last_result", "host_message",
                      "poll_result", "phone_result", "fifty_used_this_q",
                      "audience_used_this_q", "phone_used_this_q", "correct_answer_reveal"]:
                if k in ss:
                    del st.session_state[k]
            init_state()
            st.rerun()
