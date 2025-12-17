import streamlit as st
import requests
import pandas as pd
from io import BytesIO
from bs4 import BeautifulSoup
import urllib3
import cloudscraper
import re
import base64
import time
import json

# ÇEVİRİ KÜTÜPHANESİ
try:
    from deep_translator import GoogleTranslator
except ImportError:
    st.error("⚠️ deep-translator eksik! requirements.txt kontrol edin.")
    st.stop()

# SELENIUM
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
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
    st.success("✅ Gutenberg: Aktif")
    st.success("✅ Sidestone: Hybrid Hack Modu")
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

# --- ÇEVİRİ FONKSİYONU ---
def translate_to_turkish(text):
    if not text or len(text) < 3: return text
    try:
        if len(text) > 4000: text = text[:4000]
        return GoogleTranslator(source='auto', target='tr').translate(text)
    except: return text

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
# 3. YARDIMCI ARAÇLAR (PDF & SELENIUM)
# ========================================================
def get_selenium_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # Kullanıcı Ajanı (Önemli: Bot gibi görünmemek için)
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    try:
        import os
        service = None
        if os.path.exists("/usr/bin/chromium"):
            chrome_options.binary_location = "/usr/bin/chromium"
            service = Service("/usr/bin/chromedriver")
        else:
            service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=chrome_options)
    except Exception as e:
        st.error(f"Driver Hatası: {e}")
        return None

def convert_html_to_pdf_selenium(html_url):
    """
    Sayfayı aşağı kaydırarak (Lazy Load Tetikleme) yazdırır.
    """
    status_box = st.empty()
    status_box.info("🚀 Chrome motoru başlatılıyor...")
    
    driver = get_selenium_driver()
    if not driver: return None

    try:
        status_box.info("📄 Sayfa yükleniyor...")
        driver.get(html_url)
        time.sleep(5) # İlk yükleme beklemesi

        # --- AUTO-SCROLL (LAZY LOAD TETİKLEYİCİ) ---
        status_box.info("🔄 Sayfalar yükleniyor (Aşağı kaydırılıyor)...")
        last_height = driver.execute_script("return document.body.scrollHeight")
        
        # Yavaş yavaş aşağı in (Hızlı inerse yüklenmeyebilir)
        for i in range(1, 10): # Maksimum 10 adımda inelim (çok uzun sürmesin)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight * arguments[0] / 10);", i)
            time.sleep(1) # Her adımda bekle
        
        # En sona git ve biraz daha bekle
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        
        # En başa dön (Bazen yazdırma için gerekir)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)

        status_box.info("🖨️ PDF basılıyor...")
        pdf_data = driver.execute_cdp_cmd("Page.printToPDF", {
            "printBackground": True, 
            "paperWidth": 8.27, 
            "paperHeight": 11.69,
            "marginTop": 0.4, "marginBottom": 0.4, "marginLeft": 0.4, "marginRight": 0.4
        })
        
        status_box.empty()
        return base64.b64decode(pdf_data['data'])
    except Exception as e: 
        status_box.error(f"Dönüştürme Hatası: {str(e)}")
        return None
    finally:
        driver.quit()

# ========================================================
# 4. PROJECT GUTENBERG
# ========================================================
def get_gutenberg_metadata(book_url):
    try:
        r = requests.get(book_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        data = {"html_link": None, "epub_link": None, "cover": None, "language": "Bilinmiyor", "category": "Belirtilmemiş", "title_tr": None, "title_orig": None, "summary": None, "summary_tr": None}
        
        title_h1 = soup.find('h1', itemprop="name")
        if title_h1:
            orig_title = title_h1.get_text(strip=True)
            data["title_orig"] = orig_title
            data["title_tr"] = translate_to_turkish(orig_title)
        
        html_tag = soup.find('a', class_='read_html')
        if html_tag: data["html_link"] = "https://www.gutenberg.org" + html_tag['href']
        epub_tag = soup.find('a', type='application/epub+zip')
        if epub_tag: data["epub_link"] = "https://www.gutenberg.org" + epub_tag['href']
        cover_tag = soup.find('img', class_='cover-art')
        if cover_tag: data["cover"] = cover_tag['src']
        
        lang_row = soup.find('tr', {'itemprop': 'inLanguage'})
        if lang_row: data["language"] = lang_row.find('td').get_text(strip=True)
        for tr in soup.find_all('tr'):
            th = tr.find('th')
            if th and "LoC Class" in th.get_text():
                data["category"] = tr.find('td').get_text(strip=True)
                break
        
        summary_div = soup.find('div', class_='summary-text-container')
        if summary_div:
            full_text = summary_div.get_text(" ", strip=True)
            original_summary = full_text.replace("Read More", "").replace("Show Less", "").strip()
            data["summary"] = original_summary
            data["summary_tr"] = translate_to_turkish(original_summary)
        else:
            data["summary"] = "Summary not found."
            data["summary_tr"] = "Özet bulunamadı."
        return data
    except: return None

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
                img_tag = item.find('img', class_='cover-thumb')
                img_src = base_url + img_tag['src'] if img_tag else None
                books.append({"title": title, "author": author, "link": book_url, "image": img_src})
            except: continue
        return books
    except: return []

# ========================================================
# 5. SIDESTONE PRESS (HYBRID HACK)
# ========================================================
def download_sidestone_native_pdf_selenium(viewer_url):
    """
    Selenium ile sayfaya girip 'iv' token'ını ve cookie'leri canlı çeker.
    Sonra requests ile dosyayı indirir.
    """
    status_box = st.empty()
    status_box.info("🕵️‍♂️ Tarayıcı başlatılıyor (Token Avı)...")
    
    driver = get_selenium_driver()
    if not driver: return None
    
    try:
        # 1. Sayfaya Git
        driver.get(viewer_url)
        
        # 2. Sayfanın tamamen yüklenmesini ve IV elementinin oluşmasını bekle
        status_box.info("⏳ Sayfa yükleniyor, anahtar bekleniyor...")
        try:
            # 'iv' isimli input elementini bekle (maks 15 saniye)
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.NAME, "iv"))
            )
        except:
            status_box.warning("IV elementi normal yolla bulunamadı, kaynak kod taranıyor...")

        # 3. IV Değerini Çek (JavaScript ile en garantisi)
        iv_token = driver.execute_script("return document.getElementsByName('iv')[0].value;")
        
        if not iv_token:
            status_box.error("❌ Gizli anahtar (IV) bulunamadı.")
            return None
            
        status_box.success(f"🔑 Anahtar yakalandı!")
        
        # 4. Cookie'leri Çal
        cookies = driver.get_cookies()
        session_cookies = {cookie['name']: cookie['value'] for cookie in cookies}
        
        # 5. İndirme Linkini Hazırla
        pdf_target_url = viewer_url + ".pdf"
        
        # 6. POST İsteği At (Requests kütüphanesiyle)
        headers = {
            "Referer": viewer_url,
            "User-Agent": driver.execute_script("return navigator.userAgent;"),
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        payload = {"iv": iv_token}
        
        status_box.info("📥 Orijinal dosya indiriliyor...")
        
        # Cookie'leri ve Token'ı kullanarak istek at
        r = requests.post(pdf_target_url, headers=headers, data=payload, cookies=session_cookies, stream=True)
        
        if r.status_code == 200:
            status_box.empty()
            return r.content
        else:
            status_box.error(f"Sunucu erişimi reddetti (Kod: {r.status_code})")
            return None

    except Exception as e:
        status_box.error(f"Hack Hatası: {e}")
        return None
    finally:
        driver.quit()

def get_sidestone_details(book_url):
    try:
        r = requests.get(book_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        data = {
            "pdf_link": None,
            "read_link": None,
            "title_tr": None,
            "desc_tr": None,
            "abstract_tr": None, "abstract_orig": None,
            "contents_tr": None, "contents_orig": None
        }
        
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link['href']
            text = link.get_text().lower()
            full_href = href if href.startswith("http") else "https://www.sidestone.com" + href
            
            if (".pdf" in href and "download" in href) or "ebook (pdf)" in text:
                data["pdf_link"] = full_href
            if "bookviewer" in href or "read online" in text:
                data["read_link"] = full_href

        # Abstract
        abs_div = soup.find(id='abstract')
        if abs_div:
            txt = abs_div.get_text("\n", strip=True)
            data["abstract_orig"] = txt
            data["abstract_tr"] = translate_to_turkish(txt)
        
        # Contents
        cont_div = soup.find(id='contents')
        if cont_div:
            txt = cont_div.get_text("\n", strip=True)
            data["contents_orig"] = txt
            data["contents_tr"] = translate_to_turkish(txt)

        return data
    except: return None

def search_sidestone(keyword):
    base_url = "https://www.sidestone.com"
    search_url = f"{base_url}/books/?q={keyword}"
    try:
        r = requests.get(search_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
        soup = BeautifulSoup(r.text, 'html.parser')
        books = []
        containers = soup.find_all('div', class_='small-12 medium-8 columns container')
        
        for div in containers:
            try:
                title_a = div.find('a', class_='title')
                if not title_a: continue
                link = title_a['href']
                title = title_a.find('h1').get_text(strip=True)
                
                author_h2 = div.find('h2', style=re.compile(r'margin-top'))
                author = author_h2.get_text(strip=True) if author_h2 else "Bilinmiyor"
                
                parent = div.parent
                img_tag = parent.find('img')
                img_src = img_tag['src'] if img_tag else None
                if img_src and not img_src.startswith("http"): img_src = base_url + img_src
                
                desc_tag = div.find('p')
                desc = desc_tag.get_text(strip=True) if desc_tag else ""
                
                books.append({"title": title, "author": author, "link": link, "image": img_src, "desc": desc})
            except: continue
        return books
    except: return []

# ========================================================
# ARAYÜZ
# ========================================================
st.title("🌍 Harici Kaynaklar & Canlı Arama")
tab1, tab2, tab3, tab4 = st.tabs(["📜 HTU Arşivi", "🤖 DergiPark", "📚 Gutenberg", "🏛️ Sidestone"])

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

# --- SEKME 3: GUTENBERG ---
with tab3:
    with st.form("gutenberg_form"):
        col1, col2 = st.columns([4,1])
        gb_kelime = col1.text_input("Kitap Ara:", placeholder="Örn: Ottoman, Nutuk...")
        gb_btn = col2.form_submit_button("📖 Ara")
    if 'gb_results' not in st.session_state: st.session_state.gb_results = []
    if 'gb_cache' not in st.session_state: st.session_state.gb_cache = {}
    if gb_btn and gb_kelime:
        st.session_state.gb_cache = {} 
        with st.spinner("📚 Kütüphane taranıyor..."):
            st.session_state.gb_results = search_gutenberg(gb_kelime)
    if st.session_state.gb_results:
        st.success(f"✅ {len(st.session_state.gb_results)} kitap bulundu.")
        for i, book in enumerate(st.session_state.gb_results):
            with st.container():
                c1, c2 = st.columns([4, 2])
                unique_gb_key = f"gb_{i}"
                with c1:
                    if unique_gb_key in st.session_state.gb_cache:
                        cached_data = st.session_state.gb_cache[unique_gb_key]
                        st.subheader(cached_data['title_tr'])
                        if cached_data['title_orig']: st.caption(f"🇬🇧 Orijinal: {cached_data['title_orig']}")
                    else: st.subheader(book['title'])
                    st.write(f"✍️ **Yazar:** {book['author']}")
                    if book['image']: st.image(book['image'], width=80)
                with c2:
                    if unique_gb_key in st.session_state.gb_cache:
                        details = st.session_state.gb_cache[unique_gb_key]
                        st.info(f"🗣️ **Dil:** {details['language']}\n\n📂 **Kategori:** {details['category']}")
                        if details['epub_link']: st.link_button("📱 EPUB İndir", details['epub_link'])
                        if details['html_link']:
                            if st.button("📄 PDF Yap ve İndir (Auto-Scroll)", key=f"pdf_gen_{unique_gb_key}"):
                                pdf_bytes = convert_html_to_pdf_selenium(details['html_link'])
                                if pdf_bytes:
                                    clean_name = re.sub(r'[\\/*?:"<>|]', "", book['title'])[:30] + ".pdf"
                                    st.download_button("💾 PDF KAYDET", pdf_bytes, clean_name, "application/pdf", key=f"dl_pdf_{unique_gb_key}", type="primary")
                        st.markdown("### 📖 Kitap Özeti (TR)")
                        st.write(details['summary_tr'])
                        with st.expander("📝 İngilizce Orijinalini Gör"): st.write(details['summary'])
                    else:
                        if st.button("🔍 Detay & İndirme (Çevir)", key=f"meta_{unique_gb_key}"):
                            with st.spinner("Başlık ve özet çevriliyor..."):
                                meta = get_gutenberg_metadata(book['link'])
                                if meta:
                                    st.session_state.gb_cache[unique_gb_key] = meta
                                    st.rerun()
                                else: st.error("Detay bulunamadı.")
                st.divider()
    elif gb_btn: st.error("😔 Kitabı Bulamadım.")

# --- SEKME 4: SIDESTONE PRESS ---
with tab4:
    st.header("🏛️ Sidestone Press (Akademik Arkeoloji & Tarih)")
    with st.form("sidestone_form"):
        col1, col2 = st.columns([4,1])
        ss_kelime = col1.text_input("Yayın Ara:", placeholder="Örn: Ottoman, Archaeology...")
        ss_btn = col2.form_submit_button("🏛️ Ara")
    if 'ss_results' not in st.session_state: st.session_state.ss_results = []
    if 'ss_cache' not in st.session_state: st.session_state.ss_cache = {}
    
    if ss_btn and ss_kelime:
        st.session_state.ss_cache = {}
        with st.spinner("🏛️ Sidestone kütüphanesi taranıyor..."):
            st.session_state.ss_results = search_sidestone(ss_kelime)
    
    if st.session_state.ss_results:
        st.success(f"✅ {len(st.session_state.ss_results)} kaynak bulundu.")
        for i, book in enumerate(st.session_state.ss_results):
            with st.container():
                c1, c2 = st.columns([4, 2])
                unique_ss_key = f"ss_{i}"
                with c1:
                    if unique_ss_key in st.session_state.ss_cache:
                        cached = st.session_state.ss_cache[unique_ss_key]
                        st.subheader(cached['title_tr'])
                        st.caption(f"🇬🇧 Orijinal: {book['title']}")
                    else: st.subheader(book['title'])
                    st.write(f"✍️ **Yazar:** {book['author']}")
                    if book['image']: st.image(book['image'], width=100)
                with c2:
                    if unique_ss_key in st.session_state.ss_cache:
                        details = st.session_state.ss_cache[unique_ss_key]
                        
                        if details['pdf_link']:
                            st.link_button("📥 PDF İndir (Direkt)", details['pdf_link'], type="primary")
                        
                        if details['read_link']:
                            st.link_button("📖 Tarayıcıda Oku", details['read_link'])
                            
                            # 1. HACK İNDİRME
                            if st.button("🗝️ Orijinal PDF'i Çek (Hack)", key=f"hack_ss_{unique_ss_key}"):
                                pdf_bytes = download_sidestone_native_pdf_selenium(details['read_link'])
                                if pdf_bytes:
                                    clean_name = re.sub(r'[\\/*?:"<>|]', "", book['title'])[:30] + ".pdf"
                                    st.download_button("💾 ORİJİNAL İNDİR", pdf_bytes, clean_name, "application/pdf", key=f"dl_hack_{unique_ss_key}", type="primary")
                            
                            # 2. YAZDIRMA (YEDEK)
                            if st.button("📄 Sayfayı Yazdır (Auto-Scroll)", key=f"print_ss_{unique_ss_key}"):
                                with st.spinner("Sayfa taranıyor ve yazdırılıyor..."):
                                    pdf_bytes = convert_html_to_pdf_selenium(details['read_link'])
                                    if pdf_bytes:
                                        clean_name = re.sub(r'[\\/*?:"<>|]', "", book['title'])[:30] + "_Print.pdf"
                                        st.download_button("💾 PDF OLARAK KAYDET", pdf_bytes, clean_name, "application/pdf", key=f"dl_print_{unique_ss_key}")

                        if details['abstract_tr']:
                            st.markdown("### 📝 Geniş Özet")
                            st.write(details['abstract_tr'])
                            with st.expander("🇬🇧 Orijinal"): st.write(details['abstract_orig'])
                        
                        if details['contents_tr']:
                            with st.expander("📑 İçindekiler"):
                                st.text(details['contents_tr'])
                    else:
                        if st.button("🔍 İndirme, Özet & TOC", key=f"ss_meta_{unique_ss_key}"):
                            with st.spinner("Veriler çekiliyor..."):
                                details = get_sidestone_details(book['link'])
                                if details:
                                    details['title_tr'] = translate_to_turkish(book['title'])
                                    st.session_state.ss_cache[unique_ss_key] = details
                                    st.rerun()
                                else: st.error("Bağlantı hatası.")
                st.divider()
    elif ss_btn: st.error("😔 Kaynak Bulunamadı.")
