import streamlit as st
from datetime import datetime
import pandas as pd

# Sayfa Ayarları
st.set_page_config(page_title="ÖSYM 2026 Geri Sayım", page_icon="⏳", layout="centered")

# --- CSS İle Biraz Görsellik Katalım ---
st.markdown("""
    <style>
    .big-font {
        font-size:20px !important;
        font-weight: bold;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🎓 2026 ÖSYM Sınavları Geri Sayım")
st.markdown("Aşağıda 2026 yılı için belirlenen ALES, KPSS ve MEB-AGS sınavlarına kalan süreler listelenmektedir.")
st.divider()

# --- GÜNCELLENMİŞ SINAV BİLGİLERİ ---
# Tarihler görsellerden alınmıştır. Saat standart 10:15 olarak ayarlandı.
sinav_listesi = [
    {"isim": "ALES/1 - 2026", "tarih": "2026-05-10 10:15"},   # Kaynak: Görsel 2
    {"isim": "MEB-AGS - 2026", "tarih": "2026-07-12 10:15"},   # Kaynak: Görsel 3
    {"isim": "ALES/2 - 2026", "tarih": "2026-07-26 10:15"},   # Kaynak: Görsel 2
    {"isim": "KPSS Lisans - 2026", "tarih": "2026-09-06 10:15"}, # Kaynak: Görsel 1
    {"isim": "ALES/3 - 2026", "tarih": "2026-11-29 10:15"}    # Kaynak: Görsel 2
]

# --- HESAPLAMA FONKSİYONU ---
def kalan_sureyi_hesapla(hedef_tarih_str):
    hedef = datetime.strptime(hedef_tarih_str, "%Y-%m-%d %H:%M")
    simdi = datetime.now()
    
    fark = hedef - simdi
    
    # Sınav geçtiyse
    if fark.total_seconds() < 0:
        return None, "Sınav Tamamlandı!"
    
    # Gün, Saat, Dakika hesabı
    toplam_saniye = int(fark.total_seconds())
    gun = fark.days
    
    # Ay hesabı (Yaklaşık)
    ay = gun // 30
    kalan_gun = gun % 30
    
    saat = (toplam_saniye // 3600) % 24
    dakika = (toplam_saniye // 60) % 60
    
    # Metin oluşturma: Eğer 1 aydan az kaldıysa sadece gün/saat göster
    if ay > 0:
        metin = f"{ay} Ay, {kalan_gun} Gün, {saat} Saat"
    else:
        metin = f"{kalan_gun} Gün, {saat} Saat, {dakika} Dakika"
        
    return hedef, metin

# --- LİSTELEME DÖNGÜSÜ ---
for sinav in sinav_listesi:
    hedef_tarih, kalan_metin = kalan_sureyi_hesapla(sinav["tarih"])
    
    col1, col2 = st.columns([2, 3])
    
    with col1:
        st.subheader(f"📅 {sinav['isim']}")
        if hedef_tarih:
            # Tarihi Türkçe formatta göstermek için (Gün.Ay.Yıl)
            st.caption(f"Tarih: {hedef_tarih.strftime('%d.%m.%Y')} - Saat: 10:15")
        
    with col2:
        if hedef_tarih:
            st.metric(label="Kalan Süre", value=kalan_metin)
        else:
            st.success(kalan_metin) # Tamamlanan sınav yeşil görünsün
            
    st.markdown("---")

# Sayfa yenileme butonu
if st.button('Süreyi Güncelle'):
    st.rerun()
