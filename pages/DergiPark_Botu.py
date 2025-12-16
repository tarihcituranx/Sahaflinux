import streamlit as st
import time
import requests
import re
import os
import pandas as pd
from io import BytesIO
import zipfile
from bs4 import BeautifulSoup
import urllib3

# SSL Uyarılarını Sustur
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- SELENIUM KÜTÜPHANELERİ ---
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    from webdriver_manager.core.os_manager import ChromeType
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
except ImportError:
    st.error("⚠️ Gerekli kütüphaneler eksik! Lütfen requirements.txt dosyasını kontrol edin.")
    st.stop()

st.set_page_config(page_title="Harici Kaynaklar", page_icon="🌍", layout="wide")

# --- SESSION STATE ---
if 'dergipark_cache' not in st.session_state:
    st.session_state.dergipark_cache = {}
if 'dp_results' not in st.session_state:
    st.session_state.dp_results = []

# --- YAN MENÜ ---
with st.sidebar:
    st.title("⚙️ Kontrol Paneli")
    st.success("✅ Modüller Aktif")
    st.markdown("- **HTU:** LXML Motoru (Tam Liste)\n- **DergiPark:** Selenium (Anti-Bot)")
    st.markdown("---")

# --- YARDIMCI: URL DÜZELTİCİ ---
def fix_url(link):
    if not link.startswith("http"):
        if link.startswith("dergipark") or link.startswith("www"):
            link = "https://" + link
        elif link.startswith("/"):
            link = "https://dergipark.org.tr" + link
    return link

# ========================================================
# 1. HTU ARŞİVİ (LXML GÜÇLENDİRİLMİŞ PARSER)
# ========================================================
@st.cache_data(ttl=3600)
def htu_verilerini_getir():
    """
    lxml parser kullanarak bozuk HTML yapılarını da okur.
    2600+ kaydın tamamını çekmek için optimize edilmiştir.
    """
    base_url = "https://www.tufs.ac.jp/common/fs/asw/tur/htu/"
    pages = ["list1.html", "list2.html"] 
    headers = {'User-Agent': 'Mozilla/5.0'}
    all_data = []
    
    # Bilgi mesajı
    status_text = st.empty()
    
    for page in pages:
        full_url = base_url + page
        try:
            status_text.text(f"Veritabanı taranıyor: {page}...")
            r = requests.get(full_url, headers=headers, timeout=30, verify=False)
            r.encoding = 'utf-8' 
            
            if r.status_code == 200:
                # LXML parser kullan (Daha sağlamdır)
                try:
                    soup = BeautifulSoup(r.text, 'lxml')
                except:
                    # Lxml yoksa fallback
                    soup = BeautifulSoup(r.text, 'html.parser')

                # Tabloyu bul (ID yoksa herhangi bir tabloyu dene)
                table = soup.find('table', id='tblist')
                if not table:
                    table = soup.find('table') 
                
                if table:
                    rows = table.find_all('tr')
                    for row in rows:
                        try:
                            cols = row.find_all('td')
                            # En az 3 sütunlu satırları al
                            if len(cols) >= 3:
                                col_texts = [c.get_text(strip=True) for c in cols]
                                htu_no = col_texts[1]
                                
                                # Başlık satırlarını atla
                                if "HTU NO" in htu_no or not htu_no:
                                    continue
                                
                                # Verileri al
                                baslik = col_texts[2] if len(cols) > 2 else ""
                                aciklama = col_texts[3] if len(cols) > 3 else ""

                                # Linki al
                                link_tag = cols[2].find('a')
                                raw_link = link_tag['href'] if link_tag and link_tag.has_attr('href') else ""
                                full_link = base_url + raw_link if raw_link and not raw_link.startswith("http") else raw_link
                                
                                all_data.append({
                                    "HTU NO.": htu_no, 
                                    "BAŞLIK": baslik,
                                    "AÇIKLAMA": aciklama, 
                                    "LINK": full_link
                                })
                        except:
                            continue
        except Exception as e:
            st.error(f"Hata ({page}): {e}")
    
    status_text.empty()
    return pd.DataFrame(all_data)

def download_and_process_djvu(url, filename):
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, stream=True, verify=False)
        return (r.content, "OK") if r.status_code == 200 else (None, "Bulunamadı")
    except Exception as e: return None, str(e)


# ========================================================
# 2. DERGİPARK (SELENIUM CLOUD UYUMLU - 404 FIX)
# ========================================================

def search_dergipark_brave(keyword, count=15):
    try: api_key = st.secrets["BRAVE_API_KEY"]
    except: st.error("⚠️ Brave API Anahtarı eksik!"); return []

    url = "https://api.search.brave.com/res/v1/web/search"
    query = f'site:dergipark.org.tr/tr/pub "{keyword}"'
    headers = {"Accept": "application/json", "Accept-Encoding": "gzip", "X-Subscription-Token": api_key}
    params = {"q": query, "count": count, "country": "tr"}
    
    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            results = []
            if "web" in data and "results" in data["web"]:
                for item in data["web"]["results"]:
                    raw_link = item["url"]
                    clean_link = fix_url(raw_link)
                    # Sadece geçerli makale linklerini al
                    if "dergipark.org.tr" in clean_link and "/pub/article/" not in clean_link:
                        results.append({
                            "title": item["title"],
                            "link": clean_link,
                            "desc": item.get("description", "")
                        })
            return results
    except Exception as e: st.error(f"Arama Hatası: {e}")
    return []

def fetch_pdf_content(article_url):
    """
    Streamlit Cloud uyumlu, 404 ve Bot korumasını aşan Selenium indiricisi.
    """
    status_box = st.empty()
    status_box.info(f"🚀 Sunucu tarayıcısı başlatılıyor...")
    
    # Tarayıcı Ayarları
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = None
    try:
        # --- TARAYICI SÜRÜCÜSÜ SEÇİMİ (CLOUD FIX) ---
        service = None
        
        # 1. Cloud Ortamı (packages.txt ile kurulanlar)
        if os.path.exists("/usr/bin/chromium"):
            chrome_options.binary_location = "/usr/bin/chromium"
            service = Service("/usr/bin/chromedriver")
        elif os.path.exists("/usr/bin/chromium-browser"):
            chrome_options.binary_location = "/usr/bin/chromium-browser"
            service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
        else:
            # 2. Local Ortam (Windows/Mac)
            service = Service(ChromeDriverManager().install())

        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Sayfaya Git
        driver.get(article_url)
        
        # 404 Kontrolü
        if "404" in driver.title or "Bulunamadı" in driver.title:
            status_box.error("❌ Hata: Sayfa bulunamadı (404).")
            return None

        # İndirme Butonunu Bekle ve Bul
        try:
            download_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='download/article-file']"))
            )
            
            pdf_path = download_element.get_attribute("href")
            pdf_link = fix_url(pdf_path)
            
            # COOKIE TRANSFERİ (Anti-Bot Sihri)
            selenium_cookies = driver.get_cookies()
            session = requests.Session()
            for cookie in selenium_cookies:
                session.cookies.set(cookie['name'], cookie['value'])
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": driver.current_url
            }
            
            status_box.info("📥 PDF indiriliyor...")
            response = session.get(pdf_link, headers=headers, stream=True)
            
            if response.status_code == 200:
                # Dosya boyutu kontrolü (Hata sayfaları genelde küçüktür)
                if len(response.content) < 1500:
                    status_box.warning("⚠️ İndirilen dosya çok küçük, PDF olmayabilir.")
                    return None
                
                status_box.empty()
                return response.content
            else:
                status_box.error(f"Sunucu hatası: {response.status_code}")
                return None

        except Exception as e:
            status_box.warning("⚠️ İndirme butonu bulunamadı (Erişim kısıtlı olabilir).")
            return None

    except Exception as e:
        status_box.error(f"Tarayıcı Hatası: {e}")
        return None
    finally:
        if driver:
            driver.quit()

# ========================================================
# ARAYÜZ YAPILANDIRMASI
# ========================================================
st.title("🌍 Harici Kaynaklar & Canlı Arama")
tab1, tab2 = st.tabs(["📜 HTU Arşivi", "🤖 DergiPark Botu"])

# --- SEKME 1: HTU ---
with tab1:
    st.header("📜 HTU Dijital Süreli Yayınlar")
    col1, col2 = st.columns([4,1])
    search_term = col1.text_input("HTU Yayını Ara (NO veya İsim):", placeholder="Örn: 2662, Tanin...")
    
    # Otomatik yükleme
    with st.spinner("Arşiv listeleri (LXML parser ile) taranıyor..."):
        df = htu_verilerini_getir()
    
    if not df.empty:
        if search_term:
            df = df[
                df['BAŞLIK'].str.contains(search_term, case=False) | 
                df['HTU NO.'].str.contains(search_term, case=False) |
                df['AÇIKLAMA'].str.contains(search_term, case=False)
            ]
        
        st.success(f"Toplam {len(df)} kayıt listelendi.")
        
        df.insert(0, "Seç", False)
        
        edited_df = st.data_editor(
            df,
            column_config={
                "Seç": st.column_config.CheckboxColumn("İndir", default=False),
                "LINK": st.column_config.LinkColumn("Görüntüle")
            },
            hide_index=True, use_container_width=True, key="htu_editor"
        )
        
        selected_rows = edited_df[edited_df["Seç"] == True]
        if not selected_rows.empty and st.button("📦 Seçilenleri İndir (ZIP)", type="primary"):
            progress_bar = st.progress(0)
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zf:
                for idx, row in enumerate(selected_rows.itertuples()):
                    safe_title = re.sub(r'[\\/*?:"<>|]', "", row.BAŞLIK)[:40]
                    safe_filename = f"{row._2}_{safe_title}" # row._2 = HTU NO
                    
                    if row.LINK.endswith(".djvu"):
                        c, m = download_and_process_djvu(row.LINK, safe_filename)
                        if c: zf.writestr(f"{safe_filename}.djvu", c)
                        else: zf.writestr(f"{safe_filename}_HATA.txt", m)
                    else:
                        zf.writestr(f"{safe_filename}_LINK.txt", f"Bu bir klasör veya HTML linkidir: {row.LINK}")
                    progress_bar.progress((idx + 1) / len(selected_rows))
            st.download_button("💾 ZIP Kaydet", zip_buffer.getvalue(), "HTU_Arsiv.zip", "application/zip")

# --- SEKME 2: DERGİPARK ---
with tab2:
    st.header("🤖 DergiPark Makale Avcısı")
    with st.form("dp_form"):
        col1, col2 = st.columns([4,1])
        dp_kelime = col1.text_input("Makale Ara:", placeholder="Örn: Milli Mücadele...")
        dp_btn = col2.form_submit_button("🚀 Ara")

    if dp_btn and dp_kelime:
        st.session_state.dergipark_cache = {} 
        with st.spinner("🦁 Brave arşivleri tarıyor..."):
            st.session_state.dp_results = search_dergipark_brave(dp_kelime)

    if 'dp_results' in st.session_state and st.session_state.dp_results:
        st.success(f"✅ {len(st.session_state.dp_results)} makale bulundu.")
        for i, makale in enumerate(st.session_state.dp_results):
            with st.expander(f"📄 {makale['title']}"):
                st.write(f"_{makale['desc']}_")
                st.caption(f"🔗 {makale['link']}")
                col_a, col_b = st.columns([1, 3])
                unique_key = f"dp_{i}"
                with col_a:
                    if unique_key not in st.session_state.dergipark_cache:
                        if st.button("📥 PDF Hazırla", key=f"btn_{unique_key}"):
                            pdf_data = fetch_pdf_content(makale['link'])
                            if pdf_data:
                                st.session_state.dergipark_cache[unique_key] = pdf_data
                                st.rerun()
                    else:
                        clean_name = re.sub(r'[\\/*?:"<>|]', "", makale['title'])[:30] + ".pdf"
                        st.download_button("💾 PDF İNDİR", st.session_state.dergipark_cache[unique_key], clean_name, "application/pdf", key=f"dl_{unique_key}", type="primary")
                with col_b: st.markdown(f"👉 **[Siteye Git]({makale['link']})**")
    elif dp_btn: st.warning("Sonuç bulunamadı.")
