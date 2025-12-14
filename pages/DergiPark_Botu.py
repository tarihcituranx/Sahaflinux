import streamlit as st
import time
import requests
import re
import os
import pandas as pd
from io import BytesIO
import zipfile

# --- SELENIUM AYARLARI ---
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
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

# --- SEKMELER ---
tab1, tab2 = st.tabs(["📜 HTU Arşivi (Canlı Tarama)", "🤖 DergiPark Botu"])

# --------------------------------------------------------
# SEKME 1: HTU ARŞİVİ (CANLI ARAMA VE İNDİRME)
# --------------------------------------------------------
with tab1:
    st.header("📜 HTU Dijital Süreli Yayınlar")
    st.info("Bu modül, Tokyo Üniversitesi'nin veritabanını canlı olarak tarar.")

    if not SELENIUM_AVAILABLE:
        st.error("Selenium eksik! requirements.txt dosyasını kontrol et.")
    else:
        # Arama Kutusu
        with st.form("htu_form"):
            col1, col2 = st.columns([4,1])
            htu_kelime = col1.text_input("Yayın Adı veya HTU No Ara:", placeholder="Örn: 11 Temmuz, 0141...")
            htu_btn = col2.form_submit_button("🔍 Sitede Ara")

        # Session State ile sonuçları sakla (Sayfa yenilenince gitmesin)
        if 'htu_results' not in st.session_state:
            st.session_state.htu_results = []

        if htu_btn and htu_kelime:
            with st.status("📡 Siteye bağlanılıyor ve taranıyor...", expanded=True) as status:
                try:
                    driver = baslat_driver()
                    # Tokyo Üniversitesi Listesi
                    TARGET_URL = "http://www.tufs.ac.jp/common/fs/asw/turkey/htu/list_all.html"
                    st.write("Veritabanına erişiliyor...")
                    driver.get(TARGET_URL)
                    
                    st.write("Veriler analiz ediliyor...")
                    # Tablodaki satırları bul
                    rows = driver.find_elements(By.XPATH, "//table[@id='tblist']//tr")
                    
                    bulunanlar = []
                    for row in rows:
                        text_content = row.text
                        # Arama kelimesi satırda geçiyor mu? (Büyük küçük harf duyarsız)
                        if htu_kelime.lower() in text_content.lower():
                            cols = row.find_elements(By.TAG_NAME, "td")
                            # HTML yapısı: [No] [HTU No] [Title(Link)] [Desc]
                            if len(cols) >= 4:
                                htu_no = cols[1].text
                                title_elem = cols[2]
                                title_text = title_elem.text
                                desc_text = cols[3].text
                                
                                # Linki al
                                try:
                                    link = title_elem.find_element(By.TAG_NAME, "a").get_attribute("href")
                                except:
                                    link = ""

                                bulunanlar.append({
                                    "HTU NO.": htu_no,
                                    "BAŞLIK": title_text,
                                    "AÇIKLAMA": desc_text,
                                    "LINK": link
                                })
                    
                    st.session_state.htu_results = bulunanlar
                    driver.quit()
                    status.update(label="Arama Tamamlandı!", state="complete", expanded=False)
                    
                except Exception as e:
                    if 'driver' in locals(): driver.quit()
                    st.error(f"Hata: {str(e)}")

        # SONUÇLARI GÖSTERME VE SEÇİM TABLOSU
        if st.session_state.htu_results:
            st.write(f"Toplam {len(st.session_state.htu_results)} sonuç bulundu.")
            
            df = pd.DataFrame(st.session_state.htu_results)
            
            # Seçim sütunu ekle (Varsayılan False)
            df.insert(0, "Seç", False)
            
            # Link sütununu gizleyip arka planda tutacağız, tabloda göstermeyeceğiz
            display_cols = ["Seç", "HTU NO.", "BAŞLIK", "AÇIKLAMA"]
            
            edited_df = st.data_editor(
                df[display_cols],
                column_config={
                    "Seç": st.column_config.CheckboxColumn("İndir", default=False),
                    "HTU NO.": st.column_config.TextColumn("HTU NO.", width="small"),
                    "BAŞLIK": st.column_config.TextColumn("BAŞLIK", width="medium"),
                    "AÇIKLAMA": st.column_config.TextColumn("AÇIKLAMA", width="large"),
                },
                hide_index=True,
                use_container_width=True
            )
            
            # İNDİRME İŞLEMİ
            # Seçilen satırları bul
            selected_indices = edited_df[edited_df["Seç"] == True].index
            
            if len(selected_indices) > 0:
                st.divider()
                st.success(f"✅ {len(selected_indices)} yayın seçildi.")
                
                if st.button("📦 Seçilenleri İndir (ZIP)", type="primary"):
                    zip_buffer = BytesIO()
                    
                    with st.status("Dosyalar hazırlanıyor...", expanded=True) as dl_status:
                        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zf:
                            for idx in selected_indices:
                                item = st.session_state.htu_results[idx]
                                link = item['LINK']
                                title = item['BAŞLIK']
                                
                                # Dosya ismini temizle
                                safe_title = re.sub(r'[\\/*?:"<>|]', "", title)[:30]
                                
                                if link.endswith(".djvu"):
                                    # DjVu indirme ve PDF'e çevirme mantığı
                                    st.write(f"İndiriliyor: {title}...")
                                    try:
                                        # Not: Gerçek sunucuda DjVu to PDF için 'ddjvu' komutu çalışmalı
                                        # Burada basitçe dosyayı indirip koyuyoruz.
                                        r = requests.get(link, timeout=30)
                                        if r.status_code == 200:
                                            # Orijinal dosyayı ekle
                                            zf.writestr(f"{safe_title}.djvu", r.content)
                                        else:
                                            zf.writestr(f"{safe_title}_HATA.txt", f"Linke erisilemedi: {link}")
                                    except Exception as e:
                                        zf.writestr(f"{safe_title}_HATA.txt", str(e))
                                else:
                                    zf.writestr(f"{safe_title}_LINK.txt", f"Bu yayin icin direkt link bulunamadi.\nLink: {link}")
                        
                        dl_status.update(label="Hazır!", state="complete", expanded=False)
                    
                    zip_buffer.seek(0)
                    st.download_button(
                        label="💾 ZIP Dosyasını Kaydet",
                        data=zip_buffer,
                        file_name="HTU_Secilenler.zip",
                        mime="application/zip"
                    )
        elif htu_btn:
            st.warning("Eşleşen kayıt bulunamadı.")

# --------------------------------------------------------
# SEKME 2: DERGİPARK BOTU (Eski Kodun Aynısı)
# --------------------------------------------------------
with tab2:
    st.header("🤖 DergiPark Makale Avcısı")
    
    with st.form("dp_form"):
        col1, col2 = st.columns([4,1])
        dp_kelime = col1.text_input("Makale Ara:", placeholder="Örn: İttihat ve Terakki")
        dp_btn = col2.form_submit_button("🚀 Botu Başlat")

    if dp_btn and dp_kelime:
        with st.status("📡 DergiPark taranıyor...", expanded=True) as status:
            try:
                driver = baslat_driver()
                driver.get(f"https://dergipark.org.tr/tr/search?q={dp_kelime}&section=article")
                
                WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CLASS_NAME, "card-title")))
                
                results = []
                items = driver.find_elements(By.CSS_SELECTOR, "h5.card-title a")
                for item in items[:15]:
                    results.append({"title": item.text, "link": item.get_attribute("href")})
                
                driver.quit()
                status.update(label="Bitti!", state="complete", expanded=False)
                
                if results:
                    st.success(f"{len(results)} makale.")
                    for r in results:
                        with st.expander(r['title']):
                            st.write(f"Link: {r['link']}")
                            # İndirme butonu
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
