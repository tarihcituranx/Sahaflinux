import streamlit as st
import requests
import html
import random
import json
import time
import os

# ─── Sayfa Ayarları ───────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Kim Turanyoner Olmak Ister",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700;900&family=Rajdhani:wght@300;400;600;700&display=swap');
*, *::before, *::after { box-sizing: border-box; }
html, body, .stApp { background: #000814 !important; color: #e2c97e !important; font-family: 'Rajdhani', sans-serif !important; }
.stApp::before { content:''; position:fixed; inset:0; pointer-events:none; z-index:0;
    background: radial-gradient(ellipse 80% 50% at 50% 0%, rgba(14,58,120,0.35) 0%, transparent 70%),
                radial-gradient(ellipse 60% 40% at 50% 100%, rgba(100,20,20,0.2) 0%, transparent 70%); }
.show-title { font-family:'Cinzel',serif; font-size:clamp(1.4rem,4vw,2.8rem); font-weight:900;
    text-align:center; letter-spacing:0.05em; margin-bottom:0.1rem; line-height:1.1;
    background:linear-gradient(135deg,#ffe066,#e2c97e,#f5b800,#fff1a8,#e2c97e); background-size:300% 300%;
    animation:shimmer 4s ease infinite; -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text; }
.host-name { font-family:'Rajdhani',sans-serif; font-size:1rem; color:#90afd4; text-align:center; letter-spacing:0.3em; text-transform:uppercase; margin-bottom:1rem; }
@keyframes shimmer { 0%{background-position:0% 50%} 50%{background-position:100% 50%} 100%{background-position:0% 50%} }
@keyframes pulse-red { 0%,100%{opacity:1} 50%{opacity:0.4} }
.question-box { background:linear-gradient(145deg,rgba(10,30,70,0.95),rgba(5,15,40,0.98));
    border:1px solid rgba(226,201,126,0.3); border-radius:16px; padding:2rem 2.5rem; text-align:center;
    font-family:'Rajdhani',sans-serif; font-size:clamp(1rem,2.5vw,1.4rem); font-weight:600; color:#ffffff;
    line-height:1.5; margin-bottom:1.5rem; box-shadow:0 0 40px rgba(14,58,120,0.4); }
.question-number-badge { display:inline-block; background:linear-gradient(135deg,#f5b800,#e2c97e); color:#000;
    font-family:'Cinzel',serif; font-weight:700; font-size:0.75rem; padding:0.25rem 0.9rem; border-radius:20px; letter-spacing:0.1em; margin-bottom:0.8rem; }
.stButton > button { width:100% !important; background:linear-gradient(145deg,rgba(10,30,80,0.9),rgba(5,15,50,0.95)) !important;
    color:#e2c97e !important; border:1px solid rgba(226,201,126,0.35) !important; border-radius:10px !important;
    font-family:'Rajdhani',sans-serif !important; font-size:1rem !important; font-weight:600 !important;
    padding:0.7rem 1.2rem !important; transition:all 0.2s ease !important; text-align:left !important; }
.stButton > button:hover { background:linear-gradient(145deg,rgba(30,70,160,0.95),rgba(15,40,100,0.98)) !important;
    border-color:rgba(226,201,126,0.7) !important; box-shadow:0 0 18px rgba(226,201,126,0.25) !important; transform:translateY(-1px) !important; }
.joker-btn > button { background:linear-gradient(145deg,rgba(60,20,5,0.9),rgba(40,10,2,0.95)) !important;
    border-color:rgba(200,80,20,0.5) !important; color:#ff9966 !important; font-size:0.85rem !important; text-align:center !important; }
.joker-btn > button:hover { background:linear-gradient(145deg,rgba(120,40,10,0.95),rgba(80,20,5,0.98)) !important;
    border-color:rgba(255,120,50,0.8) !important; box-shadow:0 0 18px rgba(200,80,20,0.35) !important; }
.joker-btn > button:disabled { opacity:0.3 !important; cursor:not-allowed !important; }
.confirm-box { background:linear-gradient(145deg,rgba(5,20,60,0.98),rgba(2,10,30,0.99));
    border:2px solid rgba(226,201,126,0.6); border-radius:14px; padding:1.5rem 2rem; margin:1rem 0; text-align:center;
    box-shadow:0 0 40px rgba(226,201,126,0.2); }
.prize-item { font-family:'Rajdhani',sans-serif; font-size:0.9rem; font-weight:600; padding:0.25rem 0.7rem;
    border-radius:6px; margin:2px 0; display:flex; justify-content:space-between; color:#90afd4; }
.prize-item.current { background:linear-gradient(90deg,rgba(226,201,126,0.2),rgba(245,184,0,0.1));
    color:#ffe066; border-left:3px solid #f5b800; font-size:1rem; font-weight:700; }
.prize-item.earned { color:#4caf50; }
.prize-item.guaranteed { color:#ff9966; font-weight:700; }
.prize-item.guaranteed.earned { color:#4caf50; }
.info-box { background:rgba(10,30,80,0.7); border:1px solid rgba(226,201,126,0.2); border-radius:10px;
    padding:1rem 1.5rem; margin:0.8rem 0; font-family:'Rajdhani',sans-serif; font-size:1rem; color:#c8daf5; line-height:1.5; }
.correct-box { background:rgba(20,80,20,0.7); border:1px solid rgba(100,200,100,0.4); border-radius:10px;
    padding:1rem 1.5rem; margin:0.8rem 0; color:#a8ffb0; font-family:'Rajdhani',sans-serif; font-size:1.1rem; font-weight:700; text-align:center; }
.wrong-box { background:rgba(80,10,10,0.7); border:1px solid rgba(200,60,60,0.4); border-radius:10px;
    padding:1rem 1.5rem; margin:0.8rem 0; color:#ffaaaa; font-family:'Rajdhani',sans-serif; font-size:1.1rem; font-weight:700; text-align:center; }
.prize-box { background:linear-gradient(135deg,rgba(40,30,5,0.9),rgba(20,15,2,0.95));
    border:2px solid rgba(226,201,126,0.5); border-radius:16px; padding:2rem; text-align:center; margin:1rem 0; }
.big-prize { font-family:'Cinzel',serif; font-size:clamp(2rem,6vw,4rem); font-weight:900;
    background:linear-gradient(135deg,#ffe066,#f5b800,#fff1a8); -webkit-background-clip:text;
    -webkit-text-fill-color:transparent; background-clip:text; }
div[data-testid="stSelectbox"] > div > div { background:rgba(10,30,70,0.9) !important; border:1px solid rgba(226,201,126,0.3) !important; color:#e2c97e !important; border-radius:8px !important; }
section[data-testid="stSidebar"] { background:rgba(3,8,20,0.97) !important; border-right:1px solid rgba(226,201,126,0.15) !important; }
label { color:#90afd4 !important; font-family:'Rajdhani',sans-serif !important; font-weight:600 !important; }
div[data-testid="stTextInput"] input { background:rgba(10,30,70,0.9) !important; color:#e2c97e !important; border:1px solid rgba(226,201,126,0.3) !important; border-radius:8px !important; }
hr { border-color:rgba(226,201,126,0.15) !important; margin:1rem 0 !important; }
</style>
""", unsafe_allow_html=True)

# ─── Sabitler ─────────────────────────────────────────────────────────────────
PRIZE_AMOUNTS = [
    1_000, 2_000, 3_000, 5_000, 10_000,
    20_000, 40_000, 75_000, 150_000, 300_000,
    500_000, 1_000_000, 2_000_000, 3_000_000, 5_000_000
]
GUARANTEED_LEVELS = {2: 3_000, 6: 20_000, 10: 500_000}

def get_time_limit(q_index):
    if q_index < 5:  return 45
    if q_index < 10: return 35
    return 25

CATEGORIES = {
    "Rastgele": None, "Genel Bilgi": 9, "Kitaplar": 10, "Film": 11, "Muzik": 12,
    "Televizyon": 14, "Video Oyunlari": 15, "Bilim & Doga": 17, "Bilgisayar": 18,
    "Matematik": 19, "Mitoloji": 20, "Spor": 21, "Cografya": 22, "Tarih": 23,
    "Sanat": 25, "Hayvanlar": 27,
}
DIFFICULTY_MAP = {"Kolay": "easy", "Orta": "medium", "Zor": "hard", "Karisik": None}

CATEGORY_TR = {
    "General Knowledge": "Genel Kultur", "Entertainment: Books": "Eglence: Kitaplar",
    "Entertainment: Film": "Eglence: Filmler", "Entertainment: Music": "Eglence: Muzik",
    "Entertainment: Musicals & Theatres": "Eglence: Muzikal & Tiyatro",
    "Entertainment: Television": "Eglence: Televizyon",
    "Entertainment: Video Games": "Eglence: Video Oyunlari",
    "Entertainment: Board Games": "Eglence: Kutu Oyunlari",
    "Science & Nature": "Bilim & Doga", "Science: Computers": "Bilim: Bilgisayar",
    "Science: Mathematics": "Bilim: Matematik", "Science: Gadgets": "Bilim: Teknoloji",
    "Mythology": "Mitoloji", "Sports": "Spor", "Geography": "Cografya",
    "History": "Tarih", "Politics": "Siyaset", "Art": "Sanat",
    "Celebrities": "Unluler", "Animals": "Hayvanlar", "Vehicles": "Tasitlar",
    "Entertainment: Comics": "Eglence: Cizgi Roman",
    "Entertainment: Japanese Anime & Manga": "Eglence: Anime & Manga",
    "Entertainment: Cartoon & Animations": "Eglence: Cizgi Film",
}

JOKER_LABELS = {"fifty_fifty": "50:50", "phone": "Arkadasa Sor", "audience": "Seyirci Oylamasi"}
JOKER_CONFIRM = {
    "fifty_fifty": ["Iki sik gidecek — hangileri olacak? Turan Kaya merakla bakiyor...",
                    "Yarısını siliyoruz mu? Turan Kaya: 'Dusundunuz mu iyi?'",
                    "Bilgisayar iki sikki silecek. Emin misiniz?"],
    "phone":       ["Bir arkadasiniza danismak istiyorsunuz. Turan Kaya: 'Umarim dogru kisiyi ariyorsunuz...'",
                    "Telefon jokeri... Turan Kaya: 'Bu arkadasiniz guvenilir biri mi?'",
                    "Arayacak misiniz? Turan Kaya: 'Arkadasiniz bu soruyu biliyor mu acaba?'"],
    "audience":    ["Seyirciyi sormak istiyorsunuz. Turan Kaya: 'Studyo ne diyecek bakalim...'",
                    "Kalabaliga danisiyorsunuz. Turan Kaya: 'Bilgi ucmaz, ama halk yanilabilir!'",
                    "Seyirci yoklamasi... Turan Kaya: 'Bazen halk cok zekidir. Bazen...'"],
}
RATE_LIMIT_FILE = "/tmp/kto_ratelimit.json"


# ─── Yardımcı Fonksiyonlar ────────────────────────────────────────────────────
def format_prize(amount):
    return f"{amount:,} TL".replace(",", ".")

def get_guaranteed_amount(q_index):
    earned = 0
    for lvl, amt in GUARANTEED_LEVELS.items():
        if q_index > lvl:
            earned = amt
    return earned

def play_sound_js(sound_type):
    if sound_type == "correct":
        notes, wave = "[[0,660,0.12],[0.12,880,0.3]]", "sine"
    elif sound_type == "wrong":
        notes, wave = "[[0,300,0.15],[0.15,200,0.4]]", "sawtooth"
    else:
        return
    st.components.v1.html(f"""<script>(function(){{try{{var ctx=new(window.AudioContext||window.webkitAudioContext)();
    {notes}.forEach(function(n){{var o=ctx.createOscillator(),g=ctx.createGain();o.connect(g);g.connect(ctx.destination);
    o.type='{wave}';o.frequency.value=n[1];g.gain.setValueAtTime(0.18,ctx.currentTime+n[0]);
    g.gain.exponentialRampToValueAtTime(0.001,ctx.currentTime+n[0]+n[2]);
    o.start(ctx.currentTime+n[0]);o.stop(ctx.currentTime+n[0]+n[2]+0.05);}})}}catch(e){{}}}})()</script>""", height=0)

def load_rate_limits():
    try:
        if os.path.exists(RATE_LIMIT_FILE):
            with open(RATE_LIMIT_FILE) as f: return json.load(f)
    except: pass
    return {}

def save_rate_limits(data):
    try:
        with open(RATE_LIMIT_FILE, "w") as f: json.dump(data, f)
    except: pass

def check_rate_limit(player_name):
    if not player_name.strip(): return False, "Lutfen adinizi girin."
    rl = load_rate_limits()
    key = player_name.strip().lower()
    now = time.time()
    if key in rl:
        entry = rl[key]
        cooldown = 7200 if entry.get("won_jackpot") else 3600
        elapsed = now - entry.get("last_game", 0)
        if elapsed < cooldown:
            rem = int((cooldown - elapsed) / 60)
            if entry.get("won_jackpot"):
                return False, f"Buyuk odulu kazandiniz! Bir sonraki oyun icin {rem} dakika beklemeniz gerekiyor."
            return False, f"Saatte 1 yarisma oynanabilir. {rem} dakika sonra tekrar gelin!"
    return True, ""

def record_game(player_name, jackpot=False):
    rl = load_rate_limits()
    key = player_name.strip().lower()
    if key not in rl: rl[key] = {}
    rl[key]["last_game"] = time.time()
    if jackpot: rl[key]["won_jackpot"] = True
    save_rate_limits(rl)

def fetch_questions(amount=15, category=None, difficulty=None):
    params = {"amount": amount, "type": "multiple"}
    if category: params["category"] = category
    if difficulty: params["difficulty"] = difficulty
    try:
        r = requests.get("https://opentdb.com/api.php", params=params, timeout=10)
        data = r.json()
        if data["response_code"] != 0: return []
        qs = []
        for q in data["results"]:
            correct = html.unescape(q["correct_answer"])
            wrongs  = [html.unescape(w) for w in q["incorrect_answers"]]
            opts = wrongs + [correct]; random.shuffle(opts)
            qs.append({"question": html.unescape(q["question"]), "correct": correct,
                       "options": opts, "difficulty": q["difficulty"], "category": html.unescape(q["category"])})
        return qs
    except Exception as e:
        st.error(f"Soru yuklenirken hata: {e}"); return []

def _extract_json(raw: str):
    """JSON bloğunu güvenli şekilde ayıklar."""
    raw = raw.strip()
    # ```json ... ``` veya ``` ... ``` bloğu
    if "```" in raw:
        parts = raw.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("[") or part.startswith("{"):
                return part
    # Direkt JSON
    start = raw.find("[")
    end   = raw.rfind("]") + 1
    if start != -1 and end > start:
        return raw[start:end]
    return raw

def _translate_batch(client, batch: list) -> dict:
    """Bir grup soruyu çevirir, {id: translated_item} döner."""
    system = (
        "Sen bir Türkçe çevirmen yapay zekasısın. "
        "Sana verilen JSON dizisindeki bilgi yarışması sorularını ve şıklarını Türkçeye çeviriyorsun. "
        "Özel isimler, yer adları, marka adları ve bilimsel terimler (element adları, türler vb.) orijinal haliyle kalmalı. "
        "Çeviri doğal ve akıcı Türkçe olmalı. "
        "SADECE geçerli bir JSON dizisi döndür, başka hiçbir şey yazma."
    )
    user = (
        "Aşağıdaki JSON dizisini çevir. Her öğedeki 'question', 'correct' ve 'options' alanlarını Türkçeye çevir. "
        "'id' alanını kesinlikle değiştirme. Sadece JSON döndür:\n\n"
        + json.dumps(batch, ensure_ascii=False)
    )
    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        max_tokens=3000,
        temperature=0.1,
    )
    raw = resp.choices[0].message.content
    parsed = json.loads(_extract_json(raw))
    return {item["id"]: item for item in parsed}

def translate_questions(questions, api_key):
    """Soruları 5'erli gruplar halinde Türkçeye çevirir."""
    if not api_key:
        return questions
    try:
        from groq import Groq
        client = Groq(api_key=api_key)

        payload = [
            {"id": i, "question": q["question"], "correct": q["correct"], "options": q["options"]}
            for i, q in enumerate(questions)
        ]

        # 5'erli batch — token limitini aşmamak için
        BATCH = 5
        tr_map = {}
        for start in range(0, len(payload), BATCH):
            batch = payload[start:start+BATCH]
            try:
                tr_map.update(_translate_batch(client, batch))
            except Exception as batch_err:
                # Bu batch başarısız olduysa orijinal kalsın, devam et
                st.toast(f"Batch {start//BATCH+1} çevrilemedi, orijinal kullanılıyor.")

        # Çevirileri uygula
        for i, q in enumerate(questions):
            if i in tr_map:
                t = tr_map[i]
                q["question"] = t.get("question", q["question"])
                new_opts    = t.get("options", q["options"])
                new_correct = t.get("correct", q["correct"])
                if len(new_opts) == len(q["options"]):
                    q["options"]  = new_opts
                    q["correct"]  = new_correct
        return questions

    except Exception as e:
        st.warning(f"Çeviri başlatılamadı: {e}")
        return questions

def groq_phone_friend(question, options, api_key):
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        opts = "\n".join([f"{chr(65+i)}) {o}" for i, o in enumerate(options)])
        resp = client.chat.completions.create(model="llama-3.3-70b-versatile",
            messages=[{"role":"user","content": f"Sen bir bilgi yarismasi uzmanis. Soruyu ve secenek incel, dogru cevabi ver. Kisa ve net yaz.\n\nSoru: {question}\n\n{opts}"}],
            max_tokens=200)
        return resp.choices[0].message.content
    except Exception as e:
        return f"Arkadasiniza ulasilamadi: {e}"

def groq_host_comment(situation, context, api_key):
    """Turan Kaya ozgun yorum uretir."""
    if not api_key: return ""
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        prompt = (f"Sen 'Kim Turanyoner Olmak Ister?' adli bilgi yarismasi sunucusu Turan Kaya'sin. "
                  f"Turk televizyon sunucu tarzi, esprili, mizahi, bazen igneleyici ama sevecen. "
                  f"1-2 cumle Turkce ozgun yorum yap. Klise olmayan, gercekten komik bir sey soy. "
                  f"Bazen oyuncunun adini kullan, bazen soruyla ilgili bir espri yap.\n"
                  f"Durum: {situation}\nBagiam: {json.dumps(context, ensure_ascii=False)}\n"
                  f"Sadece yorumu yaz:")
        resp = client.chat.completions.create(model="llama-3.3-70b-versatile",
            messages=[{"role":"user","content":prompt}], max_tokens=120, temperature=0.95)
        return resp.choices[0].message.content.strip().strip('"')
    except: return ""

def audience_poll(options, correct):
    base = [random.randint(3, 12) for _ in options]
    base[options.index(correct)] += random.randint(35, 55)
    total = sum(base)
    return {opt: round(v/total*100, 1) for opt, v in zip(options, base)}

def get_timer_elapsed():
    """Gercek gecen sureyi hesapla (duraklatma dahil)."""
    ss = st.session_state
    if ss["q_start_time"] is None: return 0.0
    offset = ss["timer_offset"]
    if ss["paused_at"] is not None:
        offset += time.time() - ss["paused_at"]
    return max(0.0, time.time() - ss["q_start_time"] - offset)

def render_timer(q_index, paused=False):
    ss = st.session_state
    tl = get_time_limit(q_index)
    elapsed = get_timer_elapsed()
    remaining = max(0, tl - int(elapsed))
    pct = remaining / tl * 100
    color = "#4caf50" if pct > 50 else ("#ff9800" if pct > 25 else "#f44336")
    tier = "1-5. SORULAR (45s)" if q_index < 5 else ("6-10. SORULAR (35s)" if q_index < 10 else "11-15. SORULAR (25s)")
    pulse = "animation:pulse-red 0.5s ease infinite;" if (pct <= 20 and not paused) else ""
    label = "DURAKLATILDI" if paused else f"{remaining}s"
    st.markdown(f"""
    <div style='margin:0.3rem 0 0.8rem 0;'>
        <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;'>
            <span style='font-family:Rajdhani,sans-serif;font-size:0.72rem;color:#555;letter-spacing:0.15em;'>{tier}</span>
            <span style='font-family:Cinzel,serif;font-size:1.4rem;font-weight:700;color:{color};{pulse}'>{label}</span>
        </div>
        <div style='width:100%;background:rgba(255,255,255,0.06);border-radius:8px;height:10px;overflow:hidden;'>
            <div style='width:{pct:.1f}%;height:100%;background:linear-gradient(90deg,{color},rgba(255,255,255,0.5));border-radius:8px;{pulse}'></div>
        </div>
    </div>""", unsafe_allow_html=True)
    return remaining

def render_question_box(q_data, q_index):
    diff_color = {"easy":"#4caf50","medium":"#ff9800","hard":"#f44336"}.get(q_data["difficulty"],"#90afd4")
    diff_label = {"easy":"KOLAY","medium":"ORTA","hard":"ZOR"}.get(q_data["difficulty"],"")
    cat = q_data["category"]
    cat_display = f"{cat} ({CATEGORY_TR[cat]})" if cat in CATEGORY_TR else cat
    st.markdown(f"""
    <div class='question-box'>
        <div><span class='question-number-badge'>SORU {q_index+1} / 15</span>
             &nbsp;<span style='font-size:0.7rem;color:{diff_color};font-family:Rajdhani,sans-serif;font-weight:700;letter-spacing:0.2em;'>{diff_label}</span></div>
        <div style='margin-top:0.5rem;'>{q_data['question']}</div>
        <div style='font-size:0.72rem;color:#445;margin-top:0.5rem;font-family:Rajdhani,sans-serif;'>{cat_display}</div>
    </div>""", unsafe_allow_html=True)

def render_joker_results():
    ss = st.session_state
    if ss["phone_result"]:
        st.markdown(f"<div class='info-box'><b style='color:#e2c97e;'>Arkadasiniz diyor ki:</b><br>{ss['phone_result']}</div>", unsafe_allow_html=True)
    if ss["poll_result"]:
        html_str = "<div class='info-box'><b style='color:#e2c97e;'>Seyirci Oylamasi:</b><br>"
        for opt, pct in sorted(ss["poll_result"].items(), key=lambda x: -x[1]):
            bw = min(int(pct),100)
            html_str += f"""<div style='margin:4px 0;font-family:Rajdhani,sans-serif;'>
                <span style='color:#c8daf5;display:inline-block;width:44%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;vertical-align:middle;font-size:0.85rem;'>{opt}</span>
                <div style='display:inline-block;width:44%;vertical-align:middle;background:rgba(255,255,255,0.05);border-radius:4px;height:14px;'>
                    <div style='width:{bw}%;background:linear-gradient(90deg,#1565c0,#42a5f5);height:100%;border-radius:4px;'></div>
                </div>
                <span style='color:#ffe066;font-weight:700;font-size:0.85rem;margin-left:6px;'>{pct}%</span></div>"""
        html_str += "</div>"
        st.markdown(html_str, unsafe_allow_html=True)

def render_answer_buttons(q_data, q_index, eliminated):
    letters = ["A","B","C","D"]
    chosen = None
    for row_letters, row_opts in [(letters[:2], q_data["options"][:2]), (letters[2:], q_data["options"][2:])]:
        cols = st.columns(2)
        for col, letter, option in zip(cols, row_letters, row_opts):
            with col:
                if option in eliminated:
                    st.markdown(f"""<div style='background:rgba(5,10,30,0.5);border:1px solid rgba(50,50,80,0.3);
                        border-radius:10px;padding:0.7rem 1.2rem;color:rgba(100,100,130,0.4);
                        font-family:Rajdhani,sans-serif;font-size:1rem;min-height:3rem;display:flex;align-items:center;'>
                        <b style='margin-right:0.5rem;'>{letter})</b> — — —</div>""", unsafe_allow_html=True)
                else:
                    if st.button(f"{letter})  {option}", key=f"ans_{q_index}_{letter}", use_container_width=True):
                        chosen = option
    return chosen


# ─── Session State ────────────────────────────────────────────────────────────
DEFAULTS = {
    "phase":           "setup",
    "questions":       [],
    "q_index":         0,
    "score_index":     -1,
    "lifelines":       {"fifty_fifty": True, "phone": True, "audience": True},
    "eliminated":      [],
    "poll_result":     None,
    "phone_result":    None,
    "host_message":    "",
    "groq_key":        "",
    "player_name":     "",
    "q_start_time":    None,   # None = henuz baslamadi
    "timer_offset":    0.0,
    "paused_at":       None,
    "pending_joker":   None,
    "pending_comment": "",
    "last_answer_ok":  None,
    "reveal_correct":  "",
    "groq_comment":    "",
    "last_result":     None,
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v
ss = st.session_state


# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("<div style='font-family:Cinzel,serif;font-size:1.1rem;font-weight:700;color:#e2c97e;text-align:center;letter-spacing:0.05em;margin-bottom:0.5rem;'>ODUL MERDIVENI</div>", unsafe_allow_html=True)
    phtml = ""
    for i in range(len(PRIZE_AMOUNTS)-1,-1,-1):
        cls = "prize-item" + (" guaranteed" if i in GUARANTEED_LEVELS else "")
        prefix = "* " if i in GUARANTEED_LEVELS else ""
        if ss["phase"] in ["playing","confirm_joker","answer_reveal"]:
            if i == ss["q_index"]: cls += " current"
            elif i < ss["q_index"]: cls += " earned"
        phtml += f"<div class='{cls}'><span>{prefix}{i+1}. Soru</span><span>{format_prize(PRIZE_AMOUNTS[i])}</span></div>"
    st.markdown(phtml, unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)
    if ss["player_name"] and ss["phase"] != "setup":
        g = get_guaranteed_amount(ss["q_index"])
        st.markdown(f"""<div style='text-align:center;padding:0.5rem;'>
            <div style='color:#e2c97e;font-family:Cinzel,serif;font-size:0.9rem;'>{ss['player_name']}</div>
            <div style='color:#90afd4;font-size:0.7rem;letter-spacing:0.15em;margin-top:2px;'>GARANTILI KAZANIM</div>
            <div style='color:#ff9966;font-family:Cinzel,serif;font-size:1.1rem;font-weight:700;'>{format_prize(g)}</div>
        </div>""", unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("<div style='color:#333;font-size:0.7rem;text-align:center;font-family:Rajdhani,sans-serif;'>SUNUCU: TURAN KAYA</div>", unsafe_allow_html=True)


# ─── Baslik ───────────────────────────────────────────────────────────────────
st.markdown("""<div style='text-align:center;padding:1rem 0 0.5rem 0;'>
    <div class='show-title'>KIM TURANYONER OLMAK ISTER</div>
    <div class='host-name'>Sunucu: Turan Kaya &nbsp;|&nbsp; Buyuk Odul: 5.000.000 TL</div>
</div>""", unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SETUP
# ══════════════════════════════════════════════════════════════════════════════
if ss["phase"] == "setup":
    ss["groq_key"] = st.secrets.get("GROQ_API_KEY", "")

    _, col, _ = st.columns([1,2,1])
    with col:
        st.markdown("""<div class='info-box' style='text-align:center;margin-bottom:1.5rem;'>
            <div style='font-family:Cinzel,serif;font-size:1.2rem;color:#e2c97e;margin-bottom:0.5rem;'>Buyuk Odule Hazir Misiniz?</div>
            <div style='color:#90afd4;'>15 soruda 5.000.000 TL kazanabilirsiniz!<br>3 joker hakkiniz var.</div>
        </div>""", unsafe_allow_html=True)

        player_name = st.text_input("Adiniz", placeholder="Turanoyner adayi...", value=ss["player_name"])
        ss["player_name"] = player_name.strip()
        cat_choice  = st.selectbox("Kategori Secin",  list(CATEGORIES.keys()))
        diff_choice = st.selectbox("Zorluk Secin",    list(DIFFICULTY_MAP.keys()))
        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("YARISMAYA BASLA", use_container_width=True):
            if not ss["player_name"]:
                st.error("Lutfen adinizi girin!")
            else:
                allowed, msg = check_rate_limit(ss["player_name"])
                if not allowed:
                    st.error(f"Bekleme: {msg}")
                else:
                    with st.spinner("Sorular hazirlaniyor..."):
                        questions = fetch_questions(15, CATEGORIES[cat_choice], DIFFICULTY_MAP[diff_choice])
                    if not questions or len(questions) < 5:
                        st.error("Yeterli soru yuklenemedi. Farkli kategori veya zorluk deneyin.")
                    else:
                        with st.spinner("Sorular Turkceye cevriliyor..."):
                            questions = translate_questions(questions[:15], ss["groq_key"])
                        record_game(ss["player_name"])
                        # State sifirla
                        for k, v in DEFAULTS.items():
                            if k not in ("groq_key","player_name"): ss[k] = v if not callable(v) else v()
                        ss["questions"]    = questions
                        ss["host_message"] = (f"Hos geldiniz {ss['player_name']}! Ben Turan Kaya. "
                                              f"Bugün sizi 5 milyon TL'ye tasiyacagim... ya da tasimayacagim. Birlikte gorecegiz!")
                        ss["q_start_time"] = None   # ONEMLI: ilk soruda baslatilacak
                        ss["phase"]        = "playing"
                        st.rerun()

        st.markdown("""<div style='margin-top:2rem;'>
            <div class='info-box'><div style='font-family:Cinzel,serif;color:#e2c97e;margin-bottom:0.5rem;'>JOKER HAKLARI</div>
                50:50 — Bilgisayar iki yanlis sikkı eler<br>
                Arkadasa Sor — Groq Yapay Zekasi yorumlar<br>
                Seyirci Oylamasi — Studio oylıyor
            </div>
            <div class='info-box'><div style='font-family:Cinzel,serif;color:#e2c97e;margin-bottom:0.5rem;'>SURELERINIZ</div>
                1-5. sorular: <b style='color:#4caf50;'>45 saniye</b> &nbsp;
                6-10. sorular: <b style='color:#ff9800;'>35 saniye</b><br>
                11-15. sorular: <b style='color:#f44336;'>25 saniye</b> — Joker secincel sure durur
            </div>
            <div class='info-box'><div style='font-family:Cinzel,serif;color:#e2c97e;margin-bottom:0.5rem;'>GARANTI ODULLERI</div>
                3. soruda 3.000 TL &nbsp; 7. soruda 20.000 TL &nbsp; 11. soruda 500.000 TL garanti
            </div>
            <div class='info-box'><div style='font-family:Cinzel,serif;color:#e2c97e;margin-bottom:0.5rem;'>KURAL</div>
                Saatte 1 yarisma — buyuk odulu kazananlar 2 saat bekler
            </div>
        </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PLAYING
# ══════════════════════════════════════════════════════════════════════════════
elif ss["phase"] == "playing":
    q_data = ss["questions"][ss["q_index"]]

    # Timer: ilk gosterimde basla
    if ss["q_start_time"] is None:
        ss["q_start_time"] = time.time()
        ss["timer_offset"]  = 0.0
        ss["paused_at"]     = None

    tl = get_time_limit(ss["q_index"])
    elapsed = get_timer_elapsed()

    # Timeout kontrolu
    if elapsed >= tl:
        groq_c = groq_host_comment("Sure doldu, yarisma bitti",
            {"soru": q_data["question"], "dogru": q_data["correct"], "oyuncu": ss["player_name"]},
            ss["groq_key"])
        ss["host_message"]  = groq_c or "Sure doldu! Turan Kaya sahnede dona kaldi..."
        ss["reveal_correct"] = q_data["correct"]
        ss["last_result"]   = "timeout"
        play_sound_js("wrong")
        ss["phase"] = "result"
        st.rerun()

    # Sunucu mesaji
    if ss["host_message"]:
        st.markdown(f"<div class='info-box'><span style='color:#e2c97e;font-weight:700;'>Turan Kaya:</span> {ss['host_message']}</div>", unsafe_allow_html=True)

    remaining = render_timer(ss["q_index"], paused=False)

    # Joker butonlari
    j1, j2, j3, j4 = st.columns([1,1,1,0.5])
    for col, jk in zip([j1,j2,j3], ["fifty_fifty","phone","audience"]):
        with col:
            st.markdown('<div class="joker-btn">', unsafe_allow_html=True)
            lbl = JOKER_LABELS[jk] + (" [X]" if not ss["lifelines"][jk] else "")
            if st.button(lbl, disabled=not ss["lifelines"][jk], key=f"btn_{jk}"):
                ss["pending_joker"]   = jk
                ss["pending_comment"] = random.choice(JOKER_CONFIRM[jk])
                ss["paused_at"]       = time.time()
                ss["phase"]           = "confirm_joker"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
    with j4:
        st.markdown('<div class="joker-btn">', unsafe_allow_html=True)
        if st.button("Cekil", key="btn_quit"):
            ss["last_result"] = "quit"; ss["phase"] = "result"; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    render_question_box(q_data, ss["q_index"])
    render_joker_results()

    chosen = render_answer_buttons(q_data, ss["q_index"], ss["eliminated"])

    if chosen is not None:
        if chosen == q_data["correct"]:
            ss["last_answer_ok"] = True
            ss["score_index"]    = ss["q_index"]
            play_sound_js("correct")
            if ss["q_index"] == 14:
                record_game(ss["player_name"], jackpot=True)
                groq_c = groq_host_comment("Yarisma 5 milyon TL buyuk odulu kazandi",
                    {"oyuncu": ss["player_name"]}, ss["groq_key"])
                ss["host_message"] = groq_c or f"5 MILYON TL! {ss['player_name']} KAZANDI! INANILMAZ!"
                ss["last_result"]  = "jackpot"
                ss["phase"]        = "result"
            else:
                groq_c = groq_host_comment("Yarisma dogru cevap verdi",
                    {"soru_no": ss["q_index"]+1, "oyuncu": ss["player_name"],
                     "kazanilan": format_prize(PRIZE_AMOUNTS[ss["q_index"]])}, ss["groq_key"])
                ss["reveal_correct"] = chosen
                ss["groq_comment"]   = groq_c
                ss["phase"]          = "answer_reveal"
        else:
            ss["last_answer_ok"] = False
            ss["reveal_correct"] = q_data["correct"]
            play_sound_js("wrong")
            groq_c = groq_host_comment("Yarisma yanlis cevap verdi",
                {"soru_no": ss["q_index"]+1, "yanlis": chosen,
                 "dogru": q_data["correct"], "oyuncu": ss["player_name"]}, ss["groq_key"])
            ss["groq_comment"] = groq_c
            ss["phase"] = "answer_reveal"
        st.rerun()

    st.markdown(f"""<div style='text-align:center;font-family:Rajdhani,sans-serif;margin-top:0.5rem;'>
        <span style='color:#555;font-size:0.8rem;letter-spacing:0.2em;'>BU SORUNUN ODULU</span><br>
        <span style='color:#ffe066;font-family:Cinzel,serif;font-size:1.5rem;font-weight:700;'>
            {format_prize(PRIZE_AMOUNTS[ss['q_index']])}</span></div>""", unsafe_allow_html=True)

    time.sleep(1)
    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# JOKER ONAY (sure duraklatildi)
# ══════════════════════════════════════════════════════════════════════════════
elif ss["phase"] == "confirm_joker":
    q_data = ss["questions"][ss["q_index"]]

    if ss["host_message"]:
        st.markdown(f"<div class='info-box'><span style='color:#e2c97e;font-weight:700;'>Turan Kaya:</span> {ss['host_message']}</div>", unsafe_allow_html=True)

    render_timer(ss["q_index"], paused=True)

    render_question_box(q_data, ss["q_index"])
    render_joker_results()

    jk_label = JOKER_LABELS.get(ss["pending_joker"],"Joker")
    st.markdown(f"""<div class='confirm-box'>
        <div style='font-family:Cinzel,serif;font-size:1.1rem;color:#e2c97e;margin-bottom:0.5rem;'>{jk_label.upper()} JOKERI</div>
        <div style='color:#c8daf5;font-family:Rajdhani,sans-serif;font-size:1rem;margin-bottom:1.2rem;'>{ss['pending_comment']}</div>
        <div style='font-family:Cinzel,serif;font-size:1.3rem;color:#ffe066;'>Son karariniz mi?</div>
    </div>""", unsafe_allow_html=True)

    yes_col, no_col = st.columns(2)

    with yes_col:
        if st.button("EVET, KULLANALIM!", use_container_width=True, key="confirm_yes"):
            # Offset'e duraklatma suresini ekle
            if ss["paused_at"] is not None:
                ss["timer_offset"] += time.time() - ss["paused_at"]
                ss["paused_at"] = None

            jk = ss["pending_joker"]
            ss["lifelines"][jk] = False
            ss["pending_joker"]  = None

            if jk == "fifty_fifty":
                wrongs = [o for o in q_data["options"] if o != q_data["correct"]]
                ss["eliminated"] = random.sample(wrongs, min(2, len(wrongs)))
                groq_c = groq_host_comment("50-50 jokeri kullanildi",
                    {"kalan": [o for o in q_data["options"] if o not in ss["eliminated"]]}, ss["groq_key"])
                ss["host_message"] = groq_c or "Bilgisayar iki sikki sildi. Simdi daha kolay mi?"
            elif jk == "phone":
                visible = [o for o in q_data["options"] if o not in ss["eliminated"]]
                with st.spinner("Arkadasiniz dusunuyor..."):
                    ans = groq_phone_friend(q_data["question"], visible, ss["groq_key"])
                ss["phone_result"] = ans
                groq_c = groq_host_comment("Telefon jokeri kullanildi",
                    {"cevap_ozeti": ans[:80]}, ss["groq_key"])
                ss["host_message"] = groq_c or "Arkadasiniz konustu. Simdi karar sizin!"
            elif jk == "audience":
                visible = [o for o in q_data["options"] if o not in ss["eliminated"]]
                ss["poll_result"] = audience_poll(visible, q_data["correct"])
                top = max(ss["poll_result"], key=ss["poll_result"].get)
                groq_c = groq_host_comment("Seyirci oylamasi yapildi",
                    {"en_cok_oy": top, "oran": ss["poll_result"][top]}, ss["groq_key"])
                ss["host_message"] = groq_c or "Seyirci oyladi! Peki ya siz?"

            ss["phase"] = "playing"
            st.rerun()

    with no_col:
        if st.button("HAYIR, DUSUNEYIM", use_container_width=True, key="confirm_no"):
            if ss["paused_at"] is not None:
                ss["timer_offset"] += time.time() - ss["paused_at"]
                ss["paused_at"] = None
            ss["pending_joker"]   = None
            ss["pending_comment"] = ""
            groq_c = groq_host_comment("Yarisma jokerden vazgecti",
                {"oyuncu": ss["player_name"]}, ss["groq_key"])
            ss["host_message"] = groq_c or f"{ss['player_name']} jokerden vazgecti! Turan Kaya: 'Cesursuuz!'"
            ss["phase"] = "playing"
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# CEVAP ACIKLAMA
# ══════════════════════════════════════════════════════════════════════════════
elif ss["phase"] == "answer_reveal":
    q_data = ss["questions"][ss["q_index"]]

    if ss["last_answer_ok"]:
        st.markdown(f"""<div class='correct-box'>
            DOGRU CEVAP! Tebrikler {ss['player_name']}!<br>
            <span style='font-size:0.9rem;color:#4caf50;'>Cevap: {ss['reveal_correct']}</span><br>
            <span style='font-size:1.2rem;'>Kazandiniz: {format_prize(PRIZE_AMOUNTS[ss['q_index']])}</span>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""<div class='wrong-box'>
            YANLIS CEVAP!<br>
            <span style='font-size:0.9rem;'>Dogru cevap: <b>{ss['reveal_correct']}</b></span>
        </div>""", unsafe_allow_html=True)

    if ss["groq_comment"]:
        st.markdown(f"""<div class='info-box' style='text-align:center;font-size:1.05rem;'>
            <span style='color:#e2c97e;font-weight:700;'>Turan Kaya:</span><br>
            <i>"{ss['groq_comment']}"</i></div>""", unsafe_allow_html=True)

    _, btn_col, _ = st.columns([1,1,1])
    with btn_col:
        if ss["last_answer_ok"]:
            if st.button("DEVAM ET", use_container_width=True, key="btn_cont"):
                ss["q_index"]     += 1
                ss["q_start_time"] = time.time()
                ss["timer_offset"] = 0.0
                ss["paused_at"]    = None
                ss["eliminated"]   = []
                ss["poll_result"]  = None
                ss["phone_result"] = None
                ss["pending_joker"]= None
                ss["groq_comment"] = ""
                ss["host_message"] = ""
                ss["phase"]        = "playing"
                st.rerun()
        else:
            g = get_guaranteed_amount(ss["q_index"])
            st.markdown(f"""<div class='prize-box' style='margin-bottom:1rem;'>
                <div style='color:#90afd4;font-family:Rajdhani,sans-serif;font-size:0.9rem;letter-spacing:0.2em;margin-bottom:0.3rem;'>GARANTI KAZANIMINIZ</div>
                <div class='big-prize'>{format_prize(g)}</div></div>""", unsafe_allow_html=True)
            if st.button("SONUCLARA GIT", use_container_width=True, key="btn_res"):
                ss["last_result"] = "wrong"
                ss["phase"]       = "result"
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# SONUC
# ══════════════════════════════════════════════════════════════════════════════
elif ss["phase"] == "result":
    _, col, _ = st.columns([1,2,1])
    with col:
        res = ss["last_result"]

        if res == "jackpot":
            st.markdown(f"""<div style='text-align:center;margin:1rem 0;'>
                <div style='font-family:Cinzel,serif;font-size:1.4rem;color:#ffe066;letter-spacing:0.1em;margin-bottom:0.5rem;'>INANILMAZ! TARIHI AN!</div></div>
            <div class='prize-box'>
                <div style='color:#90afd4;font-family:Rajdhani,sans-serif;font-size:0.9rem;letter-spacing:0.2em;margin-bottom:0.3rem;'>
                    {ss['player_name'].upper()} KAZANDI</div>
                <div class='big-prize'>5.000.000 TL</div>
                <div style='color:#ff9966;font-family:Cinzel,serif;margin-top:0.5rem;'>BUYUK ODUL!</div>
            </div>""", unsafe_allow_html=True)
            if ss["host_message"]:
                st.markdown(f"<div class='correct-box'>{ss['host_message']}</div>", unsafe_allow_html=True)

        elif res in ["wrong","timeout"]:
            msg_box = "SURE DOLDU!" if res == "timeout" else "YANLIS CEVAP!"
            reveal  = ss.get("reveal_correct","")
            g = get_guaranteed_amount(ss["q_index"])
            st.markdown(f"""<div class='wrong-box'>{msg_box}
                {'<br><span style="font-size:0.85rem;color:#ccc;">Dogru cevap: ' + reveal + '</span>' if reveal else ''}
            </div>
            <div class='prize-box'>
                <div style='color:#90afd4;font-family:Rajdhani,sans-serif;font-size:0.9rem;letter-spacing:0.2em;margin-bottom:0.3rem;'>KAZANIMINIZ</div>
                <div class='big-prize'>{format_prize(g)}</div>
                <div style='color:#90afd4;font-family:Rajdhani,sans-serif;margin-top:0.3rem;'>Garanti odulunuz</div>
            </div>""", unsafe_allow_html=True)
            if ss["host_message"]:
                st.markdown(f"<div class='info-box'><b style='color:#e2c97e;'>Turan Kaya:</b> {ss['host_message']}</div>", unsafe_allow_html=True)

        elif res == "quit":
            g = get_guaranteed_amount(ss["q_index"])
            if ss["score_index"] >= 0: g = max(g, PRIZE_AMOUNTS[ss["score_index"]])
            st.markdown(f"""<div class='prize-box'>
                <div style='color:#90afd4;font-family:Rajdhani,sans-serif;font-size:0.9rem;letter-spacing:0.2em;margin-bottom:0.3rem;'>CEKILDINIZ — KAZANIMINIZ</div>
                <div class='big-prize'>{format_prize(g)}</div>
            </div>""", unsafe_allow_html=True)
            groq_c = groq_host_comment("Yarisma kendi istegiyle cekildi",
                {"oyuncu": ss["player_name"], "kazanilan": format_prize(g)}, ss["groq_key"])
            st.markdown(f"<div class='info-box'><b style='color:#e2c97e;'>Turan Kaya:</b> {groq_c or 'Cesur bir karar! Kazanciniz emin ellerde!'}</div>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("YENIDEN OYNA", use_container_width=True, key="btn_replay"):
            keep = {"groq_key": ss["groq_key"], "player_name": ss["player_name"]}
            for k in list(st.session_state.keys()): del st.session_state[k]
            for k, v in DEFAULTS.items(): st.session_state[k] = v
            st.session_state["groq_key"]    = keep["groq_key"]
            st.session_state["player_name"] = keep["player_name"]
            st.rerun()
