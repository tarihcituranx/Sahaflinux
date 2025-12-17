import streamlit as st
import requests
import pandas as pd
from io import BytesIO
import zipfile
from bs4 import BeautifulSoup
import urllib3
import cloudscraper
import re
import base64
import time

# Selenium (PDF Dönüştürme İçin Şart)
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    from webdriver_manager.core.os_manager import ChromeType
except ImportError:
    st.error("Selenium modülleri eksik.")
    st.stop()

# SSL Uyarılarını Sustur
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="Harici Kaynaklar", page_icon="🌍", layout="wide")

# --- YAN MENÜ ---
with st.sidebar:
    st.title("⚙️ Kontrol Paneli")
    st.success("✅ HTU: Aktif")
    st.success("✅ DergiPark: Aktif")
    st.success("✅ Gutenberg: PDF Dönüştürücü Aktif")
    st.markdown("---")

# --- URL DÜZELTİCİ ---
def fix_url(link):
    if not link: return ""
    if not link.startswith("http"):
        if link.startswith("dergipark") or link.startswith("www"):
            link = "https://" + link
        elif link.startswith("/"):
            link = "https://dergipark.org.tr" + link
    if "?" in link:
        link = link.split("?")[0]
    return link.strip()

# ========================================================
# 1. HTU ARŞİVİ
# ========================================================
@st.cache_data(ttl=3600)
def htu_verilerini_getir():
    base_url = "https://www.tufs.ac.jp/common/fs/asw/tur/htu/"
    pages = ["list1.html", "list2.html"] 
    headers = {'User-Agent': 'Mozilla/5.0'}
    all_data = []
    
    for page in pages:
        full_url = base_url + page
        try:
            r = requests.get(full_url, headers=headers, timeout=30, verify=False)
            r.encoding = 'utf-8' 
            if r.status_code == 200:
                try: soup = BeautifulSoup(r.content, 'lxml')
                except: soup = BeautifulSoup(r.content, 'html.parser')
                all_rows = soup.find_all('tr')
                for row in all_rows:
                    try:
                        cols = row.find_all(['td', 'th'])
                        if len(cols) >= 3:
                            col_texts = [c.get_text(strip=True) for c in cols]
                            htu_no = col_texts[1]
                            if "HTU NO" in htu_no or not htu_no: continue
                            if len(htu_no) > 20: continue
                            baslik = col_texts[2] if len(cols) > 2 else ""
                            aciklama = col_texts[3] if len(cols) > 3 else ""
                            link_tag = cols[2].find('a')
                            raw_link = link_tag['href'] if link_tag and link_tag.has_attr('href') else ""
                            full_link = base_url + raw_link if raw_link and not raw_link.startswith("http") else raw_link
                            all_data.append({"HTU NO.": htu_no, "BAŞLIK": baslik, "AÇIKLAMA": aciklama, "LINK": full_link})
                    except: continue
        except Exception as e: st.error(f"HTU Hatası: {e}")
    
    df = pd.DataFrame(all_data)
    if not df.empty: df = df.drop_duplicates(subset=['HTU NO.'])
    return df

def download_and_process_djvu(url, filename):
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, stream=True, verify=False)
        return (r.content, "OK") if r.status_code == 200 else (None, "Bulunamadı")
    except Exception as e: return None, str(e)

# ========================================================
# 2. DERGİPARK
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
                    if "dergipark.org.tr" in clean_link and "/pub/article/" not in clean_link:
                        results.append({"title": item["title"], "link": clean_link, "desc": item.get("description", "")})
            return results
    except Exception as e: st.error(f"Arama Hatası: {e}")
    return []

def get_real_pdf_link(article_url):
    scraper = cloudscraper.create_scraper()
    try:
        response = scraper.get(article_url, timeout=10)
        if response.status_code != 200: return None
        soup = BeautifulSoup(response.text, 'lxml')
        meta_tag = soup.find("meta", {"name": "citation_pdf_url"})
        if meta_tag: return fix_url(meta_tag.get("content"))
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            if 'download/article-file' in link['href']: return fix_url(link['href'])
    except: return None
    return None

# ========================================================
# 3. PROJECT GUTENBERG (PDF CONVERTER)
# ========================================================

def get_gutenberg_metadata(book_url):
    """
    Kitap detay sayfasına gidip 'Read Online' (HTML) ve 'EPUB' linklerini çeker.
    """
    try:
        r = requests.get(book_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        data = {"html_link": None, "epub_link": None, "cover": None}
        
        # HTML Linki (PDF yapmak için bu lazım)
        html_tag = soup.find('a', class_='read_html') # Senin attığın HTML'deki class
        if html_tag:
            data["html_link"] = "https://www.gutenberg.org" + html_tag['href']
            
        # EPUB Linki
        # Genelde 'application/epub+zip' içeren link
        epub_tag = soup.find('a', type='application/epub+zip')
        if epub_tag:
             data["epub_link"] = "https://www.gutenberg.org" + epub_tag['href']
             
        # Kapak Resmi
        cover_tag = soup.find('img', class_='cover-art')
        if cover_tag:
             data["cover"] = cover_tag['src']
             
        return data
    except:
        return None

def convert_html_to_pdf_selenium(html_url):
    """
    Selenium kullanarak Gutenberg HTML sayfasını PDF olarak yazdırır.
    """
    status_box = st.empty()
    status_box.info("🚀 Chrome motoru başlatılıyor...")
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    driver = None
    try:
        # Streamlit Cloud için driver yolu
        import os
        service = None
        if os.path.exists("/usr/bin/chromium"):
            chrome_options.binary_location = "/usr/bin/chromium"
            service = Service("/usr/bin/chromedriver")
        else:
            service = Service(ChromeDriverManager().install())
            
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        status_box.info("📄 Sayfa yükleniyor (Bu işlem kitabın boyutuna göre sürebilir)...")
        driver.get(html_url)
        
        # Sayfanın tam yüklenmesi için bekle
        time.sleep(2)
        
        status_box.info("🖨️ PDF oluşturuluyor (Chrome Print)...")
        
        # Chrome DevTools Protocol (CDP) ile yazdırma komutu
        pdf_data = driver.execute_cdp_cmd("Page.printToPDF", {
            "printBackground": True,       # Arka plan resimlerini bas
            "paperWidth": 8.27,            # A4 Genişlik (inç)
            "paperHeight": 11.69,          # A4 Yükseklik (inç)
            "marginTop": 0.4,
            "marginBottom": 0.4,
            "marginLeft": 0.4,
            "marginRight": 0.4
        })
        
        status_box.empty()
        # Base64 veriyi decode et ve döndür
        return base64.b64decode(pdf_data['data'])

    except Exception as e:
        status_box.error(f"Dönüştürme Hatası: {e}")
        return None
    finally:
        if driver:
            driver.quit()

def search_gutenberg(keyword):
    base_url = "https://www.gutenberg.org"
    search_url = f"{base_url}/ebooks/search/?query={keyword}"
    try:
        r = requests.get(search_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
        soup = BeautifulSoup(r.text, 'html.parser')
        books = []
        book_items = soup.find_all('li', class_='booklink')
        for item in book_items:
            try:
                link_tag = item.find('a', class_='link')
                if not link_tag: continue
                book_url = base_url + link_tag['href']
                
                title_tag = item.find('span', class_='title')
                title = title_tag.get_text(strip=True) if title_tag else "Başlıksız"
                
                author_tag = item.find('span', class_='subtitle')
                author = author_tag.get_text(strip=True) if author_tag else "Bilinmiyor"
                
                books.append({"title": title, "author": author, "link": book_url})
            except: continue
        return books
    except: return []

# ========================================================
# ARAYÜZ
# ========================================================
st.title("🌍 Harici Kaynaklar & Canlı Arama")
tab1, tab2, tab3 = st.tabs(["📜 HTU Arşivi", "🤖 DergiPark", "📚 Gutenberg"])

# --- SEKME 1: HTU ---
with tab1:
    col1, col2 = st.columns([4,1])
    search_term = col1.text_input("HTU Yayını Ara (NO veya İsim):", placeholder="Örn: 2662, Tanin...")
    with st.spinner("Taranıyor..."):
        df = htu_verilerini_getir()
    if not df.empty:
        if search_term:
            df = df[df['BAŞLIK'].str.contains(search_term, case=False) | df['HTU NO.'].str.contains(search_term, case=False)]
        st.success(f"Toplam {len(df)} kayıt.")
        df.insert(0, "Seç", False)
        edited_df = st.data_editor(df, column_config={"Seç": st.column_config.CheckboxColumn("İndir", default=False), "LINK": st.column_config.LinkColumn("Görüntüle")}, hide_index=True, use_container_width=True, key="htu_editor")
        selected_rows = edited_df[edited_df["Seç"] == True]
        if not selected_rows.empty and st.button("📦 Seçilenleri İndir (ZIP)", type="primary"):
            progress_bar = st.progress(0)
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zf:
                for idx, row in enumerate(selected_rows.itertuples()):
                    safe_title = re.sub(r'[\\/*?:"<>|]', "", row.BAŞLIK)[:40]
                    safe_filename = f"{row._2}_{safe_title}" 
                    if row.LINK.endswith(".djvu"):
                        c, m = download_and_process_djvu(row.LINK, safe_filename)
                        if c: zf.writestr(f"{safe_filename}.djvu", c)
                    else: zf.writestr(f"{safe_filename}_LINK.txt", f"Link: {row.LINK}")
                    progress_bar.progress((idx + 1) / len(selected_rows))
            st.download_button("💾 ZIP Kaydet", zip_buffer.getvalue(), "HTU_Arsiv.zip", "application/zip")

# --- SEKME 2: DERGİPARK ---
with tab2:
    with st.form("dp_form"):
        col1, col2 = st.columns([4,1])
        dp_kelime = col1.text_input("Makale Ara:", placeholder="Örn: Milli Mücadele...")
        dp_btn = col2.form_submit_button("🚀 Ara")
    if 'dp_results' not in st.session_state: st.session_state.dp_results = []
    if 'found_links' not in st.session_state: st.session_state.found_links = {}
    if dp_btn and dp_kelime:
        st.session_state.found_links = {} 
        with st.spinner("🦁 Taranıyor..."):
            st.session_state.dp_results = search_dergipark_brave(dp_kelime)
    if st.session_state.dp_results:
        st.success(f"✅ {len(st.session_state.dp_results)} makale bulundu.")
        for i, makale in enumerate(st.session_state.dp_results):
            with st.expander(f"📄 {makale['title']}"):
                st.write(f"_{makale['desc']}_")
                col_a, col_b = st.columns([1, 3])
                unique_key = f"dp_{i}"
                with col_a:
                    if unique_key in st.session_state.found_links:
                        status, link = st.session_state.found_links[unique_key]
                        if status == "PDF": st.link_button("📥 PDF'İ İNDİR (Yeni Sekme)", link, type="primary")
                        else: st.link_button("📄 MAKALEYE GİT", link)
                    else:
                        if st.button("🔍 PDF Linkini Bul", key=f"btn_{unique_key}"):
                            with st.spinner("Link çözümleniyor..."):
                                pdf_link = get_real_pdf_link(makale['link'])
                                if pdf_link:
                                    st.session_state.found_links[unique_key] = ("PDF", pdf_link)
                                    st.rerun()
                                else:
                                    st.warning("PDF linki gizli.")
                                    st.session_state.found_links[unique_key] = ("PAGE", makale['link'])
                                    st.rerun()
                with col_b: st.markdown(f"👉 **[Makale Sayfasına Git]({makale['link']})**")

# --- SEKME 3: GUTENBERG (PDF DÖNÜŞTÜRÜCÜ) ---
with tab3:
    st.header("📚 Project Gutenberg (E-Kitap)")
    
    with st.form("gutenberg_form"):
        col1, col2 = st.columns([4,1])
        gb_kelime = col1.text_input("Kitap Ara:", placeholder="Örn: Ottoman, Nutuk...")
        gb_btn = col2.form_submit_button("📖 Ara")
        
    if 'gb_results' not in st.session_state: st.session_state.gb_results = []
    if 'gb_cache' not in st.session_state: st.session_state.gb_cache = {} # Detayları saklamak için
    
    if gb_btn and gb_kelime:
        st.session_state.gb_cache = {} # Yeni aramada temizle
        with st.spinner("📚 Kütüphane taranıyor..."):
            st.session_state.gb_results = search_gutenberg(gb_kelime)
            
    if st.session_state.gb_results:
        st.success(f"✅ {len(st.session_state.gb_results)} kitap bulundu.")
        
        for i, book in enumerate(st.session_state.gb_results):
            with st.container():
                c1, c2 = st.columns([4, 2])
                unique_gb_key = f"gb_{i}"
                
                with c1:
                    st.subheader(book['title'])
                    st.write(f"✍️ **Yazar:** {book['author']}")
                
                with c2:
                    # Detayları (HTML/EPUB linkleri) daha önce çektik mi?
                    if unique_gb_key in st.session_state.gb_cache:
                        details = st.session_state.gb_cache[unique_gb_key]
                        
                        # 1. EPUB İndir (Varsa)
                        if details['epub_link']:
                            st.link_button("📱 EPUB İndir (Orijinal)", details['epub_link'])
                        
                        # 2. PDF Dönüştür (HTML Varsa)
                        if details['html_link']:
                            if st.button("📄 PDF'e Çevir ve İndir", key=f"pdf_gen_{unique_gb_key}"):
                                pdf_bytes = convert_html_to_pdf_selenium(details['html_link'])
                                if pdf_bytes:
                                    clean_name = re.sub(r'[\\/*?:"<>|]', "", book['title'])[:30] + ".pdf"
                                    st.download_button(
                                        "💾 PDF OLARAK KAYDET", 
                                        pdf_bytes, 
                                        clean_name, 
                                        "application/pdf",
                                        key=f"dl_pdf_{unique_gb_key}",
                                        type="primary"
                                    )
                    
                    else:
                        # Henüz detay çekilmedi, butona basınca çek
                        if st.button("🔍 İndirme Seçenekleri", key=f"meta_{unique_gb_key}"):
                            with st.spinner("Kitap kaynakları taranıyor..."):
                                meta = get_gutenberg_metadata(book['link'])
                                if meta:
                                    st.session_state.gb_cache[unique_gb_key] = meta
                                    st.rerun()
                                else:
                                    st.error("Kaynak bulunamadı.")
                st.divider()
