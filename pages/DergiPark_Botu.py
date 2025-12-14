import streamlit as st
import time
import requests
import re
import os
import pandas as pd
from io import BytesIO
import zipfile
from bs4 import BeautifulSoup

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
    # Dosya adın 'Ana_Sayfa.py' ise burası doğru
    st.page_link("app.py", label="⬅️ Gazete Arşivine Dön", icon="↩️")
    st.markdown("---")

st.title("🌍 Harici Kaynaklar & Canlı Arama")

# --- TARAYICI BAŞLATMA FONKSİYONU ---
def baslat_driver():
    options = Options()
    options.add_argument("--headless") # Cloud için şart
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

# --- HTU VERİ ÇEKME FONKSİYONU (REQUESTS İLE - DAHA HIZLI) ---
@st.cache_data(ttl=3600) # 1 saat önbellekte tutar, sürekli siteye gitmez
def htu_verilerini_getir():
    base_url = "https://www.tufs.ac.jp/common/fs/asw/tur/htu/"
    pages = ["list1.html", "list2.html"] # A-L ve M-Z listeleri
    
    all_data = []
    
    for page in pages:
        try:
            r = requests.get(base_url + page)
            r.encoding = 'utf-8'
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, 'html.parser')
                # Tabloyu bul (id='tblist')
                table = soup.find('table', id='tblist')
                if table:
                    rows = table.find_all('tr')
                    for row in rows:
                        cols = row.find_all('td')
                        # Yapı: [No] [HTU No] [Title (Link)] [Desc]
                        if len(cols) >= 4:
                            htu_no = cols[1].get_text(strip=True)
                            title_col = cols[2]
                            desc_col = cols[3]
                            
                            title_text = title_col.get_text(strip=True)
                            desc_text = desc_col.get_text(strip=True)
                            
                            # Linki al ve tam adrese çevir
                            link_tag = title_col.find('a')
                            if link_tag and link_tag.has_attr('href'):
                                full_link = base_url + link_tag['href']
                            else:
                                full_link = ""
                                
                            # Başlık satırlarını (A, B, C...) atla
                            if "HTU no." in htu_no or not htu_no:
                                continue
                                
                            all_data.append({
                                "HTU NO.": htu_no,
                                "BAŞLIK": title_text,
                                "AÇIKLAMA": desc_text,
                                "LINK": full_link
                            })
        except Exception as e:
            st.error(f"Veri çekme hatası ({page}): {e}")
            
    return pd.DataFrame(all_data)

# --- DJVU İNDİRME VE DÖNÜŞTÜRME ---
def download_and_process_djvu(url, filename):
    try:
        # 1. Dosyayı İndir
        r = requests.get(url, stream=True)
        if r.status_code != 200:
            return None, "Dosya indirilemedi."
        
        djvu_content = r.content
        
        # 2. PDF'e çevirmeyi dene (Sunucuda araç varsa)
        # Not: Streamlit Cloud'da 'ddjvu' komutu packages.txt ile yüklenir.
        # Ancak işlemci gücü yetmeyebilir veya dosya çok büyük olabilir.
        # Bu yüzden önce basitçe orijinali verelim, opsiyonel çeviri yapalım.
        
        return djvu_content, "OK"
        
    except Exception as e:
        return None, str(e)

# --- SEKMELER ---
tab1, tab2 = st.tabs(["📜 HTU Arşivi (Canlı Tarama)", "🤖 DergiPark Botu"])

# --------------------------------------------------------
# SEKME 1: HTU ARŞİVİ (CANLI ARAMA VE İNDİRME)
# --------------------------------------------------------
with tab1:
    st.header("📜 HTU Dijital Süreli Yayınlar")
    st.info("Bu modül, Tokyo Üniversitesi'nin (HTU) A-Z listelerini canlı tarar.")

    # Arama Kutusu
    col1, col2 = st.columns([4,1])
    search_term = col1.text_input("Yayın Adı veya HTU No Ara:", placeholder="Örn: 11 Temmuz...")
    
    # Verileri Çek
    with st.spinner("Veritabanı güncelleniyor..."):
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
        
        # Tabloyu Göster (Seçim Kutulu)
        # Önce 'Seç' sütunu ekle
        filtered_df.insert(0, "Seç", False)
        
        edited_df = st.data_editor(
            filtered_df,
            column_config={
                "Seç": st.column_config.CheckboxColumn("İndir", default=False),
                "LINK": st.column_config.LinkColumn("Doğrudan Link"),
            },
            hide_index=True,
            use_container_width=True,
            key="htu_editor"
        )
        
        # İndirme Butonu
        selected_rows = edited_df[edited_df["Seç"] == True]
        
        if not selected_rows.empty:
            st.divider()
            st.success(f"✅ {len(selected_rows)} yayın seçildi.")
            
            if st.button("📦 Seçilenleri İndir (ZIP)", type="primary"):
                progress_bar = st.progress(0)
                zip_buffer = BytesIO()
                
                with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zf:
                    for idx, row in enumerate(selected_rows.itertuples()):
                        link = row.LINK
                        title = row.BAŞLIK
                        safe_title = re.sub(r'[\\/*?:"<>|]', "", title)[:40] # Dosya adı temizliği
                        
                        if link.endswith(".djvu"):
                            st.toast(f"İndiriliyor: {safe_title}...")
                            content, msg = download_and_process_djvu(link, safe_title)
                            
                            if content:
                                # Orijinal DjVu dosyasını ekle
                                zf.writestr(f"{safe_title}.djvu", content)
                            else:
                                zf.writestr(f"{safe_title}_HATA.txt", f"İndirme hatası: {msg}")
                        else:
                            zf.writestr(f"{safe_title}_LINK.txt", f"Bu yayın bir klasör veya sayfadır. Link: {link}")
                        
                        progress_bar.progress((idx + 1) / len(selected_rows))
                
                zip_buffer.seek(0)
                st.download_button(
                    label="💾 ZIP Dosyasını Kaydet",
                    data=zip_buffer,
                    file_name="HTU_Secilenler.zip",
                    mime="application/zip"
                )
    else:
        st.warning("Veri çekilemedi. Lütfen bağlantınızı kontrol edin.")

# --------------------------------------------------------
# SEKME 2: DERGİPARK BOTU (Mevcut Bot Kodu)
# --------------------------------------------------------
with tab2:
    st.header("🤖 DergiPark Makale Avcısı")
    
    if not SELENIUM_AVAILABLE:
        st.error("Selenium kütüphanesi eksik!")
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
                    
                    # Bekleme süresi arttırıldı
                    time.sleep(5)
                    
                    results = []
                    # CSS selector güncellendi
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
                                        # Basit PDF bulucu
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
