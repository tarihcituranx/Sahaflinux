import streamlit as st
import requests
from PIL import Image
from io import BytesIO
import re

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="Brave Destekli Sahaf",
    page_icon="🦁",
    layout="wide"
)

# --- API ANAHTARI KONTROLÜ ---
try:
    API_KEY = st.secrets["BRAVE_API_KEY"]
except:
    st.error("⚠️ API Anahtarı bulunamadı! Lütfen .streamlit/secrets.toml dosyasını oluşturun.")
    st.stop()

# --- TEMİZLİK FONKSİYONU (YENİ EKLENDİ) ---
def clean_ocr_text(text):
    """
    OCR metinlerindeki bozuklukları Python ile temizler.
    Yapay zeka kullanmaz, kural tabanlı çalışır.
    """
    if not text:
        return ""

    # 1. Tire (-) ile bölünmüş kelimeleri birleştir (Örn: "da- vası" -> "davası")
    # Hem satır sonu (-) hem de kelime ortası yanlış boşluklu tireleri yakalar.
    text = re.sub(r'-\s+', '', text)

    # 2. Fazla boşlukları, tab'ları ve yeni satırları tek bir boşluğa indir
    text = re.sub(r'\s+', ' ', text)

    # 3. Yaygın OCR hatalarını düzelt (Dictionary Yöntemi)
    # Eski taramalarda harfler bazen ayrı ayrı çıkar.
    replacements = {
        " v e ": " ve ",
        " b ir ": " bir ",
        " b u ": " bu ",
        " d e ": " de ",
        " d a ": " da ",
        " n e ": " ne ",
        " i ç i n ": " için ",
        " o l a n ": " olan ",
        " ı ": "ı", 
        " i ": "i",
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)

    # 4. Metnin başındaki ve sonundaki boşlukları temizle
    return text.strip()

# --- DİĞER FONKSİYONLAR ---

def search_brave(keyword, count=20):
    """Brave Search API kullanarak arama yapar"""
    url = "https://api.search.brave.com/res/v1/web/search"
    query = f'site:gastearsivi.com {keyword}'
    
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": API_KEY
    }
    
    params = {
        "q": query,
        "count": count,
        "country": "tr",
        "safesearch": "off"
    }
    
    found_items = []
    
    try:
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            if "web" in data and "results" in data["web"]:
                results = data["web"]["results"]
                
                for r in results:
                    page_url = r["url"]
                    # Açıklamayı alıyoruz (Bazen description boş olabilir)
                    raw_desc = r.get("description", "") or r.get("title", "")
                    
                    # --- OTOMATİK TEMİZLİK BURADA YAPILIYOR ---
                    final_desc = clean_ocr_text(raw_desc)
                    
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
                            "desc": final_desc, # Artık temizlenmiş metni kaydediyoruz
                            "url": page_url
                        })
        elif response.status_code == 429:
            st.warning("Hız sınırı aşıldı.")
        elif response.status_code == 401:
            st.error("API Anahtarı geçersiz.")
            
    except Exception as e:
        st.error(f"Hata: {e}")
        
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

# --- SESSION STATE ---
if 'search_results' not in st.session_state:
    st.session_state.search_results = []
if 'pdf_cache' not in st.session_state:
    st.session_state.pdf_cache = {}

# --- ARAYÜZ ---

st.title("🦁 Brave Destekli Dijital Sahaf")
st.markdown("Google'ın engellerine takılmadan, **Brave API** gücüyle arşivde arama yapın.")

with st.sidebar:
    st.header("Arama Ayarları")
    keyword = st.text_input("Anahtar Kelime", placeholder="Örn: 10 Kasım, Hatay...")
    count_slider = st.slider("Sonuç Sayısı", 10, 50, 20)
    
    if st.button("ARA 🔎", type="primary"):
        if keyword:
            with st.spinner("Brave arşivi tarıyor ve metinleri temizliyor..."):
                st.session_state.search_results = search_brave(keyword, count_slider)
                st.session_state.pdf_cache = {} 
        else:
            st.warning("Lütfen bir kelime girin.")
    
    st.info("Brave API, ayda 2000 aramaya kadar ücretsizdir.")

# SONUÇLARI GÖSTER
results = st.session_state.search_results

if results:
    st.success(f"✅ {len(results)} sonuç bulundu.")
    st.markdown("---")
    
    for item in results:
        with st.container():
            c1, c2 = st.columns([1, 4])
            
            with c1:
                img = get_cdn_image(item['id'], item['date'], item['page'])
                if img:
                    st.image(img, use_container_width=True)
                else:
                    st.image("https://placehold.co/200x300?text=Resim+Yok", use_container_width=True)
                    
            with c2:
                st.subheader(f"{item['name']} - {item['date']}")
                st.caption(f"Sayfa: {item['page']}")
                
                # TEMİZLENMİŞ METİN BURADA GÖSTERİLİYOR
                st.write(f"_{item['desc']}_")
                
                col_dl, col_go = st.columns([1, 3])
                
                unique_id = f"{item['id']}_{item['date']}_{item['page']}"
                
                with col_dl:
                    if unique_id not in st.session_state.pdf_cache:
                        if st.button(f"📥 PDF Hazırla", key=f"btn_{unique_id}"):
                            with st.spinner("PDF Dönüştürülüyor..."):
                                pdf_data = download_pdf(item['id'], item['date'], item['page'])
                                if pdf_data:
                                    st.session_state.pdf_cache[unique_id] = pdf_data
                                    st.rerun()
                                else:
                                    st.error("Dosya alınamadı.")
                    else:
                        fname = f"{item['name']}_{item['date']}_S{item['page']}.pdf"
                        st.download_button(
                            label="💾 PDF İNDİR",
                            data=st.session_state.pdf_cache[unique_id],
                            file_name=fname,
                            mime="application/pdf",
                            key=f"dl_{unique_id}",
                            type="primary"
                        )

                with col_go:
                    st.markdown(f"[Orjinal Sayfaya Git]({item['url']})")
                    
            st.divider()
