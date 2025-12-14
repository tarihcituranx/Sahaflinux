import streamlit as st
import requests
from PIL import Image, ImageEnhance, ImageOps
from io import BytesIO
from datetime import date, datetime
import json
import re

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="Gaste Arama Motoru",
    page_icon="🔍",
    layout="wide"
)

# --- FONKSİYONLAR ---

def search_via_html(keyword, start_date, end_date):
    """
    API yerine doğrudan Arama Sayfasına gidip, 
    sayfa içine gizlenmiş JSON verisini (APOLLO_STATE) çeker.
    Bu yöntem bot korumalarına takılmaz.
    """
    
    # Gerçek bir Chrome tarayıcı gibi görünmek için Header'lar
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.gastearsivi.com/",
        "Upgrade-Insecure-Requests": "1"
    }

    # Arama URL'sini oluştur
    s_date_str = start_date.strftime("%Y-%m-%d")
    e_date_str = end_date.strftime("%Y-%m-%d")
    
    # URL Parametreleri
    target_url = f"https://www.gastearsivi.com/ara?q={keyword}&startDate={s_date_str}&endDate={e_date_str}&sort=best"
    
    try:
        response = requests.get(target_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            html_content = response.text
            
            # HTML içindeki gizli JSON verisini Regex ile bul
            # Aradığımız kalıp: window.__APOLLO_STATE__ = { ... };
            pattern = r'window\.__APOLLO_STATE__\s*=\s*({.*?});'
            match = re.search(pattern, html_content, re.DOTALL)
            
            if match:
                json_str = match.group(1)
                data = json.loads(json_str)
                
                # JSON verisi karmaşık bir ağaç yapısındadır, içinden "Sayfa"ları ayıklamalıyız
                found_pages = []
                
                # ROOT_QUERY içindeki arama sonuçlarına bak
                for key, value in data.items():
                    # Anahtar "ROOT_QUERY" ise veya bir Gazete Sayfası (Page) ise
                    if key == "ROOT_QUERY":
                        # Arama sonucunu bul (Anahtar ismi dinamiktir, örn: arama({"query":"..."}))
                        for sub_key, sub_val in value.items():
                            if sub_key.startswith("arama") and "sayfalar" in sub_val:
                                # Sayfa referanslarını al (örn: [{"ref":"Page:123"}, ...])
                                page_refs = sub_val["sayfalar"]
                                
                                # Referansları gerçek verilerle eşleştir
                                for ref in page_refs:
                                    ref_id = ref.get("__ref") # "Page:12345"
                                    if ref_id and ref_id in data:
                                        page_data = data[ref_id]
                                        found_pages.append({
                                            "id": page_data.get("id"),
                                            "gazete": page_data.get("gazete"),
                                            "tarih": page_data.get("tarih"),
                                            "sayfa": page_data.get("sayfa"),
                                            "thumbnail": page_data.get("thumbnail")
                                        })
                return found_pages
            else:
                st.error("Sayfa yüklendi ancak veri çözümlenemedi (Regex hatası).")
                # Hata ayıklama için HTML'in bir kısmını göster (İsteğe bağlı)
                # st.code(html_content[:500])
        else:
            st.error(f"Sunucu Hatası: {response.status_code}")
            
    except Exception as e:
        st.error(f"Bağlantı Hatası: {e}")
        
    return []

def download_page_as_pdf(gid, date_str, page_num):
    """Seçilen sayfayı indirip PDF yapar"""
    base_url = "https://dzp35pmd4yqn4.cloudfront.net"
    img_url = f"{base_url}/sayfalar/{gid}/{date_str}-{page_num}.jpg"
    
    try:
        r = requests.get(img_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if r.status_code == 200:
            image = Image.open(BytesIO(r.content))
            image = image.convert("L") # Siyah Beyaz
            
            pdf_buffer = BytesIO()
            image.save(pdf_buffer, format="PDF", resolution=100.0, quality=85)
            pdf_buffer.seek(0)
            return pdf_buffer
    except:
        return None
    return None

# --- ARAYÜZ ---

st.title("🔍 Tarihi Gazete Arama Motoru")
st.markdown("Arşivde kelime bazlı arama yapın (Örn: 'Atatürk', 'Seçim', 'Kıbrıs').")

with st.form("search_form"):
    c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
    
    keyword = c1.text_input("Aranacak Kelime", placeholder="Bir konu yazın...")
    s_date = c2.date_input("Başlangıç", date(1923, 10, 29))
    e_date = c3.date_input("Bitiş", date(1938, 11, 10))
    submit_btn = c4.form_submit_button("ARA 🚀", use_container_width=True)

if submit_btn and keyword:
    with st.spinner(f"'{keyword}' için arşiv taranıyor..."):
        # Yeni HTML Parse Fonksiyonunu Kullanıyoruz
        results = search_via_html(keyword, s_date, e_date)
        
        if results:
            st.success(f"Toplam {len(results)} sayfa bulundu.")
            st.markdown("---")
            
            # Sonuçları Göster
            cols = st.columns(4)
            for idx, item in enumerate(results):
                with cols[idx % 4]:
                    # Görsel URL
                    thumb_url = f"https://dzp35pmd4yqn4.cloudfront.net/{item['thumbnail']}"
                    
                    st.image(thumb_url, use_container_width=True)
                    st.markdown(f"**{item['gazete'].upper()}**")
                    st.caption(f"📅 {item['tarih']} | Sayfa: {item['sayfa']}")
                    
                    # İndirme Butonu
                    unique_key = f"{item['id']}_{idx}"
                    
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
            st.warning("Sonuç bulunamadı.")
            st.info("İpucu: Tarih aralığını genişletmeyi deneyin.")
