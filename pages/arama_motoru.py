import streamlit as st
import requests
from PIL import Image
from io import BytesIO
import re
import time

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="Brave Destekli Sahaf",
    page_icon="🦁",
    layout="wide"
)

# --- API ANAHTARI KONTROLÜ ---
# Şifreyi koddan değil, secrets.toml dosyasından çekiyoruz
try:
    API_KEY = st.secrets["BRAVE_API_KEY"]
except:
    st.error("⚠️ API Anahtarı bulunamadı! Lütfen .streamlit/secrets.toml dosyasını oluşturun.")
    st.stop()

# --- FONKSİYONLAR ---

def search_brave(keyword, count=20):
    """Brave Search API kullanarak arama yapar"""
    url = "https://api.search.brave.com/res/v1/web/search"
    
    # Sadece gastearsivi.com içinde ara
    query = f'site:gastearsivi.com {keyword}'
    
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": API_KEY  # <--- Şifre burada kullanılıyor
    }
    
    params = {
        "q": query,
        "count": count,
        "country": "tr", # Türkiye sonuçları
        "safesearch": "off"
    }
    
    found_items = []
    
    try:
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            
            # Brave sonuçları 'web' -> 'results' altındadır
            if "web" in data and "results" in data["web"]:
                results = data["web"]["results"]
                
                for r in results:
                    page_url = r["url"]
                    title = r["title"]
                    desc = r.get("description", "")
                    
                    # URL'den Gazete Bilgilerini Sökme (Regex)
                    # Link: .../gazete/aksam/1938-11-10/1
                    match = re.search(r"gazete\/([^\/]+)\/(\d{4}-\d{2}-\d{2})\/(\d+)", page_url)
                    
                    if match:
                        gid = match.group(1)
                        date_str = match.group(2)
                        page_num = match.group(3)
                        
                        g_name = gid.replace("_", " ").title()
                        
                        found_items.append({
                            "id": gid,
                            "name": g_name,
                            "date": date_str,
                            "page": page_num,
                            "desc": desc,
                            "url": page_url
                        })
        elif response.status_code == 429:
            st.warning("Çok hızlı arama yaptınız. Brave API limitine takıldık. Biraz bekleyin.")
        elif response.status_code == 401:
            st.error("API Anahtarı geçersiz! secrets.toml dosyasını kontrol edin.")
        else:
            st.error(f"Brave Hatası: {response.status_code}")
            
    except Exception as e:
        st.error(f"Bağlantı Hatası: {e}")
        
    return found_items

def get_cdn_image(gid, date_str, page_num):
    """Resmi CDN'den çeker"""
    base_url = "https://dzp35pmd4yqn4.cloudfront.net"
    url = f"{base_url}/thumbnails/{gid}/{date_str}-{page_num}-thumbnail250.jpg"
    
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=2)
        if r.status_code == 200:
            return Image.open(BytesIO(r.content))
    except:
        pass
    return None

def download_pdf(gid, date_str, page_num):
    """PDF İndirir"""
    url = f"https://dzp35pmd4yqn4.cloudfront.net/sayfalar/{gid}/{date_str}-{page_num}.jpg"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            img = Image.open(BytesIO(r.content)).convert("L")
            pdf_buffer = BytesIO()
            img.save(pdf_buffer, format="PDF", resolution=100.0, quality=85)
            pdf_buffer.seek(0)
            return pdf_buffer
    except:
        return None
    return None

# --- ARAYÜZ ---

st.title("🦁 Brave Destekli Dijital Sahaf")
st.markdown("Google'ın engellerine takılmadan, **Brave API** gücüyle arşivde arama yapın.")

with st.sidebar:
    st.header("Arama Ayarları")
    keyword = st.text_input("Anahtar Kelime", placeholder="Örn: 10 Kasım, Hatay...")
    count_slider = st.slider("Sonuç Sayısı", 10, 50, 20)
    search_btn = st.button("ARA 🔎", type="primary")
    
    st.info("Brave API, ayda 2000 aramaya kadar ücretsizdir.")

if search_btn and keyword:
    with st.spinner("Brave arşivi tarıyor..."):
        results = search_brave(keyword, count_slider)
        
        if results:
            st.success(f"✅ {len(results)} sonuç bulundu.")
            st.markdown("---")
            
            for item in results:
                with st.container():
                    c1, c2 = st.columns([1, 4])
                    
                    with c1:
                        # Resim
                        img = get_cdn_image(item['id'], item['date'], item['page'])
                        if img:
                            st.image(img, use_container_width=True)
                        else:
                            st.image("https://placehold.co/200x300?text=Resim+Yok", use_container_width=True)
                            
                    with c2:
                        # Bilgi
                        st.subheader(f"{item['name']} - {item['date']}")
                        st.caption(f"Sayfa: {item['page']}")
                        st.write(f"_{item['desc']}_")
                        
                        # Butonlar
                        u_key = f"{item['id']}_{item['date']}_{item['page']}"
                        
                        col_dl, col_go = st.columns([1, 3])
                        with col_dl:
                            if st.button(f"📥 PDF İndir", key=u_key):
                                with st.spinner("İndiriliyor..."):
                                    pdf_data = download_pdf(item['id'], item['date'], item['page'])
                                    if pdf_data:
                                        fname = f"{item['name']}_{item['date']}_S{item['page']}.pdf"
                                        st.download_button("💾 Kaydet", pdf_data, fname, "application/pdf", key=f"save_{u_key}")
                                    else:
                                        st.error("Dosya bulunamadı.")
                        with col_go:
                            st.markdown(f"[Orjinal Sayfaya Git]({item['url']})")
                            
                    st.divider()
        else:
            st.warning("Sonuç bulunamadı.")
