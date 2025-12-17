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
    from selenium.webdriver.common.keys import Keys
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
    st.success("✅ Sidestone: Aktif")
    st.success("✅ JSTOR: Aktif")
    st.success("✅ Harman: Aktif")
    st.success("✅ CORE: Aktif")
    st.warning("🗝️ Sci-Hub: Link Üretici")
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
# YARDIMCI ARAÇLAR (SELENIUM MOTORU)
# ========================================================
def get_selenium_driver():
    """
    Selenium WebDriver'ı başlatır (Linux/Windows uyumlu).
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # Bot korumasını aşmak için User-Agent
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
    driver = get_selenium_driver()
    if not driver: return None
    try:
        driver.get(html_url)
        time.sleep(2)
        pdf_data = driver.execute_cdp_cmd("Page.printToPDF", {"printBackground": True, "paperWidth": 8.27, "paperHeight": 11.69})
        return base64.b64decode(pdf_data['data'])
    except: return None
    finally: driver.quit()

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
        try:
            r = requests.get(base_url + page, headers=headers, timeout=30, verify=False)
            if r.status_code == 200:
                soup = BeautifulSoup(r.content, 'html.parser')
                for row in soup.find_all('tr'):
                    cols = row.find_all(['td', 'th'])
                    if len(cols) >= 3:
                        htu_no = cols[1].get_text(strip=True)
                        if "HTU NO" in htu_no or not htu_no: continue
                        baslik = cols[2].get_text(strip=True)
                        aciklama = cols[3].get_text(strip=True) if len(cols) > 3 else ""
                        link_tag = cols[2].find('a')
                        full_link = base_url + link_tag['href'] if link_tag else ""
                        all_data.append({"HTU NO.": htu_no, "BAŞLIK": baslik, "AÇIKLAMA": aciklama, "LINK": full_link})
        except: continue
    return pd.DataFrame(all_data).drop_duplicates(subset=['HTU NO.']) if all_data else pd.DataFrame()

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
    except: return []
    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {"Accept": "application/json", "X-Subscription-Token": api_key}
    params = {"q": f'site:dergipark.org.tr/tr/pub "{keyword}"', "count": count}
    try:
        data = requests.get(url, headers=headers, params=params).json()
        results = []
        if "web" in data and "results" in data["web"]:
            for item in data["web"]["results"]:
                clean_link = fix_url(item["url"])
                if "dergipark.org.tr" in clean_link:
                    results.append({"title": item["title"], "link": clean_link, "desc": item.get("description", "")})
        return results
    except: return []

def get_real_pdf_link(article_url):
    try:
        soup = BeautifulSoup(cloudscraper.create_scraper().get(article_url).text, 'lxml')
        meta = soup.find("meta", {"name": "citation_pdf_url"})
        return fix_url(meta.get("content")) if meta else None
    except: return None

# ========================================================
# 3. PROJECT GUTENBERG
# ========================================================
def get_gutenberg_metadata(book_url):
    try:
        r = requests.get(book_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        data = {"html_link": None, "epub_link": None, "title_tr": None, "language": "Bilinmiyor", "category": "Belirtilmemiş", "summary_tr": "Özet yok.", "summary": ""}
        
        if h1 := soup.find('h1', itemprop="name"):
            data["title_tr"] = translate_to_turkish(h1.get_text(strip=True))
            
        if link := soup.find('a', class_='read_html'): data["html_link"] = "https://www.gutenberg.org" + link['href']
        if link := soup.find('a', type='application/epub+zip'): data["epub_link"] = "https://www.gutenberg.org" + link['href']
        
        # Özet
        if summary := soup.find('div', class_='summary-text-container'):
            txt = summary.get_text(" ", strip=True).replace("Read More", "").strip()
            data["summary"] = txt
            data["summary_tr"] = translate_to_turkish(txt)

        return data
    except: return None

def search_gutenberg(keyword):
    try:
        soup = BeautifulSoup(requests.get(f"https://www.gutenberg.org/ebooks/search/?query={keyword}", headers={'User-Agent': 'Mozilla/5.0'}).text, 'html.parser')
        books = []
        for item in soup.find_all('li', class_='booklink'):
            link = "https://www.gutenberg.org" + item.find('a', class_='link')['href']
            title = item.find('span', class_='title').get_text(strip=True)
            author = item.find('span', class_='subtitle').get_text(strip=True) if item.find('span', class_='subtitle') else "Bilinmiyor"
            img = item.find('img', class_='cover-thumb')
            img_src = "https://www.gutenberg.org" + img['src'] if img else None
            books.append({"title": title, "author": author, "link": link, "image": img_src})
        return books
    except: return []

# ========================================================
# 4. SIDESTONE PRESS
# ========================================================
def get_sidestone_details(book_url):
    try:
        soup = BeautifulSoup(requests.get(book_url, headers={'User-Agent': 'Mozilla/5.0'}).text, 'html.parser')
        data = {"pdf_link": None, "read_link": None, "title_tr": None, "desc_tr": None}
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            full = "https://www.sidestone.com" + href if not href.startswith("http") else href
            if "download" in href and ".pdf" in href: data["pdf_link"] = full
            if "read online" in link.get_text().lower(): data["read_link"] = full
            
        if title := soup.find('h1'): data["title_tr"] = translate_to_turkish(title.get_text(strip=True))
        if abstract := soup.find(id='abstract'): data["desc_tr"] = translate_to_turkish(abstract.get_text(strip=True))
        return data
    except: return None

def search_sidestone(keyword):
    try:
        soup = BeautifulSoup(requests.get(f"https://www.sidestone.com/books/?q={keyword}", headers={'User-Agent': 'Mozilla/5.0'}).text, 'html.parser')
        books = []
        for div in soup.find_all('div', class_='small-12 medium-8 columns container'):
            if title_a := div.find('a', class_='title'):
                books.append({
                    "title": title_a.find('h1').get_text(strip=True),
                    "link": title_a['href'],
                    "author": div.find('h2').get_text(strip=True) if div.find('h2') else "Bilinmiyor",
                    "image": "https://www.sidestone.com" + div.parent.find('img')['src'] if div.parent.find('img') else None
                })
        return books
    except: return []

# ========================================================
# 5. JSTOR (SELENIUM İLE) - GERİ GELDİ!
# ========================================================
def search_jstor_selenium(keyword):
    driver = get_selenium_driver()
    if not driver: return []
    results = []
    try:
        driver.get(f"https://www.jstor.org/action/doBasicSearch?Query={keyword}&so=rel&acc=on")
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "ol")))
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        for item in soup.find_all('li', {'class': re.compile(r'result-item')}):
            try:
                title = item.find('div', class_='title').get_text(strip=True)
                link = "https://www.jstor.org" + item.find('a', href=True)['href']
                author = item.find('div', class_='contrib').get_text(strip=True) if item.find('div', class_='contrib') else "Yazar Yok"
                results.append({"title": title, "author": author, "link": link})
            except: continue
    except: pass
    finally: driver.quit()
    return results

# ========================================================
# 6. HARMAN (TÜBİTAK API) - GERİ GELDİ!
# ========================================================
def search_harman_api(keyword):
    url = "https://search.harman.ulakbim.gov.tr/api/defaultSearch/publication/"
    params = {"q": keyword, "order": "relevance-DESC", "page": 1, "limit": 20}
    try:
        r = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        return r.json().get("data", []) if r.status_code == 200 else []
    except: return []

def get_harman_link(record):
    if "uri" in record and record["uri"]:
        for link in record["uri"]:
            if "dergipark" in link or "handle.net" in link or ".pdf" in link: return link
        return record["uri"][0]
    return None

# ========================================================
# 7. SCI-HUB LINK GENERATOR
# ========================================================
def generate_scihub_link(doi):
    base = doi.strip()
    return [f"https://sci-hub.se/{base}", f"https://sci-hub.ru/{base}", f"https://sci-hub.st/{base}"]

# ========================================================
# 8. CORE (SELENIUM)
# ========================================================
def search_core_selenium(keyword):
    driver = get_selenium_driver()
    if not driver: return []
    results = []
    try:
        driver.get(f"https://core.ac.uk/search?q={keyword}")
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CLASS_NAME, "search-result")))
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        for card in soup.find_all("div", class_="search-result"):
            try:
                title = card.find("a", href=True).get_text(strip=True)
                link = "https://core.ac.uk" + card.find("a", href=True)['href']
                author = card.find("div", class_="authors").get_text(strip=True) if card.find("div", class_="authors") else "Bilinmiyor"
                abstract = card.find("div", class_="abstract").get_text(strip=True) if card.find("div", class_="abstract") else ""
                
                pdf_link = None
                for a in card.find_all("a", href=True):
                    if "pdf" in a.get_text().lower() or "download" in a['href']:
                        pdf_link = a['href']
                        break

                results.append({
                    "title": title, "title_tr": translate_to_turkish(title),
                    "author": author, "link": link, "pdf": pdf_link,
                    "abstract": abstract, "abstract_tr": translate_to_turkish(abstract)
                })
            except: continue
    except: pass
    finally: driver.quit()
    return results

# ========================================================
# ARAYÜZ
# ========================================================
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "📜 HTU", "🤖 DergiPark", "📚 Gutenberg", "🏛️ Sidestone", 
    "🏛️ JSTOR", "🇹🇷 Harman", "🗝️ Sci-Hub", "🌐 CORE"
])

# 1. HTU
with tab1:
    col1, col2 = st.columns([4,1])
    search_term = col1.text_input("HTU Yayını Ara (NO veya İsim):", placeholder="Örn: 2662, Tanin...")
    with st.spinner("Taranıyor..."): df = htu_verilerini_getir()
    if not df.empty and search_term: df = df[df['BAŞLIK'].str.contains(search_term, case=False) | df['HTU NO.'].str.contains(search_term, case=False)]
    st.data_editor(df, column_config={"LINK": st.column_config.LinkColumn()}, hide_index=True)

# 2. DERGİPARK
with tab2:
    with st.form("dp"):
        k = st.text_input("Makale:")
        b = st.form_submit_button("Ara")
    if b: st.session_state.dp_res = search_dergipark_brave(k)
    if 'dp_res' in st.session_state:
        for m in st.session_state.dp_res:
            with st.expander(m['title']):
                st.write(m['desc'])
                if st.button("PDF Bul", key=m['link']):
                    pdf = get_real_pdf_link(m['link'])
                    if pdf: st.link_button("📥 İndir", pdf)
                    else: st.error("PDF Bulunamadı")

# 3. GUTENBERG
with tab3:
    with st.form("gb"):
        k = st.text_input("Kitap:")
        b = st.form_submit_button("Ara")
    if b: st.session_state.gb_res = search_gutenberg(k)
    if 'gb_res' in st.session_state:
        for book in st.session_state.gb_res:
            c1, c2 = st.columns([4,1])
            c1.subheader(book['title'])
            if c1.button("Detay", key=book['link']):
                meta = get_gutenberg_metadata(book['link'])
                if meta:
                    st.info(meta['title_tr'])
                    st.write(meta['summary_tr'])
                    if meta['html_link']:
                        data = convert_html_to_pdf_selenium(meta['html_link'])
                        if data: st.download_button("PDF İndir", data, "kitap.pdf")

# 4. SIDESTONE
with tab4:
    with st.form("ss"):
        k = st.text_input("Yayın:")
        b = st.form_submit_button("Ara")
    if b: st.session_state.ss_res = search_sidestone(k)
    if 'ss_res' in st.session_state:
        for book in st.session_state.ss_res:
            with st.container():
                st.subheader(book['title'])
                if st.button("Detay & Çevir", key=book['link']):
                    d = get_sidestone_details(book['link'])
                    if d:
                        st.info(d['title_tr'])
                        if d['pdf_link']: st.link_button("PDF İndir", d['pdf_link'])
                        elif d['read_link']: st.link_button("Oku", d['read_link'])

# 5. JSTOR
with tab5:
    st.header("🏛️ JSTOR (Open Access)")
    with st.form("js"):
        k = st.text_input("Makale:")
        b = st.form_submit_button("Ara")
    if b:
        with st.spinner("JSTOR taranıyor..."):
            st.session_state.js_res = search_jstor_selenium(k)
    if 'js_res' in st.session_state:
        for item in st.session_state.js_res:
            st.subheader(item['title'])
            st.caption(item['author'])
            st.link_button("Git", item['link'])
            st.divider()

# 6. HARMAN
with tab6:
    st.header("🇹🇷 Harman (TÜBİTAK)")
    with st.form("hr"):
        k = st.text_input("Tez/Makale:")
        b = st.form_submit_button("Ara")
    if b: st.session_state.hr_res = search_harman_api(k)
    if 'hr_res' in st.session_state:
        for item in st.session_state.hr_res:
            st.subheader(item.get("title", [""])[0])
            st.caption(f"{item.get('author', [''])[0]} | {item.get('publisher', [''])[0]}")
            if l := get_harman_link(item): st.link_button("Kaynağa Git", l)
            st.divider()

# 7. SCI-HUB
with tab7:
    with st.form("sh"):
        doi = st.text_input("DOI:")
        b = st.form_submit_button("Linkle")
    if b:
        for l in generate_scihub_link(doi): st.link_button("Link", l)

# 8. CORE
with tab8:
    st.header("🌐 CORE (Global)")
    with st.form("cr"):
        k = st.text_input("Makale:")
        b = st.form_submit_button("Ara")
    if b:
        with st.spinner("Taranıyor..."):
            st.session_state.cr_res = search_core_selenium(k)
    if 'cr_res' in st.session_state:
        for item in st.session_state.cr_res:
            st.subheader(item['title_tr'])
            st.caption(item['title'])
            if item['abstract_tr']:
                with st.expander("Özet"): st.write(item['abstract_tr'])
            c1, c2 = st.columns(2)
            c1.link_button("Git", item['link'])
            if item['pdf']: c2.link_button("PDF İndir", item['pdf'])
            st.divider()
