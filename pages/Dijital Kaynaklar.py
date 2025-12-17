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
    st.success("✅ JSTOR: Selenium Aktif")
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
# YARDIMCI ARAÇLAR (PDF & SELENIUM)
# ========================================================
def get_selenium_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # JSTOR Bot Korumasını Atlatmak İçin Gerçekçi User-Agent
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
        time.sleep(3)
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
        return (r.content, "OK") if r.status_code == 200 else (None, "Hata")
    except Exception as e: return None, str(e)

# ========================================================
# 2. DERGİPARK
# ========================================================
def search_dergipark_brave(keyword):
    try: api_key = st.secrets["BRAVE_API_KEY"]
    except: return []
    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {"Accept": "application/json", "X-Subscription-Token": api_key}
    params = {"q": f'site:dergipark.org.tr/tr/pub "{keyword}"', "count": 15}
    try:
        data = requests.get(url, headers=headers, params=params).json()
        return [{"title": i["title"], "link": i["url"], "desc": i.get("description", "")} for i in data.get("web", {}).get("results", [])]
    except: return []

def get_real_pdf_link(article_url):
    try:
        soup = BeautifulSoup(cloudscraper.create_scraper().get(article_url).text, 'lxml')
        meta = soup.find("meta", {"name": "citation_pdf_url"})
        return meta.get("content") if meta else None
    except: return None

# ========================================================
# 3. PROJECT GUTENBERG
# ========================================================
def search_gutenberg(keyword):
    try:
        soup = BeautifulSoup(requests.get(f"https://www.gutenberg.org/ebooks/search/?query={keyword}", headers={'User-Agent': 'Mozilla/5.0'}).text, 'html.parser')
        books = []
        for item in soup.find_all('li', class_='booklink'):
            link = "https://www.gutenberg.org" + item.find('a', class_='link')['href']
            title = item.find('span', class_='title').get_text(strip=True)
            author = item.find('span', class_='subtitle').get_text(strip=True) if item.find('span', class_='subtitle') else "Bilinmiyor"
            books.append({"title": title, "author": author, "link": link})
        return books
    except: return []

def get_gutenberg_metadata(book_url):
    try:
        soup = BeautifulSoup(requests.get(book_url, headers={'User-Agent': 'Mozilla/5.0'}).text, 'html.parser')
        data = {"html_link": None, "epub_link": None, "title_tr": None}
        html_tag = soup.find('a', class_='read_html')
        if html_tag: data["html_link"] = "https://www.gutenberg.org" + html_tag['href']
        epub_tag = soup.find('a', type='application/epub+zip')
        if epub_tag: data["epub_link"] = "https://www.gutenberg.org" + epub_tag['href']
        title = soup.find('h1', itemprop="name").get_text(strip=True)
        data["title_tr"] = translate_to_turkish(title)
        return data
    except: return None

# ========================================================
# 4. SIDESTONE PRESS
# ========================================================
def search_sidestone(keyword):
    try:
        soup = BeautifulSoup(requests.get(f"https://www.sidestone.com/books/?q={keyword}", headers={'User-Agent': 'Mozilla/5.0'}).text, 'html.parser')
        books = []
        for div in soup.find_all('div', class_='small-12 medium-8 columns container'):
            title_a = div.find('a', class_='title')
            if not title_a: continue
            books.append({
                "title": title_a.find('h1').get_text(strip=True),
                "link": title_a['href'],
                "desc": div.find('p').get_text(strip=True) if div.find('p') else ""
            })
        return books
    except: return []

def get_sidestone_details(book_url):
    try:
        soup = BeautifulSoup(requests.get(book_url, headers={'User-Agent': 'Mozilla/5.0'}).text, 'html.parser')
        data = {"read_link": None, "title_tr": None, "desc_tr": None}
        
        for link in soup.find_all('a', href=True):
            if "read online" in link.get_text().lower():
                data["read_link"] = "https://www.sidestone.com" + link['href'] if not link['href'].startswith("http") else link['href']
        
        # Başlık ve Özet Çevirisi
        if soup.find('h1'): data["title_tr"] = translate_to_turkish(soup.find('h1').get_text(strip=True))
        if soup.find(id='abstract'): data["desc_tr"] = translate_to_turkish(soup.find(id='abstract').get_text(strip=True))
        
        return data
    except: return None

# ========================================================
# 5. JSTOR (YENİ - SELENIUM İLE)
# ========================================================
def search_jstor_selenium(keyword):
    """
    JSTOR üzerinde 'Open Access' (acc=on) araması yapar.
    Bot korumasını Selenium ile aşar.
    """
    driver = get_selenium_driver()
    if not driver: return []
    
    base_url = "https://www.jstor.org/action/doBasicSearch"
    # acc=on -> Sadece erişilebilir içerik (Open Access)
    search_url = f"{base_url}?Query={keyword}&so=rel&acc=on"
    
    results = []
    
    try:
        driver.get(search_url)
        # Vue.js yüklenene kadar bekle (sonuç listesini arıyoruz)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "ol"))
        )
        
        # Sayfa kaynağını al ve parse et
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # JSTOR sonuçları genelde <ol> içindeki <li> elementleridir
        items = soup.find_all('li', {'class': re.compile(r'result-item')})
        
        for item in items:
            try:
                # Başlık
                title_tag = item.find('div', class_='title')
                if not title_tag: continue
                title = title_tag.get_text(strip=True)
                
                # Link (Stable Link)
                link_tag = item.find('a', href=True)
                link = "https://www.jstor.org" + link_tag['href']
                
                # Yazar
                author_tag = item.find('div', class_='contrib')
                author = author_tag.get_text(strip=True) if author_tag else "Yazar belirtilmemiş"
                
                # Yayın Bilgisi
                pub_tag = item.find('div', class_='src')
                pub_info = pub_tag.get_text(strip=True) if pub_tag else ""
                
                # Tür (Makale/Kitap Bölümü)
                type_badge = item.find('div', class_='badge')
                content_type = type_badge.get_text(strip=True) if type_badge else "Kaynak"

                results.append({
                    "title": title,
                    "author": author,
                    "link": link,
                    "pub_info": pub_info,
                    "type": content_type
                })
            except: continue
            
    except Exception as e:
        print(f"JSTOR Hatası: {e}")
    finally:
        driver.quit()
        
    return results

# ========================================================
# ARAYÜZ
# ========================================================
st.title("🌍 Harici Kaynaklar & Canlı Arama")
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📜 HTU", "🤖 DergiPark", "📚 Gutenberg", "🏛️ Sidestone", "🏛️ JSTOR"])

# --- SEKME 1: HTU ---
with tab1:
    search_term = st.text_input("HTU Ara:", placeholder="Örn: Tanin...")
    df = htu_verilerini_getir()
    if not df.empty and search_term:
        df = df[df['BAŞLIK'].str.contains(search_term, case=False)]
    st.data_editor(df, column_config={"LINK": st.column_config.LinkColumn()}, hide_index=True)

# --- SEKME 2: DERGİPARK ---
with tab2:
    with st.form("dp_form"):
        dp_kelime = st.text_input("Makale Ara:")
        dp_btn = st.form_submit_button("Ara")
    if dp_btn:
        st.session_state.dp_results = search_dergipark_brave(dp_kelime)
    if 'dp_results' in st.session_state:
        for m in st.session_state.dp_results:
            with st.expander(m['title']):
                st.write(m['desc'])
                if st.button("PDF Linki Bul", key=m['link']):
                    pdf = get_real_pdf_link(m['link'])
                    if pdf: st.link_button("📥 İndir", pdf)
                    else: st.error("Bulunamadı")

# --- SEKME 3: GUTENBERG ---
with tab3:
    with st.form("gb_form"):
        gb_kelime = st.text_input("Kitap Ara (İngilizce):")
        gb_btn = st.form_submit_button("Ara")
    if gb_btn: st.session_state.gb_results = search_gutenberg(gb_kelime)
    if 'gb_results' in st.session_state:
        for b in st.session_state.gb_results:
            with st.container():
                st.subheader(b['title'])
                if st.button("Detay & Çevir", key=b['link']):
                    meta = get_gutenberg_metadata(b['link'])
                    if meta:
                        st.info(f"🇹🇷 {meta['title_tr']}")
                        if meta['html_link']:
                            pdf_data = convert_html_to_pdf_selenium(meta['html_link'])
                            if pdf_data: st.download_button("PDF İndir", pdf_data, "kitap.pdf")

# --- SEKME 4: SIDESTONE ---
with tab4:
    with st.form("ss_form"):
        ss_kelime = st.text_input("Yayın Ara:")
        ss_btn = st.form_submit_button("Ara")
    if ss_btn: st.session_state.ss_results = search_sidestone(ss_kelime)
    if 'ss_results' in st.session_state:
        for b in st.session_state.ss_results:
            with st.expander(b['title']):
                st.write(b['desc'])
                if st.button("Çevir & Oku", key=b['link']):
                    d = get_sidestone_details(b['link'])
                    if d:
                        st.subheader(d['title_tr'])
                        st.write(d['desc_tr'])
                        if d['read_link']: st.link_button("📖 Oku", d['read_link'])

# --- SEKME 5: JSTOR (YENİ) ---
with tab5:
    st.header("🏛️ JSTOR Akademik Arşiv (Open Access)")
    st.info("JSTOR'un sadece ücretsiz erişime açık makalelerini tarar. PDF indirmek yerine makale sayfasına yönlendirir.")
    
    with st.form("jstor_form"):
        col1, col2 = st.columns([4,1])
        js_kelime = col1.text_input("Makale/Konu Ara (İngilizce önerilir):", placeholder="Örn: Ottoman History...")
        js_btn = col2.form_submit_button("🏛️ Ara")
    
    if 'js_results' not in st.session_state: st.session_state.js_results = []
    
    if js_btn and js_kelime:
        with st.spinner("🦁 Selenium, JSTOR korumasını aşıyor ve tarıyor..."):
            st.session_state.js_results = search_jstor_selenium(js_kelime)
            
    if st.session_state.js_results:
        st.success(f"✅ {len(st.session_state.js_results)} sonuç bulundu.")
        
        for i, item in enumerate(st.session_state.js_results):
            with st.container():
                c1, c2 = st.columns([5, 1])
                with c1:
                    # Başlık
                    st.subheader(item['title'])
                    # Yazar ve Yayın Bilgisi
                    st.caption(f"✍️ {item['author']} | 📅 {item['pub_info']}")
                    # Tür Etiketi
                    st.markdown(f"**Tür:** `{item['type']}`")
                
                with c2:
                    # JSTOR'da direkt PDF indirmek ban sebebidir, o yüzden link veriyoruz
                    st.link_button("📄 Makaleye Git", item['link'], type="primary")
                
                st.divider()
    elif js_btn:
        st.warning("Sonuç bulunamadı veya JSTOR erişimi engelledi.")
