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

# SSL Uyarılarını Sustur (Log kirliliğini önler)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- SELENIUM AYARLARI ---
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

# GERİ DÖN BUTONU
with st.sidebar:
    st.title("⚙️ Kontrol Paneli")
    st.page_link("app.py", label="⬅️ Gazete Arşivine Dön", icon="↩️")
    st.markdown("---")

st.title("🌍 Harici Kaynaklar & Canlı Arama")

# --- TARAYICI BAŞLATMA FONKSİYONU ---
def baslat_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    
    try:
        service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
        return webdriver.Chrome(service=service, options=options)
    except:
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)

# --- GÜÇLENDİRİLMİŞ HTU VERİ ÇEKME FONKSİYONU ---
@st.cache_data(ttl=3600)
def htu_verilerini_getir():
    base_url = "https://www.tufs.ac.jp/common/fs/asw/tur/htu/"
    pages = ["list1.html", "list2.html"]
    
    # Tarayıcı Taklidi Yapan Başlıklar
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
    }
    
    all_data = []
    
    for page in pages:
        full_url = base_url + page
        try:
            # verify=False ekledik (SSL hatasını aşmak için)
            r = requests.get(full_url, headers=headers, timeout=30, verify=False)
            r.encoding = 'utf-8' # Türkçe karakter sorunu için
            
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, 'html.parser')
                table = soup.find('table', id='tblist')
                
                if table:
                    rows = table.find_all('tr')
                    for row in rows:
                        cols = row.find_all('td')
                        if len(cols) >= 4:
                            htu_no = cols[1].get_text(strip=True)
                            
                            # Başlık satırlarını atla
                            if "HTU NO." in htu_no or not htu_no:
                                continue

                            title_col = cols[2]
                            desc_col = cols[3]
                            
                            title_text = title_col.get_text(strip=True)
                            desc_text = desc_col.get_text(strip=True)
                            
                            # Linki al
                            link_tag = title_col.find('a')
                            if link_tag and link_tag.has_attr('href'):
                                raw_link = link_tag['href']
                                # Eğer link "data/..." diye başlıyorsa başına base_url ekle
                                if not raw_link.startswith("http"):
                                    full_link = base_url + raw_link
                                else:
                                    full_link = raw_link
                            else:
                                full_link = ""
                                
                            all_data.append({
                                "HTU NO.": htu_no,
                                "BAŞLIK": title_text,
                                "AÇIKLAMA": desc_text,
                                "LINK": full_link
                            })
            else:
                st.error(f"Hata: {page} sayfası {r.status_code} kodu döndürdü.")
                
        except Exception as e:
            st.error(f"Bağlantı hatası ({page}): {e}")
            
    return pd.DataFrame(all_data)

# --- DJVU İNDİRME ---
def download_and_process_djvu(url, filename):
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get(url, headers=headers, stream=True, verify=False)
        if r.status_code != 200:
            return None, "Dosya sunucuda bulunamadı."
        return r.content, "OK"
    except Exception as e:
        return None, str(e)

# --- SEKMELER ---
tab1, tab2 = st.tabs(["📜 HTU Arşivi (Canlı Tarama)", "🤖 DergiPark Botu"])

# --------------------------------------------------------
# SEKME 1: HTU ARŞİVİ
# --------------------------------------------------------
with tab1:
    st.header("📜 HTU Dijital Süreli Yayınlar")
    st.info("Tokyo Üniversitesi Arşivi (Canlı Veri)")

    # Arama Kutusu
    col1, col2 = st.columns([4,1])
    search_term = col1.text_input("Yayın Adı veya HTU No Ara:", placeholder="Örn: 11 Temmuz...")
    
    # Verileri Çek
    with st.spinner("Veritabanına bağlanılıyor..."):
        df = htu_verilerini_getir()
    
    if not df.empty:
        # Filtreleme
        if search_term:
            filtered_df = df[
                df['BAŞLIK'].str.contains(search_term, case=False) | 
                df['HTU NO.'].str.contains(search_term, case=False) |
                df['AÇIKLAMA'].str.contains(search_term, case=False)
            ]
        else:
            filtered_df = df

        st.write(f"Toplam {len(filtered_df)} sonuç bulundu.")
        
        # Tablo
        filtered_df.insert(0, "Seç", False)
        
        edited_df = st.data_editor(
            filtered_df,
            column_config={
                "Seç": st.column_config.CheckboxColumn("İndir", default=False),
                "LINK": st.column_config.LinkColumn("Görüntüle"),
            },
            hide_index=True,
            use_container_width=True,
            key="htu_editor"
        )
        
        # İndirme Butonu
        selected_rows = edited_df[edited_df["Seç"] == True]
        
        if not selected_rows.empty:
            st.divider()
            if st.button("📦 Seçilenleri İndir (ZIP)", type="primary"):
                progress_bar = st.progress(0)
                zip_buffer = BytesIO()
                
                with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zf:
                    for idx, row in enumerate(selected_rows.itertuples()):
                        link = row.LINK
                        title = row.BAŞLIK
                        safe_title = re.sub(r'[\\/*?:"<>|]', "", title)[:40]
                        
                        if link.endswith(".djvu"):
                            # DjVu dosyasını indir
                            content, msg = download_and_process_djvu(link, safe_title)
                            if content:
                                zf.writestr(f"{safe_title}.djvu", content)
                            else:
                                zf.writestr(f"{safe_title}_HATA.txt", f"Hata: {msg}")
                        else:
                            # Link DjVu değilse (HTML sayfası veya klasör ise)
                            txt_info = f"Bu yayin direkt dosya degil, bir sayfa veya klasordur.\nLutfen tarayicida aciniz: {link}"
                            zf.writestr(f"{safe_title}_LINK.txt", txt_info)
                        
                        progress_bar.progress((idx + 1) / len(selected_rows))
                
                zip_buffer.seek(0)
                st.download_button(
                    label="💾 ZIP Dosyasını Kaydet",
                    data=zip_buffer,
                    file_name="HTU_Arsiv.zip",
                    mime="application/zip"
                )
    else:
        st.warning("Veriler çekilemedi. Bağlantınızı kontrol edin veya siteye erişilemiyor.")

# --------------------------------------------------------
# SEKME 2: DERGİPARK BOTU
# --------------------------------------------------------
with tab2:
    st.header("🤖 DergiPark Makale Avcısı")
    
    if not SELENIUM_AVAILABLE:
        st.error("Selenium eksik! requirements.txt'yi kontrol et.")
    else:
        with st.form("dp_form"):
            col1, col2 = st.columns([4,1])
            dp_kelime = col1.text_input("Makale Ara:", placeholder="Örn: İttihat ve Terakki")
            dp_btn = col2.form_submit_button("🚀 Botu Başlat")

        if dp_btn and dp_kelime:
            with st.status("📡 DergiPark taranıyor...", expanded=True) as status:
                try:
                    driver = baslat_driver()
                    driver.get(f"https://dergipark.org.tr/tr/search?q={dp_kelime}&section=article")
                    
                    time.sleep(5)
                    
                    results = []
                    items = driver.find_elements("css selector", "h5.card-title a")
                    for item in items[:15]:
                        results.append({"title": item.text, "link": item.get_attribute("href")})
                    
                    driver.quit()
                    status.update(label="Bitti!", state="complete", expanded=False)
                    
                    if results:
                        st.success(f"{len(results)} makale bulundu.")
                        for r in results:
                            with st.expander(r['title']):
                                st.write(f"Link: {r['link']}")
                                if st.button("📥 PDF İndir", key=r['link']):
                                    try:
                                        headers = {'User-Agent': 'Mozilla/5.0'}
                                        req = requests.get(r['link'], headers=headers)
                                        match = re.search(r'/tr/download/article-file/\d+', req.text)
                                        if match:
                                            pdf_url = "https://dergipark.org.tr" + match.group(0)
                                            pdf_data = requests.get(pdf_url, headers=headers).content
                                            clean_name = re.sub(r'[\\/*?:"<>|]', "", r['title'])[:30] + ".pdf"
                                            st.download_button("💾 Kaydet", pdf_data, clean_name, "application/pdf")
                                        else:
                                            st.error("PDF bulunamadı.")
                                    except:
                                        st.error("Hata.")
                    else:
                        st.warning("Sonuç yok.")
                except Exception as e:
                    st.error(f"Hata: {str(e)}")
