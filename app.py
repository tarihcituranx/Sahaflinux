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
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. VERİTABANI BAŞLATMA (SQLITE) ---
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

# --- 3. RESMİ GAZETE LİSTESİ (SİTEDEN ÇEKİLDİ) ---
# Senin gönderdiğin kaynak koddan çıkarılan %100 doğru listedir.
GASTE_ARSIVI_DATABASE = [
    {"id": "agac", "name": "Ağaç"},
    {"id": "ahali_filibe", "name": "Ahali (Filibe)"},
    {"id": "akbaba", "name": "Akbaba"},
    {"id": "akis", "name": "Akis"},
    {"id": "aksam", "name": "Akşam"},
    {"id": "anadolu", "name": "Anadolu"},
    {"id": "ant", "name": "Ant"},
    {"id": "aydede", "name": "Aydede"},
    {"id": "balkan_filibe", "name": "Balkan (Filibe)"},
    {"id": "bilim_teknik", "name": "Bilim ve Teknik"},
    {"id": "birgun", "name": "Birgün"},
    {"id": "bugun", "name": "Bugün"},
    {"id": "bugun_2005", "name": "Bugün (2005-2016)"},
    {"id": "buyuk_dogu", "name": "Büyük Doğu"},
    {"id": "carsaf", "name": "Çarşaf"},
    {"id": "commodore", "name": "Commodore"},
    {"id": "cumhuriyet", "name": "Cumhuriyet"},
    {"id": "demokrat_izmir", "name": "Demokrat İzmir"},
    {"id": "diyojen", "name": "Diyojen"},
    {"id": "dunya", "name": "Dünya"},
    {"id": "girgir", "name": "Gırgır"},
    {"id": "gunaydin", "name": "Günaydın"},
    {"id": "gunes", "name": "Güneş"},
    {"id": "haber", "name": "Haber"},
    {"id": "haberturk", "name": "Habertürk"},
    {"id": "hakimiyeti_milliye", "name": "Hakimiyet-i Milliye"},
    {"id": "halkin_sesi", "name": "Halkın Sesi"},
    {"id": "hayat", "name": "Hayat"},
    {"id": "hayat_1956", "name": "Hayat (1956)"},
    {"id": "her_ay", "name": "Her Ay"},
    {"id": "hey", "name": "Hey"},
    {"id": "hurriyet", "name": "Hürriyet"},
    {"id": "ikaz", "name": "İkaz (Afyonkarahisar)"},
    {"id": "ikdam_sabah_postasi", "name": "İkdam (Sabah Postası)"},
    {"id": "iradei_milliye_sivas", "name": "İrade-i Milliye (Sivas)"},
    {"id": "kadro", "name": "Kadro"},
    {"id": "karar", "name": "Karar"},
    {"id": "kurun", "name": "Kurun"},
    {"id": "limon", "name": "Limon"},
    {"id": "milli_gazete", "name": "Milli Gazete"},
    {"id": "milliyet", "name": "Milliyet (Eski)"},
    {"id": "milliyet2", "name": "Milliyet (Yeni)"}, # Sitede iki Milliyet var, ikisini de ekledim
    {"id": "nokta", "name": "Nokta"},
    {"id": "peyam", "name": "Peyam"},
    {"id": "pismis_kelle", "name": "Pişmiş Kelle"},
    {"id": "radikal", "name": "Radikal"},
    {"id": "sabah", "name": "Sabah"},
    {"id": "sebilurresad", "name": "Sebilürreşad"},
    {"id": "serbes_cumhuriyet", "name": "Serbes Cumhuriyet"},
    {"id": "servet", "name": "Servet"},
    {"id": "serveti_funun", "name": "Servet-i Fünun"},
    {"id": "servetifunun_uyanis", "name": "Servetifunun (Uyanış)"},
    {"id": "ses", "name": "Ses"},
    {"id": "son_posta", "name": "Son Posta"},
    {"id": "son_telgraf", "name": "Son Telgraf"},
    {"id": "sozcu", "name": "Sözcü"},
    {"id": "star", "name": "Star"},
    {"id": "takvimi_vekayi", "name": "Takvim-i Vekayi"},
    {"id": "tan", "name": "Tan"},
    {"id": "tanin", "name": "Tanin"},
    {"id": "tanin_yeni", "name": "Tanin (Yeni)"},
    {"id": "taraf", "name": "Taraf"},
    {"id": "tasviri_efkar", "name": "Tasviri Efkar"},
    {"id": "turk_dili", "name": "Türk Dili"},
    {"id": "tvde7gun", "name": "TV'de 7 Gün"},
    {"id": "ulus", "name": "Ulus"},
    {"id": "ulusal_birlik_izmir", "name": "Ulusal Birlik (İzmir)"},
    {"id": "vakit", "name": "Vakit"},
    {"id": "vatan", "name": "Vatan"},
    {"id": "yarim_ay", "name": "Yarım Ay"},
    {"id": "yarın", "name": "Yarın"},
    {"id": "yeniakit", "name": "Yeni Akit"},
    {"id": "yeni_asir", "name": "Yeni Asır"},
    {"id": "yenigun_antakya", "name": "Yenigün (Antakya)"},
    {"id": "yeni_istanbul", "name": "Yeni İstanbul"},
    {"id": "yeni_sabah", "name": "Yeni Sabah"},
    {"id": "yeni_safak", "name": "Yeni Şafak"},
    {"id": "zafer", "name": "Zafer"},
    {"id": "zaman", "name": "Zaman"},
    {"id": "zaman_feza", "name": "Zaman (Feza)"}
]
# Listeyi isme göre sırala
GASTE_ARSIVI_DATABASE.sort(key=lambda x: x["name"])

# --- 4. SESSION STATE ---
if 'current_date' not in st.session_state:
    st.session_state.current_date = date(1930, 1, 1)

def change_date(days):
    st.session_state.current_date += timedelta(days=days)

# --- 5. YARDIMCI FONKSİYONLAR ---

def log_download(newspaper, pub_date, dl_type):
    c = conn.cursor()
    c.execute("INSERT INTO downloads VALUES (?, ?, ?, ?)", 
              (datetime.now(), newspaper, pub_date.strftime("%Y-%m-%d"), dl_type))
    conn.commit()

def add_favorite(newspaper, pub_date, note=""):
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
    # Senin bulduğun Cloudfront Sunucusu
    base_url = "https://dzp35pmd4yqn4.cloudfront.net"
    url = f"{base_url}/sayfalar/{gid}/{date_str}-{page_num}.jpg"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=3)
        if r.status_code == 200:
            return Image.open(BytesIO(r.content))
    except:
        pass
    return None

def check_daily_availability(check_date):
    """RADAR: Seçili tarihte hangi gazeteler var?"""
    available_papers = []
    date_str = check_date.strftime("%Y-%m-%d")
    progress_bar = st.progress(0)
    total = len(GASTE_ARSIVI_DATABASE)
    
    base_url = "https://dzp35pmd4yqn4.cloudfront.net"
    
    for idx, paper in enumerate(GASTE_ARSIVI_DATABASE):
        # Hızlı kontrol için sadece başlık isteği (HEAD) atıyoruz
        url = f"{base_url}/sayfalar/{paper['id']}/{date_str}-1.jpg"
        try:
            r = requests.head(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=0.2)
            if r.status_code == 200:
                available_papers.append(paper['name'])
        except:
            pass
        progress_bar.progress((idx + 1) / total)
        
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
        if tolerance >= 3: break # 3 Sayfa üst üste yoksa dur
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

# --- 6. ARAYÜZ (SOL PANEL) ---
st.sidebar.title("🛠️ Kontrol Paneli")
nav_mode = st.sidebar.radio("Çalışma Modu", ["📖 Katalogdan Seç", "🔗 Link ile İndir", "🆚 Manşet Kıyaslama"])
st.sidebar.markdown("---")

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

# --- 7. ANA EKRAN ---
tab_app, tab_lib, tab_guide = st.tabs(["🚀 Uygulama", "🗄️ Kütüphanem", "📖 Kılavuz"])

with tab_app:
    # --- KIYASLAMA MODU ---
    if nav_mode == "🆚 Manşet Kıyaslama":
        st.title("🆚 Manşet Kıyaslama")
        c1, c2, c3 = st.columns([1, 4, 1])
        if c1.button("⬅️ Geri", use_container_width=True): change_date(-1); st.rerun()
        with c2: st.markdown(f"<h3 style='text-align: center; margin:0'>{st.session_state.current_date.strftime('%d %B %Y')}</h3>", unsafe_allow_html=True)
        if c3.button("İleri ➡️", use_container_width=True): change_date(1); st.rerun()
        
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

    # --- NORMAL MODLAR ---
    else:
        gid = None
        selected_name = ""
        if nav_mode == "📖 Katalogdan Seç":
            st.title("🎓 Dijital Sahaf Pro")
            selected_name = st.selectbox("Yayın Seçiniz", [i["name"] for i in GASTE_ARSIVI_DATABASE])
            item_data = next(i for i in GASTE_ARSIVI_DATABASE if i["name"] == selected_name)
            gid = item_data["id"]
            if date_mode == "Tek Gün":
                c1, c2, c3 = st.columns([1, 4, 1])
                if c1.button("⬅️ Geri", use_container_width=True): change_date(-1); st.rerun()
                with c2: st.markdown(f"<h3 style='text-align: center; margin:0'>{st.session_state.current_date.strftime('%d %B %Y')}</h3>", unsafe_allow_html=True)
                if c3.button("İleri ➡️", use_container_width=True): change_date(1); st.rerun()
        else:
            st.title("🔗 Link Çözücü")
            url_input = st.text_input("GasteArsivi Linki (Yapıştır)")
            if url_input: 
                # Linkten ID ve Tarihi sök
                match = re.search(r"gazete\/([^\/]+)\/(\d{4}-\d{2}-\d{2})", url_input)
                if match:
                    gid = match.group(1)
                    st.session_state.current_date = date(*map(int, match.group(2).split('-')))
                    date_mode = "Tek Gün"
                    # Listeden ismini bulmaya çalış
                    found = next((i["name"] for i in GASTE_ARSIVI_DATABASE if i["id"] == gid), None)
                    selected_name = found if found else gid.title()
                    st.success(f"Link Algılandı: {selected_name}")

        if gid:
            st.markdown("---")
            col_preview, col_action = st.columns([1, 1.5])
            with col_preview:
                st.subheader("🔍 Önizleme")
                date_str = st.session_state.current_date.strftime("%Y-%m-%d")
                with st.spinner("Sunucudan alınıyor..."):
                    raw_preview = get_page_image(gid, date_str, 1)
                    if raw_preview:
                        st.image(apply_image_filters(raw_preview, **img_settings), caption=f"{selected_name} - Sayfa 1", use_container_width=True)
                        if st.button("⭐ Favorilere Ekle", use_container_width=True):
                            if add_favorite(selected_name, st.session_state.current_date): st.success("Eklendi!")
                            else: st.info("Zaten ekli.")
                        preview_ok = True
                    else:
                        st.warning(f"Bu tarihte ({date_str}) yayın bulunamadı.")
                        preview_ok = False
                
                if date_mode == "Tek Gün":
                    with st.expander("📡 Yayın Radarı (Bu Tarihteki Diğerleri)"):
                        if st.button("Taramayı Başlat"):
                            available = check_daily_availability(st.session_state.current_date)
                            if available:
                                st.success(f"{len(available)} yayın bulundu:")
                                for p in available: st.write(f"• {p}")
                            else: st.warning("Başka yayın yok.")

            with col_action:
                st.subheader("⚙️ İşlemler")
                if date_mode == "Tek Gün": citation = generate_apa_citation(selected_name, st.session_state.current_date)
                else: citation = generate_apa_citation(selected_name, st.session_state.current_date, selected_date_end)
                st.text_area("🎓 APA Kaynakça", citation, height=70)
                
                if preview_ok or date_mode != "Tek Gün":
                    if st.button("🚀 İndirmeyi Başlat", type="primary"):
                        if date_mode == "Tek Gün":
                            with st.spinner("PDF Hazırlanıyor..."):
                                pdf = process_archive_single(gid, selected_name, st.session_state.current_date, img_settings, pdf_settings)
                                if pdf:
                                    fname = f"{selected_name}_{st.session_state.current_date}.pdf"
                                    st.download_button("💾 PDF İndir", pdf, fname, "application/pdf")
                                    log_download(selected_name, st.session_state.current_date, "Tekil PDF")
                        else:
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

# --- 8. KÜTÜPHANE VE KILAVUZ ---
with tab_lib:
    st.header("🗄️ Kişisel Arşiv")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("⭐ Favoriler")
        try:
            df_fav = pd.read_sql_query("SELECT newspaper, pub_date FROM favorites ORDER BY date_added DESC", conn)
            st.dataframe(df_fav, use_container_width=True)
        except: st.info("Boş")
    with c2:
        st.subheader("📥 İndirme Geçmişi")
        try:
            df_hist = pd.read_sql_query("SELECT date_added, newspaper, pub_date, type FROM downloads ORDER BY date_added DESC LIMIT 50", conn)
            st.dataframe(df_hist, use_container_width=True)
        except: st.info("Boş")

with tab_guide:
    st.header("📖 Kullanım Kılavuzu")
    st.markdown("""
    ### Bu sürüm resmi sunucu verileriyle güncellenmiştir.
    * **Katalogdan Seç:** Tam listeden seçim yapın.
    * **Zaman Yolculuğu:** Üstteki oklarla (⬅️ ➡️) günleri değiştirin.
    * **Resim Sunucusu:** Sistem doğrudan Amazon Cloudfront sunucusuna bağlanır, çok hızlıdır.
    * **Siyah-Beyaz Modu:** Eski gazeteler için en net okuma modudur.
    """)
