import streamlit as st
from datetime import datetime
import time

# Sayfa Ayarları
st.set_page_config(page_title="2026 Sınav Sayacı", page_icon="⏱️", layout="wide")

# --- CSS GÜNCELLEMESİ (Dark Mode Sorunu Çözüldü) ---
st.markdown("""
    <style>
    /* Ana kapsayıcı */
    .main-container {
        font-family: 'Arial', sans-serif;
    }
    
    /* Kart Tasarımı - Renkleri sabitledik */
    .exam-card {
        background-color: #ffffff !important; /* Arka plan hep BEYAZ */
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        border-left: 8px solid #ccc;
    }
    
    /* Başlık Rengi - Hep SİYAH (Dark modda beyaz olmasın diye) */
    .exam-title {
        font-size: 20px;
        font-weight: bold;
        color: #000000 !important; 
        margin: 0;
        padding-top: 5px;
    }
    
    /* Tarih Rengi - Hep KOYU GRİ */
    .exam-date {
        font-size: 14px;
        color: #555555 !important;
        margin-bottom: 10px;
    }

    /* Sayaç Metni - Hep KOYU LACİVERT */
    .countdown-text {
        font-size: 24px;
        font-weight: 800;
        font-family: 'Courier New', monospace;
        color: #1e3799 !important;
    }
    
    /* Etiket (Badge) Tasarımı */
    .badge {
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: bold;
        float: right;
        color: #ffffff !important; /* Etiket içi yazı hep BEYAZ */
        text-shadow: 1px 1px 2px rgba(0,0,0,0.2); /* Okunurluk için gölge */
    }
    
    /* Sınavlara özel renkler */
    .border-ales { border-left-color: #e67e22 !important; }
    .bg-ales { background-color: #e67e22 !important; } 
    
    .border-kpss { border-left-color: #c0392b !important; }
    .bg-kpss { background-color: #c0392b !important; }
    
    .border-meb { border-left-color: #2980b9 !important; }
    .bg-meb { background-color: #2980b9 !important; }

    </style>
    """, unsafe_allow_html=True)

st.title("⏳ 2026 Sınav Geri Sayım")
st.markdown("Sınav takvimi aşağıda **canlı** olarak işlemektedir.")
st.divider()

# --- SINAV LİSTESİ ---
sinavlar = [
    {"kod": "ALES", "isim": "ALES/1", "tarih": "2026-05-10 10:15", "renk": "border-ales", "bg": "bg-ales"},
    {"kod": "MEB",  "isim": "MEB-AGS (Öğretmenlik)", "tarih": "2026-07-12 10:15", "renk": "border-meb",  "bg": "bg-meb"},
    {"kod": "ALES", "isim": "ALES/2", "tarih": "2026-07-26 10:15", "renk": "border-ales", "bg": "bg-ales"},
    {"kod": "KPSS", "isim": "KPSS Lisans", "tarih": "2026-09-06 10:15", "renk": "border-kpss", "bg": "bg-kpss"},
    {"kod": "ALES", "isim": "ALES/3", "tarih": "2026-11-29 10:15", "renk": "border-ales", "bg": "bg-ales"},
]

def format_time_remaining(target_date_str):
    hedef = datetime.strptime(target_date_str, "%Y-%m-%d %H:%M")
    simdi = datetime.now()
    fark = hedef - simdi
    
    if fark.total_seconds() < 0:
        return "Sınav Tamamlandı!", hedef
    
    days = fark.days
    seconds = fark.seconds
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    return f"{days} GÜN | {hours:02d}:{minutes:02d}:{secs:02d}", hedef

# --- CANLI AKIŞ ---
placeholder = st.empty()

try:
    while True:
        with placeholder.container():
            col1, col2 = st.columns(2)
            
            for index, sinav in enumerate(sinavlar):
                kalan_sure_str, hedef_dt = format_time_remaining(sinav["tarih"])
                tarih_str = hedef_dt.strftime('%d.%m.%Y')
                
                # HTML KART
                card_html = f"""
                <div class="exam-card {sinav['renk']}">
                    <span class="badge {sinav['bg']}">{sinav['kod']}</span>
                    <div class="exam-title">{sinav['isim']}</div>
                    <div class="exam-date">📅 {tarih_str} - Saat: 10:15</div>
                    <div class="countdown-text">{kalan_sure_str}</div>
                </div>
                """
                
                if index % 2 == 0:
                    with col1:
                        st.markdown(card_html, unsafe_allow_html=True)
                else:
                    with col2:
                        st.markdown(card_html, unsafe_allow_html=True)
        
        time.sleep(1)

except KeyboardInterrupt:
    pass
