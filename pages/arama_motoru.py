import streamlit as st
import requests
from PIL import Image, ImageEnhance, ImageOps
from io import BytesIO
from datetime import date, timedelta
import time

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="Dijital Sahaf: Arşiv Gezgini",
    page_icon="🏛️",
    layout="wide"
)

# --- SABİT GAZETE LİSTESİ (En Kapsamlı) ---
GAZETELER = [
    {"id": "aksam", "name": "Akşam"},
    {"id": "cumhuriyet", "name": "Cumhuriyet"},
    {"id": "hurriyet", "name": "Hürriyet"},
    {"id": "milliyet", "name": "Milliyet"},
    {"id": "tan", "name": "Tan"},
    {"id": "tanin", "name": "Tanin"},
    {"id": "ulus", "name": "Ulus"},
    {"id": "vakit", "name": "Vakit"},
    {"id": "vatan", "name": "Vatan"},
    {"id": "yeni_asir", "name": "Yeni Asır"},
    {"id": "zaman", "name": "Zaman"},
    {"id": "hakimiyeti_milliye", "name": "Hakimiyet-i Milliye"},
    {"id": "tasviri_efkar", "name": "Tasviri Efkar"},
    {"id": "tercumani_ahval", "name": "Tercüman-ı Ahval"},
    {"id": "takvimi_vekayi", "name": "Takvim-i Vekayi"},
    {"id": "ikdam", "name": "İkdam"},
    {"id": "son_posta", "name": "Son Posta"},
    {"id": "yarin", "name": "Yarın"},
    {"id": "kurun", "name": "Kurun"},
    {"id": "serveti_funun", "name": "Servet-i Fünun"},
    {"id": "resimli_ay", "name": "Resimli Ay"},
    {"id": "yedi_gun", "name": "Yedi Gün"},
    {"id": "hayat", "name": "Hayat Mecmuası"},
    {"id": "akbaba", "name": "Akbaba (Mizah)"},
    {"id": "girgir", "name": "Gırgır (Mizah)"},
    {"id": "markopasa", "name": "Markopaşa"},
    {"id": "karagoz", "name": "Karagöz"},
    {"id": "diyojen", "name": "Diyojen"},
    {"id": "sozcu", "name": "Sözcü"},
    {"id": "sabah", "name": "Sabah"},
    {"id": "tercuman", "name": "Tercüman"}
]
# Listeyi isme göre sırala
GAZETELER.sort(key=lambda x: x["name"])

# --- FONKSİYONLAR ---

def get_page_image(gid, date_obj, page_num):
    """Resim sunucusundan sayfayı çeker (CDN)"""
    date_str = date_obj.strftime("%Y-%m-%d")
    base_url = "https://dzp35pmd4yqn4.cloudfront.net"
    
    # URL Varyasyonları (Bazen sayfa numaraları farklı formatta olabiliyor)
    urls = [
        f"{base_url}/sayfalar/{gid}/{date_str}-{page_num}.jpg",     # Standart
        f"{base_url}/sayfalar/{gid}/{date_str}-0{page_num}.jpg",    # Sıfırlı
        f"{base_url}/thumbnails/{gid}/{date_str}-{page_num}-thumbnail250.jpg" # Küçük Resim (Yedek)
    ]
    
    for url in urls:
        try:
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=2)
            if r.status_code == 200:
                return Image.open(BytesIO(r.content))
        except:
            continue
    return None

def make_pdf(image):
    """Görüntüyü PDF'e çevirir"""
    pdf_buffer = BytesIO()
    if image.mode != 'RGB':
        image = image.convert('RGB')
    image.save(pdf_buffer, format="PDF", resolution=100.0, quality=85)
    pdf_buffer.seek(0)
    return pdf_buffer

# --- SESSION STATE ---
if 'curr_date' not in st.session_state:
    st.session_state.curr_date = date(1938, 11, 10)

def day_change(delta):
    st.session_state.curr_date += timedelta(days=delta)

# --- ARAYÜZ ---

st.title("🏛️ Dijital Sahaf: Arşiv Gezgini")
st.markdown("Arama motorlarına takılmadan, **doğrudan raflardan** gazete çekin.")

# Üst Panel: Seçimler
with st.container():
    c1, c2, c3 = st.columns([2, 1, 1])
    
    # Gazete Seçimi
    selected_paper = c1.selectbox("Gazete Seçiniz", [g['name'] for g in GAZETELER], index=1)
    gid = next(item['id'] for item in GAZETELER if item['name'] == selected_paper)
    
    # Tarih Kontrolleri
    c2.markdown("###") # Boşluk
    if c2.button("⬅️ Önceki Gün", use_container_width=True):
        day_change(-1)
        st.rerun()
        
    c3.markdown("###")
    if c3.button("Sonraki Gün ➡️", use_container_width=True):
        day_change(1)
        st.rerun()

    # Tarih Göstergesi
    st.session_state.curr_date = st.date_input("Tarih Seçiniz", st.session_state.curr_date)
    
    st.info(f"Seçili: **{selected_paper}** - **{st.session_state.curr_date.strftime('%d %B %Y')}**")

# --- GÖRÜNTÜLEME ALANI ---
st.markdown("---")

if st.button("📥 GAZETEYİ GETİR", type="primary", use_container_width=True):
    
    found_pages = 0
    cols = st.columns(3) # 3 sütunlu görünüm
    
    # Sayfaları 1'den 20'ye kadar dene (Genelde en fazla 20 sayfa olur)
    with st.spinner("Sayfalar taranıyor..."):
        for page_num in range(1, 25):
            img = get_page_image(gid, st.session_state.curr_date, page_num)
            
            if img:
                found_pages += 1
                with cols[(page_num - 1) % 3]:
                    st.image(img, caption=f"Sayfa {page_num}", use_container_width=True)
                    
                    # İndirme Butonu
                    pdf_data = make_pdf(img)
                    fname = f"{selected_paper}_{st.session_state.curr_date}_Sayfa{page_num}.pdf"
                    
                    st.download_button(
                        label=f"💾 Sayfa {page_num} İndir",
                        data=pdf_data,
                        file_name=fname,
                        mime="application/pdf",
                        key=f"dl_{page_num}"
                    )
            else:
                # Eğer 1. sayfa yoksa gazete o gün çıkmamıştır, döngüyü kır
                if page_num == 1:
                    st.warning(f"⚠️ {selected_paper} gazetesinin {st.session_state.curr_date} tarihinde yayını bulunamadı.")
                    st.caption("Not: O tarihte gazete kapanmış olabilir, tatil olabilir veya dijitalleştirilmemiş olabilir.")
                    break
                # Eğer ortada bir sayfa yoksa (örn: 1 var, 2 yok) belki atlamıştır, devam etme.
                # Ama genelde 1 varsa devamı gelir.
                if page_num > 1 and page_num < 4: # İlk 3-4 sayfada kesilirse dur
                    break
                    
    if found_pages > 0:
        st.success(f"Toplam {found_pages} sayfa bulundu.")

# --- YARDIMCI: KELİME ARA (GOOGLE) ---
with st.sidebar:
    st.header("🔍 Konu Ara (Google)")
    st.caption("Hangi tarihe bakacağınızı bilmiyorsanız buradan aratın.")
    keyword = st.text_input("Konu (Örn: Menemen Olayı)")
    if st.button("Google'da Tarih Ara"):
        query = f'site:gastearsivi.com "{keyword}"'
        import webbrowser
        webbrowser.open(f"https://www.google.com/search?q={query}")
        st.write("Google açıldı! Orada bulduğunuz tarihi ana ekrana girin.")
