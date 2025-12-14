import streamlit as st
from duckduckgo_search import DDGS
import requests
from PIL import Image, ImageEnhance, ImageOps
from io import BytesIO
import re
import time

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="Dijital Sahaf (DDG)",
    page_icon="🦆",
    layout="wide"
)

# --- FONKSİYONLAR ---

def search_duckduckgo(keyword, max_results=20):
    """DuckDuckGo üzerinden site içi arama yapar"""
    query = f'site:gastearsivi.com "{keyword}"'
    found_items = []
    
    try:
        # DDGS kütüphanesi ile arama yapıyoruz
        with DDGS() as ddgs:
            # region="tr-tr" ile Türkiye sonuçlarını önceliyoruz
            results = ddgs.text(query, region='tr-tr', safesearch='off', max_results=max_results)
            
            for r in results:
                url = r['href']
                title = r['title']
                body = r['body']
                
                # Link Analizi (ID, Tarih ve Sayfa No'yu söküyoruz)
                # Link Tipi: https://www.gastearsivi.com/gazete/aksam/1938-11-10/1
                match = re.search(r"gazete\/([^\/]+)\/(\d{4}-\d{2}-\d{2})\/(\d+)", url)
                
                if match:
                    gid = match.group(1)
                    date_str = match.group(2)
                    page_num = match.group(3)
                    
                    # Gazete adını düzelt
                    g_name = gid.replace("_", " ").title()
                    
                    found_items.append({
                        "id": gid,
                        "name": g_name,
                        "date": date_str,
                        "page": page_num,
                        "title": title,
                        "desc": body,
                        "url": url
                    })
                    
    except Exception as e:
        st.error(f"DuckDuckGo Hatası: {e}")
    
    return found_items

def get_cdn_image(gid, date_str, page_num):
    """Resmi CDN'den çeker (Engel yok)"""
    base_url = "https://dzp35pmd4yqn4.cloudfront.net"
    
    # Küçük resim (Thumbnail) hızlı yüklenir
    url = f"{base_url}/thumbnails/{gid}/{date_str}-{page_num}-thumbnail250.jpg"
    
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=2)
        if r.status_code == 200:
            return Image.open(BytesIO(r.content))
    except:
        pass
    return None

def download_pdf(gid, date_str, page_num):
    """Yüksek kaliteli PDF indirir"""
    # Büyük resim (Sayfalar klasörü)
    url = f"https://dzp35pmd4yqn4.cloudfront.net/sayfalar/{gid}/{date_str}-{page_num}.jpg"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            img = Image.open(BytesIO(r.content)).convert("L") # Siyah Beyaz yap
            pdf_buffer = BytesIO()
            img.save(pdf_buffer, format="PDF", resolution=100.0, quality=85)
            pdf_buffer.seek(0)
            return pdf_buffer
    except:
        return None
    return None

# --- ARAYÜZ ---

st.title("🦆 DuckDuckGo Destekli Arşiv Arama")
st.markdown("Google engelliyorsa, ördek (DuckDuckGo) yardımımıza koşar. Aradığınız kelimenin geçtiği gazeteleri bulun.")

with st.sidebar:
    st.header("Arama Paneli")
    keyword = st.text_input("Aranacak Konu", placeholder="Örn: Serbest Fırka, Hatay...")
    limit = st.slider("Sonuç Limiti", 10, 50, 20)
    
    st.info("Not: Tarih aralığı için kelimenin yanına yıl yazabilirsiniz. Örn: 'Menemen Olayı 1930'")
    
    search_btn = st.button("ARA 🔎", type="primary")

# --- SONUÇ EKRANI ---
if search_btn and keyword:
    with st.spinner("DuckDuckGo arşivleri tarıyor..."):
        # 1 saniye bekletelim ki arka arkaya basınca IP banlanmasın
        time.sleep(1)
        results = search_duckduckgo(keyword, limit)
        
        if results:
            st.success(f"✅ {len(results)} gazete sayfası bulundu.")
            st.markdown("---")
            
            for item in results:
                with st.container():
                    c1, c2 = st.columns([1, 4])
                    
                    # Sol: Resim
                    with c1:
                        img = get_cdn_image(item['id'], item['date'], item['page'])
                        if img:
                            st.image(img, use_container_width=True)
                        else:
                            st.image("https://placehold.co/200x300?text=Resim+Yok", use_container_width=True)
                    
                    # Sağ: Detaylar
                    with c2:
                        st.subheader(f"{item['name']} - {item['date']}")
                        st.caption(f"Sayfa: {item['page']} | Kaynak: GasteArşivi")
                        st.write(f"**İçerik Özeti:** ...{item['desc']}...")
                        
                        # Benzersiz Buton Key'i
                        u_key = f"{item['id']}_{item['date']}_{item['page']}"
                        
                        col_dl, col_link = st.columns([1, 3])
                        
                        with col_dl:
                            if st.button(f"📥 İndir (PDF)", key=u_key):
                                with st.spinner("İndiriliyor..."):
                                    pdf_data = download_pdf(item['id'], item['date'], item['page'])
                                    if pdf_data:
                                        fname = f"{item['name']}_{item['date']}_S{item['page']}.pdf"
                                        st.download_button(
                                            label="💾 Kaydet",
                                            data=pdf_data,
                                            file_name=fname,
                                            mime="application/pdf",
                                            key=f"save_{u_key}"
                                        )
                                    else:
                                        st.error("Dosya alınamadı.")
                        
                        with col_link:
                            st.markdown(f"[Orjinal Sayfaya Git]({item['url']})")
                    
                    st.divider()
        else:
            st.warning("DuckDuckGo sonuç bulamadı. Kelimeyi değiştirip tekrar deneyin.")
