import streamlit as st
from googlesearch import search
import requests
from PIL import Image, ImageOps
from io import BytesIO
import re
import time

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="Google Destekli Sahaf",
    page_icon="🌍",
    layout="wide"
)

# --- FONKSİYONLAR ---

def google_ile_ara(keyword, num_results=20):
    """
    Google'da 'site:gastearsivi.com keyword' araması yapar
    ve sonuçları bizim formatımıza çevirir.
    """
    # Google'a özel sorgu formatı
    query = f'site:gastearsivi.com "{keyword}"'
    
    found_items = []
    
    try:
        # Google'dan sonuçları çek (advanced=True başlık ve açıklama da getirir)
        search_results = search(query, num_results=num_results, advanced=True, lang="tr")
        
        for result in search_results:
            url = result.url
            title = result.title
            desc = result.description
            
            # URL Analizi (Regex ile ID, Tarih ve Sayfa No'yu söküyoruz)
            # Link Tipi: https://www.gastearsivi.com/gazete/aksam/1938-11-10/1
            match = re.search(r"gazete\/([^\/]+)\/(\d{4}-\d{2}-\d{2})\/(\d+)", url)
            
            if match:
                gid = match.group(1)
                date_str = match.group(2)
                page_num = match.group(3)
                
                # Gazete adını güzelleştir
                g_name = gid.replace("_", " ").replace("-", " ").title()
                
                found_items.append({
                    "id": gid,
                    "name": g_name,
                    "date": date_str,
                    "page": page_num,
                    "title": title,
                    "desc": desc,
                    "url": url
                })
                
    except Exception as e:
        st.error(f"Google Arama Hatası: {e}")
        st.warning("Çok sık arama yaptıysanız Google geçici olarak engellemiş olabilir.")
        
    return found_items

def get_cdn_image(gid, date_str, page_num):
    """Resmi CDN'den çeker (Engel yok)"""
    base_url = "https://dzp35pmd4yqn4.cloudfront.net"
    
    # İki tip thumbnail adresi deniyoruz (Büyük ve Küçük)
    urls = [
        f"{base_url}/thumbnails/{gid}/{date_str}-{page_num}-thumbnail250.jpg", # Küçük (Hızlı)
        f"{base_url}/sayfalar/{gid}/{date_str}-{page_num}.jpg" # Büyük
    ]
    
    for url in urls:
        try:
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=3)
            if r.status_code == 200:
                return Image.open(BytesIO(r.content))
        except:
            pass
    return None

def download_pdf(gid, date_str, page_num):
    """Yüksek kaliteli PDF indirir"""
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

st.title("🌍 Google Destekli Dijital Sahaf")
st.markdown("""
Bu modül, sitenin kendi arama motorunu değil, **Google altyapısını** kullanır. 
Böylece 'Sonuç Bulunamadı' veya '403 Yasak' hatalarını aşarsınız.
""")

with st.sidebar:
    st.header("Arama Ayarları")
    keyword = st.text_input("Anahtar Kelime", placeholder="Örn: Hatay Meselesi")
    limit = st.slider("Sonuç Sayısı", 10, 100, 20)
    search_btn = st.button("Google'da Ara 🚀", type="primary")
    
    st.info("İpucu: Tarih aralığı için kelimenin yanına yıl yazabilirsiniz. Örn: 'Atatürk 1938'")

# --- İŞLEM ---
if search_btn and keyword:
    with st.spinner("Google taranıyor, linkler ayıklanıyor..."):
        results = google_ile_ara(keyword, limit)
        
        if results:
            st.success(f"✅ {len(results)} adet sonuç bulundu ve listelendi.")
            st.markdown("---")
            
            # Sonuçları Göster
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
                    
                    # Sağ: Bilgi ve İndirme
                    with c2:
                        st.subheader(f"{item['name']} - {item['date']}")
                        st.caption(f"Sayfa: {item['page']} | Kaynak: Google")
                        st.write(f"**Özet:** {item['desc']}")
                        st.markdown(f"[Orjinal Linke Git]({item['url']})")
                        
                        # İndirme Butonu
                        unique_key = f"{item['id']}_{item['date']}_{item['page']}"
                        if st.button(f"📥 PDF Olarak İndir ({item['name']})", key=unique_key):
                            with st.spinner("İndiriliyor..."):
                                pdf_data = download_pdf(item['id'], item['date'], item['page'])
                                if pdf_data:
                                    fname = f"{item['name']}_{item['date']}_S{item['page']}.pdf"
                                    st.download_button(
                                        label="💾 Dosyayı Kaydet",
                                        data=pdf_data,
                                        file_name=fname,
                                        mime="application/pdf",
                                        key=f"dl_{unique_key}"
                                    )
                                else:
                                    st.error("Dosya sunucudan çekilemedi.")
                    st.divider()
        else:
            st.warning("Google'da bu kelimeyle ilgili, bu siteye ait sonuç bulunamadı.")
