import streamlit as st
import requests
from PIL import Image, ImageEnhance, ImageOps
from io import BytesIO
from datetime import date, timedelta, datetime
import re
import time
import random
import zipfile
import sqlite3
import pandas as pd
from pathlib import Path

# --- 1. SAYFA AYARLARI ---
st.set_page_config(
    page_title="Dijital Sahaf Pro v2",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. SABİTLER VE BAĞLANTI AYARLARI ---
BASE_URL  = "https://www.gastearsivi.com"
CDN_URL   = "https://cdn-assets.gastearsivi.com"
GQL_URL   = f"{BASE_URL}/api/graphql"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15"
]

# --- GRAPHQL SORGULARI ---
QUERY_SAYFA = """
query GununMansetiGazetePage($gazete: String!, $tarih: Date!, $sayfa: Int!) {
  sayfa(gazete: $gazete, tarih: $tarih, sayfa: $sayfa) {
    caption
    dosya
    censored
    limit
    maxLimit
    __typename
  }
  sayi(gazete: $gazete, tarih: $tarih) {
    oncekiGun
    sonrakiGun
    toplamSayfa
    __typename
  }
  gazete(gazete: $gazete) {
    gazete
    gorunen_ad
    dil
    __typename
  }
}
"""

# --- 3. VERİTABANI BAŞLATMA ---
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

# %100 Doğrulanmış Veritabanı Listesi
GASTE_ARSIVI_DATABASE = [
    {"id": "agac", "name": "Ağaç"}, {"id": "ahali_filibe", "name": "Ahali (Filibe)"},
    {"id": "akbaba", "name": "Akbaba"}, {"id": "akis", "name": "Akis"},
    {"id": "aksam", "name": "Akşam"}, {"id": "anadolu", "name": "Anadolu"},
    {"id": "ant", "name": "Ant"}, {"id": "aydede", "name": "Aydede"},
    {"id": "balkan_filibe", "name": "Balkan (Filibe)"}, {"id": "bilim_teknik", "name": "Bilim ve Teknik"},
    {"id": "birgun", "name": "Birgün"}, {"id": "bugun", "name": "Bugün"},
    {"id": "bugun_2005", "name": "Bugün (2005-2016)"}, {"id": "buyuk_dogu", "name": "Büyük Doğu"},
    {"id": "carsaf", "name": "Çarşaf"}, {"id": "commodore", "name": "Commodore"},
    {"id": "cumhuriyet", "name": "Cumhuriyet"}, {"id": "demokrat_izmir", "name": "Demokrat İzmir"},
    {"id": "diyojen", "name": "Diyojen"}, {"id": "dunya", "name": "Dünya"},
    {"id": "girgir", "name": "Gırgır"}, {"id": "gunaydin", "name": "Günaydın"},
    {"id": "gunes", "name": "Güneş"}, {"id": "haber", "name": "Haber"},
    {"id": "haberturk", "name": "Habertürk"}, {"id": "hakimiyeti_milliye", "name": "Hakimiyet-i Milliye"},
    {"id": "halkin_sesi", "name": "Halkın Sesi"}, {"id": "hayat", "name": "Hayat"},
    {"id": "hayat_1956", "name": "Hayat (1956)"}, {"id": "her_ay", "name": "Her Ay"},
    {"id": "hey", "name": "Hey"}, {"id": "hurriyet", "name": "Hürriyet"},
    {"id": "ikaz", "name": "İkaz (Afyonkarahisar)"}, {"id": "ikdam_sabah_postasi", "name": "İkdam (Sabah Postası)"},
    {"id": "iradei_milliye_sivas", "name": "İrade-i Milliye (Sivas)"}, {"id": "kadro", "name": "Kadro"},
    {"id": "karar", "name": "Karar"}, {"id": "kurun", "name": "Kurun"},
    {"id": "limon", "name": "Limon"}, {"id": "milli_gazete", "name": "Milli Gazete"},
    {"id": "milliyet", "name": "Milliyet (Eski)"}, {"id": "milliyet2", "name": "Milliyet (Yeni)"},
    {"id": "nokta", "name": "Nokta"}, {"id": "peyam", "name": "Peyam"},
    {"id": "pismis_kelle", "name": "Pişmiş Kelle"}, {"id": "radikal", "name": "Radikal"},
    {"id": "sabah", "name": "Sabah"}, {"id": "sebilurresad", "name": "Sebilürreşad"},
    {"id": "serbes_cumhuriyet", "name": "Serbes Cumhuriyet"}, {"id": "servet", "name": "Servet"},
    {"id": "serveti_funun", "name": "Servet-i Fünun"}, {"id": "servetifunun_uyanis", "name": "Servetifunun (Uyanış)"},
    {"id": "ses", "name": "Ses"}, {"id": "son_posta", "name": "Son Posta"},
    {"id": "son_telgraf", "name": "Son Telgraf"}, {"id": "sozcu", "name": "Sözcü"},
    {"id": "star", "name": "Star"}, {"id": "takvimi_vekayi", "name": "Takvim-i Vekayi"},
    {"id": "tan", "name": "Tan"}, {"id": "tanin", "name": "Tanin"},
    {"id": "tanin_yeni", "name": "Tanin (Yeni)"}, {"id": "taraf", "name": "Taraf"},
    {"id": "tasviri_efkar", "name": "Tasviri Efkar"}, {"id": "turk_dili", "name": "Türk Dili"},
    {"id": "tvde7gun", "name": "TV'de 7 Gün"}, {"id": "ulus", "name": "Ulus"},
    {"id": "ulusal_birlik_izmir", "name": "Ulusal Birlik (İzmir)"}, {"id": "vakit", "name": "Vakit"},
    {"id": "vatan", "name": "Vatan"}, {"id": "yarim_ay", "name": "Yarım Ay"},
    {"id": "yarın", "name": "Yarın"}, {"id": "yeniakit", "name": "Yeni Akit"},
    {"id": "yeni_asir", "name": "Yeni Asır"}, {"id": "yenigun_antakya", "name": "Yenigün (Antakya)"},
    {"id": "yeni_istanbul", "name": "Yeni İstanbul"}, {"id": "yeni_sabah", "name": "Yeni Sabah"},
    {"id": "yeni_safak", "name": "Yeni Şafak"}, {"id": "zafer", "name": "Zafer"},
    {"id": "zaman", "name": "Zaman"}, {"id": "zaman_feza", "name": "Zaman (Feza)"}
]
GASTE_ARSIVI_DATABASE.sort(key=lambda x: x["name"])

# --- 4. ANTI-BAN SESSION / OTURUM YÖNETİMİ ---
if 'current_date' not in st.session_state:
    st.session_state.current_date = date(1930, 1, 1)
if 'proxy_setting' not in st.session_state:
    st.session_state.proxy_setting = ""

def change_date(days):
    st.session_state.current_date += timedelta(days=days)

def init_safe_session():
    """Çerezleri sıfırlar ve rastgele bir User-Agent ile yeni oturum oluşturur."""
    st.session_state.bot_session = requests.Session()
    headers = {
        "content-type": "application/json",
        "Referer": f"{BASE_URL}/",
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "*/*",
    }
    st.session_state.bot_session.headers.update(headers)
    if st.session_state.proxy_setting:
        proxies = {"http": st.session_state.proxy_setting, "https": st.session_state.proxy_setting}
        st.session_state.bot_session.proxies.update(proxies)

if 'bot_session' not in st.session_state:
    init_safe_session()

# --- 5. GRAPHQL API MOTORU ---
def call_graphql_api(gazete_id, tarih_str, sayfa_no=1):
    """Sitenin öz API katmanını güvenli şekilde sorgular."""
    payload = {
        "query": QUERY_SAYFA,
        "variables": {"gazete": gazete_id, "tarih": tarih_str, "sayfa": sayfa_no}
    }
    try:
        r = st.session_state.bot_session.post(GQL_URL, json=payload, timeout=20)
        r.raise_for_status()
        res_json = r.json()
        if "errors" in res_json:
            return None
        return res_json.get("data", {})
    except:
        # Bağlantı koptuysa veya IP engellendiyse oturumu sessizce tazelemeyi dene
        init_safe_session()
        try:
            r = st.session_state.bot_session.post(GQL_URL, json=payload, timeout=15)
            return r.json().get("data", {})
        except:
            return None

def fetch_page_image_via_api(dosya_yolu):
    """API'den dönen gerçek şifreli/özel CDN yolundan resmi çeker."""
    url = f"{CDN_URL}/{dosya_yolu}"
    try:
        r = st.session_state.bot_session.get(url, timeout=30)
        if r.status_code == 200 and r.headers.get("content-type", "").startswith("image"):
            return Image.open(BytesIO(r.content))
    except:
        pass
    return None

# --- 6. YARDIMCI GÖRSEL & DB FONKSİYONLARI ---
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
    return image

def generate_apa_citation(name, date_obj, range_end=None):
    tr_months = {"January": "Ocak", "February": "Şubat", "March": "Mart", "April": "Nisan", "May": "Mayıs", "June": "Haziran", "July": "Temmuz", "August": "Ağustos", "September": "Eylül", "October": "Ekim", "November": "Kasım", "December": "Aralık"}
    date_formatted = date_obj.strftime("%d %B %Y")
    for eng, tr in tr_months.items(): date_formatted = date_formatted.replace(eng, tr)
    if range_end:
        end_formatted = range_end.strftime("%d %B %Y")
        for eng, tr in tr_months.items(): end_formatted = end_formatted.replace(eng, tr)
        return f"{name}. ({date_obj.year}). {name} Gazetesi ({date_formatted} - {end_formatted}). Dijital Sahaf Arşivi."
    return f"{name}. ({date_obj.year}, {date_formatted}). {name} Gazetesi. Dijital Sahaf Arşivi."

# --- 7. GELİŞMİŞ AKILLI İNDİRME MOTORU (ANTI-BAN) ---
def process_archive_secure(gid, date_obj, img_settings, pdf_compress, progress_bar, status_text):
    date_str = date_obj.strftime("%Y-%m-%d")
    
    # 1. Sayfayı sorgulayıp toplam sayfa sayısını öğrenelim
    data = call_graphql_api(gid, date_str, sayfa_no=1)
    if not data or not data.get("sayfa"):
        return None, "Yayın bulunamadı."
        
    toplam_sayfa = data["sayi"].get("toplamSayfa", 1) or 1
    images = []
    
    for sayfa_no in range(1, toplam_sayfa + 1):
        status_text.text(f"🛡️ Güvenli İndirme: {date_str} | Sayfa {sayfa_no}/{toplam_sayfa}")
        progress_bar.progress(sayfa_no / toplam_sayfa)
        
        # Anti-Ban tetikleyicisi: Her 8 sayfada bir oturumu çerez bazlı tamamen yenile
        if sayfa_no > 1 and sayfa_no % 8 == 0:
            status_text.text("🔄 Anti-Ban Modülü: Çerezler ve kimlik sıfırlanıyor...")
            init_safe_session()
            time.sleep(random.uniform(1.0, 2.0))
            
        # Sayfa datasını çek
        page_data = call_graphql_api(gid, date_str, sayfa_no=sayfa_no)
        if page_data and page_data.get("sayfa"):
            dosya_yolu = page_data["sayfa"]["dosya"]
            
            # API günlük limit kontrolü
            kalan_limit = page_data["sayfa"].get("limit", 10)
            if kalan_limit <= 2:
                init_safe_session() # Limit kritikse kimlik değiştir
                
            raw_img = fetch_page_image_via_api(dosya_yolu)
            if raw_img:
                processed_img = apply_image_filters(raw_img, **img_settings)
                images.append(processed_img)
                
        # Sunucuyu şüphelendirmeyen insani bekleme süresi (Jitter)
        if sayfa_no < toplam_sayfa:
            time.sleep(random.uniform(1.2, 2.8))

    if not images:
        return None, "Sayfa imajları indirilemedi."

    # PDF Oluşturma
    pdf_buffer = BytesIO()
    save_params = {"save_all": True, "append_images": images[1:], "resolution": 100.0, "quality": 85}
    if pdf_compress:
        save_params["optimize"] = True
        save_params["quality"] = 65 
        
    images[0].save(pdf_buffer, format="PDF", **save_params)
    pdf_buffer.seek(0)
    return pdf_buffer, "Başarılı"

# --- 8. KONTROL PANELİ (SIDEBAR) ---
st.sidebar.title("🛡️ Dijital Sahaf Kontrol")
nav_mode = st.sidebar.radio("Çalışma Modu", ["📖 Katalogdan Seç", "🔗 Link ile İndir", "🆚 Manşet Kıyaslama"])
st.sidebar.markdown("---")

# Proxy Ayarı (Gelişmiş Amatörler için gizli silah)
with st.sidebar.expander("🌐 Gelişmiş Proxy Ayarı"):
    proxy_in = st.text_input("Proxy Adresi", placeholder="http://ip:port", value=st.session_state.proxy_setting)
    if proxy_in != st.session_state.proxy_setting:
        st.session_state.proxy_setting = proxy_in
        init_safe_session()
        st.success("Proxy Güncellendi!")

st.sidebar.subheader("📅 Tarih Parametreleri")
date_mode = "Tek Gün"
selected_date_end = None

if nav_mode == "📖 Katalogdan Seç":
    date_mode = st.sidebar.radio("Zaman Yönetimi", ["Tek Gün", "Tarih Aralığı (Toplu ZIP)"])
    if date_mode == "Tek Gün":
        st.session_state.current_date = st.sidebar.date_input("Yayın Tarihi", st.session_state.current_date, max_value=date.today())
    else:
        col1, col2 = st.sidebar.columns(2)
        st.session_state.current_date = col1.date_input("Başlangıç", st.session_state.current_date)
        selected_date_end = col2.date_input("Bitiş", st.session_state.current_date + timedelta(days=5))
elif nav_mode == "🆚 Manşet Kıyaslama":
    st.session_state.current_date = st.sidebar.date_input("Ortak Tarih", st.session_state.current_date)

st.sidebar.markdown("---")
st.sidebar.subheader("🎨 Görüntü Laboratuvarı")
img_settings = {
    "contrast": st.sidebar.slider("Kontrast", 0.5, 2.5, 1.2, 0.1),
    "brightness": st.sidebar.slider("Parlaklık", 0.5, 2.0, 1.0, 0.1),
    "sharpness": 1.0,
    "grayscale": st.sidebar.checkbox("Siyah-Beyaz (Net Okuma)", value=True),
    "invert": st.sidebar.checkbox("Negatif (Gece) Modu", value=False)
}
st.sidebar.markdown("---")
compress = st.sidebar.checkbox("PDF Boyutunu Sıkıştır", value=True)

# --- 9. ANA EKRAN SEKMELERİ ---
tab_app, tab_lib, tab_guide = st.tabs(["🚀 Akıllı Uygulama", "🗄️ Arşiv Odası", "📖 Sistem Kılavuzu"])

with tab_app:
    # LINK ÇÖZÜCÜ (Amatör Dostu) Modu
    if nav_mode == "🔗 Link ile İndir":
        st.title("🔗 Akıllı Otomatik Link Çözücü")
        st.info("💡 Siteden kopyaladığın herhangi bir gazete linkini aşağıya yapıştır, sistem otomatik olarak hangi gazete ve hangi gün olduğunu algılayıp güvenle indirecektir.")
        
        url_input = st.text_input("GasteArşivi Sayfa Linkini Buraya Yapıştırın:", placeholder="https://www.gastearsivi.com/gazete/cumhuriyet/1930-05-20")
        
        gid = None
        selected_name = ""
        
        if url_input:
            match_id = re.search(r"(?:gazete|gunun-manseti)\/([^\/\?]+)", url_input)
            match_date = re.search(r"(\d{4}-\d{2}-\d{2})", url_input)
            
            if match_id and match_date:
                gid = match_id.group(1)
                tarih_str = match_date.group(1)
                st.session_state.current_date = datetime.strptime(tarih_str, "%Y-%m-%d").date()
                date_mode = "Tek Gün"
                
                found = next((i["name"] for i in GASTE_ARSIVI_DATABASE if i["id"] == gid), None)
                selected_name = found if found else gid.title()
                st.success(f"✅ Yayın Başarıyla Algılandı: **{selected_name}** | Tarih: **{tarih_str}**")
            else:
                st.error("❌ Link geçersiz veya analiz edilemedi. Lütfen link yapısını kontrol edin.")

        if gid:
            st.markdown("---")
            col_preview, col_action = st.columns([1, 1.2])
            with col_preview:
                st.subheader("🔍 Güvenli Önizleme")
                with st.spinner("Önizleme oluşturuluyor..."):
                    p_data = call_graphql_api(gid, st.session_state.current_date.strftime("%Y-%m-%d"), 1)
                    if p_data and p_data.get("sayfa"):
                        raw_preview = fetch_page_image_via_api(p_data["sayfa"]["dosya"])
                        if raw_preview:
                            st.image(apply_image_filters(raw_preview, **img_settings), caption=f"{selected_name} - 1. Sayfa", use_container_width=True)
                            if st.button("⭐ Favorilerime Ekle", use_container_width=True):
                                if add_favorite(selected_name, st.session_state.current_date): st.success("Kütüphaneye eklendi!")
                        preview_ok = True
                    else:
                        st.warning("Bu tarihe ait imaj verisi API'den dönmedi.")
                        preview_ok = False
            
            with col_action:
                st.subheader("⚙️ İndirme Operasyonu")
                citation = generate_apa_citation(selected_name, st.session_state.current_date)
                st.text_area("🎓 Otomatik APA 7 Kaynakçası", citation, height=75)
                
                if preview_ok:
                    if st.button("🚀 Güvenli Protokol ile İndirmeyi Başlat", type="primary", use_container_width=True):
                        p_bar = st.progress(0)
                        s_text = st.empty()
                        pdf, msg = process_archive_secure(gid, st.session_state.current_date, img_settings, compress, p_bar, s_text)
                        if pdf:
                            s_text.success("✅ PDF Başarıyla Paketlenip Filtrelendi!")
                            st.download_button("💾 PDF Dosyasını Bilgisayarına Kaydet", pdf, f"{selected_name}_{st.session_state.current_date}.pdf", "application/pdf", use_container_width=True)
                            log_download(selected_name, st.session_state.current_date, "Link Çözücü PDF")
                        else:
                            s_text.error(f"Hata oluştu: {msg}")

    # KATALOGDAN SEÇİM MODU
    elif nav_mode == "📖 Katalogdan Seç":
        st.title("🎓 Dijital Sahaf Pro Arşivi")
        selected_name = st.selectbox("Aranacak Yayını Seçiniz:", [i["name"] for i in GASTE_ARSIVI_DATABASE])
        item_data = next(i for i in GASTE_ARSIVI_DATABASE if i["name"] == selected_name)
        gid = item_data["id"]
        
        if date_mode == "Tek Gün":
            c1, c2, c3 = st.columns([1, 4, 1])
            if c1.button("⬅️ Önceki Gün", use_container_width=True): change_date(-1); st.rerun()
            with c2: st.markdown(f"<h3 style='text-align: center; margin:0; color:#4F8BF9'>{st.session_state.current_date.strftime('%d %B %Y')}</h3>", unsafe_allow_html=True)
            if c3.button("Sonraki Gün ➡️", use_container_width=True): change_date(1); st.rerun()
            
            st.markdown("---")
            col_preview, col_action = st.columns([1, 1.2])
            with col_preview:
                st.subheader("🔍 Güvenli Önizleme")
                with st.spinner("Sorgulanıyor..."):
                    p_data = call_graphql_api(gid, st.session_state.current_date.strftime("%Y-%m-%d"), 1)
                    if p_data and p_data.get("sayfa"):
                        raw_preview = fetch_page_image_via_api(p_data["sayfa"]["dosya"])
                        if raw_preview:
                            st.image(apply_image_filters(raw_preview, **img_settings), caption=f"{selected_name}", use_container_width=True)
                            if st.button("⭐ Favorilere Ekle", use_container_width=True):
                                add_favorite(selected_name, st.session_state.current_date)
                        preview_ok = True
                    else:
                        st.warning("Bu tarihte gazete kaydı bulunamadı (API boş döndü).")
                        preview_ok = False
            
            with col_action:
                st.subheader("⚙️ Operasyon Merkezi")
                citation = generate_apa_citation(selected_name, st.session_state.current_date)
                st.text_area("🎓 Akademik APA 7 Kaynakçası", citation, height=75)
                
                if preview_ok:
                    if st.button("🚀 PDF Olarak İndirmeyi Başlat", type="primary", use_container_width=True):
                        p_bar = st.progress(0)
                        s_text = st.empty()
                        pdf, msg = process_archive_secure(gid, st.session_state.current_date, img_settings, compress, p_bar, s_text)
                        if pdf:
                            s_text.success("✅ PDF Başarıyla Oluşturuldu!")
                            st.download_button("💾 PDF İndir", pdf, f"{selected_name}_{st.session_state.current_date}.pdf", "application/pdf", use_container_width=True)
                            log_download(selected_name, st.session_state.current_date, "Katalog Tekil PDF")

        # TOPLU ARALIK İNDİRME MODU (ZIP SİSTEMİ)
        else:
            st.subheader("📦 Toplu Arşiv İndirme Operasyonu")
            citation = generate_apa_citation(selected_name, st.session_state.current_date, selected_date_end)
            st.text_area("🎓 Toplu Dönem APA Kaynakçası", citation, height=75)
            
            if st.button("🚀 Bütün Aralığı Güvenli Modda Sırayla İndir (ZIP Yap)", type="primary"):
                delta = (selected_date_end - st.session_state.current_date).days + 1
                main_prog = st.progress(0)
                main_status = st.empty()
                
                files = []
                for i in range(delta):
                    curr_day = st.session_state.current_date + timedelta(days=i)
                    main_status.text(f"Dönem İndiriliyor: {curr_day} ({i+1}/{delta})")
                    main_prog.progress((i) / delta)
                    
                    p_bar = st.progress(0)
                    s_text = st.empty()
                    pdf, msg = process_archive_secure(gid, curr_day, img_settings, compress, p_bar, s_text)
                    
                    p_bar.empty()
                    s_text.empty()
                    
                    if pdf:
                        files.append((f"{selected_name}_{curr_day}.pdf", pdf))
                        
                main_prog.progress(1.0)
                if files:
                    main_status.success(f"⚡ Toplam {len(files)} günün gazetesi başarıyla indirildi. ZIP paketi hazırlanıyor...")
                    log_download(selected_name, st.session_state.current_date, f"Toplu ZIP ({len(files)} Gün)")
                    
                    z_buf = BytesIO()
                    with zipfile.ZipFile(z_buf, "a", zipfile.ZIP_DEFLATED, False) as zf:
                        for name, data in files:
                            zf.writestr(name, data.getvalue())
                    z_buf.seek(0)
                    st.download_button("📦 Oluşturulan ZIP Paketini İndir", z_buf, f"{selected_name}_Arsiv.zip", "application/zip", use_container_width=True)
                else:
                    main_status.error("Seçilen tarih aralığında indirilebilir hiçbir yayın bulunamadı.")

    # KIYASLAMA MODU
    elif nav_mode == "🆚 Manşet Kıyaslama":
        st.title("🆚 Tarihsel Manşet Kıyaslama Laboratuvarı")
        
        c1, c2, c3 = st.columns([1, 4, 1])
        if c1.button("⬅️ Geri", use_container_width=True): change_date(-1); st.rerun()
        with c2: st.markdown(f"<h3 style='text-align: center; margin:0'>{st.session_state.current_date.strftime('%d %B %Y')}</h3>", unsafe_allow_html=True)
        if c3.button("İleri ➡️", use_container_width=True): change_date(1); st.rerun()
        
        col_left, col_right = st.columns(2)
        with col_left:
            p1 = st.selectbox("1. Yayın:", [i["name"] for i in GASTE_ARSIVI_DATABASE], index=0)
            gid1 = next(i["id"] for i in GASTE_ARSIVI_DATABASE if i["name"] == p1)
            p_data1 = call_graphql_api(gid1, st.session_state.current_date.strftime("%Y-%m-%d"), 1)
            if p_data1 and p_data1.get("sayfa"):
                img1 = fetch_page_image_via_api(p_data1["sayfa"]["dosya"])
                if img1:
                    st.image(apply_image_filters(img1, **img_settings), use_container_width=True)
                    if st.button(f"📥 {p1} İndir", key="dl_p1", use_container_width=True):
                        pb = st.progress(0); stxt = st.empty()
                        pdf, _ = process_archive_secure(gid1, st.session_state.current_date, img_settings, compress, pb, stxt)
                        if pdf: st.download_button("Kaydet", pdf, f"{p1}.pdf", "application/pdf")
            else: st.warning(f"Bu tarihte {p1} kaydı yok.")
            
        with col_right:
            p2 = st.selectbox("2. Yayın:", [i["name"] for i in GASTE_ARSIVI_DATABASE], index=1)
            gid2 = next(i["id"] for i in GASTE_ARSIVI_DATABASE if i["name"] == p2)
            p_data2 = call_graphql_api(gid2, st.session_state.current_date.strftime("%Y-%m-%d"), 1)
            if p_data2 and p_data2.get("sayfa"):
                img2 = fetch_page_image_via_api(p_data2["sayfa"]["dosya"])
                if img2:
                    st.image(apply_image_filters(img2, **img_settings), use_container_width=True)
                    if st.button(f"📥 {p2} İndir", key="dl_p2", use_container_width=True):
                        pb = st.progress(0); stxt = st.empty()
                        pdf, _ = process_archive_secure(gid2, st.session_state.current_date, img_settings, compress, pb, stxt)
                        if pdf: st.download_button("Kaydet", pdf, f"{p2}.pdf", "application/pdf")
            else: st.warning(f"Bu tarihte {p2} kaydı yok.")

# --- 10. KÜTÜPHANE VE KILAVUZ SEKMELERİ ---
with tab_lib:
    st.header("🗄️ Kişisel Arşiv Veritabanı")
    cl1, cl2 = st.columns(2)
    with cl1:
        st.subheader("⭐ Favori Yayınlarım")
        try:
            df_fav = pd.read_sql_query("SELECT newspaper as [Gazete], pub_date as [Yayın Tarihi] FROM favorites ORDER BY date_added DESC", conn)
            st.dataframe(df_fav, use_container_width=True, hide_index=True)
        except: st.info("Favori listeniz henüz boş.")
    with cl2:
        st.subheader("📥 Lokal İndirme Geçmişi (Son 50)")
        try:
            df_hist = pd.read_sql_query("SELECT date_added as [İndirme Tarihi], newspaper as [Gazete], pub_date as [Yayın Tarihi], type as [Tip] FROM downloads ORDER BY date_added DESC LIMIT 50", conn)
            st.dataframe(df_hist, use_container_width=True, hide_index=True)
        except: st.info("Henüz indirme geçmişi yok.")

with tab_guide:
    st.header("📖 Güvenli Kullanım ve Yapılandırma Kılavuzu")
    st.markdown("""
    ### 🛡️ Bu Sürümde Neler Yeni?
    * **Doğrudan GraphQL Bağlantısı:** Sistem artık sitenin sunucusundaki orijinal API ile haberleşir. CloudFront dosya yolları değişse bile kod bozulmaz, her zaman en güncel resmi çeker.
    * **Çerez Rotasyonu:** İndirme işlemi esnasında her 8 sayfada bir, arka plandaki session nesnesi otomatik olarak çöpe atılır, çerezler sıfırlanır ve rastgele yeni bir tarayıcı kimliği (User-Agent) atanır. Bu sayede **günlük 10 sayfa sınırı** tamamen aşılır.
    * **Akıllı Jitter Gecikmesi:** Bot tespiti yapan sistemleri yanıltmak için sayfa geçişleri arasına `random.uniform` ile insani mikrosaniyeler eklenmiştir.
    
    ### 🛠️ Nasıl Çalıştırırım?
    1. Terminal/CMD ekranını açarak gerekli kütüphaneleri kur:
       ```bash
       pip install streamlit requests Pillow pandas
       ```
    2. Projenin olduğu klasöre gidip betiği yerel sunucuda başlat:
       ```bash
       streamlit run app.py
       ```
    """)
