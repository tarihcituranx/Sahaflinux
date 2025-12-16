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

# --- METİN TEMİZLEME FONKSİYONU ---
def clean_ocr_text(text):
    if not text: return ""
    text = re.sub(r'-\s+', '', text)
    text = re.sub(r'\s+', ' ', text)
    replacements = {
        " v e ": " ve ", " b ir ": " bir ", " b u ": " bu ", 
        " d e ": " de ", " d a ": " da ", " n e ": " ne ",
        " i ç i n ": " için ", " o l a n ": " olan ", " ı ": "ı", " i ": "i",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.strip()

# --- KRİTİK GÜNCELLEME: DOSYA İSMİ VARYASYONLARI ---
def generate_variations(date_str, page_num, suffix):
    """
    Sunucudaki olası dosya isimlerini üretir.
    Örn: URL'de sayfa 1 ise, dosya 0.jpg olabilir.
    """
    variations = []
    try:
        y, m, d = date_str.split("-")
        p_num = int(page_num)
        
        # --- EN ÖNEMLİ EKLEMELER BURADA ---
        
        # 1. İhtimal: Sayfa numarasının 1 eksiği (0 tabanlı indeksleme)
        # Senin örneğindeki gibi URL'de 1 yazıp dosyada 0 yazıyorsa bunu yakalar.
        if p_num > 0:
            variations.append(f"{date_str}-{p_num - 1}{suffix}")          # 1957-09-10-0.jpg
            variations.append(f"{date_str}-{p_num - 1:02d}{suffix}")      # 1957-09-10-00.jpg

        # 2. İhtimal: Standart (Aynısı)
        variations.append(f"{date_str}-{p_num}{suffix}")                  # 1957-09-10-1.jpg
        
        # 3. İhtimal: Sıfır dolgulu (01)
        variations.append(f"{date_str}-{p_num:02d}{suffix}")              # 1957-09-10-01.jpg
        
        # 4. İhtimal: Sıfırsız Tarih (1957-9-10)
        variations.append(f"{y}-{int(m)}-{int(d)}-{p_num}{suffix}")       # 1957-9-10-1.jpg
        
        # 5. İhtimal: Sıfırsız Tarih + 1 Eksiği
        if p_num > 0:
            variations.append(f"{y}-{int(m)}-{int(d)}-{p_num - 1}{suffix}") # 1957-9-10-0.jpg

    except:
        pass
    
    # Debug için (Hangi linkleri denediğini görmek istersen açabilirsin)
    # st.write(variations) 
    return variations

# --- GÖRÜNTÜ VE PDF İŞLEMLERİ ---

def get_cdn_image(gid, date_str, page_num):
    base_url = "https://dzp35pmd4yqn4.cloudfront.net/thumbnails"
    variations = generate_variations(date_str, page_num, "-thumbnail250.jpg")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": "https://www.gastearsivi.com/"
    }

    for filename in variations:
        url = f"{base_url}/{gid}/{filename}"
        try:
            r = requests.get(url, headers=headers, timeout=2)
            if r.status_code == 200:
                return Image.open(BytesIO(r.content))
        except:
            continue
    return None

def download_pdf(gid, date_str, page_num):
    base_url = "https://dzp35pmd4yqn4.cloudfront.net/sayfalar"
    variations = generate_variations(date_str, page_num, ".jpg")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": "https://www.gastearsivi.com/"
    }

    for filename in variations:
        url = f"{base_url}/{gid}/{filename}"
        try:
            # stream=True ile sadece varlığını kontrol et
            r = requests.get(url, headers=headers, timeout=5, stream=True)
            if r.status_code == 200:
                # Bulundu! İndir.
                img = Image.open(BytesIO(r.content)).convert("L")
                pdf_buffer = BytesIO()
                img.save(pdf_buffer, format="PDF", resolution=100.0, quality=85)
                pdf_buffer.seek(0)
                return pdf_buffer
        except:
            continue
    return None

# --- ARAMA FONKSİYONU ---
def search_brave(keyword, count=20):
    url = "https://api.search.brave.com/res/v1/web/search"
    query = f'site:gastearsivi.com {keyword}'
    
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": API_KEY
    }
    
    params = {"q": query, "count": count, "country": "tr", "safesearch": "off"}
    found_items = []
    
    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            if "web" in data and "results" in data["web"]:
                results = data["web"]["results"]
                for r in results:
                    page_url = r["url"]
                    raw_desc = r.get("description", "") or r.get("title", "")
                    final_desc = clean_ocr_text(raw_desc)
                    
                    match = re.search(r"gazete\/([^\/]+)\/(\d{4}-\d{2}-\d{2})\/(\d+)", page_url)
                    if match:
                        gid = match.group(1)
                        date_str = match.group(2)
                        page_num = match.group(3)
                        g_name = gid.replace("_", " ").title()
                        
                        found_items.append({
                            "id": gid, "name": g_name, "date": date_str,
                            "page": page_num, "desc": final_desc, "url": page_url
                        })
        elif response.status_code == 429:
            st.warning("Hız sınırı aşıldı.")
        elif response.status_code == 401:
            st.error("API Anahtarı geçersiz.")
    except Exception as e:
        st.error(f"Hata: {e}")
    return found_items

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
                st.write(f"_{item['desc']}_")
                
                col_dl, col_go = st.columns([1, 3])
                unique_id = f"{item['id']}_{item['date']}_{item['page']}"
                
                with col_dl:
                    if unique_id not in st.session_state.pdf_cache:
                        if st.button(f"📥 PDF Hazırla", key=f"btn_{unique_id}"):
                            with st.spinner("Arşiv taranıyor (Varyasyonlar deneniyor)..."):
                                pdf_data = download_pdf(item['id'], item['date'], item['page'])
                                if pdf_data:
                                    st.session_state.pdf_cache[unique_id] = pdf_data
                                    st.rerun()
                                else:
                                    st.error("Dosya sunucuda bulunamadı.")
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
