import streamlit as st
import requests
from PIL import Image
from io import BytesIO
from datetime import date, datetime

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="Gaste Arama Motoru",
    page_icon="🔍",
    layout="wide"
)

# --- FONKSİYONLAR ---

def search_api(keyword, start_date, end_date):
    """GasteArşivi sunucusunda kelime bazlı arama yapar"""
    url = "https://www.gastearsivi.com/graphql"
    
    query = """
    query arama($query: String!, $startDate: Date, $endDate: Date, $sort: String, $offset: Int) {
      arama(query: $query, startDate: $startDate, endDate: $endDate, sort: $sort, count: 50, offset: $offset) {
        sayfalar {
          id
          gazete
          tarih
          sayfa
          thumbnail
        }
      }
    }
    """
    
    variables = {
        "query": keyword,
        "startDate": start_date.strftime("%Y-%m-%d"),
        "endDate": end_date.strftime("%Y-%m-%d"),
        "sort": "best", # "date" de yapılabilir
        "offset": 0
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Content-Type": "application/json",
        "Referer": "https://www.gastearsivi.com/ara"
    }
    
    try:
        r = requests.post(url, json={"query": query, "variables": variables}, headers=headers)
        if r.status_code == 200:
            data = r.json()
            # Sonuç var mı kontrol et
            if "data" in data and data["data"]["arama"]:
                return data["data"]["arama"]["sayfalar"]
    except Exception as e:
        st.error(f"Bağlantı Hatası: {e}")
    return []

def download_page_as_pdf(gid, date_str, page_num):
    """Seçilen sayfayı indirip PDF yapar"""
    # Bulduğumuz Cloudfront Sunucusu
    base_url = "https://dzp35pmd4yqn4.cloudfront.net"
    img_url = f"{base_url}/sayfalar/{gid}/{date_str}-{page_num}.jpg"
    
    try:
        r = requests.get(img_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        if r.status_code == 200:
            image = Image.open(BytesIO(r.content))
            
            # Siyah Beyaz yap (Okunabilirlik için)
            image = image.convert("L")
            
            pdf_buffer = BytesIO()
            image.save(pdf_buffer, format="PDF", resolution=100.0, quality=85)
            pdf_buffer.seek(0)
            return pdf_buffer
    except:
        return None
    return None

# --- ARAYÜZ ---

st.title("🔍 Tarihi Gazete Arama Motoru")
st.markdown("Anahtar kelimenizi girin, tarih aralığını seçin ve o kelimenin geçtiği sayfaları bulun.")

with st.form("search_form"):
    c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
    
    keyword = c1.text_input("Aranacak Kelime", placeholder="Örn: Atatürk, Seçim, Deprem...")
    s_date = c2.date_input("Başlangıç", date(1923, 10, 29))
    e_date = c3.date_input("Bitiş", date(1938, 11, 10))
    submit_btn = c4.form_submit_button("ARA 🚀", use_container_width=True)

if submit_btn and keyword:
    with st.spinner(f"'{keyword}' için arşiv taranıyor..."):
        results = search_api(keyword, s_date, e_date)
        
        if results:
            st.success(f"Toplam {len(results)} sayfa bulundu.")
            st.markdown("---")
            
            # Sonuçları 4'lü ızgara (grid) şeklinde göster
            cols = st.columns(4)
            for idx, item in enumerate(results):
                with cols[idx % 4]:
                    # Görsel URL (Thumbnail)
                    thumb_url = f"https://dzp35pmd4yqn4.cloudfront.net/{item['thumbnail']}"
                    
                    # Kart Yapısı
                    st.image(thumb_url, use_container_width=True)
                    st.markdown(f"**{item['gazete'].upper()}**")
                    st.caption(f"📅 {item['tarih']} | Sayfa: {item['sayfa']}")
                    
                    # İndirme Butonu (Her butonun key'i benzersiz olmalı)
                    unique_key = f"{item['id']}_{idx}"
                    
                    # PDF Hazırlama (Callback mantığıyla)
                    if st.button("📥 İndir", key=unique_key):
                        pdf_data = download_page_as_pdf(item['gazete'], item['tarih'], item['sayfa'])
                        if pdf_data:
                            file_name = f"{item['gazete']}_{item['tarih']}_S{item['sayfa']}.pdf"
                            st.download_button(
                                label="💾 Kaydet",
                                data=pdf_data,
                                file_name=file_name,
                                mime="application/pdf",
                                key=f"dl_{unique_key}"
                            )
                        else:
                            st.error("Dosya alınamadı.")
        else:
            st.warning("Sonuç bulunamadı veya sunucu yanıt vermedi.")
