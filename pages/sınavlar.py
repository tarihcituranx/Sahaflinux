import streamlit as st
from datetime import datetime
import time

# Sayfa Ayarları (Geniş mod ve başlık)
st.set_page_config(page_title="2026 Sınav Sayacı", page_icon="⏱️", layout="wide")

# --- ÖZEL CSS TASARIMI ---
# Bu kısım kartların, gölgelerin ve renklerin ayarlandığı yerdir.
st.markdown("""
    <style>
    /* Ana kapsayıcı ayarları */
    .main-container {
        font-family: 'Helvetica', sans-serif;
    }
    
    /* Kart Tasarımı */
    .exam-card {
        background-color: #ffffff;
        border-radius: 15px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        transition: transform 0.3s ease;
        border-left: 10px solid #ccc; /* Varsayılan sol çizgi */
    }
    
    .exam-card:hover {
        transform: scale(1.02);
    }

    /* Sınav Başlığı */
    .exam-title {
        font-size: 22px;
        font-weight: 700;
        color: #333;
        margin: 0;
    }
    
    /* Tarih */
    .exam-date {
        font-size: 14px;
        color: #666;
        margin-bottom: 15px;
    }

    /* Sayaç Metni */
    .countdown-text {
        font-size: 28px;
        font-weight: 800;
        font-family: 'Courier New', monospace; /* Dijital saat hissi için */
        color: #2c3e50;
    }
    
    /* Sınav Türlerine Göre Renkler */
    .border-ales { border-left-color: #e67e22 !important; } /* Turuncu */
    .border-kpss { border-left-color: #e74c3c !important; } /* Kırmızı */
    .border-meb { border-left-color: #3498db !important; }  /* Mavi */
    
    /* Küçük etiketler */
    .badge {
        padding: 5px 10px;
        border-radius: 5px;
        color: white;
        font-size: 12px;
        font-weight: bold;
        float: right;
    }
    .bg-ales { background-color: #e67e22; }
    .bg-kpss { background-color: #e74c3c; }
    .bg-meb { background-color: #3498db; }

    </style>
    """, unsafe_allow_html=True)

st.title("⏳ 2026 ÖSYM Sınav Takvimi & Geri Sayım")
st.markdown("Sınavlara kalan süre **saniye saniye** aşağıda güncellenmektedir.")
st.divider()

# --- SINAV VERİLERİ ---
sinavlar = [
    {"kod": "ales", "isim": "ALES/1", "tarih": "2026-05-10 10:15", "renk": "border-ales", "bg": "bg-ales"},
    {"kod": "meb",  "isim": "MEB-AGS", "tarih": "2026-07-12 10:15", "renk": "border-meb",  "bg": "bg-meb"},
    {"kod": "ales", "isim": "ALES/2", "tarih": "2026-07-26 10:15", "renk": "border-ales", "bg": "bg-ales"},
    {"kod": "kpss", "isim": "KPSS Lisans", "tarih": "2026-09-06 10:15", "renk": "border-kpss", "bg": "bg-kpss"},
    {"kod": "ales", "isim": "ALES/3", "tarih": "2026-11-29 10:15", "renk": "border-ales", "bg": "bg-ales"},
]

def format_time_remaining(target_date_str):
    """Kalan süreyi hesaplar ve süslü bir string döndürür"""
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
    
    # Dijital saat formatı: 120 Gün - 05:12:43
    return f"{days} GÜN &nbsp; <span style='color:#555'>|</span> &nbsp; {hours:02d}:{minutes:02d}:{secs:02d}", hedef

# --- CANLI DÖNGÜ ALANI ---
# Burası sihrin gerçekleştiği yer. 
# st.empty() bir yer tutucu oluşturur, biz döngü içinde sürekli bu kutunun içini değiştiririz.

placeholder = st.empty()

try:
    while True:
        with placeholder.container():
            # Ekranı iki kolona bölelim (Geniş ekranlar için daha şık)
            col1, col2 = st.columns(2)
            
            for index, sinav in enumerate(sinavlar):
                kalan_sure_str, hedef_dt = format_time_remaining(sinav["tarih"])
                tarih_str = hedef_dt.strftime('%d.%m.%Y - Saat: %H:%M')
                
                # HTML KART YAPISI
                card_html = f"""
                <div class="exam-card {sinav['renk']}">
                    <span class="badge {sinav['bg']}">{sinav['kod'].upper()}</span>
                    <h3 class="exam-title">{sinav['isim']}</h3>
                    <div class="exam-date">📅 {tarih_str}</div>
                    <div class="countdown-text">{kalan_sure_str}</div>
                </div>
                """
                
                # Sınavları sırayla sol ve sağ kolona dağıt
                if index % 2 == 0:
                    with col1:
                        st.markdown(card_html, unsafe_allow_html=True)
                else:
                    with col2:
                        st.markdown(card_html, unsafe_allow_html=True)
        
        # CPU'yu yormamak için 1 saniye bekle
        time.sleep(1)

except KeyboardInterrupt:
    print("Sayaç durduruldu.")
