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
    {"id": "yarin", "name": "Yarın", "dates": "1929-1931"},
    {"id": "akbaba", "name": "Akbaba", "dates": "1922-1977"},
    {"id": "hakimiyeti_milliye", "name": "Hakimiyet-i Milliye", "dates": "1920-1934"}
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
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=3)
        if r.status_code == 200:
            return Image.open(BytesIO(r.content))
    except:
        pass
    return None

def check_daily_availability(check_date):
    available_papers = []
    date_str = check_date.strftime("%Y-%m-%d")
    progress_bar = st.progress(0)
    total = len(GASTE_ARSIVI_DATABASE)
    for idx, paper in enumerate(GASTE_ARSIVI_DATABASE):
        url = f"https://dzp35pmd4yqn4.cloudfront.net/sayfalar/{paper['id']}/{date_str}-1.jpg"
        try:
            r = requests.head(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=0.5)
            if r.status_code == 200:
                available_papers.append(paper['name'])
        except:
            pass
        progress_bar.progress((idx + 1) / total)
    progress_bar.empty()
    return available_papers

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

nav_mode = st.sidebar.radio(
    "Çalışma Modu", 
    ["📖 Katalogdan Seç", "🔗 Link ile İndir", "🆚 Manşet Kıyaslama"]
)
st.sidebar.markdown("---")

# TARİH & GÖRÜNTÜ AYARLARI (MODA GÖRE DEĞİŞİR)
selected_date_start = None
selected_date_end = None
date_mode = "Tek Gün"

if nav_mode == "🆚 Manşet Kıyaslama":
    st.sidebar.info("Kıyaslama modunda tarih ortaktır.")
    selected_date_start = st.sidebar.date_input("Kıyaslama Tarihi", date(1930, 1, 1), min_value=date(1800, 1, 1))
    selected_date_end = selected_date_start
elif nav_mode == "📖 Katalogdan Seç":
    st.sidebar.subheader("📅 Tarih Modu")
    date_mode = st.sidebar.radio("İndirme Tipi", ["Tek Gün", "Tarih Aralığı (Toplu ZIP)"])
    if date_mode == "Tek Gün":
        selected_date_start = st.sidebar.date_input("Tarih", date(1930, 1, 1), min_value=date(1800, 1, 1))
        selected_date_end = selected_date_start
    else:
        col_d1, col_d2 = st.sidebar.columns(2)
        with col_d1: selected_date_start = st.date_input("Başlangıç", date(1930, 1, 1))
        with col_d2: selected_date_end = st.date_input("Bitiş", date(1930, 1, 7))

st.sidebar.markdown("---")
st.sidebar.subheader("🎨 Görüntü Laboratuvarı")
contrast = st.sidebar.slider("Kontrast", 0.5, 2.0, 1.0, 0.1)
brightness = st.sidebar.slider("Parlaklık", 0.5, 2.0, 1.0, 0.1)
grayscale = st.sidebar.checkbox("Siyah-Beyaz Modu", value=False)
invert = st.sidebar.checkbox("Negatif (Gece) Modu", value=False)

img_settings = {"contrast": contrast, "brightness": brightness, "sharpness": 1.0, "grayscale": grayscale, "invert": invert}

st.sidebar.markdown("---")
compress = st.sidebar.checkbox("PDF Sıkıştırma", value=True)
pdf_settings = {"compress": compress, "ocr": False}

# --- SEKME YAPISI ---
tab_app, tab_guide, tab_notes = st.tabs(["🚀 Uygulama", "📖 Kılavuz & İpuçları", "📝 Sürüm Notları"])

# --- TAB 1: UYGULAMA ---
with tab_app:
    # ---------------------------
    # MOD: KIYASLAMA (COMPARISON)
    # ---------------------------
    if nav_mode == "🆚 Manşet Kıyaslama":
        st.title("🆚 Manşet Kıyaslama Masası")
        st.caption(f"Seçili Tarih: {selected_date_start.strftime('%d.%m.%Y')}")
        
        col_left, col_right = st.columns(2)
        
        # SOL GAZETE
        with col_left:
            st.subheader("Yayın A (Sol)")
            paper_a = st.selectbox("1. Gazeteyi Seç", [i["name"] for i in GASTE_ARSIVI_DATABASE], index=0)
            gid_a = next(i["id"] for i in GASTE_ARSIVI_DATABASE if i["name"] == paper_a)
            
            with st.spinner(f"{paper_a} yükleniyor..."):
                img_a = get_page_image(gid_a, selected_date_start.strftime("%Y-%m-%d"), 1)
                if img_a:
                    proc_a = apply_image_filters(img_a, contrast, brightness, 1.0, invert, grayscale)
                    st.image(proc_a, caption=f"{paper_a} Manşet", use_container_width=True)
                    if st.button(f"📥 {paper_a} İndir", key="dl_a"):
                        pdf = process_archive_single(gid_a, paper_a, selected_date_start, img_settings, pdf_settings)
                        if pdf: st.download_button("Kaydet", pdf, f"{paper_a}.pdf", "application/pdf")
                else:
                    st.error("Yayın Bulunamadı")
                    st.image("https://placehold.co/400x600?text=Yok", use_container_width=True)

        # SAĞ GAZETE
        with col_right:
            st.subheader("Yayın B (Sağ)")
            paper_b = st.selectbox("2. Gazeteyi Seç", [i["name"] for i in GASTE_ARSIVI_DATABASE], index=1)
            gid_b = next(i["id"] for i in GASTE_ARSIVI_DATABASE if i["name"] == paper_b)
            
            with st.spinner(f"{paper_b} yükleniyor..."):
                img_b = get_page_image(gid_b, selected_date_start.strftime("%Y-%m-%d"), 1)
                if img_b:
                    proc_b = apply_image_filters(img_b, contrast, brightness, 1.0, invert, grayscale)
                    st.image(proc_b, caption=f"{paper_b} Manşet", use_container_width=True)
                    if st.button(f"📥 {paper_b} İndir", key="dl_b"):
                        pdf = process_archive_single(gid_b, paper_b, selected_date_start, img_settings, pdf_settings)
                        if pdf: st.download_button("Kaydet", pdf, f"{paper_b}.pdf", "application/pdf")
                else:
                    st.error("Yayın Bulunamadı")
                    st.image("https://placehold.co/400x600?text=Yok", use_container_width=True)

    # ---------------------------
    # MOD: KATALOG & LINK
    # ---------------------------
    else:
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
                    selected_date_start = date(*map(int, match.group(2).split('-')))
                    selected_date_end = selected_date_start
                    date_mode = "Tek Gün"
                    found_name = next((i["name"] for i in GASTE_ARSIVI_DATABASE if i["id"] == gid), gid)
                    selected_name = found_name
                    st.success(f"Link Algılandı: {selected_name}")

        if gid and selected_date_start:
            st.markdown("---")
            delta = selected_date_end - selected_date_start
            total_days = delta.days + 1
            
            col_preview, col_action = st.columns([1, 2])
            
            with col_preview:
                st.subheader("🔍 Referans Önizleme")
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
                
                # YAYIN RADARI
                with st.expander("📡 Bu Tarihteki Diğer Yayınlar (Radar)"):
                    st.caption("Seçili tarihte çıkan diğer gazeteleri tarar.")
                    if st.button("Taramayı Başlat"):
                        available = check_daily_availability(selected_date_start)
                        if available:
                            st.success(f"{len(available)} yayın bulundu:")
                            for p in available:
                                st.write(f"• {p}")
                        else:
                            st.warning("Başka yayın bulunamadı.")

            with col_action:
                st.subheader("⚙️ İşlem Merkezi")
                st.info(f"**Yayın:** {selected_name} | **Aralık:** {total_days} Gün")
                
                with st.expander("🎓 APA Kaynakça", expanded=True):
                    apa_text = generate_apa_citation(selected_name, selected_date_start, selected_date_end if total_days > 1 else None)
                    st.code(apa_text, language="text")

                if preview_ok or total_days > 1:
                    btn_label = f"🚀 {total_days} Günlük Arşivi İndir" if total_days > 1 else "🚀 PDF İndir"
                    create_zip = st.checkbox("📂 Aralığı ZIP Yap", value=True, disabled=(date_mode=="Tek Gün"), key="zip_main")
                    
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
                                st.download_button(f"📦 ZIP İndir", zip_buffer, f"{selected_name}_Arsiv.zip", "application/zip")
                            else:
                                for fname, data in generated_files:
                                    st.download_button(f"📄 {fname}", data, file_name=fname, mime="application/pdf", key=fname)
                        else:
                            st.warning("Hiçbir yayın bulunamadı.")

# --- TAB 2: KILAVUZ ---
with tab_guide:
    st.header("📖 Dijital Sahaf Kullanım Kılavuzu")
    
    st.markdown("""
    ### 1. Navigasyon (Sol Menü)
    * **Katalogdan Seç:** Sistemde tanımlı gazeteleri (Cumhuriyet, Tan, Akşam vb.) listeden seçerek ilerlersiniz.
    * **Link ile İndir:** GasteArşivi sitesindeki bir linki yapıştırarak direkt o sayıya gidersiniz.
    * **Manşet Kıyaslama:** Aynı tarihteki iki farklı gazeteyi yan yana açıp karşılaştırmanızı sağlar.

    ### 2. Görüntü Laboratuvarı (Image Lab)
    Eski ve silik gazeteleri okunabilir hale getirmek için filtreleri kullanın:
    * **Kontrast:** Yazıları koyulaştırır, kağıt lekesini siler.
    * **Parlaklık:** Çok koyu (kömürleşmiş) taramaları açar.
    * **Siyah-Beyaz Modu:** Arka planı tamamen beyazlatır, sadece yazıyı bırakır (Önerilen).
    * **Negatif Mod:** Gece okumaları için renkleri ters çevirir.

    ### 3. Toplu İndirme ve ZIP
    * Sol menüden **"Tarih Aralığı (Toplu ZIP)"** seçeneğini seçin.
    * Başlangıç ve Bitiş tarihlerini girin (Örn: 1-30 Ocak 1930).
    * **"Aralığı ZIP Yap"** kutusunu işaretleyin.
    * İndir butonuna bastığınızda sistem tüm günleri tarar ve tek bir dosya verir.

    ### 4. Yayın Radarı
    * Bir gazeteyi görüntülerken, alt kısımdaki **"Bu Tarihteki Diğer Yayınlar"** panelini açın.
    * "Taramayı Başlat" dediğinizde, sistem o gün yayınlanan diğer tüm gazeteleri sizin için bulur.
    """)

# --- TAB 3: NOTLAR ---
with tab_notes:
    st.header("📝 Sürüm Notları")
    
    st.info("Mevcut Sürüm: **v20.1 (Stable - Docs Edition)**")
    
    st.markdown("""
    #### v20.1
    * 🐛 Sekme yapısındaki kayma sorunu düzeltildi.
    * 📖 Kullanım Kılavuzu sekmesi detaylandırıldı.
    
    #### v20.0 - Platinum Edition
    * ✅ **Manşet Kıyaslama Modu:** İki gazete yan yana analiz edilebilir.
    * ✅ **Yayın Radarı:** Tarih bazlı çapraz tarama özelliği eklendi.
    * ✅ **Akıllı ZIP:** Çoklu dosya indirmelerinde otomatik paketleme.
    
    #### v19.0 - Akademik Araştırma
    * ✅ **APA Atıf Motoru:** Otomatik kaynakça oluşturma.
    * ✅ **Görüntü İşleme:** Kontrast ve Siyah-Beyaz filtreleri.
    """)
