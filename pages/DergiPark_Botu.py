import streamlit as st
import requests
import pandas as pd
from io import BytesIO
import zipfile
from bs4 import BeautifulSoup
import urllib3
import re

# ZENROWS KÜTÜPHANESİ
try:
    from zenrows import ZenRowsClient
except ImportError:
    st.error("⚠️ `zenrows` kütüphanesi eksik! requirements.txt dosyasına ekleyin.")
    st.stop()

# SSL Uyarılarını Sustur
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="Harici Kaynaklar", page_icon="🌍", layout="wide")

# --- API ANAHTARI ---
# Normalde st.secrets içinden almalısın ama şimdilik senin verdiğini kullanıyoruz.
ZENROWS_KEY = "6f09eed1a045e0384a2e8aa817a155f0ade82187"

# --- YAN MENÜ ---
with st.sidebar:
    st.title("⚙️ Kontrol Paneli")
    st.success("✅ HTU: Agresif Mod")
    st.success("✅ DergiPark: ZenRows API (Premium)")
    st.markdown("---")

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
# 2. DERGİPARK (ZENROWS İLE KESİN ÇÖZÜM)
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

def fetch_pdf_with_zenrows(article_url):
    """
    ZenRows API kullanarak DergiPark korumasını deler ve PDF'i indirir.
    """
    status_box = st.empty()
    status_box.info("🚀 ZenRows API ile bağlanılıyor...")
    
    client = ZenRowsClient(ZENROWS_KEY)
    
    try:
        # 1. ADIM: Makale sayfasına git ve PDF linkini bul
        # 'js_render=true' ve 'antibot=true' parametreleri korumayı aşar
        params = {"js_render": "true", "antibot": "true"}
        
        response = client.get(article_url, params=params)
        
        if response.status_code != 200:
            status_box.error(f"Sayfa açılamadı. Kod: {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, 'lxml')
        
        # Meta etiketinden PDF linkini al
        pdf_link = None
        meta_tag = soup.find("meta", {"name": "citation_pdf_url"})
        
        if meta_tag:
            pdf_link = meta_tag.get("content")
        else:
            # Bulamazsa butonları tara
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                if 'download/article-file' in link['href']:
                    pdf_link = link['href']
                    break
        
        if not pdf_link:
            status_box.error("❌ PDF linki bulunamadı.")
            return None
            
        final_pdf_url = fix_url(pdf_link)
        status_box.info(f"✅ Link bulundu! İndiriliyor...")

        # 2. ADIM: PDF'i ZenRows üzerinden indir (Yine korumayı aşarak)
        # Binary veri olduğu için .content alacağız
        pdf_response = client.get(final_pdf_url, params=params)
        
        if pdf_response.status_code == 200:
            status_box.empty()
            return pdf_response.content
        else:
            status_box.error(f"İndirme başarısız: {pdf_response.status_code}")
            return None

    except Exception as e:
        status_box.error(f"ZenRows Hatası: {e}")
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

# --- SEKME 2: DERGİPARK (ZENROWS) ---
with tab2:
    st.header("🤖 DergiPark Makale Avcısı")
    with st.form("dp_form"):
        col1, col2 = st.columns([4,1])
        dp_kelime = col1.text_input("Makale Ara:", placeholder="Örn: Milli Mücadele...")
        dp_btn = col2.form_submit_button("🚀 Ara")

    if 'dp_results' not in st.session_state:
        st.session_state.dp_results = []
    
    if 'dergipark_cache' not in st.session_state:
        st.session_state.dergipark_cache = {}

    if dp_btn and dp_kelime:
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
                    if unique_key not in st.session_state.dergipark_cache:
                        if st.button("📥 PDF Hazırla (ZenRows)", key=f"btn_{unique_key}"):
                            pdf_data = fetch_pdf_with_zenrows(makale['link'])
                            if pdf_data:
                                st.session_state.dergipark_cache[unique_key] = pdf_data
                                st.rerun()
                    else:
                        clean_name = re.sub(r'[\\/*?:"<>|]', "", makale['title'])[:30] + ".pdf"
                        st.download_button("💾 PDF İNDİR", st.session_state.dergipark_cache[unique_key], clean_name, "application/pdf", key=f"dl_{unique_key}", type="primary")

                with col_b:
                    st.markdown(f"👉 **[Siteye Git]({makale['link']})**")
    elif dp_btn:
        st.warning("Sonuç bulunamadı.")
