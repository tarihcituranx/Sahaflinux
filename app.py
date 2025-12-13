import streamlit as st
import requests
from PIL import Image
from io import BytesIO
from datetime import date, timedelta
import re

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="Dijital Sahaf - Web",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- VERİ HAVUZU ---
GASTE_ARSIVI_DATABASE = [
    {"id": "aksam", "name": "Akşam", "dates": "1918-Günümüz"},
    {"id": "cumhuriyet", "name": "Cumhuriyet", "dates": "1924-Günümüz"},
    {"id": "hurriyet", "name": "Hürriyet", "dates": "1948-Günümüz"},
    {"id": "milliyet", "name": "Milliyet", "dates": "1950-Günümüz"},
    {"id": "sabah", "name": "Sabah", "dates": "1985-Günümüz"},
    {"id": "sozcu", "name": "Sözcü", "dates": "2007-Günümüz"},
    {"id": "tan", "name": "Tan", "dates": "1935-1945"},
    {"id": "tanin", "name": "Tanin", "dates": "1908-1947"},
    {"id": "ulus", "name": "Ulus", "dates": "1934-1971"},
    {"id": "vakit", "name": "Vakit", "dates": "1917-1950"},
    {"id": "vatan", "name": "Vatan", "dates": "1923-1975"},
    {"id": "yeni-asir", "name": "Yeni Asır", "dates": "1895-Günümüz"},
    {"id": "zaman", "name": "Zaman", "dates": "1986-2016"},
    {"id": "tasviri-efkar", "name": "Tasviri Efkar", "dates": "1862-1871"},
    {"id": "tercuman-i-ahval", "name": "Tercüman-ı Ahval", "dates": "1860-1866"}
]
# Listeyi isme göre sırala
GASTE_ARSIVI_DATABASE.sort(key=lambda x: x["name"])

# --- FONKSİYONLAR ---
def get_preview_image(gid, date_obj):
    """Canlı önizleme için 1. sayfayı çeker"""
    date_str = date_obj.strftime("%Y-%m-%d")
    url = f"https://dzp35pmd4yqn4.cloudfront.net/sayfalar/{gid}/{date_str}-1.jpg"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=3)
        if r.status_code == 200:
            return Image.open(BytesIO(r.content)), True
    except:
        pass
    return None, False

def create_pdf(gid, date_obj):
    """PDF oluşturur ve RAM'de tutar (Diske kaydetmez)"""
    date_str = date_obj.strftime("%Y-%m-%d")
    base_url = "https://dzp35pmd4yqn4.cloudfront.net/sayfalar"
    images = []
    page = 1
    tolerance = 0
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    while page <= 99:
        if tolerance >= 2: break
        
        url = f"{base_url}/{gid}/{date_str}-{page}.jpg"
        status_text.text(f"Sayfa {page} indiriliyor...")
        
        try:
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
            if r.status_code == 200:
                img = Image.open(BytesIO(r.content)).convert("RGB")
                images.append(img)
                tolerance = 0
            else:
                tolerance += 1
        except:
            tolerance += 1
        
        page += 1
        progress_bar.progress(min(page / 20, 1.0)) # Tahmini progress

    status_text.empty()
    progress_bar.empty()
    
    if images:
        pdf_buffer = BytesIO()
        images[0].save(pdf_buffer, format="PDF", save_all=True, append_images=images[1:])
        pdf_buffer.seek(0)
        return pdf_buffer
    return None

# --- ARAYÜZ (SIDEBAR) ---
st.sidebar.title("📚 Dijital Sahaf")
st.sidebar.markdown("---")

# Gazete Seçimi
selected_name = st.sidebar.selectbox(
    "Yayın Seçiniz",
    options=[item["name"] for item in GASTE_ARSIVI_DATABASE]
)

# Seçilen gazetenin ID'sini bul
selected_item = next(item for item in GASTE_ARSIVI_DATABASE if item["name"] == selected_name)
gid = selected_item["id"]

# Tarih Seçimi
st.sidebar.markdown("### 📅 Tarih")
selected_date = st.sidebar.date_input(
    "Yayın Tarihi",
    value=date(1930, 1, 1),
    min_value=date(1800, 1, 1),
    max_value=date.today()
)

st.sidebar.info(f"📅 Arşiv Aralığı:\n{selected_item['dates']}")

# --- ANA EKRAN ---
st.title(f"{selected_name}")
st.markdown(f"**Seçili Tarih:** {selected_date.strftime('%d.%m.%Y')}")

col1, col2 = st.columns([1, 1])

# CANLI ÖNİZLEME (OTOMATİK)
with col1:
    st.subheader("🔍 Canlı Önizleme")
    with st.spinner("Önizleme yükleniyor..."):
        preview_img, found = get_preview_image(gid, selected_date)
        
        if found:
            st.image(preview_img, caption=f"{selected_name} - {selected_date}", use_container_width=True)
        else:
            st.warning("Bu tarihe ait yayın bulunamadı veya arşivde yok.")
            st.image("https://via.placeholder.com/400x600?text=Yayin+Yok", use_container_width=True)

# İNDİRME ALANI
with col2:
    st.subheader("📥 İndirme İşlemleri")
    
    if found:
        st.success("✅ Yayın mevcut! Aşağıdaki butona basarak PDF olarak indirebilirsiniz.")
        st.markdown("---")
        
        if st.button("📄 PDF Oluştur ve İndir"):
            with st.spinner("Sayfalar toplanıyor ve birleştiriliyor... Lütfen bekleyin."):
                pdf_data = create_pdf(gid, selected_date)
                
                if pdf_data:
                    file_name = f"{selected_name.replace(' ', '_')}_{selected_date}.pdf"
                    st.download_button(
                        label="💾 Dosyayı Kaydet",
                        data=pdf_data,
                        file_name=file_name,
                        mime="application/pdf"
                    )
                    st.balloons()
                else:
                    st.error("Bir hata oluştu, PDF oluşturulamadı.")
    else:
        st.error("Önizleme bulunamadığı için indirme işlemi yapılamaz.")

st.markdown("---")
st.caption("Dijital Sahaf Web v1.0 | Akademik Amaçlıdır.")
