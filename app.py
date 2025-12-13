import streamlit as st
import requests
from PIL import Image, ImageEnhance, ImageOps
from io import BytesIO
from datetime import date, timedelta
import re
import time
import zipfile

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="Dijital Sahaf Pro",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# OCR Kütüphanesi Kontrolü
try:
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

# --- VERİ TABANI ---
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
    {"id": "tercuman-i-ahval", "name": "Tercüman-ı Ahval", "dates": "1860-1866"},
    {"id": "resimli-ay", "name": "Resimli Ay", "dates": "1924-1938"},
    {"id": "yarin", "name": "Yarın", "dates": "1929-1931"}
]
GASTE_ARSIVI_DATABASE.sort(key=lambda x: x["name"])

# --- YARDIMCI FONKSİYONLAR ---

def apply_image_filters(image, contrast, brightness, sharpness, invert, grayscale):
    if grayscale:
        image = image.convert("L") 
    else:
        image = image.convert("RGB")
        
    if invert:
        image = ImageOps.invert(image if not grayscale else image.convert("RGB"))
        if grayscale: image = image.convert("L")

    if contrast != 1.0:
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(contrast)
    
    if brightness != 1.0:
        enhancer = ImageEnhance.Brightness(image)
        image = enhancer.enhance(brightness)
        
    if sharpness != 1.0:
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(sharpness)
        
    return image

def get_page_image(gid, date_str, page_num):
    url = f"https://dzp35pmd4yqn4.cloudfront.net/sayfalar/{gid}/{date_str}-{page_num}.jpg"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        if r.status_code == 200:
            return Image.open(BytesIO(r.content))
    except:
        pass
    return None

def generate_apa_citation(name, date_obj, range_end=None):
    tr_months = {
        "January": "Ocak", "February": "Şubat", "March": "Mart", "April": "Nisan", "May": "Mayıs", "June": "Haziran",
        "July": "Temmuz", "August": "Ağustos", "September": "Eylül", "October": "Ekim", "November": "Kasım", "December": "Aralık"
    }
    date_formatted = date_obj.strftime("%d %B %Y")
    for eng, tr in tr_months.items():
        date_formatted = date_formatted.replace(eng, tr)

    if range_end:
        end_formatted = range_end.strftime("%d %B %Y")
        for eng, tr in tr_months.items():
            end_formatted = end_formatted.replace(eng, tr)
        return f"{name}. ({date_obj.year}). {name} Gazetesi ({date_formatted} - {end_formatted}). Dijital Sahaf Arşivi."
    else:
        return f"{name}. ({date_obj.year}, {date_formatted}). {name} Gazetesi. Dijital Sahaf Arşivi."

def process_archive_single(gid, name, date_obj, img_settings, pdf_settings, progress_callback=None):
    date_str = date_obj.strftime("%Y-%m-%d")
    images = []
    page = 1
    tolerance = 0
    
    while page <= 99:
        if tolerance >= 2: break
        if progress_callback:
            progress_callback(f"{date_str} - Sayfa {page} işleniyor...")
        
        raw_img = get_page_image(gid, date_str, page)
        
        if raw_img:
            processed_img = apply_image_filters(
                raw_img, 
                img_settings['contrast'], 
                img_settings['brightness'], 
                img_settings['sharpness'],
                img_settings['invert'],
                img_settings['grayscale']
            )
            images.append(processed_img)
            tolerance = 0
        else:
            tolerance += 1
        
        page += 1
        time.sleep(0.05) 

    if not images:
        return None

    pdf_buffer = BytesIO()
    save_params = {
        "save_all": True,
        "append_images": images[1:],
        "resolution": 100.0,
        "quality": 85
    }
    
    if pdf_settings['compress']:
        save_params["optimize"] = True
        save_params["quality"] = 65 
        
    images[0].save(pdf_buffer, format="PDF", **save_params)
    pdf_buffer.seek(0)
    return pdf_buffer

# --- ARAYÜZ BAŞLANGICI ---

# YAN MENÜ (GLOBAL AYARLAR)
st.sidebar.title("🛠️ Kontrol Paneli")

nav_mode = st.sidebar.radio("Navigasyon Modu", ["📖 Katalogdan Seç", "🔗 Link ile İndir"])
st.sidebar.markdown("---")

st.sidebar.subheader("📅 Tarih Modu")
date_mode = st.sidebar.radio("İndirme Tipi", ["Tek Gün", "Tarih Aralığı (Toplu ZIP)"])

selected_date_start = None
selected_date_end = None

if date_mode == "Tek Gün":
    selected_date_start = st.sidebar.date_input("Tarih", date(1930, 1, 1), min_value=date(1800, 1, 1), max_value=date.today())
    selected_date_end = selected_date_start
else:
    st.sidebar.info("Başlangıç ve Bitiş tarihlerini seçin.")
    col_d1, col_d2 = st.sidebar.columns(2)
    with col_d1:
        selected_date_start = st.date_input("Başlangıç", date(1930, 1, 1), min_value=date(1800, 1, 1))
    with col_d2:
        selected_date_end = st.date_input("Bitiş", date(1930, 1, 7), min_value=date(1800, 1, 1))

st.sidebar.markdown("---")

st.sidebar.subheader("🎨 Görüntü Laboratuvarı")
contrast = st.sidebar.slider("Kontrast", 0.5, 2.0, 1.0, 0.1)
brightness = st.sidebar.slider("Parlaklık", 0.5, 2.0, 1.0, 0.1)
grayscale = st.sidebar.checkbox("Siyah-Beyaz Modu", value=False)
invert = st.sidebar.checkbox("Negatif (Gece) Modu", value=False)

img_settings = {
    "contrast": contrast,
    "brightness": brightness,
    "sharpness": 1.0,
    "grayscale": grayscale,
    "invert": invert
}

st.sidebar.markdown("---")
st.sidebar.subheader("💾 Çıktı")
compress = st.sidebar.checkbox("PDF Sıkıştırma (Optimize)", value=True)
create_zip = st.sidebar.checkbox("📂 Aralığı ZIP Yap", value=True, disabled=(date_mode=="Tek Gün"))

pdf_settings = {
    "compress": compress,
    "ocr": False
}

# --- SEKME YAPISI ---
tab_app, tab_guide, tab_notes = st.tabs(["🚀 Uygulama", "📖 Kullanma Kılavuzu", "📝 Güncelleme Notları"])

# --- TAB 1: UYGULAMA (ANA MODÜL) ---
with tab_app:
    gid = None
    selected_name = ""

    if nav_mode == "📖 Katalogdan Seç":
        st.title("🎓 Dijital Sahaf: Akademik Arşiv")
        selected_name = st.selectbox("Yayın Seçiniz", [i["name"] for i in GASTE_ARSIVI_DATABASE])
        item_data = next(i for i in GASTE_ARSIVI_DATABASE if i["name"] == selected_name)
        gid = item_data["id"]
    else:
        st.title("🔗 Link Çözücü")
        url_input = st.text_input("GasteArsivi Linki")
        if url_input:
            match = re.search(r"gazete\/([^\/]+)\/(\d{4}-\d{2}-\d{2})", url_input)
            if match:
                gid = match.group(1)
                date_str = match.group(2)
                y, m, d = map(int, date_str.split('-'))
                selected_date_start = date(y, m, d)
                selected_date_end = selected_date_start
                date_mode = "Tek Gün"
                found_name = next((i["name"] for i in GASTE_ARSIVI_DATABASE if i["id"] == gid), gid)
                selected_name = found_name
                st.success(f"Link Algılandı: {selected_name}")

    if gid and selected_date_start:
        st.markdown("---")
        delta = selected_date_end - selected_date_start
        total_days = delta.days + 1
        
        if total_days < 1:
            st.error("Bitiş tarihi başlangıçtan önce olamaz!")
            st.stop()

        col_preview, col_action = st.columns([1, 2])
        
        with col_preview:
            st.subheader("🔍 Referans Önizleme")
            st.caption(f"Tarih: {selected_date_start}")
            
            with st.spinner("Görüntü alınıyor..."):
                date_str = selected_date_start.strftime("%Y-%m-%d")
                raw_preview = get_page_image(gid, date_str, 1)
                
                if raw_preview:
                    final_preview = apply_image_filters(raw_preview, contrast, brightness, 1.0, invert, grayscale)
                    st.image(final_preview, caption=f"Filtreli Görünüm", use_container_width=True)
                    preview_ok = True
                else:
                    st.warning("Başlangıç tarihinde yayın yok.")
                    st.image("https://placehold.co/400x600?text=Arsiv+Yok", use_container_width=True)
                    preview_ok = False

        with col_action:
            st.subheader("⚙️ İşlem Merkezi")
            st.info(f"**Yayın:** {selected_name} | **Aralık:** {total_days} Gün")
            
            with st.expander("🎓 APA Kaynakça (Kopyala)", expanded=True):
                apa_text = generate_apa_citation(selected_name, selected_date_start, selected_date_end if total_days > 1 else None)
                st.code(apa_text, language="text")

            if preview_ok or total_days > 1:
                btn_label = f"🚀 {total_days} Günlük Arşivi İndir" if total_days > 1 else "🚀 PDF İndir"
                
                if st.button(btn_label, type="primary"):
                    progress_bar = st.progress(0)
                    status_area = st.empty()
                    generated_files = [] 
                    
                    for i in range(total_days):
                        current_date = selected_date_start + timedelta(days=i)
                        status_area.text(f"İşleniyor: {current_date.strftime('%d.%m.%Y')} ({i+1}/{total_days})")
                        progress_bar.progress((i) / total_days)
                        
                        pdf_data = process_archive_single(gid, selected_name, current_date, img_settings, pdf_settings)
                        
                        if pdf_data:
                            fname = f"{selected_name.replace(' ', '_')}_{current_date.strftime('%Y-%m-%d')}.pdf"
                            generated_files.append((fname, pdf_data))
                    
                    progress_bar.progress(1.0)
                    status_area.success(f"Tamamlandı! {len(generated_files)} dosya hazır.")
                    
                    if len(generated_files) > 0:
                        if len(generated_files) > 1 and create_zip:
                            zip_buffer = BytesIO()
                            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zf:
                                for fname, data in generated_files:
                                    zf.writestr(fname, data.getvalue())
                            zip_buffer.seek(0)
                            zip_name = f"{selected_name}_Arsiv_{selected_date_start}_{selected_date_end}.zip"
                            st.download_button(f"📦 ZIP İndir ({len(generated_files)} Dosya)", zip_buffer, file_name=zip_name, mime="application/zip")
                        else:
                            for fname, data in generated_files:
                                st.download_button(f"📄 {fname}", data, file_name=fname, mime="application/pdf", key=fname)
                    else:
                        st.warning("Hiçbir yayın bulunamadı.")

# --- TAB 2: KULLANMA KILAVUZU ---
with tab_guide:
    st.header("📖 Dijital Sahaf Nasıl Kullanılır?")
    
    st.markdown("""
    ### 1. Adım: Yayın Seçimi
    * **Katalogdan Seç:** Listeden istediğiniz gazeteyi (Örn: Tanin, Cumhuriyet) seçin.
    * **Link ile İndir:** GasteArşivi.com'dan kopyaladığınız bir linki yapıştırarak direkt o sayıya gidin.
    
    ### 2. Adım: Tarih Belirleme (Sol Menü)
    * **Tek Gün:** Sadece belirli bir tarihi indirmek için kullanılır.
    * **Tarih Aralığı (Toplu):** Araştırma yaparken belirli bir dönemi (Örn: 1-30 Ocak 1930) komple indirmek için seçin.
    * *İpucu:* Toplu indirmede **"Aralığı ZIP Yap"** seçeneği işaretliyse tüm PDF'ler tek bir pakette iner.
    
    ### 3. Adım: Görüntü İyileştirme (Image Lab)
    Eski gazetelerin okunabilirliğini artırmak için sol menüdeki ayarları kullanın:
    * **Kontrast:** Yazıları koyulaştırır, arka planı siler.
    * **Parlaklık:** Çok koyu taramaları açar.
    * **Siyah-Beyaz Modu:** En temiz okuma deneyimi için önerilir (Fotokopi gibi yapar).
    * **Negatif Mod:** Göz yorgunluğunu azaltmak için (Mikrofilm tarzı).
    * *Not:* Yaptığınız ayarlar önizlemede anlık görünür ve inen PDF'e de işlenir.
    
    ### 4. Adım: İndirme ve Kaynakça
    * **Önizleme:** Seçtiğiniz tarihte gazete varsa sağda kapağını görürsünüz.
    * **Kaynakça:** Tez veya makaleniz için otomatik oluşturulan **APA formatındaki** metni kopyalayın.
    * **İndir:** Butona basın, işlem bitince dosyanızı kaydedin.
    """)

# --- TAB 3: GÜNCELLEME NOTLARI ---
with tab_notes:
    st.header("📝 Sürüm Geçmişi")
    
    st.info("Şu Anki Sürüm: **v19.0 (Docs Edition)**")
    
    st.markdown("""
    #### v19.0 - Dokümantasyon
    * ✅ **Kullanma Kılavuzu** sekmesi eklendi.
    * ✅ **Güncelleme Notları** takip sistemi eklendi.
    * ✅ Arayüz sekmeli yapıya geçirildi (Daha temiz görünüm).
    
    #### v18.0 - Akademik Araştırma
    * ✅ **Tarih Aralığı Seçimi:** Tek seferde aylık/yıllık tarama imkanı.
    * ✅ **ZIP Paketleyici:** Çoklu indirmeleri tek dosyada birleştirme.
    * ✅ **APA Kaynakça:** Otomatik atıf metni oluşturucu.
    
    #### v17.0 - Web & Image Lab
    * ✅ **Web Arayüzü:** Streamlit teknolojisine geçiş (Telefondan erişim).
    * ✅ **Görüntü Laboratuvarı:** Kontrast, Parlaklık, Siyah-Beyaz filtreleri.
    * ✅ **Link Ayrıştırıcı:** Direkt link ile indirme desteği.
    """)
