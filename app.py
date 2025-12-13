import streamlit as st
import requests
from PIL import Image, ImageEnhance, ImageOps
from io import BytesIO
from datetime import date, timedelta, datetime
import re
import time
import zipfile
import sqlite3
import pandas as pd

# --- 1. SAYFA AYARLARI ---
st.set_page_config(
    page_title="Dijital Sahaf Pro",
    page_icon="🕰️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# OCR Kütüphanesi Kontrolü (Hata vermemesi için güvenli blok)
try:
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

# --- 2. VERİTABANI BAŞLATMA (SQLITE - KÜTÜPHANE İÇİN) ---
def init_db():
    conn = sqlite3.connect('sahaf_library.db', check_same_thread=False)
    c = conn.cursor()
    # İndirme Geçmişi Tablosu
    c.execute('''CREATE TABLE IF NOT EXISTS downloads 
                 (date_added TIMESTAMP, newspaper TEXT, pub_date TEXT, type TEXT)''')
    # Favoriler Tablosu
    c.execute('''CREATE TABLE IF NOT EXISTS favorites 
                 (date_added TIMESTAMP, newspaper TEXT, pub_date TEXT, note TEXT)''')
    conn.commit()
    return conn

conn = init_db()

# --- 3. GARANTİLİ VERİ TABANI (WINDOWS SÜRÜMÜNDEN) ---
# Sadece GasteArsivi sunucularında kesin var olanlar.
GASTE_ARSIVI_DATABASE = [
    {"id": "ahali_filibe", "name": "Ahali (Filibe)", "dates": "1897 – 1900'ler"},
    {"id": "akbaba", "name": "Akbaba", "dates": "1922 – 1977"},
    {"id": "akis", "name": "Akis", "dates": "1954 – 1967"},
    {"id": "aksam", "name": "Akşam", "dates": "1918 – Günümüz"},
    {"id": "anadolu", "name": "Anadolu", "dates": "1912 – 2010'lar"},
    {"id": "ant", "name": "Ant", "dates": "1967 – 1971"},
    {"id": "aydede", "name": "Aydede", "dates": "1922 (Ocak – Kasım)"},
    {"id": "agac", "name": "Ağaç", "dates": "1936"},
    {"id": "balkan_filibe", "name": "Balkan (Filibe)", "dates": "1906 – 1910"},
    {"id": "bilim_teknik", "name": "Bilim ve Teknik", "dates": "1967 – Günümüz"},
    {"id": "birgun", "name": "Birgün", "dates": "2004 – Günümüz"},
    {"id": "bugun_2005", "name": "Bugün (2005)", "dates": "2005 – 2016"},
    {"id": "buyuk_dogu", "name": "Büyük Doğu", "dates": "1943 – 1978"},
    {"id": "commodore", "name": "Commodore", "dates": "1980'ler – 1990'lar"},
    {"id": "cumhuriyet", "name": "Cumhuriyet", "dates": "1924 – Günümüz"},
    {"id": "demokrat_izmir", "name": "Demokrat İzmir", "dates": "1946 – 1980"},
    {"id": "diyojen", "name": "Diyojen", "dates": "1870 – 1873"},
    {"id": "dunya", "name": "Dünya", "dates": "1952 – Günümüz"},
    {"id": "girgir", "name": "Gırgır", "dates": "1972 – 1989"},
    {"id": "hakimiyeti_milliye", "name": "Hakimiyet-i Milliye", "dates": "1920 – 1934"},
    {"id": "hayat_1956", "name": "Hayat (1956)", "dates": "1956 – 1980'ler"},
    {"id": "kadro", "name": "Kadro", "dates": "1932 – 1934"},
    {"id": "kurun", "name": "Kurun", "dates": "1930'lar"},
    {"id": "markopasa", "name": "Markopaşa", "dates": "1946 – 1947"},
    {"id": "milli_gazete", "name": "Milli Gazete", "dates": "1973 – Günümüz"},
    {"id": "nokta", "name": "Nokta", "dates": "1982 – 2007"},
    {"id": "peyam", "name": "Peyam", "dates": "1913 – 1922"},
    {"id": "resimli_ay", "name": "Resimli Ay", "dates": "1924 – 1938"},
    {"id": "sebilurresad", "name": "Sebilürreşad", "dates": "1908 – 1966"},
    {"id": "serbes_cumhuriyet", "name": "Serbes Cumhuriyet", "dates": "1930"},
    {"id": "serveti_funun", "name": "Servet-i Fünun", "dates": "1891 – 1944"},
    {"id": "son_posta", "name": "Son Posta", "dates": "1930 – 1960"},
    {"id": "tan", "name": "Tan", "dates": "1935 – 1945"},
    {"id": "tanin", "name": "Tanin", "dates": "1908 – 1947"},
    {"id": "taraf", "name": "Taraf", "dates": "2007 – 2016"},
    {"id": "tasviri_efkar", "name": "Tasviri Efkar", "dates": "1862 – 1871"},
    {"id": "ulus", "name": "Ulus", "dates": "1934 – 1971"},
    {"id": "vakit", "name": "Vakit", "dates": "1917 – 1950'ler"},
    {"id": "vatan", "name": "Vatan", "dates": "1923 – 1975"},
    {"id": "yarim_ay", "name": "Yarım Ay", "dates": "1935 – 1940"},
    {"id": "yarın", "name": "Yarın", "dates": "1929 – 1931"},
    {"id": "yeni_asir", "name": "Yeni Asır", "dates": "1895 – Günümüz"},
    {"id": "zaman", "name": "Zaman", "dates": "1986 – 2016"},
    {"id": "iradei_milliye_sivas", "name": "İrade-i Milliye (Sivas)", "dates": "1919 – 1922"},
    {"id": "gunaydin", "name": "Günaydın", "dates": "1968 – 1999"},
    {"id": "haberturk", "name": "Habertürk", "dates": "2009 – 2018"},
    {"id": "hurriyet", "name": "Hürriyet", "dates": "1948 - Günümüz"},
    {"id": "milliyet", "name": "Milliyet", "dates": "1950 – Günümüz"},
    {"id": "sabah", "name": "Sabah", "dates": "1985 – Günümüz"},
    {"id": "sozcu", "name": "Sözcü", "dates": "2007 – Günümüz"},
    {"id": "yeni_safak", "name": "Yeni Şafak", "dates": "1994 – Günümüz"},
    {"id": "takvimi_vekayi", "name": "Takvim-i Vekayi", "dates": "1831 – 1922"},
    {"id": "tercumani_ahval", "name": "Tercüman-ı Ahval", "dates": "1860 - 1866"},
    {"id": "ceridei_havadis", "name": "Ceride-i Havadis", "dates": "1840 - 1864"}
]
GASTE_ARSIVI_DATABASE.sort(key=lambda x: x["name"])

# --- 4. SESSION STATE (ZAMAN YOLCULUĞU İÇİN) ---
if 'current_date' not in st.session_state:
    st.session_state.current_date = date(1930, 1, 1)

def change_date(days):
    """Tarihi ileri/geri sarar"""
    st.session_state.current_date += timedelta(days=days)

# --- 5. YARDIMCI FONKSİYONLAR ---

def log_download(newspaper, pub_date, dl_type):
    """İndirmeyi veritabanına kaydeder"""
    c = conn.cursor()
    c.execute("INSERT INTO downloads VALUES (?, ?, ?, ?)", 
              (datetime.now(), newspaper, pub_date.strftime("%Y-%m-%d"), dl_type))
    conn.commit()

def add_favorite(newspaper, pub_date, note=""):
    """Favorilere ekler"""
    c = conn.cursor()
    check = c.execute("SELECT * FROM favorites WHERE newspaper=? AND pub_date=?", 
                      (newspaper, pub_date.strftime("%Y-%m-%d"))).fetchone()
    if not check:
        c.execute("INSERT INTO favorites VALUES (?, ?, ?, ?)", 
                  (datetime.now(), newspaper, pub_date.strftime("%Y-%m-%d"), note))
        conn.commit()
        return True
    return False

def apply_image_filters(image, contrast, brightness, sharpness, invert, grayscale):
    """Görüntü iyileştirme motoru"""
    if grayscale: image = image.convert("L") 
    else: image = image.convert("RGB")
    
    if invert:
        image = ImageOps.invert(image if not grayscale else image.convert("RGB"))
        if grayscale: image = image.convert("L")

    if contrast != 1.0: image = ImageEnhance.Contrast(image).enhance(contrast)
    if brightness != 1.0: image = ImageEnhance.Brightness(image).enhance(brightness)
    if sharpness != 1.0: image = ImageEnhance.Sharpness(image).enhance(sharpness)
    return image

def get_page_image(gid, date_str, page_num):
    """Sunucudan resim çeker (RAM'e)"""
    url = f"https://dzp35pmd4yqn4.cloudfront.net/sayfalar/{gid}/{date_str}-{page_num}.jpg"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=3)
        if r.status_code == 200: return Image.open(BytesIO(r.content))
    except: pass
    return None

def check_daily_availability(check_date):
    """RADAR: O gün çıkan diğer gazeteleri tarar"""
    available_papers = []
    date_str = check_date.strftime("%Y-%m-%d")
    progress_bar = st.progress(0)
    total = len(GASTE_ARSIVI_DATABASE)
    
    for idx, paper in enumerate(GASTE_ARSIVI_DATABASE):
        # Sadece başlık (HEAD) isteği atar, hızlıdır
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
    """Akademik APA kaynakçası oluşturur"""
    tr_months = {"January": "Ocak", "February": "Şubat", "March": "Mart", "April": "Nisan", "May": "Mayıs", "June": "Haziran", "July": "Temmuz", "August": "Ağustos", "September": "Eylül", "October": "Ekim", "November": "Kasım", "December": "Aralık"}
    date_formatted = date_obj.strftime("%d %B %Y")
    for eng, tr in tr_months.items(): date_formatted = date_formatted.replace(eng, tr)

    if range_end:
        end_formatted = range_end.strftime("%d %B %Y")
        for eng, tr in tr_months.items(): end_formatted = end_formatted.replace(eng, tr)
        return f"{name}. ({date_obj.year}). {name} Gazetesi ({date_formatted} - {end_formatted}). Dijital Sahaf Arşivi."
    else:
        return f"{name}. ({date_obj.year}, {date_formatted}). {name} Gazetesi. Dijital Sahaf Arşivi."

def process_archive_single(gid, name, date_obj, img_settings, pdf_settings, progress_callback=None):
    """Tekil indirme ve işleme motoru"""
    date_str = date_obj.strftime("%Y-%m-%d")
    images = []
    page = 1
    tolerance = 0
    
    while page <= 99:
        if tolerance >= 2: break
        if progress_callback: progress_callback(f"{date_str} - Sayfa {page} işleniyor...")
        
        raw_img = get_page_image(gid, date_str, page)
        if raw_img:
            processed_img = apply_image_filters(raw_img, **img_settings)
            images.append(processed_img)
            tolerance = 0
        else: tolerance += 1
        page += 1
        time.sleep(0.05) 

    if not images: return None

    pdf_buffer = BytesIO()
    save_params = {"save_all": True, "append_images": images[1:], "resolution": 100.0, "quality": 85}
    if pdf_settings['compress']:
        save_params["optimize"] = True
        save_params["quality"] = 65 
        
    images[0].save(pdf_buffer, format="PDF", **save_params)
    pdf_buffer.seek(0)
    return pdf_buffer

# --- 6. ARAYÜZ (SIDEBAR) ---

st.sidebar.title("🛠️ Kontrol Paneli")
nav_mode = st.sidebar.radio("Çalışma Modu", ["📖 Katalogdan Seç", "🔗 Link ile İndir", "🆚 Manşet Kıyaslama"])
st.sidebar.markdown("---")

# TARİH AYARLARI
st.sidebar.subheader("📅 Tarih Modu")
date_mode = "Tek Gün"
selected_date_end = None

if nav_mode == "📖 Katalogdan Seç":
    date_mode = st.sidebar.radio("İndirme Tipi", ["Tek Gün", "Tarih Aralığı (Toplu ZIP)"])
    if date_mode == "Tek Gün":
        st.session_state.current_date = st.sidebar.date_input("Tarih", st.session_state.current_date, min_value=date(1800, 1, 1), max_value=date.today())
    else:
        col1, col2 = st.sidebar.columns(2)
        st.session_state.current_date = col1.date_input("Başlangıç", st.session_state.current_date)
        selected_date_end = col2.date_input("Bitiş", st.session_state.current_date + timedelta(days=7))
elif nav_mode == "🆚 Manşet Kıyaslama":
    st.session_state.current_date = st.sidebar.date_input("Kıyaslama Tarihi", st.session_state.current_date)

st.sidebar.markdown("---")
# GÖRÜNTÜ AYARLARI
st.sidebar.subheader("🎨 Görüntü Laboratuvarı")
img_settings = {
    "contrast": st.sidebar.slider("Kontrast", 0.5, 2.0, 1.0, 0.1),
    "brightness": st.sidebar.slider("Parlaklık", 0.5, 2.0, 1.0, 0.1),
    "sharpness": 1.0,
    "grayscale": st.sidebar.checkbox("Siyah-Beyaz Modu (Okuma İçin)", value=False),
    "invert": st.sidebar.checkbox("Negatif (Gece) Modu", value=False)
}

st.sidebar.markdown("---")
compress = st.sidebar.checkbox("PDF Sıkıştırma (Optimize)", value=True)
create_zip = st.sidebar.checkbox("📂 Aralığı ZIP Yap", value=True, disabled=(date_mode=="Tek Gün"))
pdf_settings = {"compress": compress, "ocr": False}

# --- 7. SEKME YAPISI (MAIN) ---
tab_app, tab_lib, tab_guide, tab_notes = st.tabs(["🚀 Uygulama", "🗄️ Kütüphanem", "📖 Kılavuz", "📝 Notlar"])

# --- TAB 1: UYGULAMA ---
with tab_app:
    # ---------------------------
    # A. MOD: KIYASLAMA
    # ---------------------------
    if nav_mode == "🆚 Manşet Kıyaslama":
        st.title("🆚 Manşet Kıyaslama")
        
        # ZAMAN YOLCULUĞU BUTONLARI
        c1, c2, c3 = st.columns([1, 4, 1])
        if c1.button("⬅️ Önceki Gün", use_container_width=True): change_date(-1); st.rerun()
        with c2: st.markdown(f"<h3 style='text-align: center; margin:0'>{st.session_state.current_date.strftime('%d.%m.%Y')}</h3>", unsafe_allow_html=True)
        if c3.button("Sonraki Gün ➡️", use_container_width=True): change_date(1); st.rerun()
        
        col_left, col_right = st.columns(2)
        with col_left:
            p1 = st.selectbox("1. Yayın", [i["name"] for i in GASTE_ARSIVI_DATABASE], index=0)
            gid1 = next(i["id"] for i in GASTE_ARSIVI_DATABASE if i["name"] == p1)
            with st.spinner("Yükleniyor..."):
                img1 = get_page_image(gid1, st.session_state.current_date.strftime("%Y-%m-%d"), 1)
                if img1: 
                    st.image(apply_image_filters(img1, **img_settings), use_container_width=True)
                    if st.button(f"📥 {p1} İndir", key="dl_a"):
                        pdf = process_archive_single(gid1, p1, st.session_state.current_date, img_settings, pdf_settings)
                        if pdf: st.download_button("Kaydet", pdf, f"{p1}.pdf", "application/pdf")
                else: st.warning("Yayın Yok")
        with col_right:
            p2 = st.selectbox("2. Yayın", [i["name"] for i in GASTE_ARSIVI_DATABASE], index=1)
            gid2 = next(i["id"] for i in GASTE_ARSIVI_DATABASE if i["name"] == p2)
            with st.spinner("Yükleniyor..."):
                img2 = get_page_image(gid2, st.session_state.current_date.strftime("%Y-%m-%d"), 1)
                if img2: 
                    st.image(apply_image_filters(img2, **img_settings), use_container_width=True)
                    if st.button(f"📥 {p2} İndir", key="dl_b"):
                        pdf = process_archive_single(gid2, p2, st.session_state.current_date, img_settings, pdf_settings)
                        if pdf: st.download_button("Kaydet", pdf, f"{p2}.pdf", "application/pdf")
                else: st.warning("Yayın Yok")

    # ---------------------------
    # B. MOD: KATALOG & LINK
    # ---------------------------
    else:
        gid = None
        selected_name = ""

        if nav_mode == "📖 Katalogdan Seç":
            st.title("🎓 Dijital Sahaf: Akademik Arşiv")
            selected_name = st.selectbox("Yayın Seçiniz", [i["name"] for i in GASTE_ARSIVI_DATABASE])
            item_data = next(i for i in GASTE_ARSIVI_DATABASE if i["name"] == selected_name)
            gid = item_data["id"]
            
            if date_mode == "Tek Gün":
                c1, c2, c3 = st.columns([1, 4, 1])
                if c1.button("⬅️ Önceki Gün", use_container_width=True): change_date(-1); st.rerun()
                with c2: st.markdown(f"<h3 style='text-align: center; margin:0'>{st.session_state.current_date.strftime('%d %B %Y')}</h3>", unsafe_allow_html=True)
                if c3.button("Sonraki Gün ➡️", use_container_width=True): change_date(1); st.rerun()
        
        else:
            st.title("🔗 Link Çözücü")
            url_input = st.text_input("GasteArsivi Linki Yapıştır")
            if url_input: 
                match = re.search(r"gazete\/([^\/]+)\/(\d{4}-\d{2}-\d{2})", url_input)
                if match:
                    gid = match.group(1)
                    st.session_state.current_date = date(*map(int, match.group(2).split('-')))
                    date_mode = "Tek Gün"
                    found_name = next((i["name"] for i in GASTE_ARSIVI_DATABASE if i["id"] == gid), gid)
                    selected_name = found_name
                    st.success(f"Link Algılandı: {selected_name}")

        if gid:
            st.markdown("---")
            col_preview, col_action = st.columns([1, 1.5])
            
            # ÖNİZLEME ALANI
            with col_preview:
                st.subheader("🔍 Önizleme")
                date_str = st.session_state.current_date.strftime("%Y-%m-%d")
                
                with st.spinner("Önizleme alınıyor..."):
                    raw_preview = get_page_image(gid, date_str, 1)
                    if raw_preview:
                        st.image(apply_image_filters(raw_preview, **img_settings), caption=f"{selected_name} - Sayfa 1", use_container_width=True)
                        if st.button("⭐ Favorilere Ekle", use_container_width=True):
                            if add_favorite(selected_name, st.session_state.current_date): st.success("Kütüphaneye eklendi!")
                            else: st.info("Zaten favorilerde.")
                        preview_ok = True
                    else:
                        st.warning(f"{date_str} tarihinde yayın bulunamadı.")
                        st.image("https://placehold.co/400x600?text=Arsiv+Yok", use_container_width=True)
                        preview_ok = False
                
                # RADAR
                if date_mode == "Tek Gün":
                    with st.expander("📡 Bu Tarihteki Diğer Yayınlar"):
                        if st.button("Taramayı Başlat"):
                            available = check_daily_availability(st.session_state.current_date)
                            if available:
                                st.success(f"{len(available)} yayın bulundu:")
                                for p in available: st.write(f"• {p}")
                            else: st.warning("Başka yayın yok.")

            # İŞLEM ALANI
            with col_action:
                st.subheader("⚙️ İşlemler")
                # APA Citation
                if date_mode == "Tek Gün": citation = generate_apa_citation(selected_name, st.session_state.current_date)
                else: citation = generate_apa_citation(selected_name, st.session_state.current_date, selected_date_end)
                st.text_area("🎓 APA Kaynakça", citation, height=70)
                
                if preview_ok or date_mode != "Tek Gün":
                    if st.button("🚀 İndirmeyi Başlat", type="primary"):
                        if date_mode == "Tek Gün":
                            with st.spinner("İşleniyor..."):
                                pdf = process_archive_single(gid, selected_name, st.session_state.current_date, img_settings, pdf_settings)
                                if pdf:
                                    fname = f"{selected_name}_{st.session_state.current_date}.pdf"
                                    st.download_button("💾 PDF İndir", pdf, fname, "application/pdf")
                                    log_download(selected_name, st.session_state.current_date, "Tekil PDF")
                        else:
                            # TOPLU İNDİRME MANTIĞI
                            delta = (selected_date_end - st.session_state.current_date).days + 1
                            prog = st.progress(0); status = st.empty(); files = []
                            for i in range(delta):
                                curr = st.session_state.current_date + timedelta(days=i)
                                status.text(f"İşleniyor: {curr}"); prog.progress(i/delta)
                                pdf = process_archive_single(gid, selected_name, curr, img_settings, pdf_settings)
                                if pdf: files.append((f"{selected_name}_{curr}.pdf", pdf))
                            
                            prog.progress(1.0); status.success(f"{len(files)} dosya hazır.")
                            if files:
                                log_download(selected_name, st.session_state.current_date, f"Toplu Arşiv ({len(files)})")
                                if create_zip:
                                    z_buf = BytesIO()
                                    with zipfile.ZipFile(z_buf, "a", zipfile.ZIP_DEFLATED, False) as zf:
                                        for n, d in files: zf.writestr(n, d.getvalue())
                                    z_buf.seek(0)
                                    st.download_button("📦 ZIP İndir", z_buf, "Arsiv.zip", "application/zip")
                                else:
                                    for n, d in files: st.download_button(f"📄 {n}", d, n, "application/pdf")

# --- TAB 2: KÜTÜPHANEM ---
with tab_lib:
    st.header("🗄️ Kişisel Arşiv Kütüphanesi")
    col_fav, col_hist = st.columns(2)
    with col_fav:
        st.subheader("⭐ Favoriler")
        try:
            df_fav = pd.read_sql_query("SELECT newspaper, pub_date, note FROM favorites ORDER BY date_added DESC", conn)
            if not df_fav.empty: st.dataframe(df_fav, use_container_width=True)
            else: st.info("Henüz favori eklenmemiş.")
        except: st.error("Veritabanı okunamadı.")
        
    with col_hist:
        st.subheader("📥 İndirme Geçmişi")
        try:
            df_hist = pd.read_sql_query("SELECT date_added, newspaper, pub_date, type FROM downloads ORDER BY date_added DESC LIMIT 50", conn)
            if not df_hist.empty: st.dataframe(df_hist, use_container_width=True)
            else: st.info("İndirme geçmişi boş.")
        except: st.error("Veritabanı okunamadı.")

# --- TAB 3: KILAVUZ ---
with tab_guide:
    st.header("📖 Kullanım Kılavuzu")
    st.markdown("---")
    st.markdown("""
    ### 1. Navigasyon
    * **Katalogdan Seç:** Ana moddur. Listeden gazeteyi seçip ilerleyin.
    * **Zaman Yolculuğu:** Tek gün modunda üstteki `⬅️` ve `➡️` butonları ile günleri hızlıca geçin.
    * **Kıyaslama Modu:** Sol menüden açın. İki gazeteyi yan yana koyup manşetlerini karşılaştırın.

    ### 2. Görüntü Ayarları (Image Lab)
    * ⚫ **Siyah-Beyaz:** Yazıları en net hale getirir (Tavsiye edilen).
    * 🌑 **Negatif:** Gece okumaları için.
    * 🔆 **Kontrast/Parlaklık:** Silik sayfaları düzeltir.
    * *Bu ayarlar inen PDF dosyasına da uygulanır.*

    ### 3. İndirme Seçenekleri
    * **Tek Gün:** O günün gazetesini tek PDF olarak indirir.
    * **Tarih Aralığı (ZIP):** Sol menüden seçilir. Başlangıç ve bitiş tarihlerini girip "Aralığı ZIP Yap" derseniz, tüm arşivi tek pakette indirirsiniz.

    ### 4. Akademik Araçlar
    * **Radar:** "Bu Tarihteki Diğer Yayınlar" panelinden o gün çıkan tüm gazeteleri bulabilirsiniz.
    * **APA Kaynakça:** İndirme alanında hazır verilen atıf metnini kullanabilirsiniz.
    """)

# --- TAB 4: NOTLAR ---
with tab_notes:
    st.header("📝 Sürüm Notları")
    st.info("v23.0 - Final Master Edition")
    st.markdown("""
    * ✅ **Garantili Veritabanı:** Sadece çalışan linkler eklendi.
    * ✅ **Kıyaslama Modu:** İki gazete yan yana analiz.
    * ✅ **ZIP Paketleyici:** Çoklu indirmeler tek dosyada.
    * ✅ **Kütüphane:** Favori ve geçmiş takibi (SQLite).
    * ✅ **Yayın Radarı:** Tarih bazlı çapraz tarama.
    """)
