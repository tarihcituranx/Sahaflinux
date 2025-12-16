import streamlit as st
import requests
import pandas as pd
from io import BytesIO
import zipfile
from bs4 import BeautifulSoup
import urllib3
import cloudscraper
import re

# SSL Uyarılarını Sustur
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="Harici Kaynaklar", page_icon="🌍", layout="wide")

# --- YAN MENÜ ---
with st.sidebar:
    st.title("⚙️ Kontrol Paneli")
    st.success("✅ HTU: Aktif")
    st.info("✅ DergiPark: Tarayıcı Tabanlı İndirme")
    st.markdown("---")
    st.caption("Bu modda doğrulama ekranı çıkarsa, yeni sekmede kendiniz doğrulayıp indirebilirsiniz.")

# --- URL DÜZELTİCİ ---
def fix_url(link):
    if not link: return ""
    if not link.startswith("http"):
        if link.startswith("dergipark") or link.startswith("www"):
            link = "https://" + link
        elif link.startswith("/"):
            link = "https://dergipark.org.tr" + link
    return link

# ========================================================
# 1. HTU ARŞİVİ (ZATEN ÇALIŞAN KISIM)
# ========================================================
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
                try: soup = BeautifulSoup(r.content, 'lxml')
                except: soup = BeautifulSoup(r.content, 'html.parser')

                all_rows = soup.find_all('tr')
                for row in all_rows:
                    try:
                        cols = row.find_all(['td', 'th'])
                        if len(cols) >= 3:
                            col_texts = [c.get_text(strip=True) for c in cols]
                            htu_no = col_texts[1]
                            if "HTU NO" in htu_no or not htu_no: continue
                            if len(htu_no) > 20: continue

                            baslik = col_texts[2] if len(cols) > 2 else ""
                            aciklama = col_texts[3] if len(cols) > 3 else ""

                            link_tag = cols[2].find('a')
                            raw_link = link_tag['href'] if link_tag and link_tag.has_attr('href') else ""
                            full_link = base_url + raw_link if raw_link and not raw_link.startswith("http") else raw_link
                            
                            all_data.append({
                                "HTU NO.": htu_no, "BAŞLIK": baslik,
                                "AÇIKLAMA": aciklama, "LINK": full_link
                            })
                    except: continue
        except Exception as e: st.error(f"HTU Hatası: {e}")
    
    df = pd.DataFrame(all_data)
    if not df.empty: df = df.drop_duplicates(subset=['HTU NO.'])
    return df

def download_and_process_djvu(url, filename):
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, stream=True, verify=False)
        return (r.content, "OK") if r.status_code == 200 else (None, "Bulunamadı")
    except Exception as e: return None, str(e)


# ========================================================
# 2. DERGİPARK (LİNK BULUCU MOD)
# ========================================================

def search_dergipark_brave(keyword, count=15):
    try: api_key = st.secrets["BRAVE_API_KEY"]
    except: st.error("⚠️ Brave API Anahtarı eksik!"); return []

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
                    raw_link = item["url"]
                    clean_link = fix_url(raw_link)
                    if "dergipark.org.tr" in clean_link and "/pub/article/" not in clean_link:
                        results.append({
                            "title": item["title"],
                            "link": clean_link,
                            "desc": item.get("description", "")
                        })
            return results
    except Exception as e: st.error(f"Arama Hatası: {e}")
    return []

def get_real_pdf_link(article_url):
    """
    Sadece linki bulur. İndirmeyi kullanıcıya bırakır.
    """
    scraper = cloudscraper.create_scraper()
    try:
        # Sadece HTML'i çekip linki ayıklayacağız
        response = scraper.get(article_url, timeout=10)
        soup = BeautifulSoup(response.text, 'lxml')
        
        # 1. Öncelik: Meta Etiketi (En temiz link buradadır)
        meta_tag = soup.find("meta", {"name": "citation_pdf_url"})
        if meta_tag:
            return fix_url(meta_tag.get("content"))
        
        # 2. Öncelik: Buton
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            if 'download/article-file' in link['href']:
                return fix_url(link['href'])
                
    except Exception as e:
        # Hata olsa bile en azından makale linkini döndür, kullanıcı oradan indirsin
        return None
    return None

# ========================================================
# ARAYÜZ
# ========================================================
st.title("🌍 Harici Kaynaklar & Canlı Arama")
tab1, tab2 = st.tabs(["📜 HTU Arşivi", "🤖 DergiPark Botu"])

# --- SEKME 1: HTU ---
with tab1:
    st.header("📜 HTU Dijital Süreli Yayınlar")
    col1, col2 = st.columns([4,1])
    search_term = col1.text_input("HTU Yayını Ara (NO veya İsim):", placeholder="Örn: 2662, Tanin...")
    
    with st.spinner("Tüm arşiv taranıyor..."):
        df = htu_verilerini_getir()
    
    if not df.empty:
        if search_term:
            df = df[
                df['BAŞLIK'].str.contains(search_term, case=False) | 
                df['HTU NO.'].str.contains(search_term, case=False) |
                df['AÇIKLAMA'].str.contains(search_term, case=False)
            ]
        st.success(f"Toplam {len(df)} kayıt listelendi.")
        df.insert(0, "Seç", False)
        edited_df = st.data_editor(
            df,
            column_config={
                "Seç": st.column_config.CheckboxColumn("İndir", default=False),
                "LINK": st.column_config.LinkColumn("Görüntüle")
            },
            hide_index=True, use_container_width=True, key="htu_editor"
        )
        selected_rows = edited_df[edited_df["Seç"] == True]
        if not selected_rows.empty and st.button("📦 Seçilenleri İndir (ZIP)", type="primary"):
            progress_bar = st.progress(0)
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zf:
                for idx, row in enumerate(selected_rows.itertuples()):
                    safe_title = re.sub(r'[\\/*?:"<>|]', "", row.BAŞLIK)[:40]
                    safe_filename = f"{row._2}_{safe_title}" 
                    if row.LINK.endswith(".djvu"):
                        c, m = download_and_process_djvu(row.LINK, safe_filename)
                        if c: zf.writestr(f"{safe_filename}.djvu", c)
                        else: zf.writestr(f"{safe_filename}_HATA.txt", m)
                    else:
                        zf.writestr(f"{safe_filename}_LINK.txt", f"Link: {row.LINK}")
                    progress_bar.progress((idx + 1) / len(selected_rows))
            st.download_button("💾 ZIP Kaydet", zip_buffer.getvalue(), "HTU_Arsiv.zip", "application/zip")

# --- SEKME 2: DERGİPARK (LİNK MODU) ---
with tab2:
    st.header("🤖 DergiPark Makale Avcısı")
    with st.form("dp_form"):
        col1, col2 = st.columns([4,1])
        dp_kelime = col1.text_input("Makale Ara:", placeholder="Örn: Milli Mücadele...")
        dp_btn = col2.form_submit_button("🚀 Ara")

    if 'dp_results' not in st.session_state:
        st.session_state.dp_results = []
    
    # Bulunan linkleri hafızada tutmak için
    if 'found_links' not in st.session_state:
        st.session_state.found_links = {}

    if dp_btn and dp_kelime:
        st.session_state.found_links = {} # Yeni aramada temizle
        with st.spinner("🦁 Brave arşivleri tarıyor..."):
            st.session_state.dp_results = search_dergipark_brave(dp_kelime)

    if st.session_state.dp_results:
        st.success(f"✅ {len(st.session_state.dp_results)} makale bulundu.")
        
        for i, makale in enumerate(st.session_state.dp_results):
            with st.expander(f"📄 {makale['title']}"):
                st.write(f"_{makale['desc']}_")
                
                col_a, col_b = st.columns([1, 3])
                unique_key = f"dp_{i}"
                
                with col_a:
                    # Eğer linki daha önce bulduysak direkt butonu göster
                    if unique_key in st.session_state.found_links:
                        final_link = st.session_state.found_links[unique_key]
                        st.link_button("📥 PDF'İ İNDİR (Yeni Sekme)", final_link, type="primary")
                    
                    # Henüz bulmadıysak "Hazırla" butonu göster
                    else:
                        if st.button("🔍 PDF Linkini Bul", key=f"btn_{unique_key}"):
                            with st.spinner("Link çözümleniyor..."):
                                pdf_link = get_real_pdf_link(makale['link'])
                                
                                if pdf_link:
                                    st.session_state.found_links[unique_key] = pdf_link
                                    st.rerun() # Sayfayı yenile ve butonu getir
                                else:
                                    st.error("PDF linki gizli.")
                                    # Linki bulamazsa bari makale linkini verelim
                                    st.link_button("Siteye Git ve İndir", makale['link'])

                with col_b:
                    st.markdown(f"👉 **[Makale Sayfasına Git]({makale['link']})**")
    elif dp_btn:
        st.warning("Sonuç bulunamadı.")
