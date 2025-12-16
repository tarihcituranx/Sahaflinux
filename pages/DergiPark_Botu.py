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
import cloudscraper # Cloudscraper en başta olmalı

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

# --- SESSION STATE TANIMLAMALARI (CRITICAL FIX) ---
# DergiPark PDF'lerini hafızada tutmak için
if 'dergipark_cache' not in st.session_state:
    st.session_state.dergipark_cache = {}

# GERİ DÖN BUTONU
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
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    }
    
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
                    rows = table.find_all('tr')
                    for row in rows:
                        cols = row.find_all('td')
                        if len(cols) >= 4:
                            htu_no = cols[1].get_text(strip=True)
                            if "HTU NO." in htu_no or not htu_no: continue

                            title_text = cols[2].get_text(strip=True)
                            desc_text = cols[3].get_text(strip=True)
                            
                            link_tag = cols[2].find('a')
                            if link_tag and link_tag.has_attr('href'):
                                raw_link = link_tag['href']
                                if not raw_link.startswith("http"):
                                    full_link = base_url + raw_link
                                else:
                                    full_link = raw_link
                            else:
                                full_link = ""
                                
                            all_data.append({
                                "HTU NO.": htu_no, "BAŞLIK": title_text,
                                "AÇIKLAMA": desc_text, "LINK": full_link
                            })
        except Exception as e:
            st.error(f"HTU Hatası ({page}): {e}")
            
    return pd.DataFrame(all_data)

def download_and_process_djvu(url, filename):
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get(url, headers=headers, stream=True, verify=False)
        if r.status_code != 200: return None, "Dosya bulunamadı."
        return r.content, "OK"
    except Exception as e: return None, str(e)

# --- DERGİPARK FONKSİYONLARI ---
def search_dergipark_brave(keyword, count=15):
    try:
        api_key = st.secrets["BRAVE_API_KEY"]
    except:
        st.error("⚠️ API Anahtarı eksik!")
        return []

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
                    results.append({
                        "title": item["title"],
                        "link": item["url"],
                        "desc": item.get("description", "")
                    })
            return results
    except Exception as e:
        st.error(f"Hata: {e}")
    return []

def fetch_pdf_content(article_url):
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    try:
        response = scraper.get(article_url, timeout=15)
        match = re.search(r'href="([^"]*\/download\/article-file\/\d+)"', response.text)
        if match:
            pdf_link = match.group(1)
            if not pdf_link.startswith("http"):
                pdf_link = "https://dergipark.org.tr" + pdf_link
            
            pdf_response = scraper.get(pdf_link, timeout=15)
            return pdf_response.content
    except Exception as e:
        st.error(f"İndirme hatası: {e}")
    return None

# --- ARAYÜZ SEKMELERİ ---
tab1, tab2 = st.tabs(["📜 HTU Arşivi (Canlı Tarama)", "🤖 DergiPark Botu"])

# SEKME 1: HTU
with tab1:
    st.header("📜 HTU Dijital Süreli Yayınlar")
    col1, col2 = st.columns([4,1])
    search_term = col1.text_input("HTU Yayını Ara:", placeholder="Örn: 11 Temmuz...")
    
    with st.spinner("Veritabanı taranıyor..."):
        df = htu_verilerini_getir()
    
    if not df.empty:
        if search_term:
            df = df[df['BAŞLIK'].str.contains(search_term, case=False) | df['HTU NO.'].str.contains(search_term, case=False)]
        
        st.write(f"{len(df)} kayıt bulundu.")
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
                        else: zf.writestr(f"{safe_title}_HATA.txt", m)
                    else:
                        zf.writestr(f"{safe_title}_LINK.txt", f"Link: {row.LINK}")
                    progress_bar.progress((idx + 1) / len(selected_rows))
            
            zip_buffer.seek(0)
            st.download_button("💾 ZIP Kaydet", zip_buffer, "HTU_Arsiv.zip", "application/zip")

# SEKME 2: DERGİPARK (DÜZELTİLDİ)
with tab2:
    st.header("🤖 DergiPark Makale Avcısı")
    st.info("Brave ile arama yapar, Cloudscraper ile bot korumasını aşarak PDF indirir.")

    # ARAMA FORMU
    with st.form("dp_form"):
        col1, col2 = st.columns([4,1])
        dp_kelime = col1.text_input("Makale Ara:", placeholder="Örn: Milli Mücadele...")
        dp_btn = col2.form_submit_button("🚀 Ara")

    # ARAMA MANTIĞI - YENİ SORGULARDA CACHE TEMİZLE
    if dp_btn and dp_kelime:
        # Yeni arama yapıldığında eski PDF önbelleğini temizle
        st.session_state.dergipark_cache = {}
        
        with st.spinner("🦁 Brave arşivleri tarıyor..."):
            st.session_state.dp_results = search_dergipark_brave(dp_kelime)

    # SONUÇLARI GÖSTER (Session State'den okur, böylece buton tıklamada kaybolmaz)
    if 'dp_results' in st.session_state and st.session_state.dp_results:
        st.success(f"✅ {len(st.session_state.dp_results)} makale bulundu.")
        
        for i, makale in enumerate(st.session_state.dp_results):
            with st.expander(f"📄 {makale['title']}"):
                st.write(f"_{makale['desc']}_")
                
                col_a, col_b = st.columns([1, 3])
                
                # Her makale için benzersiz anahtar
                unique_key = f"dp_{i}"
                
                with col_a:
                    # 1. DURUM: PDF henüz indirilmediyse "Hazırla" butonu göster
                    if unique_key not in st.session_state.dergipark_cache:
                        if st.button("📥 PDF Hazırla", key=f"btn_{unique_key}"):
                            with st.spinner("PDF Sunucudan Çekiliyor..."):
                                pdf_data = fetch_pdf_content(makale['link'])
                                
                                if pdf_data:
                                    # Veriyi hafızaya at ve sayfayı yenile
                                    st.session_state.dergipark_cache[unique_key] = pdf_data
                                    st.rerun()
                                else:
                                    st.error("PDF Bulunamadı.")
                    
                    # 2. DURUM: PDF indirildiyse "Kaydet" butonu göster
                    else:
                        clean_name = re.sub(r'[\\/*?:"<>|]', "", makale['title'])[:30] + ".pdf"
                        st.download_button(
                            label="💾 PDF İNDİR",
                            data=st.session_state.dergipark_cache[unique_key],
                            file_name=clean_name,
                            mime="application/pdf",
                            key=f"dl_{unique_key}",
                            type="primary"
                        )
                
                with col_b:
                    st.markdown(f"👉 **[Siteye Git]({makale['link']})**")
    elif dp_btn:
        st.warning("Sonuç bulunamadı.")
