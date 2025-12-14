import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urljoin
import os
import subprocess
import shutil

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="TUFS Arşiv Tarayıcı", page_icon="🇯🇵", layout="wide")

# --- GERİ DÖN BUTONU ---
with st.sidebar:
    st.title("🏯 TUFS Kontrol")
    st.page_link("app.py", label="⬅️ Gazete Arşivine Dön", icon="↩️")
    st.markdown("---")
    st.info("Bu modül, indirilen DjVu dosyalarını sunucuda otomatik olarak PDF'e çevirir.")

st.title("🇯🇵 TUFS: Japonya Tarih Arşivi (Otomatik PDF Çevirici)")

# --- HEDEF URL ---
BASE_URL = "https://www.tufs.ac.jp/common/fs/asw/tur/htu/list1.html"

# --- DJVU -> PDF ÇEVİRME FONKSİYONU ---
def djvu_to_pdf(input_path, output_path):
    """
    DjVu dosyasını ddjvu aracı ile PDF'e çevirir.
    Gereksinim: packages.txt içinde 'djvulibre-bin' olmalı.
    """
    try:
        # Komut: ddjvu -format=pdf input.djvu output.pdf
        # -skip bozuk sayfaları atlar, -quality ile kaliteyi koruruz
        command = ["ddjvu", "-format=pdf", "-quality=85", "-skip", input_path, output_path]
        
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode == 0 and os.path.exists(output_path):
            return True, "Başarılı"
        else:
            return False, f"Dönüştürme hatası: {result.stderr}"
    except Exception as e:
        return False, str(e)

# --- VERİ ÇEKME FONKSİYONU ---
def tufs_listesini_getir():
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(BASE_URL, headers=headers, timeout=10)
        
        if response.status_code == 200:
            response.encoding = response.apparent_encoding
            soup = BeautifulSoup(response.text, 'html.parser')
            
            veriler = []
            linkler = soup.find_all('a', href=True)
            
            for link in linkler:
                text = link.get_text().strip()
                href = link['href']
                
                if text and not href.startswith("#") and "javascript" not in href:
                    full_link = urljoin(BASE_URL, href)
                    # Sadece indirilebilir dosyalar ve listeleri al
                    if full_link.endswith(".html") or full_link.endswith(".djvu") or full_link.endswith(".pdf") or "list" in full_link:
                         veriler.append({"Eser Adı": text, "Link": full_link})
            return veriler
        else:
            st.error(f"Siteye ulaşılamadı. Kod: {response.status_code}")
            return []
    except Exception as e:
        st.error(f"Hata oluştu: {e}")
        return []

# --- ARAYÜZ ---
col1, col2 = st.columns([1, 4])
if col1.button("📡 Listeyi Getir", type="primary"):
    with st.spinner("Liste çekiliyor..."):
        sonuclar = tufs_listesini_getir()
        st.session_state.tufs_data = sonuclar # Hafızaya at

if 'tufs_data' in st.session_state and st.session_state.tufs_data:
    df = pd.DataFrame(st.session_state.tufs_data)
    st.success(f"{len(df)} eser listelendi.")
    st.dataframe(df, use_container_width=True)
    
    st.divider()
    st.subheader("📥 Dosya İndir ve Çevir")
    
    # Seçim Kutusu
    secilen_eser = st.selectbox("İndirmek istediğiniz eseri seçin:", df["Eser Adı"].tolist())
    
    if secilen_eser:
        secilen_veri = df[df["Eser Adı"] == secilen_eser].iloc[0]
        link = secilen_veri["Link"]
        
        st.write(f"**Seçilen Link:** {link}")
        
        if st.button("🚀 İndir ve PDF Yap"):
            with st.status("İşlem yapılıyor...", expanded=True) as status:
                try:
                    # 1. Dosyayı İndir
                    st.write("Dosya sunucuya indiriliyor...")
                    headers = {'User-Agent': 'Mozilla/5.0'}
                    r = requests.get(link, headers=headers, stream=True)
                    
                    dosya_adi = link.split("/")[-1]
                    if not dosya_adi.endswith(".djvu") and not dosya_adi.endswith(".pdf"):
                         # Uzantı yoksa ve content-type djvu ise ekle
                         dosya_adi += ".djvu"
                    
                    local_djvu_path = f"temp_{dosya_adi}"
                    local_pdf_path = f"{dosya_adi}.pdf"
                    
                    with open(local_djvu_path, "wb") as f:
                        f.write(r.content)
                        
                    # 2. Eğer zaten PDF ise direkt ver
                    if link.endswith(".pdf"):
                        st.write("Bu dosya zaten PDF formatında.")
                        final_path = local_djvu_path
                        mime_type = "application/pdf"
                        download_name = dosya_adi
                        
                    # 3. DJVU ise Çevir
                    elif link.endswith(".djvu") or ".djvu" in link:
                        st.write("⚙️ DjVu formatı tespit edildi. PDF'e dönüştürülüyor (Bu işlem dosya boyutuna göre sürebilir)...")
                        
                        basari, mesaj = djvu_to_pdf(local_djvu_path, local_pdf_path)
                        
                        if basari:
                            st.write("✅ Dönüştürme Başarılı!")
                            final_path = local_pdf_path
                            mime_type = "application/pdf"
                            download_name = local_pdf_path
                        else:
                            status.update(label="❌ Çevirme Hatası", state="error")
                            st.error(f"PDF'e çevrilemedi: {mesaj}")
                            st.info("Orijinal dosya indirilecek.")
                            final_path = local_djvu_path
                            mime_type = "image/vnd.djvu"
                            download_name = dosya_adi

                    # 4. İndirme Butonunu Göster
                    with open(final_path, "rb") as f:
                        btn = st.download_button(
                            label=f"💾 {download_name} İndir",
                            data=f,
                            file_name=download_name,
                            mime=mime_type
                        )
                    
                    status.update(label="✅ Hazır!", state="complete", expanded=False)
                    
                except Exception as e:
                    st.error(f"Hata: {e}")
