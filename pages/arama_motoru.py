import streamlit as st
import cloudscraper # <-- YENİ SİLAHIMIZ
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

# --- SCRAPER AYARLARI ---
# Cloudflare korumasını aşan özel tarayıcı nesnesi
scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'windows',
        'desktop': True
    }
)

# --- FONKSİYONLAR ---

def search_via_html(keyword, start_date, end_date):
    """
    Cloudscraper kullanarak siteye 'insan gibi' girer ve
    gizli JSON verisini çeker. 403 hatasını bypass eder.
    """
    
    s_date_str = start_date.strftime("%Y-%m-%d")
    e_date_str = end_date.strftime("%Y-%m-%d")
    
    # Arama URL'si
    target_url = f"https://www.gastearsivi.com/ara?q={keyword}&startDate={s_date_str}&endDate={e_date_str}&sort=best"
    
    try:
        # requests.get YERİNE scraper.get KULLANIYORUZ
        response = scraper.get(target_url, timeout=15)
        
        if response.status_code == 200:
            html_content = response.text
            
            # Gizli JSON verisini bul (Regex)
            pattern = r'window\.__APOLLO_STATE__\s*=\s*({.*?});'
            match = re.search(pattern, html_content, re.DOTALL)
            
            if match:
                json_str = match.group(1)
                data = json.loads(json_str)
                
                found_pages = []
                
                # Karmaşık JSON ağacını tarayalım
                for key, value in data.items():
                    if key == "ROOT_QUERY":
                        for sub_key, sub_val in value.items():
                            if sub_key.startswith("arama") and "sayfalar" in sub_val:
                                page_refs = sub_val["sayfalar"]
                                for ref in page_refs:
                                    ref_id = ref.get("__ref")
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
                # Eğer regex bulamazsa, belki sonuç yoktur.
                pass
        elif response.status_code == 403:
            st.error("⚠️ Site hala bot olduğumuzu düşünüyor. Biraz bekleyip tekrar deneyin.")
        else:
            st.error(f"Hata Kodu: {response.status_code}")
            
    except Exception as e:
        st.error(f"Bağlantı Hatası: {e}")
        
    return []

def download_page_as_pdf(gid, date_str, page_num):
    """Resmi indirir (Burada da Scraper kullanıyoruz)"""
    base_url = "https://dzp35pmd4yqn4.cloudfront.net"
    img_url = f"{base_url}/sayfalar/{gid}/{date_str}-{page_num}.jpg"
    
    try:
        # Resim sunucusu genelde 403 vermez ama garanti olsun diye scraper ile çekelim
        r = scraper.get(img_url, timeout=10)
        if r.status_code == 200:
            image = Image.open(BytesIO(r.content))
            image = image.convert("L") # Siyah Beyaz (Daha net)
            
            pdf_buffer = BytesIO()
            image.save(pdf_buffer, format="PDF", resolution=100.0, quality=85)
            pdf_buffer.seek(0)
            return pdf_buffer
    except:
        return None
    return None

# --- ARAYÜZ ---

st.title("🔍 Tarihi Gazete Arama Motoru")
st.caption("GasteArşivi Bot Korumasını Aşan Sürüm (v3.0)")

with st.form("search_form"):
    c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
    
    keyword = c1.text_input("Aranacak Kelime", placeholder="Örn: Atatürk, Seçim, Kıbrıs...")
    s_date = c2.date_input("Başlangıç", date(1923, 10, 29))
    e_date = c3.date_input("Bitiş", date(1938, 11, 10))
    submit_btn = c4.form_submit_button("ARA 🚀", use_container_width=True)

if submit_btn and keyword:
    with st.spinner(f"🛡️ Güvenlik duvarı aşılıyor ve '{keyword}' aranıyor..."):
        results = search_via_html(keyword, s_date, e_date)
        
        if results:
            st.success(f"✅ {len(results)} sayfa bulundu.")
            st.markdown("---")
            
            # Sonuçları Göster
            cols = st.columns(4)
            for idx, item in enumerate(results):
                with cols[idx % 4]:
                    thumb_url = f"https://dzp35pmd4yqn4.cloudfront.net/{item['thumbnail']}"
                    
                    st.image(thumb_url, use_container_width=True)
                    st.markdown(f"**{item['gazete'].upper()}**")
                    st.caption(f"📅 {item['tarih']} | Sayfa: {item['sayfa']}")
                    
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
            st.info("Eğer sürekli hata alıyorsanız, çok sık istek gönderdiğiniz için kısa süreli banlanmış olabilirsiniz.")
