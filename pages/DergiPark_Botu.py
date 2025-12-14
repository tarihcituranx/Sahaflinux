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
# SEKME 2: DERGİPARK BOTU (BRAVE + CLOUDSCRAPER)
# --------------------------------------------------------
import cloudscraper # Bunu en tepeye eklemeyi unutma, yoksa hata verir!

with tab2:
    st.header("🤖 DergiPark Makale Avcısı")
    st.caption("Brave ile bulur, Cloudscraper ile indirir.")

    # 1. BRAVE İLE ARAMA FONKSİYONU
    def search_dergipark_brave(keyword, count=15):
        try:
            api_key = st.secrets["BRAVE_API_KEY"]
        except:
            st.error("⚠️ API Anahtarı eksik! secrets.toml dosyasını kontrol et.")
            return []

        url = "https://api.search.brave.com/res/v1/web/search"
        query = f'site:dergipark.org.tr/tr/pub "{keyword}"'
        
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": api_key
        }
        
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
            else:
                st.error(f"Brave Hatası: {response.status_code}")
                return []
        except Exception as e:
            st.error(f"Bağlantı Hatası: {e}")
            return []

    # 2. PDF BULUCU (GÜÇLENDİRİLMİŞ VERSİYON)
    def fetch_pdf_content(article_url):
        # Cloudscraper ile gerçek tarayıcı taklidi yapıyoruz
        scraper = cloudscraper.create_scraper(
            browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
        )
        
        try:
            # 1. Sayfanın içine gir
            response = scraper.get(article_url, timeout=15)
            
            # 2. PDF linkini Regex ile ara (Daha esnek bir regex)
            # Hem /tr/ hem /en/ hem de direkt download linklerini yakalar
            match = re.search(r'href="([^"]*\/download\/article-file\/\d+)"', response.text)
            
            if match:
                # Link bazen tam (https://...) bazen yarım (/tr/...) gelir
                pdf_link = match.group(1)
                if not pdf_link.startswith("http"):
                    pdf_link = "https://dergipark.org.tr" + pdf_link
                
                # 3. PDF'i indir (Yine scraper ile)
                pdf_response = scraper.get(pdf_link, timeout=15)
                return pdf_response.content
            else:
                # Bazen link gizli olabilir veya yapı farklıdır
                return None
        except Exception as e:
            st.error(f"İndirme hatası: {e}")
            return None
        return None

    # --- ARAYÜZ ---
    with st.form("dp_form"):
        col1, col2 = st.columns([4,1])
        dp_kelime = col1.text_input("Makale Ara:", placeholder="Örn: Milli Mücadele, Norşin Medresesi")
        dp_btn = col2.form_submit_button("🚀 Ara")

    if dp_btn and dp_kelime:
        with st.spinner("🦁 Brave arşivleri tarıyor..."):
            sonuclar = search_dergipark_brave(dp_kelime)
            
            if sonuclar:
                st.success(f"✅ {len(sonuclar)} makale bulundu.")
                
                for i, makale in enumerate(sonuclar):
                    with st.expander(f"📄 {makale['title']}"):
                        st.write(f"_{makale['desc']}_")
                        
                        col_a, col_b = st.columns([1, 3])
                        
                        # Benzersiz Anahtar
                        unique_key = f"dp_{i}"
                        
                        with col_a:
                            if st.button("📥 PDF İndir", key=unique_key):
                                with st.spinner("Bulutlardan indiriliyor..."):
                                    pdf_data = fetch_pdf_content(makale['link'])
                                    
                                    if pdf_data:
                                        # Dosya adını temizle
                                        clean_name = re.sub(r'[\\/*?:"<>|]', "", makale['title'])[:30] + ".pdf"
                                        st.download_button(
                                            label="💾 Kaydet",
                                            data=pdf_data,
                                            file_name=clean_name,
                                            mime="application/pdf",
                                            key=f"save_{unique_key}"
                                        )
                                    else:
                                        st.error("⚠️ PDF dosyası sayfada bulunamadı (Erişim kısıtlı olabilir).")
                                        st.info("Lütfen yandaki 'Siteye Git' linkini kullanın.")
                        
                        with col_b:
                            st.markdown(f"👉 **[Siteye Git ve Oku]({makale['link']})**")
            else:
                st.warning("Sonuç bulunamadı.")
