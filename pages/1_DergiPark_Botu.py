import streamlit as st
import time
import requests
import re
import os
from io import BytesIO

# --- SELENIUM KONTROLÜ VE IMPORTLAR ---
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="DergiPark Botu", page_icon="🎓", layout="wide")

# --- SESSION STATE (Sonuçların kaybolmaması için hafıza) ---
if 'bot_results' not in st.session_state:
    st.session_state.bot_results = []

# --- YARDIMCI FONKSİYON: Dosya Adı Temizleme ---
def dosya_adi_temizle(isim):
    # Windows dosya sisteminde yasaklı karakterleri siler
    return re.sub(r'[\\/*?:"<>|]', "", isim).strip()

# --- SIDEBAR: GERİ DÖN BUTONU ---
with st.sidebar:
    st.title("🤖 Bot Kontrol")
    st.info("İşiniz bitince ana sayfaya dönmek için aşağıdaki butona basın.")
    # BURAYA DİKKAT: Ana dosyanızın adı 'Ana_Sayfa.py' ise burası doğru.
    # Eğer dosya adınız farklıysa burayı değiştirin.
    st.page_link("Ana_Sayfa.py", label="⬅️ Gazete Arşivine Dön", icon="↩️")
    st.markdown("---")

# --- ANA EKRAN ---
st.title("🎓 DergiPark Makale Avcısı (Selenium Modu)")

if not SELENIUM_AVAILABLE:
    st.error("⚠️ Selenium kütüphanesi eksik! Terminalde şu komutu çalıştırın: `pip install selenium webdriver-manager`")
else:
    st.markdown("""
    **Nasıl Çalışır?**
    1. Kelimeyi yazın ve **'Botu Başlat'** butonuna basın.
    2. Açılan Chrome penceresini **kapatmayın**.
    3. Eğer **"Ben robot değilim"** (Captcha) çıkarsa, pencerede elle işaretleyin.
    4. Bot sonuçları topladığında pencere kendiliğinden kapanacaktır.
    """)

    # ARAMA FORMU
    with st.form("arama_formu"):
        col1, col2 = st.columns([4, 1])
        kelime = col1.text_input("Aranacak Kelime:", placeholder="Örn: İttihat ve Terakki, Sosyoloji...")
        start_btn = col2.form_submit_button("🚀 Botu Başlat", type="primary", use_container_width=True)

    # --- BOT ÇALIŞMA MANTIĞI ---
    if start_btn and kelime:
        # Eski sonuçları temizle
        st.session_state.bot_results = []
        
        with st.status("📡 Bot çalışıyor... Lütfen bekleyin.", expanded=True) as status:
            try:
                # 1. Tarayıcı Ayarları
                st.write("Chrome tarayıcısı hazırlanıyor...")
                options = webdriver.ChromeOptions()
                options.add_argument("--start-maximized")
                # options.add_argument("--headless") # Görmek için kapalı, Captcha için açık olmalı
                
                driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
                
                # 2. Siteye Git
                st.write(f"'{kelime}' için arama yapılıyor...")
                base_url = f"https://dergipark.org.tr/tr/search?q={kelime}&section=article"
                driver.get(base_url)
                
                # 3. Doğrulama Bekleme (En kritik kısım)
                st.write("⚠️ Doğrulama kontrolü yapılıyor (Gerekirse elle müdahale edin)...")
                # Sonuçlar gelene kadar maks 60 saniye bekle
                WebDriverWait(driver, 60).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "card-title"))
                )
                
                # 4. Verileri Topla
                st.write("Veriler çekiliyor...")
                makaleler = driver.find_elements(By.CSS_SELECTOR, "h5.card-title a")
                
                temp_results = []
                for makale in makaleler[:20]: # İlk 20 sonuç
                    title = makale.text
                    link = makale.get_attribute("href")
                    if title and link:
                        temp_results.append({"title": title, "link": link})
                
                # Sonuçları hafızaya kaydet
                st.session_state.bot_results = temp_results
                
                driver.quit()
                status.update(label="✅ İşlem Tamamlandı!", state="complete", expanded=False)
                
            except Exception as e:
                if 'driver' in locals(): driver.quit()
                st.error(f"Hata oluştu: {str(e)}")

    # --- SONUÇLARI LİSTELEME ---
    if st.session_state.bot_results:
        st.divider()
        st.subheader(f"📄 Bulunan Sonuçlar ({len(st.session_state.bot_results)})")
        
        for i, item in enumerate(st.session_state.bot_results):
            with st.expander(f"{i+1}. {item['title']}"):
                st.write(f"🔗 **Link:** {item['link']}")
                
                # PDF İndirme Butonu Mantığı
                # Her butona benzersiz key veriyoruz (download_btn_0, download_btn_1...)
                col_dl_btn, col_info = st.columns([1, 4])
                
                with col_dl_btn:
                    if st.button("📥 PDF Hazırla", key=f"prep_{i}"):
                        with st.spinner("PDF bağlantısı çözülüyor..."):
                            try:
                                headers = {'User-Agent': 'Mozilla/5.0'}
                                # Makale sayfasına git
                                r = requests.get(item['link'], headers=headers)
                                # PDF linkini regex ile bul (/tr/download/article-file/XXXX)
                                match = re.search(r'/tr/download/article-file/\d+', r.text)
                                
                                if match:
                                    pdf_url = "https://dergipark.org.tr" + match.group(0)
                                    # PDF verisini indir (RAM'e)
                                    pdf_data = requests.get(pdf_url, headers=headers).content
                                    
                                    # İndirme butonunu göster
                                    clean_name = dosya_adi_temizle(item['title'])[:50] + ".pdf"
                                    st.download_button(
                                        label="💾 Bilgisayara Kaydet",
                                        data=pdf_data,
                                        file_name=clean_name,
                                        mime="application/pdf",
                                        key=f"save_{i}"
                                    )
                                    st.success("Hazır!")
                                else:
                                    st.error("Bu makalede açık erişim PDF bulunamadı.")
                            except Exception as e:
                                st.error(f"İndirme hatası: {e}")

    elif start_btn:
        st.warning("Sonuç bulunamadı veya zaman aşımına uğradı.")
