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

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="Dijital Sahaf Pro",
    page_icon="🕰️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- VERİTABANI BAŞLATMA (SQLITE) ---
def init_db():
    conn = sqlite3.connect('sahaf_library.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS downloads 
                 (date_added TIMESTAMP, newspaper TEXT, pub_date TEXT, type TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS favorites 
                 (date_added TIMESTAMP, newspaper TEXT, pub_date TEXT, note TEXT)''')
    conn.commit()
    return conn

conn = init_db()

# --- GENİŞLETİLMİŞ TAM VERİ TABANI ---
GASTE_ARSIVI_DATABASE = [
    # ULUSAL GAZETELER
    {"id": "aksam", "name": "Akşam", "dates": "1918-Günümüz"},
    {"id": "cumhuriyet", "name": "Cumhuriyet", "dates": "1924-Günümüz"},
    {"id": "hurriyet", "name": "Hürriyet", "dates": "1948-Günümüz"},
    {"id": "milliyet", "name": "Milliyet", "dates": "1950-Günümüz"},
    {"id": "sabah", "name": "Sabah", "dates": "1985-Günümüz"},
    {"id": "sozcu", "name": "Sözcü", "dates": "2007-Günümüz"},
    {"id": "tercuman", "name": "Tercüman", "dates": "1955-1990'lar"},
    {"id": "gunaydin", "name": "Günaydın", "dates": "1968-1990'lar"},
    {"id": "yeni-safak", "name": "Yeni Şafak", "dates": "1994-Günümüz"},
    {"id": "zaman", "name": "Zaman", "dates": "1986-2016"},
    {"id": "haberturk", "name": "Habertürk", "dates": "2009-2018"},
    {"id": "star", "name": "Star", "dates": "1999-Günümüz"},
    {"id": "posta", "name": "Posta", "dates": "1995-Günümüz"},
    {"id": "radikal", "name": "Radikal", "dates": "1996-2016"},
    {"id": "taraf", "name": "Taraf", "dates": "2007-2016"},

    # TARİHİ & MİLLİ MÜCADELE
    {"id": "hakimiyeti_milliye", "name": "Hakimiyet-i Milliye", "dates": "1920-1934"},
    {"id": "iradei_milliye", "name": "İrade-i Milliye", "dates": "1919-1922"},
    {"id": "ulus", "name": "Ulus", "dates": "1934-1971"},
    {"id": "tan", "name": "Tan", "dates": "1935-1945"},
    {"id": "tanin", "name": "Tanin", "dates": "1908-1947"},
    {"id": "vakit", "name": "Vakit", "dates": "1917-1950"},
    {"id": "vatan", "name": "Vatan", "dates": "1923-1975"},
    {"id": "ikdam", "name": "İkdam", "dates": "1894-1928"},
    {"id": "ileri", "name": "İleri", "dates": "1918-1924"},
    {"id": "tasviri-efkar", "name": "Tasviri Efkar", "dates": "1862-1871"},
    {"id": "tercuman-i-ahval", "name": "Tercüman-ı Ahval", "dates": "1860-1866"},
    {"id": "ceridei_havadis", "name": "Ceride-i Havadis", "dates": "1840-1864"},
    {"id": "takvimi_vekayi", "name": "Takvim-i Vekayi", "dates": "1831-1922"},
    {"id": "serbest_cumhuriyet", "name": "Serbest Cumhuriyet", "dates": "1930"},
    {"id": "son_posta", "name": "Son Posta", "dates": "1930-1960"},
    {"id": "son_telgraf", "name": "Son Telgraf", "dates": "1924-1937"},
    {"id": "yarin", "name": "Yarın", "dates": "1929-1931"},
    {"id": "kurun", "name": "Kurun", "dates": "1930'lar"},

    # DERGİLER & MECMUALAR
    {"id": "serveti_funun", "name": "Servet-i Fünun", "dates": "1891-1944"},
    {"id": "resimli_ay", "name": "Resimli Ay", "dates": "1924-1938"},
    {"id": "yedi_gun", "name": "Yedi Gün", "dates": "1933-1950"},
    {"id": "hayat", "name": "Hayat Mecmuası", "dates": "1950-1980"},
    {"id": "varlik", "name": "Varlık", "dates": "1933-Günümüz"},
    {"id": "buyuk_dogu", "name": "Büyük Doğu", "dates": "1943-1978"},
    {"id": "sebilurresad", "name": "Sebilürreşad", "dates": "1908-1966"},
    {"id": "kadro", "name": "Kadro", "dates": "1932-1934"},
    {"id": "ulkum", "name": "Ülkü", "dates": "1933-1950"},
    {"id": "turk_yurdu", "name": "Türk Yurdu", "dates": "1911-Günümüz"},
    {"id": "muhit", "name": "Muhit", "dates": "1928-1933"},

    # MİZAH
    {"id": "akbaba", "name": "Akbaba", "dates": "1922-1977"},
    {"id": "girgir", "name": "Gırgır", "dates": "1972-1989"},
    {"id": "markopasa", "name": "Markopaşa", "dates": "1946-1947"},
    {"id": "karagoz", "name": "Karagöz", "dates": "1908-1955"},
    {"id": "kalem", "name": "Kalem", "dates": "1908-1911"},
    {"id": "cem", "name": "Cem", "dates": "1910-1912"},
    {"id": "diyojen", "name": "Diyojen", "dates": "1870-1873"},
    {"id": "aydede", "name": "Aydede", "dates": "1922"},

    # YEREL
    {"id": "yeni-asir", "name": "Yeni Asır (İzmir)", "dates": "1895-Günümüz"},
    {"id": "anadolu", "name": "Anadolu (İzmir)", "dates": "1912-2010"},
    {"id": "yeni_adana", "name": "Yeni Adana", "dates": "1918-Günümüz"},
    {"id": "babalik", "name": "Babalık (Konya)", "dates": "1910-1952"},
    {"id": "aciksoz", "name": "Açıksöz (Kastamonu)", "dates": "1919-1931"},
    {"id": "ahali", "name": "Ahali (Edirne/Samsun)", "dates": "1930'lar"},
    {"id": "baskent", "name": "Başkent", "dates": "1968-1970'ler"},
    {"id": "bizim_anadolu", "name": "Bizim Anadolu", "dates": "1960'lar"}
]
GASTE_ARSIVI_DATABASE.sort(key=lambda x: x["name"])

# --- SESSION STATE ---
if 'current_date' not in st.session_state:
    st.session_state.current_date = date(1930, 1, 1)

def change_date(days):
    st.session_state.current_date += timedelta(days=days)

# --- YARDIMCI FONKSİYONLAR ---

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
    url = f"https://dzp35pmd4yqn4.cloudfront.net/sayfalar/{gid}/{date_str}-{page_num}.jpg"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=3)
        if r.status_code == 200: return Image.open(BytesIO(r.content))
    except: pass
    return None

def check_daily_availability(check_date):
    """Verilen tarihte hangi gazetelerin çıktığını hızlıca tarar (Radar)"""
    available_papers = []
    date_str = check_date.strftime("%Y-%m-%d")
    progress_bar = st.progress(0)
    status_text = st.empty()
    total = len(GASTE_ARSIVI_DATABASE)
    
    for idx, paper in enumerate(GASTE_ARSIVI_DATABASE):
        status_text.text(f"Taranıyor: {paper['name']}...")
        url = f"https://dzp35pmd4yqn4.cloudfront.net/sayfalar/{paper['id']}/{date_str}-1.jpg"
        try:
            r = requests.head(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=0.5)
            if r.status_code == 200:
                available_papers.append(paper['name'])
        except:
            pass
        progress_bar.progress((idx + 1) / total)
        
    status_text.empty()
    progress_bar.empty()
    return available_papers

def generate_apa_citation(name, date_obj, range_end=None):
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

# --- ARAYÜZ BAŞLANGICI ---

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
    "grayscale": st.sidebar.checkbox("Siyah-Beyaz Modu", value=False),
    "invert": st.sidebar.checkbox("Negatif (Gece) Modu", value=False)
}

st.sidebar.markdown("---")
compress = st.sidebar.checkbox("PDF Sıkıştırma", value=True)
create_zip = st.sidebar.checkbox("📂 Aralığı ZIP Yap", value=True, disabled=(date_mode=="Tek Gün"))
pdf_settings = {"compress": compress, "ocr": False}

# --- SEKME YAPISI ---
tab_app, tab_lib, tab_guide, tab_notes = st.tabs(["🚀 Uygulama", "🗄️ Kütüphanem", "📖 Kılavuz", "📝 Notlar"])

# --- TAB 1: UYGULAMA ---
with tab_app:
    # ---------------------------
    # MOD: KIYASLAMA (COMPARISON)
    # ---------------------------
    if nav_mode == "🆚 Manşet Kıyaslama":
        st.title("🆚 Manşet Kıyaslama Masası")
        
        # NAVİGASYON BUTONLARI
        c1, c2, c3 = st.columns([1, 4, 1])
        if c1.button("⬅️ Önceki Gün", use_container_width=True): change_date(-1); st.rerun()
        with c2: st.markdown(f"<h3 style='text-align: center; margin:0'>{st.session_state.current_date.strftime('%d.%m.%Y')}</h3>", unsafe_allow_html=True)
        if c3.button("Sonraki Gün ➡️", use_container_width=True): change_date(1); st.rerun()
        
        col_left, col_right = st.columns(2)
        with col_left:
            st.subheader("Yayın A")
            p1 = st.selectbox("1. Gazeteyi Seç", [i["name"] for i in GASTE_ARSIVI_DATABASE], index=0)
            gid1 = next(i["id"] for i in GASTE_ARSIVI_DATABASE if i["name"] == p1)
            with st.spinner("Yükleniyor..."):
                img1 = get_page_image(gid1, st.session_state.current_date.strftime("%Y-%m-%d"), 1)
                if img1: 
                    st.image(apply_image_filters(img1, **img_settings), use_container_width=True)
                    if st.button(f"📥 {p1} İndir", key="dl_a"):
                        pdf = process_archive_single(gid1, p1, st.session_state.current_date, img_settings, pdf_settings)
                        if pdf: st.download_button("Kaydet", pdf, f"{p1}.pdf", "application/pdf")
                else: 
                    st.warning("Bu tarihte yayın yok")
                    st.image("https://placehold.co/400x600?text=Yok", use_container_width=True)
            
        with col_right:
            st.subheader("Yayın B")
            p2 = st.selectbox("2. Gazeteyi Seç", [i["name"] for i in GASTE_ARSIVI_DATABASE], index=1)
            gid2 = next(i["id"] for i in GASTE_ARSIVI_DATABASE if i["name"] == p2)
            with st.spinner("Yükleniyor..."):
                img2 = get_page_image(gid2, st.session_state.current_date.strftime("%Y-%m-%d"), 1)
                if img2: 
                    st.image(apply_image_filters(img2, **img_settings), use_container_width=True)
                    if st.button(f"📥 {p2} İndir", key="dl_b"):
                        pdf = process_archive_single(gid2, p2, st.session_state.current_date, img_settings, pdf_settings)
                        if pdf: st.download_button("Kaydet", pdf, f"{p2}.pdf", "application/pdf")
                else: 
                    st.warning("Bu tarihte yayın yok")
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
            
            # TEK GÜN NAVİGASYON
            if date_mode == "Tek Gün":
                c1, c2, c3 = st.columns([1, 4, 1])
                if c1.button("⬅️ Önceki Gün", use_container_width=True): change_date(-1); st.rerun()
                with c2: st.markdown(f"<h3 style='text-align: center; margin:0'>{st.session_state.current_date.strftime('%d %B %Y')}</h3>", unsafe_allow_html=True)
                if c3.button("Sonraki Gün ➡️", use_container_width=True): change_date(1); st.rerun()
        
        else:
            st.title("🔗 Link Çözücü")
            url_input = st.text_input("GasteArsivi Linki")
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
            
            # TARİH ARALIĞI HESABI
            if date_mode == "Tek Gün":
                total_days = 1
                start_date = st.session_state.current_date
            else:
                total_days = (selected_date_end - st.session_state.current_date).days + 1
                start_date = st.session_state.current_date
            
            col_preview, col_action = st.columns([1, 1.5])
            
            with col_preview:
                st.subheader("🔍 Önizleme")
                date_str = start_date.strftime("%Y-%m-%d")
                
                with st.spinner("Önizleme alınıyor..."):
                    raw_preview = get_page_image(gid, date_str, 1)
                    if raw_preview:
                        st.image(apply_image_filters(raw_preview, **img_settings), caption=f"{selected_name} - Sayfa 1", use_container_width=True)
                        if st.button("⭐ Favorilere Ekle", use_container_width=True):
                            if add_favorite(selected_name, start_date): st.success("Eklendi!")
                            else: st.info("Zaten ekli.")
                        preview_ok = True
                    else:
                        st.warning(f"{date_str} tarihinde yayın bulunamadı.")
                        st.image("https://placehold.co/400x600?text=Arsiv+Yok", use_container_width=True)
                        preview_ok = False
                
                # YAYIN RADARI
                if date_mode == "Tek Gün":
                    with st.expander("📡 Bu Tarihteki Diğer Yayınlar (Radar)"):
                        if st.button("Taramayı Başlat"):
                            available = check_daily_availability(start_date)
                            if available:
                                st.success(f"{len(available)} yayın bulundu:")
                                for p in available: st.write(f"• {p}")
                            else: st.warning("Başka yayın yok.")

            with col_action:
                st.subheader("⚙️ İşlem Merkezi")
                st.info(f"**Yayın:** {selected_name} | **Kapsam:** {total_days} Gün")
                
                citation = generate_apa_citation(selected_name, start_date, selected_date_end if total_days > 1 else None)
                st.text_area("🎓 APA Kaynakça", citation, height=70)
                
                if preview_ok or total_days > 1:
                    btn_text = f"🚀 {total_days} Günlük Arşivi İndir" if total_days > 1 else "🚀 PDF İndir"
                    
                    if st.button(btn_text, type="primary"):
                        if date_mode == "Tek Gün":
                            with st.spinner("İşleniyor..."):
                                pdf = process_archive_single(gid, selected_name, start_date, img_settings, pdf_settings)
                                if pdf:
                                    fname = f"{selected_name}_{start_date}.pdf"
                                    st.download_button("💾 PDF İndir", pdf, fname, "application/pdf")
                                    log_download(selected_name, start_date, "Tekil PDF")
                        else:
                            prog = st.progress(0); status = st.empty(); files = []
                            for i in range(total_days):
                                curr = start_date + timedelta(days=i)
                                status.text(f"İşleniyor: {curr}")
                                prog.progress(i/total_days)
                                pdf = process_archive_single(gid, selected_name, curr, img_settings, pdf_settings)
                                if pdf: files.append((f"{selected_name}_{curr}.pdf", pdf))
                            
                            prog.progress(1.0); status.success(f"{len(files)} dosya hazır.")
                            if files:
                                log_download(selected_name, start_date, f"Toplu Arşiv ({len(files)})")
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
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("⭐ Favoriler")
        df = pd.read_sql_query("SELECT * FROM favorites ORDER BY date_added DESC", conn)
        if not df.empty: st.dataframe(df, use_container_width=True)
        else: st.info("Boş")
    with c2:
        st.subheader("📥 İndirme Geçmişi")
        df = pd.read_sql_query("SELECT * FROM downloads ORDER BY date_added DESC LIMIT 50", conn)
        if not df.empty: st.dataframe(df, use_container_width=True)
        else: st.info("Boş")

# --- TAB 3: KILAVUZ ---
with tab_guide:
    st.header("📖 Kullanım Kılavuzu")
    st.markdown("---")
    st.markdown("""
    ### 1. Navigasyon
    * **Katalogdan Seç:** Standart moddur. Listeden gazete ve tarih seçerek ilerlersiniz.
    * **Zaman Yolculuğu:** Tek gün modundayken üstteki `⬅️` ve `➡️` butonlarıyla gün gün gezinebilirsiniz.
    * **Kıyaslama Modu:** Sol menüden seçilir. İki gazeteyi yan yana açıp aynı tarihteki manşetlerini karşılaştırır.

    ### 2. Görüntü Ayarları (Önemli)
    Eski gazeteleri okurken sol menüdeki ayarları kullanın:
    * ⚫ **Siyah-Beyaz:** En net okuma deneyimi (Fotokopi etkisi).
    * 🌑 **Negatif:** Gece okumaları için.
    * 🔆 **Kontrast/Parlaklık:** Silik veya çok koyu sayfalar için.
    * *Not: Bu ayarlar indirdiğiniz PDF'e de işlenir.*

    ### 3. Toplu İndirme (ZIP)
    Bir tarih aralığı (Örn: 1-30 Ocak) seçip **"Aralığı ZIP Yap"** derseniz, sistem tüm günleri tarar, bulduklarını PDF yapar ve tek bir ZIP paketi olarak verir.

    ### 4. Akademik Araçlar
    * **Radar:** Önizleme altındaki "Yayın Radarı"nı açarsanız, o gün basılan diğer tüm gazeteleri bulur.
    * **Kaynakça:** Sistem sizin için otomatik APA formatında kaynakça oluşturur.
    """)

# --- TAB 4: NOTLAR ---
with tab_notes:
    st.header("📝 Sürüm Notları")
    st.info("v22.0 - Final Edition")
    st.markdown("""
    * ✅ **Genişletilmiş Veritabanı:** Yerel gazeteler, dergiler ve mizah mecmuaları eklendi.
    * ✅ **Yayın Radarı:** Tarih bazlı çapraz tarama.
    * ✅ **Kıyaslama Modu:** İkili gazete analizi.
    * ✅ **Kütüphane:** Yerel veritabanı (SQLite) ile favori ve geçmiş takibi.
    """)
