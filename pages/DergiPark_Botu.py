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

# --- SELENIUM ---
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
except ImportError:
    st.error("⚠️ Selenium kütüphanesi eksik!")
    st.stop()

st.set_page_config(page_title="Harici Kaynaklar (Debug Modu)", page_icon="🐞", layout="wide")

# --- SESSION STATE ---
if 'dergipark_cache' not in st.session_state:
    st.session_state.dergipark_cache = {}
if 'dp_results' not in st.session_state:
    st.session_state.dp_results = []

with st.sidebar:
    st.title("🐞 Debug Modu")
    st.info("Bu mod, arka planda neler döndüğünü ekrana yazar.")

# --- YARDIMCI: URL TEMİZLEYİCİ ---
def fix_url(link):
    """Linkleri standart hale getirir."""
    if not link.startswith("http"):
        # Başında www veya dergipark varsa https ekle
        if link.startswith("dergipark") or link.startswith("www"):
            link = "https://" + link
        # Hiçbiri yoksa ve / ile başlıyorsa domain ekle
        elif link.startswith("/"):
            link = "https://dergipark.org.tr" + link
    return link

# --- BRAVE ARAMA ---
def search_dergipark_brave(keyword, count=15):
    try: api_key = st.secrets["BRAVE_API_KEY"]
    except: st.error("⚠️ API Anahtarı eksik!"); return []

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
                    
                    # LINK TEMİZLEME
                    clean_link = fix_url(raw_link)
                    
                    # Sadece makale linklerini al (/article/ geçenleri)
                    if "dergipark.org.tr" in clean_link:
                        results.append({
                            "title": item["title"],
                            "link": clean_link,
                            "desc": item.get("description", "")
                        })
            return results
    except Exception as e: st.error(f"Arama Hatası: {e}")
    return []

# --- KRİTİK FONKSİYON: İNDİRME ---
def fetch_pdf_content(article_url):
    """
    Hata ayıklama mesajları ile indirme işlemi.
    """
    status_box = st.empty() # Durum mesajlarını göstermek için kutu
    
    # 1. Linki Kontrol Et
    status_box.info(f"🔗 Bağlanılan Link: {article_url}")
    
    # Tarayıcı Ayarları
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = None
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # 2. Sayfaya Git
        driver.get(article_url)
        
        # Yönlendirme oldu mu kontrol et
        current_url = driver.current_url
        if current_url != article_url:
            status_box.info(f"🔀 Yönlendirme Yapıldı: {current_url}")
        
        # Sayfa Başlığı Kontrolü (404 var mı?)
        page_title = driver.title
        if "404" in page_title or "Bulunamadı" in page_title:
            status_box.error(f"❌ HATA: Gidilen sayfa 404 veriyor! Link bozuk.")
            return None

        # 3. İndirme Linkini Bekle ve Bul
        status_box.info("🔍 Sayfa taraniyor, PDF butonu aranıyor...")
        
        try:
            # Butonun yüklenmesi için 5 saniye bekle
            # href içinde 'article-file' geçen linki arıyoruz
            download_element = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='download/article-file']"))
            )
            
            pdf_path = download_element.get_attribute("href")
            
            # Linki Tamamla
            pdf_link = fix_url(pdf_path)
            
            status_box.success(f"✅ PDF Linki Bulundu: {pdf_link}")
            
            # --- İNDİRME İŞLEMİ (Cookie Transferi ile) ---
            selenium_cookies = driver.get_cookies()
            session = requests.Session()
            for cookie in selenium_cookies:
                session.cookies.set(cookie['name'], cookie['value'])
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": current_url # Referans olarak geldiğimiz sayfayı göster
            }
            
            response = session.get(pdf_link, headers=headers, stream=True)
            
            if response.status_code == 200:
                # Dosya boyutunu kontrol et (çok küçükse hata sayfasıdır)
                if len(response.content) < 2000:
                    status_box.warning("⚠️ İndirilen dosya çok küçük (Hata sayfası olabilir).")
                    return None
                
                status_box.empty() # Mesajları temizle
                return response.content
            else:
                status_box.error(f"❌ İndirme Hatası. Sunucu Kodu: {response.status_code}")
                return None

        except Exception as e:
            status_box.warning("⚠️ Bu sayfada 'article-file' içeren bir indirme butonu bulunamadı.")
            # Sayfa kaynağının bir kısmını göster (Debug için)
            # st.code(driver.page_source[:500], language='html')
            return None

    except Exception as e:
        status_box.error(f"Sistem Hatası: {e}")
        return None
    finally:
        if driver:
            driver.quit()

# --- ARAYÜZ ---
st.header("🤖 DergiPark Botu (Debug Modu)")

with st.form("dp_form"):
    col1, col2 = st.columns([4,1])
    dp_kelime = col1.text_input("Makale Ara:", placeholder="Örn: Milli Mücadele...")
    dp_btn = col2.form_submit_button("🚀 Ara")

if dp_btn and dp_kelime:
    st.session_state.dergipark_cache = {} 
    with st.spinner("🦁 Arşiv taranıyor..."):
        st.session_state.dp_results = search_dergipark_brave(dp_kelime)

if 'dp_results' in st.session_state and st.session_state.dp_results:
    st.success(f"✅ {len(st.session_state.dp_results)} makale bulundu.")
    
    for i, makale in enumerate(st.session_state.dp_results):
        with st.expander(f"📄 {makale['title']}"):
            st.write(f"_{makale['desc']}_")
            st.caption(f"🔗 Link: {makale['link']}") # Linki kullanıcıya gösterelim
            
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
                    st.download_button(
                        "💾 PDF İNDİR", 
                        st.session_state.dergipark_cache[unique_key], 
                        clean_name, "application/pdf", 
                        key=f"dl_{unique_key}", type="primary"
                    )
            
            with col_b:
                st.markdown(f"👉 **[Siteye Git]({makale['link']})**")
