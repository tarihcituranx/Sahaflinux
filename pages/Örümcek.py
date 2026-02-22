import streamlit as st
from groq import Groq

try:
    from scrapling.fetchers import StealthyFetcher
except ImportError:
    st.error("Lütfen terminalden 'pip install scrapling' komutunu çalıştırın!")
    st.stop()

# ─────────────────────────────────────────────
# AYARLAR & ARAYÜZ
# ─────────────────────────────────────────────
st.set_page_config(page_title="Scrapling to Swagger 🕵️‍♂️", page_icon="🕸️", layout="wide")

st.markdown("""
# 🕸️ Scrapling + Groq: Web to API Analyzer
İstediğin URL'yi ver, **Scrapling** anti-botlara takılmadan siteyi çeksin, **Groq** arka plandaki olası API'leri hayal edip sana mis gibi bir **OpenAPI / Swagger** şeması çıkarsın! 🤣
""")

st.divider()

col1, col2 = st.columns([3, 1])
with col1:
    hedef_url = st.text_input("🎯 Hedef URL:", placeholder="https://example.com")
with col2:
    # Eğer secrets dosyasında yoksa UI'dan alsın
    api_key_input = st.text_input("🔑 Groq API Key:", type="password")

if st.button("🚀 Siteyi Çek ve Swagger Yarat!", use_container_width=True):
    if not hedef_url:
        st.warning("Lütfen bir URL gir!")
        st.stop()

    # 1. ADIM: SCRAPLING İLE SİTEYİ KAZIMA
    with st.spinner("🕵️‍♂️ Scrapling ninja modunda siteyi çekiyor..."):
        try:
            # StealthyFetcher bot korumalarını atlatmada çok başarılıdır
            page = StealthyFetcher.get(hedef_url)
            
            # Formları, endpoint yapılarını görmek için HTML içeriğini alalım
            raw_html = page.html_content
            
            # Groq'un token sınırını aşmamak (ve maliyeti/zamanı kısmak) için HTML'i kırpıyoruz
            MAX_CHAR = 25000
            if len(raw_html) > MAX_CHAR:
                html_snippet = raw_html[:MAX_CHAR] + "\n\n"
            else:
                html_snippet = raw_html
                
            st.success(f"✅ Sayfa başarıyla çekildi! (Toplam karakter: {len(raw_html)})")
            
            with st.expander("Gelen Ham HTML (İlk 1000 Karakter)"):
                st.code(raw_html[:1000], language="html")
                
        except Exception as e:
            st.error(f"❌ Scrapling sayfa çekiminde başarısız oldu: {e}")
            st.stop()

    # 2. ADIM: GROQ İLE ANALİZ VE SWAGGER OLUŞTURMA
    with st.spinner("🧠 Groq HTML'i yutuyor ve varsayımsal Swagger şemasını yazıyor..."):
        try:
            groq_key = api_key_input if api_key_input else st.secrets.get("GROQ_API_KEY", "")
            if not groq_key:
                st.error("Groq API Key bulunamadı!")
                st.stop()

            client = Groq(api_key=groq_key)

            system_prompt = (
                "Sen yetenekli bir API Mimarı ve Tersine Mühendislik uzmanısın. "
                "Sana bir web sayfasının HTML içeriğini vereceğim. Senden şu 3 şeyi istiyorum:\n"
                "1. Sitenin Amacı: Bu sayfa ne işe yarıyor?\n"
                "2. Otomasyon & Endpoint'ler: HTML içindeki formlara, ID'lere ve linklere bakarak arka planda hangi API isteklerinin (GET/POST) yapılıyor olabileceğini tahmin et.\n"
                "3. Swagger (OpenAPI 3.0): Tahmin ettiğin bu yapıya uygun, YAML formatında geçerli bir OpenAPI dokümanı oluştur.\n"
                "Sadece Türkçe konuş ve YAML kodunu ```yaml formunda ver."
            )

            user_prompt = f"Hedef URL: {hedef_url}\n\nİşte sayfanın kodları:\n\n{html_snippet}"

            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.4,
                max_tokens=3000
            )

            st.markdown("### 🎯 Groq'un Çıkardığı Tersine Mühendislik Raporu")
            st.markdown(response.choices[0].message.content)

        except Exception as e:
            st.error(f"❌ Groq API hatası: {e}")
