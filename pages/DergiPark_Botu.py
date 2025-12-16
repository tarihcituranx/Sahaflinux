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
import cloudscraper

# SSL Uyarılarını Sustur
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- SELENIUM KONTROLÜ ---
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    from webdriver_manager.core.os_manager import ChromeType
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

st.set_page_config(page_title="Harici Kaynaklar", page_icon="🌍", layout="wide")

# --- SESSION STATE (ÖNEMLİ: Butonların çalışması için) ---
if 'dergipark_cache' not in st.session_state:
    st.session_state.dergipark_cache = {}
if 'dp_results' not in st.session_state:
    st.session_state.dp_results = []

# YAN MENÜ
with st.sidebar:
    st.title("⚙️ Kontrol Paneli")
    st.page_link("app.py", label="⬅️ Gazete Arşivine Dön", icon="↩️")
    st.markdown("---")

st.title("🌍 Harici Kaynaklar & Canlı Arama")

# --- FONKSİYONLAR ---

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
                soup = BeautifulSoup(r.text, 'html.parser')
                table = soup.find('table', id='tblist')
                if table:
                    for row in table.find_all('tr'):
                        cols = row.find_all('td')
                        if len(cols) >= 4:
                            htu_no = cols[1].get_text(strip=True)
                            if "HTU NO." in htu_no or not htu_no: continue
                            
                            link_tag = cols[2].find('a')
                            raw_link = link_tag['href'] if link_tag and link_tag.has_attr('href') else ""
                            full_link = base_url + raw_link if raw_link and not raw_link.startswith("http") else raw_link
                            
                            all_data.append({
                                "HTU NO.": htu_no, 
                                "BAŞLIK": cols[2].get_text(strip=True),
                                "AÇIKLAMA": cols[3].get_text(strip=True), 
                                "LINK": full_link
                            })
        except Exception as e: st.error(f"Hata: {e}")
    return pd.DataFrame(all_data)

def download_and_process_djvu(url, filename):
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, stream=True, verify=False)
        return (r.content, "OK") if r.status_code == 200 else (None, "Bulunamadı")
    except Exception as e: return None, str(e)

# --- DERGİPARK FONKSİYONLARI (GÜNCELLENDİ) ---

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
                    link = item["url"]
                    
                    # --- URL KONTROLÜ (YENİ) ---
                    # Eğer linkte dergi ismi yoksa (direkt /article/ varsa) bu linki atla
                    if "/pub/article/" in link:
                        continue 
                    # ---------------------------

                    results.append({
                        "title": item["title"],
                        "link": link,
                        "desc": item.get("description", "")
                    })
            return results
    except Exception as e: st.error(f"Hata: {e}")
    return []

def fetch_pdf_content(article_url):
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    try:
        # Önce makale sayfasına git
        response = scraper.get(article_url, timeout=15)
        # İndirme linkini ara
        match = re.search(r'href="([^"]*\/download\/article-file\/\d+)"', response.text)
        
        if match:
            pdf_link = match.group(1)
            if not pdf_link.startswith("http"):
                pdf_link = "https://dergipark.org.tr" + pdf_link
            
            # PDF'i indir
            pdf_response = scraper.get(pdf_link, timeout=15)
            return pdf_response.content
    except:
        pass
    return None

# --- ARAYÜZ ---
tab1, tab2 = st.tabs(["📜 HTU Arşivi", "🤖 DergiPark Botu"])

# SEKME 1: HTU
with tab1:
    st.header("📜 HTU Dijital Süreli Yayınlar")
    col1, col2 = st.columns([4,1])
    search_term = col1.text_input("HTU Yayını Ara:", placeholder="Örn: Tanin...")
    
    with st.spinner("Veritabanı taranıyor..."):
        df = htu_verilerini_getir()
    
    if not df.empty:
        if search_term:
            df = df[df['BAŞLIK'].str.contains(search_term, case=False) | df['HTU NO.'].str.contains(search_term, case=False)]
        
        st.write(f"{len(df)} kayıt.")
        df.insert(0, "Seç", False)
        edited_df = st.data_editor(
            df,
            column_config={"Seç": st.column_config.CheckboxColumn("İndir", default=False), "LINK": st.column_config.LinkColumn("Görüntüle")},
            hide_index=True, use_container_width=True, key="htu_editor"
        )
        
        selected_rows = edited_df[edited_df["Seç"] == True]
        if not selected_rows.empty and st.button("📦 Seçilenleri İndir (ZIP)", type="primary"):
            progress_bar = st.progress(0)
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zf:
                for idx, row in enumerate(selected_rows.itertuples()):
                    safe_title = re.sub(r'[\\/*?:"<>|]', "", row.BAŞLIK)[:40]
                    if row.LINK.endswith(".djvu"):
                        c, m = download_and_process_djvu(row.LINK, safe_title)
                        if c: zf.writestr(f"{safe_title}.djvu", c)
                    else: zf.writestr(f"{safe_title}_LINK.txt", f"Link: {row.LINK}")
                    progress_bar.progress((idx + 1) / len(selected_rows))
            st.download_button("💾 ZIP Kaydet", zip_buffer.getvalue(), "HTU_Arsiv.zip", "application/zip")

# SEKME 2: DERGİPARK (DÜZELTİLDİ)
with tab2:
    st.header("🤖 DergiPark Makale Avcısı")
    st.caption("Brave ile bulur, Cloudscraper ile indirir.")

    with st.form("dp_form"):
        col1, col2 = st.columns([4,1])
        dp_kelime = col1.text_input("Makale Ara:", placeholder="Örn: Milli Mücadele...")
        dp_btn = col2.form_submit_button("🚀 Ara")

    # ARAMA İŞLEMİ
    if dp_btn and dp_kelime:
        st.session_state.dergipark_cache = {} # Yeni aramada cache temizle
        with st.spinner("🦁 Arşiv taranıyor..."):
            st.session_state.dp_results = search_dergipark_brave(dp_kelime)

    # SONUÇLARI GÖSTER
    if 'dp_results' in st.session_state and st.session_state.dp_results:
        st.success(f"✅ {len(st.session_state.dp_results)} makale bulundu.")
        
        for i, makale in enumerate(st.session_state.dp_results):
            with st.expander(f"📄 {makale['title']}"):
                st.write(f"_{makale['desc']}_")
                col_a, col_b = st.columns([1, 3])
                
                unique_key = f"dp_{i}"
                
                with col_a:
                    # BUTON MANTIĞI: Hazırla -> İndir
                    if unique_key not in st.session_state.dergipark_cache:
                        if st.button("📥 PDF Hazırla", key=f"btn_{unique_key}"):
                            with st.spinner("İndiriliyor..."):
                                pdf_data = fetch_pdf_content(makale['link'])
                                if pdf_data:
                                    st.session_state.dergipark_cache[unique_key] = pdf_data
                                    st.rerun()
                                else: st.error("İndirilemedi.")
                    else:
                        clean_name = re.sub(r'[\\/*?:"<>|]', "", makale['title'])[:30] + ".pdf"
                        st.download_button(
                            "💾 PDF İNDİR", 
                            st.session_state.dergipark_cache[unique_key], 
                            clean_name, "application/pdf", 
                            key=f"dl_{unique_key}", type="primary"
                        )
                
                with col_b: st.markdown(f"👉 **[Siteye Git]({makale['link']})**")
    elif dp_btn:
        st.warning("Sonuç bulunamadı.")
