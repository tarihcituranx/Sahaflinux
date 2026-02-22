"""
Kamu Personel Alım İlanları — Streamlit Cloud + Supabase
─────────────────────────────────────────────────────────
Mimari:
  • Supabase PostgreSQL  → ilan metadata + sayfa içerikleri + AI özetleri
  • Supabase Storage     → PDF dosyaları (kalıcı)
  • Streamlit Cloud      → UI (durumsuz, yeniden başlayabilir)

Akış:
  1. Site çekilir → DB ile karşılaştırılır
  2. Yeni ilan   → detay sayfası + PDF indirilir → DB + Storage'a kaydedilir
  3. Kaldırılan  → DB'den silinir (CASCADE → PDF'ler de silinir)
  4. Arama       → DB'de ILIKE (siteye istek atılmaz)
  5. AI özet     → DB'de varsa döner, yoksa Groq'a gider → DB'ye kaydedilir
"""

import io
import re
import time
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from urllib.parse import urljoin, unquote

import requests
import urllib3
import streamlit as st
from bs4 import BeautifulSoup
from groq import Groq
from supabase import create_client, Client

try:
    import PyPDF2
    PDF_DESTEKLI = True
except ImportError:
    PDF_DESTEKLI = False

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ─────────────────────────────────────────────────────────────
# AYARLAR
# ─────────────────────────────────────────────────────────────
ANASAYFA_URL      = "https://kamuilan.sbb.gov.tr/"
BASE_URL          = "https://kamuilan.sbb.gov.tr/"
GROQ_MODEL        = "llama-3.3-70b-versatile"
RATE_LIMIT_SANIYE = 4
TZ_TURKIYE        = timezone(timedelta(hours=3))
STORAGE_BUCKET    = "pdf-dosyalari"

HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language"   : "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding"   : "gzip, deflate, br",
    "Connection"        : "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest"    : "document",
    "Sec-Fetch-Mode"    : "navigate",
    "Sec-Fetch-Site"    : "none",
    "Sec-Fetch-User"    : "?1",
    "Cache-Control"     : "max-age=0",
}

def http_get(url: str, max_deneme: int = 3) -> requests.Response:
    """
    Önce API Ninjas scraper ile dener (devlet sitesi engelini aşar).
    PDF URL'leri için (binary içerik) doğrudan requests kullanır.
    """
    import json as _json

    try:
        api_ninjas_key = st.secrets["API_NINJAS_KEY"]
    except Exception:
        api_ninjas_key = ""
    is_pdf = url.lower().endswith(".pdf") or "getfile" in url.lower()

    # API Ninjas ile dene (HTML sayfaları için)
    if api_ninjas_key and not is_pdf:
        for deneme in range(max_deneme):
            try:
                ninja_r = requests.get(
                    "https://api.api-ninjas.com/v1/webscraper",
                    headers={"X-Api-Key": api_ninjas_key},
                    params={"url": url},
                    timeout=45,
                )
                if ninja_r.status_code == 200:
                    html = ninja_r.text
                    class FakeResponse:
                        def __init__(self, raw: str):
                            self.text        = raw
                            self.content     = raw.encode("utf-8", errors="replace")
                            self.status_code = 200
                            self._h          = {"Content-Type": "text/html; charset=utf-8"}
                        def raise_for_status(self): pass
                        @property
                        def headers(self): return self._h
                    return FakeResponse(html)
                elif ninja_r.status_code == 429:
                    time.sleep(5 * (deneme + 1))
                    continue
                else:
                    # API Ninjas hatasını göster
                    st.warning(f"API Ninjas {ninja_r.status_code}: {ninja_r.text[:200]}")
                    break
            except Exception as ninja_ex:
                st.warning(f"API Ninjas bağlantı hatası: {ninja_ex}")
                if deneme == max_deneme - 1:
                    break
                time.sleep(2)

    # Fallback: doğrudan istek (PDF veya key yoksa)
    session = requests.Session()
    session.headers.update(HTTP_HEADERS)
    for deneme in range(max_deneme):
        try:
            r = session.get(url, verify=False, timeout=20)
            if r.status_code in (403, 429):
                time.sleep(3 * (deneme + 1))
                continue
            r.raise_for_status()
            return r
        except Exception:
            if deneme == max_deneme - 1:
                raise
            time.sleep(2)

    raise requests.exceptions.ConnectionError(f"Bağlantı kurulamadı: {url}")

MESLEK_KATEGORILERI = {
    "👷 Teknik / Mühendis": [
        "mühendis","muhendis","tekniker","teknisyen","teknik","mimar",
        "bilişim","yazılım","elektrik","elektronik","makine","inşaat",
        "harita","jeoloji","jeofizik","çevre","kimya","metalurji",
    ],
    "💼 İdari / Mali": [
        "memur","uzman","şef","müdür","mudur","idari","mali","muhasebe",
        "hukuk","avukat","ekonomist","istatistik","araştırmacı","analist",
        "sekreter","büro","danışman","denetmen","kontrolör",
    ],
    "👮 Güvenlik / Askerlik": [
        "güvenlik","guvenlik","koruma","bekçi","bekci","komiser","subay",
        "astsubay","erbaş","er ","asker","jandarma","polis","itfaiye",
        "sivil savunma",
    ],
    "🏥 Sağlık": [
        "doktor","hekim","hemşire","hemsire","eczacı","eczaci","sağlık",
        "saglik","psikolog","fizyoterapist","laborant","röntgen","diş",
        "veteriner","biyolog","anestezi","radyoloji","kardiyoloji",
        "nöroloji","onkoloji","ortopedi","pediatri","dahiliye",
    ],
    "🎓 Eğitim / Akademik": [
        "öğretmen","ogretmen","eğitim","egitim","akademik","öğretim",
        "ogretim","pedagog","rehber","koordinatör",
    ],
    "🔧 İşçi / Usta": [
        "işçi","isci","usta","şoför","sofor","sürücü","forklift",
        "kaynakçı","tesisatçı","boyacı","marangoz","aşçı","asci",
        "temizlik","bahçıvan","yardımcı",
    ],
    "📊 Diğer": [],
}

# ─────────────────────────────────────────────────────────────
# SUPABASE BAĞLANTISI
# ─────────────────────────────────────────────────────────────
@st.cache_resource
def supabase_baglan() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


def sb() -> Client:
    return supabase_baglan()


# ─────────────────────────────────────────────────────────────
# YARDIMCI FONKSİYONLAR
# ─────────────────────────────────────────────────────────────
def normalize(m: str) -> str:
    return (m.lower()
            .replace("ı","i").replace("ğ","g").replace("ü","u")
            .replace("ş","s").replace("ö","o").replace("ç","c")
            .replace("İ","i").replace("Ğ","g").replace("Ü","u")
            .replace("Ş","s").replace("Ö","o").replace("Ç","c"))


def simdi_tr() -> datetime:
    return datetime.now(TZ_TURKIYE)


def meslek_kategori_bul(metin: str) -> str:
    n = normalize(metin)
    for kat, kelimeler in MESLEK_KATEGORILERI.items():
        if kat == "📊 Diğer":
            continue
        for k in kelimeler:
            if k in n:
                return kat
    return "📊 Diğer"


def durum_bul(metin: str) -> str:
    u = metin.upper()
    if "İPTAL" in u or "IPTAL" in u:
        return "iptal"
    if "UZATILDI" in u:
        return "uzatildi"
    return "aktif"


def durum_badge(durum: str) -> str:
    return {
        "aktif"   : "🟢 Aktif",
        "uzatildi": "🟡 Uzatıldı",
        "iptal"   : "🔴 İptal",
    }.get(durum, "")


# ─────────────────────────────────────────────────────────────
# VERİTABANI — OKUMA
# ─────────────────────────────────────────────────────────────
def db_ilanlar_getir(sadece_aktif: bool = False) -> list[dict]:
    """Tüm ilanları (veya sadece aktif olanları) DB'den çeker."""
    q = sb().table("ilanlar").select(
        "kod,kurum,baslik,tam_metin,basvuru_tarihi,link,durum,kategori,"
        "sayfa_icerigi,ai_ozet,eklenme_tarihi"
    )
    if sadece_aktif:
        q = q.eq("durum", "aktif")
    sonuc = q.order("eklenme_tarihi", desc=True).execute()
    return sonuc.data or []


def db_pdf_getir(ilan_kod: str) -> list[dict]:
    sonuc = sb().table("pdf_dosyalari").select(
        "id,ad,url,icerik,storage_path"
    ).eq("ilan_kod", ilan_kod).execute()
    return sonuc.data or []


def db_ilan_var_mi(kod: str) -> bool:
    sonuc = sb().table("ilanlar").select("kod").eq("kod", kod).execute()
    return bool(sonuc.data)


# ─────────────────────────────────────────────────────────────
# VERİTABANI — YAZMA
# ─────────────────────────────────────────────────────────────
def db_ilan_ekle(ilan: dict, sayfa_icerigi: str = ""):
    """Yeni ilanı DB'ye ekler."""
    sb().table("ilanlar").upsert({
        "kod"            : ilan["kod"],
        "kurum"          : ilan.get("kurum",""),
        "baslik"         : ilan.get("baslik",""),
        "tam_metin"      : ilan.get("tam_metin",""),
        "basvuru_tarihi" : ilan.get("basvuru_tarihi",""),
        "link"           : ilan.get("link",""),
        "durum"          : ilan.get("durum","aktif"),
        "kategori"       : ilan.get("kategori","📊 Diğer"),
        "sayfa_icerigi"  : sayfa_icerigi,
        "ai_ozet"        : None,
    }).execute()


def db_durum_guncelle(kod: str, yeni_durum: str):
    sb().table("ilanlar").update({"durum": yeni_durum}).eq("kod", kod).execute()


def db_ai_ozet_kaydet(kod: str, ozet: str):
    sb().table("ilanlar").update({"ai_ozet": ozet}).eq("kod", kod).execute()


def db_ilan_sil(kod: str):
    """İlanı ve CASCADE ile bağlı PDF kayıtlarını siler."""
    # Önce Storage'daki PDF dosyalarını sil
    pdf_kayitlari = db_pdf_getir(kod)
    for pdf in pdf_kayitlari:
        if pdf.get("storage_path"):
            try:
                sb().storage.from_(STORAGE_BUCKET).remove([pdf["storage_path"]])
            except Exception:
                pass
    # DB kaydını sil (CASCADE → pdf_dosyalari da silinir)
    sb().table("ilanlar").delete().eq("kod", kod).execute()


def db_pdf_ekle(ilan_kod: str, ad: str, url: str, icerik: str, storage_path: str = ""):
    sb().table("pdf_dosyalari").insert({
        "ilan_kod"    : ilan_kod,
        "ad"          : ad,
        "url"         : url,
        "icerik"      : icerik,
        "storage_path": storage_path,
    }).execute()


# ─────────────────────────────────────────────────────────────
# STORAGE — PDF YÜKLEME / İNDİRME
# ─────────────────────────────────────────────────────────────
def storage_pdf_yukle(pdf_bytes: bytes, storage_path: str) -> bool:
    """PDF bytes'ını Supabase Storage'a yükler."""
    try:
        sb().storage.from_(STORAGE_BUCKET).upload(
            path=storage_path,
            file=pdf_bytes,
            file_options={"content-type": "application/pdf", "upsert": "true"},
        )
        return True
    except Exception as e:
        st.warning(f"Storage yükleme hatası: {e}")
        return False


def storage_pdf_signed_url(storage_path: str, sure_sn: int = 3600) -> str:
    """Storage'daki PDF için geçici indirme linki üretir."""
    try:
        sonuc = sb().storage.from_(STORAGE_BUCKET).create_signed_url(
            storage_path, sure_sn
        )
        return sonuc.get("signedURL","")
    except Exception:
        return ""


# ─────────────────────────────────────────────────────────────
# PDF OKUMA (bytes → metin)
# ─────────────────────────────────────────────────────────────
def pdf_bytes_oku(pdf_bytes: bytes, max_char: int = 5000) -> str:
    if not PDF_DESTEKLI or not pdf_bytes:
        return ""
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        metin  = "".join(sayfa.extract_text() or "" for sayfa in reader.pages[:8])
        return metin[:max_char].strip()
    except Exception:
        return ""


def pdf_url_indir(url: str) -> bytes:
    """URL'den PDF bytes indirir."""
    try:
        r  = http_get(url)
        ct = r.headers.get("Content-Type","")
        if "pdf" in ct.lower() or url.lower().endswith(".pdf"):
            return r.content
    except Exception:
        pass
    return b""


# ─────────────────────────────────────────────────────────────
# DETAY SAYFASI ÇEKME + PDF İŞLEME
# ─────────────────────────────────────────────────────────────
def ilan_detay_isle(ilan: dict) -> tuple[str, list[dict]]:
    """
    İlan detay sayfasını açar, PDF'leri indirir, Storage'a yükler,
    DB'ye kaydeder.
    Döner: (sayfa_metni, pdf_listesi)
    """
    url = ilan["link"]
    kod = ilan["kod"]

    try:
        r  = http_get(url)
        ct = r.headers.get("Content-Type","")

        # Doğrudan PDF
        if "pdf" in ct.lower():
            pdf_bytes  = r.content
            pdf_metni  = pdf_bytes_oku(pdf_bytes)
            s_path     = f"{kod}/ilan.pdf"
            storage_pdf_yukle(pdf_bytes, s_path)
            db_pdf_ekle(kod, "İlan PDF", url, pdf_metni, s_path)
            return pdf_metni, [{"ad":"İlan PDF","url":url,"icerik":pdf_metni,"storage_path":s_path}]

        # HTML sayfası
        soup = BeautifulSoup(r.text, "html.parser")

        # PDF linklerini topla
        pdf_listesi = []
        gorulen     = set()

        for a in soup.find_all("a", href=True):
            href = a["href"]
            hl   = href.lower()
            if not (hl.endswith(".pdf") or any(x in hl for x in ["getfile","download","dosya"])):
                continue
            tam = urljoin(url, href)
            if tam in gorulen:
                continue
            gorulen.add(tam)
            ad        = a.get_text(strip=True) or href.split("/")[-1]
            pdf_bytes  = pdf_url_indir(tam)
            pdf_metni  = pdf_bytes_oku(pdf_bytes)
            s_path     = f"{kod}/{ad[:80].replace('/','-')}.pdf"
            if pdf_bytes:
                storage_pdf_yukle(pdf_bytes, s_path)
                db_pdf_ekle(kod, ad, tam, pdf_metni, s_path)
            else:
                db_pdf_ekle(kod, ad, tam, pdf_metni, "")
            pdf_listesi.append({"ad":ad,"url":tam,"icerik":pdf_metni,"storage_path":s_path})

        # Iframe / embed PDF
        for embed in soup.find_all(["iframe","embed"], src=True):
            src = embed["src"]
            if ".pdf" not in src.lower():
                continue
            tam = urljoin(url, src)
            if tam in gorulen:
                continue
            gorulen.add(tam)
            pdf_bytes = pdf_url_indir(tam)
            pdf_metni = pdf_bytes_oku(pdf_bytes)
            s_path    = f"{kod}/embed.pdf"
            if pdf_bytes:
                storage_pdf_yukle(pdf_bytes, s_path)
            db_pdf_ekle(kod, "Gömülü PDF", tam, pdf_metni, s_path if pdf_bytes else "")
            pdf_listesi.append({"ad":"Gömülü PDF","url":tam,"icerik":pdf_metni})

        # Sayfa düz metni
        for tag in soup(["script","style","nav","header","footer"]):
            tag.decompose()
        satirlar   = [s for s in soup.get_text("\n", strip=True).splitlines() if s.strip()]
        sayfa_metni = "\n".join(satirlar[:500])

        return sayfa_metni, pdf_listesi

    except Exception as e:
        return f"Detay alınamadı: {e}", []


# ─────────────────────────────────────────────────────────────
# SITE ÇEKME + DB SENKRONIZASYONU
# ─────────────────────────────────────────────────────────────
def site_ilanlarini_cek() -> list[dict]:
    """Ana sayfadaki ilan listesini çeker (hafif istek)."""
    try:
        r = http_get(ANASAYFA_URL)
    except Exception as e:
        st.error(f"Site çekilemedi: {e}")
        return []

    soup    = BeautifulSoup(r.text, "html.parser")
    ilanlar = []
    gorulen = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "ilanDetay.aspx?kod=" not in href:
            continue
        raw_kod = href.split("kod=")[1]
        kod     = unquote(raw_kod)
        if kod in gorulen:
            continue
        gorulen.add(kod)

        metin = a.get_text(strip=True)
        if not metin:
            continue

        link    = urljoin(BASE_URL, href)
        basvuru = ""
        m       = re.search(r"\(([^)]+)\)", metin)
        if m:
            basvuru = m.group(1).strip()
            metin   = metin[:m.start()].strip()

        satirlar = [s.strip() for s in metin.split("\n") if s.strip()]
        if len(satirlar) >= 2:
            kurum  = satirlar[0]
            baslik = " ".join(satirlar[1:])
        else:
            parcalar = re.split(r"\s{2,}", metin, maxsplit=1)
            kurum, baslik = (parcalar[0], parcalar[1]) if len(parcalar) == 2 else ("", metin)

        ilanlar.append({
            "kod"           : kod,
            "kurum"         : kurum.strip(),
            "baslik"        : baslik.strip() or metin,
            "tam_metin"     : metin,
            "basvuru_tarihi": basvuru,
            "link"          : link,
            "durum"         : durum_bul(metin),
            "kategori"      : meslek_kategori_bul(metin),
        })

    return ilanlar


def db_senkronize_et(goster_ilerleme: bool = True) -> dict:
    """
    Site listesi ile DB'yi karşılaştırır:
      - Yeni ilan   → detay + PDF indir → DB'ye ekle
      - Durum değişti → DB'yi güncelle
      - Siteden kalktı → DB'den sil (süresi doldu)
    Döner: {"yeni": [...], "degisen": [...], "silinen": [...]}
    """
    if goster_ilerleme:
        spinner = st.spinner("🔄 Site kontrol ediliyor...")
        spinner.__enter__()

    site_listesi = site_ilanlarini_cek()
    if not site_listesi:
        if goster_ilerleme:
            spinner.__exit__(None, None, None)
        return {"yeni": [], "degisen": [], "silinen": []}

    site_dict = {d["kod"]: d for d in site_listesi}
    db_listesi = db_ilanlar_getir()
    db_dict    = {d["kod"]: d for d in db_listesi}

    yeni_ilanlar    = []
    degisen_ilanlar = []
    silinen_ilanlar = []

    # Yeni + durum değişikliği
    toplam_yeni = sum(1 for kod in site_dict if kod not in db_dict)
    islem_sayac = 0

    progress_bar  = st.progress(0, text="DB senkronize ediliyor...") if goster_ilerleme and toplam_yeni > 0 else None
    durum_yazisi  = st.empty() if goster_ilerleme else None

    for kod, site_ilan in site_dict.items():
        if kod not in db_dict:
            # YENİ ILAN — detay sayfası + PDF indir
            islem_sayac += 1
            if durum_yazisi:
                durum_yazisi.caption(f"⬇️ İndiriliyor: {site_ilan.get('kurum','—')} ({islem_sayac}/{toplam_yeni})")
            if progress_bar:
                progress_bar.progress(islem_sayac / max(toplam_yeni, 1))

            sayfa_metni, _ = ilan_detay_isle(site_ilan)
            db_ilan_ekle(site_ilan, sayfa_metni)
            yeni_ilanlar.append(site_ilan)

        else:
            # Mevcut ilan — durum değişti mi?
            db_ilan  = db_dict[kod]
            eski_dur = db_ilan.get("durum","aktif")
            yeni_dur = site_ilan["durum"]
            if eski_dur != yeni_dur:
                db_durum_guncelle(kod, yeni_dur)
                degisen_ilanlar.append((eski_dur, site_ilan))

    # Siteden kalkan ilanları sil
    for kod, db_ilan in db_dict.items():
        if kod not in site_dict:
            db_ilan_sil(kod)
            silinen_ilanlar.append(db_ilan)

    if progress_bar:
        progress_bar.empty()
    if durum_yazisi:
        durum_yazisi.empty()
    if goster_ilerleme:
        try:
            spinner.__exit__(None, None, None)
        except Exception:
            pass

    degisiklikler = {
        "yeni"   : yeni_ilanlar,
        "degisen": degisen_ilanlar,
        "silinen": silinen_ilanlar,
    }
    st.session_state["degisiklikler"]  = degisiklikler
    st.session_state["son_guncelleme"] = simdi_tr()
    return degisiklikler


def veri_yukle() -> list[dict]:
    """
    Session state'te varsa oradan döner.
    Yoksa (ilk açılış / günlük yenileme) senkronizasyon yapar.
    """
    simdi = simdi_tr()
    if "ilanlar_cache" not in st.session_state:
        db_senkronize_et(goster_ilerleme=True)
        st.session_state["ilanlar_cache"] = db_ilanlar_getir()
    else:
        son = st.session_state.get("son_guncelleme")
        if son and son.date() < simdi.date():
            db_senkronize_et(goster_ilerleme=True)
            st.session_state["ilanlar_cache"] = db_ilanlar_getir()
    return st.session_state["ilanlar_cache"]


def veri_yenile():
    """Güncelle butonuna basılınca çağrılır."""
    db_senkronize_et(goster_ilerleme=True)
    st.session_state["ilanlar_cache"] = db_ilanlar_getir()


# ─────────────────────────────────────────────────────────────
# DB ARAMA (siteye istek atmaz!)
# ─────────────────────────────────────────────────────────────
def db_ara(terim: str) -> list[dict]:
    """
    Hem ilanlar tablosunu hem pdf_dosyalari tablosunu ILIKE ile tarar.
    Türkçe normalizasyon uygulanır.
    Döner: ilan dict listesi (DB'den, önbellekli PDF içerikleriyle)
    """
    if not terim.strip():
        return []

    n_terim = f"%{normalize(terim.strip())}%"

    # İlanlarda ara (normalize sütun yok ama Türkçe büyük/küçük için ilike yeterli)
    # PostgreSQL ILIKE büyük/küçük harf duyarsız ama Türkçe karakter için unaccent lazım
    # Çözüm: Python tarafında normalize edip karşılaştırıyoruz
    # Önce hepsini çek, Python'da filtrele (performans için sayfa_icerigi zaten DB'de)
    tum_ilanlar = db_ilanlar_getir(sadece_aktif=True)
    sonuclar    = []

    for ilan in tum_ilanlar:
        # İlan metni + sayfa içeriğinde ara
        hedef = normalize(
            ilan.get("tam_metin","") + " " +
            ilan.get("sayfa_icerigi","") + " " +
            ilan.get("kurum","")
        )
        if normalize(terim.strip()) in hedef:
            # PDF içeriklerini de ekle
            pdf_kayitlari = db_pdf_getir(ilan["kod"])
            pdf_hedef     = " ".join(normalize(p.get("icerik","")) for p in pdf_kayitlari)
            ilan["_pdf_kayitlari"] = pdf_kayitlari

            if normalize(terim.strip()) in hedef or normalize(terim.strip()) in pdf_hedef:
                sonuclar.append(ilan)

    # PDF içeriklerinde ayrıca ara (ilan metninde geçmeyebilir)
    bulunan_kodlar = {d["kod"] for d in sonuclar}
    for ilan in tum_ilanlar:
        if ilan["kod"] in bulunan_kodlar:
            continue
        pdf_kayitlari = db_pdf_getir(ilan["kod"])
        pdf_hedef     = " ".join(normalize(p.get("icerik","")) for p in pdf_kayitlari)
        if normalize(terim.strip()) in pdf_hedef:
            ilan["_pdf_kayitlari"] = pdf_kayitlari
            sonuclar.append(ilan)

    return sonuclar


# ─────────────────────────────────────────────────────────────
# GROQ AI
# ─────────────────────────────────────────────────────────────
GROQ_SISTEM = """Sen Türkiye kamu personel alım ilanlarını analiz eden ve sıradan vatandaşlara anlatan bir uzmansın.

AMAÇ: Kullanıcı bu ilanın kendisi için uygun olup olmadığını, ne yapması gerektiğini ve son başvuru tarihini hemen anlasın.

YAZIM KURALLARI:
- Teknik bürokrasi dili kullanma. "Müracaat" yerine "başvur", "istihdam" yerine "iş al", "nitelik" yerine "şart" de.
- Her maddeyi ayrı satıra yaz, madde madde listele.
- Sayıları büyük vurgula: "5 KİŞİ alınacak".
- Tarihler varsa MUTLAKA yaz. Atlarsan eksik olur.
- Eğer bilgi metinde yoksa o başlığı hiç yazma. Asla uydurma.
- Türkçe yaz.

ÇIKTI FORMATI:

---
### 🏛️ [KURUM ADI]

**Ne iş bu?**
[1-2 cümle, çok sade.]

**📌 Kaç kişi, hangi pozisyon?**
[Her kadro ayrı satırda. Örnek:
- Anestezi Teknikeri: 12 kişi
- Laborant: 5 kişi]

**✅ Kimler başvurabilir?**
[Madde madde — eğitim, yaş, KPSS puan türü ve taban puan, tecrübe, branş vb.]

**📋 Hangi belgeler lazım?**
[Numaralı liste. Eksik belge başvuruyu geçersiz kılar — bunu vurgula.]

**📅 Önemli Tarihler**
[Başvuru başlangıcı, son gün, varsa sınav tarihi — HEPSİNİ yaz.]

**📝 Nasıl başvurulur?**
[Online mı, şahsen mi? Hangi siteye/adrese? Net yaz.]

**⚠️ Dikkat!**
[Özel şartlar, sık yapılan hatalar — metinde geçiyorsa yaz.]
---"""


def groq_ozet_al(ilan: dict) -> str:
    """
    Önce DB'de ai_ozet var mı kontrol eder.
    Yoksa Groq'a gider, üretilen özeti DB'ye kaydeder.
    """
    # DB'de cached mi?
    if ilan.get("ai_ozet"):
        return ilan["ai_ozet"]

    bekleme = RATE_LIMIT_SANIYE - (time.time() - st.session_state.get("son_groq_istegi", 0))
    if bekleme > 0:
        time.sleep(bekleme)

    try:
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])

        pdf_kayitlari = ilan.get("_pdf_kayitlari") or db_pdf_getir(ilan["kod"])
        pdf_ek        = ""
        if pdf_kayitlari:
            pdf_ek = "\n\n=== EKLENMIŞ PDF İÇERİKLERİ ===\n"
            for p in pdf_kayitlari:
                if p.get("icerik"):
                    pdf_ek += f"\n[Belge: {p['ad']}]\n{p['icerik'][:2000]}\n"

        kullanici_mesaji = (
            f"Kurum: {ilan.get('kurum','Bilinmiyor')}\n"
            f"İlan başlığı: {ilan.get('tam_metin','')}\n"
            f"Başvuru tarihi: {ilan.get('basvuru_tarihi','Belirtilmemiş')}\n"
            f"İlan linki: {ilan.get('link','')}\n\n"
            f"=== SAYFA İÇERİĞİ ===\n"
            f"{ilan.get('sayfa_icerigi','')[:3000]}"
            f"{pdf_ek}"
        )

        yanit = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": GROQ_SISTEM},
                {"role": "user",   "content": kullanici_mesaji},
            ],
            temperature=0.05,
            max_tokens=3000,
        )
        st.session_state["son_groq_istegi"] = time.time()
        ozet = yanit.choices[0].message.content

        # DB'ye kaydet — bir daha Groq'a gitmesin
        db_ai_ozet_kaydet(ilan["kod"], ozet)
        # Lokal cache'i de güncelle
        ilan["ai_ozet"] = ozet
        return ozet

    except Exception as e:
        hata = str(e)
        if "rate_limit" in hata.lower():
            return "⏳ API rate limit aşıldı — birkaç saniye bekleyip tekrar deneyin."
        return f"❌ AI hatası: {hata}"


# ─────────────────────────────────────────────────────────────
# FAVORİLER
# ─────────────────────────────────────────────────────────────
def favori_toggle(kod: str):
    favs = st.session_state.setdefault("kamu_favoriler", set())
    favs.discard(kod) if kod in favs else favs.add(kod)


def favori_mi(kod: str) -> bool:
    return kod in st.session_state.get("kamu_favoriler", set())


# ─────────────────────────────────────────────────────────────
# FİLTRELE (başlık bazlı — hızlı)
# ─────────────────────────────────────────────────────────────
def baslik_arama_eslesiyor(arama: str, ilan: dict) -> bool:
    if not arama:
        return True
    hedef     = normalize(ilan.get("tam_metin","") + " " + ilan.get("kurum",""))
    kelimeler = normalize(arama).split()
    return all(k in hedef for k in kelimeler)


def ilan_filtrele(ilanlar: list, filtre: dict) -> list:
    sonuc = ilanlar
    if filtre["sadece_favori"]:
        favs  = st.session_state.get("kamu_favoriler", set())
        sonuc = [d for d in sonuc if d["kod"] in favs]
    if filtre["durum"] != "Tümü":
        durum_map = {"🟢 Aktif":"aktif","🟡 Uzatıldı":"uzatildi","🔴 İptal":"iptal"}
        hedef = durum_map.get(filtre["durum"],"aktif")
        sonuc = [d for d in sonuc if d["durum"] == hedef]
    if filtre["kategori"] != "Tümü":
        sonuc = [d for d in sonuc if d["kategori"] == filtre["kategori"]]
    if filtre["arama"]:
        sonuc = [d for d in sonuc if baslik_arama_eslesiyor(filtre["arama"], d)]
    return sonuc


# ─────────────────────────────────────────────────────────────
# DEĞİŞİKLİK PANELİ
# ─────────────────────────────────────────────────────────────
def degisiklik_paneli_goster():
    degisiklikler = st.session_state.get("degisiklikler")
    if not degisiklikler:
        return
    yeni    = degisiklikler.get("yeni", [])
    degisen = degisiklikler.get("degisen", [])
    silinen = degisiklikler.get("silinen", [])
    toplam  = len(yeni) + len(degisen) + len(silinen)
    if toplam == 0:
        return

    with st.expander(f"🔔 {toplam} Değişiklik Tespit Edildi", expanded=True):
        if yeni:
            st.markdown(f"### 🆕 Yeni İlanlar — {len(yeni)}")
            for d in yeni:
                st.success(
                    f"**{d.get('kurum','—')}**  \n"
                    f"{d.get('kategori','')} {d.get('baslik','')}  \n"
                    f"[İlana Git →]({d['link']})"
                )
        if degisen:
            st.markdown(f"### 🔄 Durumu Değişen — {len(degisen)}")
            for eski_dur, d in degisen:
                st.warning(
                    f"**{d.get('kurum','—')}** — {d.get('baslik','')}  \n"
                    f"{durum_badge(eski_dur)} → {durum_badge(d['durum'])}  \n"
                    f"[İlana Git →]({d['link']})"
                )
        if silinen:
            st.markdown(f"### 🗑️ Süresi Dolup Silinen — {len(silinen)}")
            for d in silinen:
                st.error(
                    f"**{d.get('kurum','—')}** — {d.get('baslik','')}  \n"
                    f"_DB'den ve Storage'dan silindi_"
                )


# ─────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────
CSS = """
<style>
.kamu-kart {
    background: #131620;
    border-left: 4px solid #7c3aed;
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 4px;
}
.kamu-kart-eslesme {
    background: #131620;
    border-left: 4px solid #059669;
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 4px;
}
.kamu-baslik { font-size:15px; font-weight:600; color:#e8eaf0; line-height:1.4; margin-bottom:3px; }
.kamu-kurum  { font-size:12px; font-weight:700; color:#a78bfa; letter-spacing:0.5px; text-transform:uppercase; margin-bottom:3px; }
.kamu-meta   { font-size:12px; color:#9aa0b4; }
.kamu-tarih  { color:#f59e0b; font-weight:500; }
.kamu-durum-aktif    { color:#22c55e; font-weight:600; }
.kamu-durum-uzatildi { color:#eab308; font-weight:600; }
.kamu-durum-iptal    { color:#ef4444; font-weight:600; }
.derin-arama-kutu {
    background: #0d1117;
    border: 1px solid #238636;
    border-radius: 10px;
    padding: 18px 20px;
    margin-bottom: 16px;
}
.arama-ipucu { font-size:11px; color:#6b7280; margin-top:2px; }
</style>
"""


# ─────────────────────────────────────────────────────────────
# KART
# ─────────────────────────────────────────────────────────────
def ilan_karti_goster(d: dict, idx, eslesme: bool = False):
    fav_ikon  = "⭐" if favori_mi(d["kod"]) else "☆"
    durum_css = {
        "aktif"   :"kamu-durum-aktif",
        "uzatildi":"kamu-durum-uzatildi",
        "iptal"   :"kamu-durum-iptal",
    }.get(d["durum"],"")
    kart_cls  = "kamu-kart-eslesme" if eslesme else "kamu-kart"

    st.markdown(f"""
    <div class="{kart_cls}">
        <div class="kamu-kurum">{d.get('kurum') or '—'}</div>
        <div class="kamu-baslik">{d.get('kategori','')} &nbsp; {d.get('baslik') or d.get('tam_metin','')}</div>
        <div class="kamu-meta">
            <span class="{durum_css}">{durum_badge(d['durum'])}</span>
            {"&nbsp;·&nbsp;<span class='kamu-tarih'>📅 " + d['basvuru_tarihi'] + "</span>"
              if d.get('basvuru_tarihi') else ""}
        </div>
    </div>
    """, unsafe_allow_html=True)

    anahtar = f"ki_ozet_{idx}"
    pdf_key = f"ki_pdf_{idx}"
    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        st.link_button("🔗 İlana Git", url=d["link"], use_container_width=True)

    with col2:
        # DB'de önceden özet varsa "önbellekten göster" yaz
        onceden_var = bool(d.get("ai_ozet"))
        btn_label   = "📄 Özeti Göster" if onceden_var else "🤖 AI Özet Al"

        if st.button(btn_label, key=f"ki_btn_{idx}", use_container_width=True):
            if anahtar in st.session_state:
                # Toggle — gizle
                st.session_state.pop(anahtar, None)
                st.session_state.pop(pdf_key, None)
                st.rerun()
            else:
                with st.spinner("🤖 Özet hazırlanıyor..." if not onceden_var else ""):
                    ozet = groq_ozet_al(d)
                    st.session_state[anahtar] = ozet
                    # PDF listesi
                    pdf_kayitlari = d.get("_pdf_kayitlari") or db_pdf_getir(d["kod"])
                    st.session_state[pdf_key] = pdf_kayitlari

    with col3:
        if st.button(f"{fav_ikon} Favori", key=f"ki_fav_{idx}", use_container_width=True):
            favori_toggle(d["kod"])
            st.rerun()

    # Özet paneli
    if anahtar in st.session_state:
        with st.expander("📄 İlan Özeti", expanded=True):
            st.markdown(st.session_state[anahtar])

        pdf_kayitlari = st.session_state.get(pdf_key, [])
        if pdf_kayitlari:
            st.markdown("**📎 Ekli Belgeler:**")
            for pdf in pdf_kayitlari:
                ca, cb = st.columns([4, 1])
                with ca:
                    st.markdown(
                        f"<div style='font-size:14px;padding:4px 0'>📄 {pdf.get('ad','Belge')}</div>",
                        unsafe_allow_html=True,
                    )
                with cb:
                    # Storage'dan signed URL al, yoksa orijinal URL
                    dl_url = pdf.get("url","")
                    if pdf.get("storage_path"):
                        signed = storage_pdf_signed_url(pdf["storage_path"])
                        if signed:
                            dl_url = signed
                    if dl_url:
                        st.link_button("⬇️ İndir", url=dl_url, use_container_width=True)

        if st.button("✖️ Kapat", key=f"ki_kapat_{idx}"):
            st.session_state.pop(anahtar, None)
            st.session_state.pop(pdf_key, None)
            st.rerun()

    st.divider()


# ─────────────────────────────────────────────────────────────
# DERİN ARAMA UI
# ─────────────────────────────────────────────────────────────
def derin_arama_bolumu(ilanlar: list):
    st.markdown("""
    <div class="derin-arama-kutu">
        <h3 style="color:#34d399;margin-top:0">🔬 Derin Arama — DB'de Tara</h3>
        <p style="color:#9aa0b4;font-size:13px;margin-bottom:0">
        İndirilen tüm ilan metinleri ve PDF içeriklerini arar.<br>
        <b>Siteye istek atmaz</b> — anlık sonuç verir.<br>
        Örnek: <i>anestezi · kardiyoloji · gaziantep · 657 · bilgisayar operatörü</i>
        </p>
    </div>
    """, unsafe_allow_html=True)

    col_a, col_b = st.columns([4, 1])
    with col_a:
        terim = st.text_input(
            "Derin arama terimi:",
            placeholder="örn: anestezi  /  ortopedi  /  erzurum",
            key="derin_arama_terim",
            label_visibility="collapsed",
        )
    with col_b:
        ara_btn = st.button("🔍 Ara", use_container_width=True, key="derin_ara_btn")

    aktif_sayisi = sum(1 for d in ilanlar if d["durum"]=="aktif")
    st.caption(
        f"ℹ️ DB'de {aktif_sayisi} aktif ilan var. "
        "Arama siteye istek atmaz, tüm metin yerel olarak taranır."
    )

    if ara_btn and terim.strip():
        with st.spinner(f"🔍 DB'de '{terim}' aranıyor..."):
            sonuclar = db_ara(terim.strip())
        st.session_state["derin_arama_sonuc"]     = sonuclar
        st.session_state["derin_arama_son_terim"] = terim.strip()

    sonuclar  = st.session_state.get("derin_arama_sonuc")
    son_terim = st.session_state.get("derin_arama_son_terim","")

    if sonuclar is None or not son_terim:
        return

    if not sonuclar:
        st.info(f"'{son_terim}' için hiçbir ilanda eşleşme bulunamadı.")
        return

    st.success(f"✅ **{len(sonuclar)} ilan** bulundu — '{son_terim}'")

    # Hepsini özetle butonu
    ozetsiz_var = any(not d.get("ai_ozet") for d in sonuclar)
    if ozetsiz_var:
        if st.button(
            f"🤖 {len(sonuclar)} İlanı AI ile Özetle",
            key="derin_ozet_hepsi",
            type="primary",
        ):
            prog = st.progress(0, text="🤖 AI özetleniyor...")
            for i, d in enumerate(sonuclar):
                if not d.get("ai_ozet"):
                    ozet = groq_ozet_al(d)
                    d["ai_ozet"] = ozet
                prog.progress((i+1)/len(sonuclar), text=f"Özetleniyor {i+1}/{len(sonuclar)}...")
            prog.empty()
            st.rerun()

    st.markdown("---")
    for i, d in enumerate(sonuclar):
        ilan_karti_goster(d, idx=f"derin_{i}", eslesme=True)


# ─────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────
def sidebar_filtre() -> dict:
    st.sidebar.title("📋 Kamu Personel\nAlım İlanları")
    st.sidebar.markdown("---")

    st.sidebar.subheader("🔴 Durum")
    durum = st.sidebar.radio(
        "Durum:", ["Tümü","🟢 Aktif","🟡 Uzatıldı","🔴 İptal"],
        index=1, key="ki_durum",
    )

    st.sidebar.markdown("---")
    st.sidebar.subheader("👔 Meslek")
    kategori = st.sidebar.selectbox(
        "Kategori:",
        ["Tümü"] + list(MESLEK_KATEGORILERI.keys()),
        key="ki_kategori",
    )

    st.sidebar.markdown("---")
    st.sidebar.subheader("🔤 Hızlı Arama")
    arama = st.sidebar.text_input(
        "Başlıkta ara:",
        placeholder="örn: sahil, hemşire",
        key="ki_arama",
    )
    st.sidebar.markdown(
        "<div class='arama-ipucu'>💡 Sadece ilan başlıklarında arar. "
        "İlan içinde aramak için <b>Derin Arama</b>'yı kullan.</div>",
        unsafe_allow_html=True,
    )

    st.sidebar.markdown("---")
    sadece_favori = st.sidebar.checkbox(
        f"⭐ Sadece Favoriler ({len(st.session_state.get('kamu_favoriler', set()))})",
        key="ki_favori",
    )

    st.sidebar.markdown("---")
    st.sidebar.subheader("🗄️ Veritabanı")
    try:
        toplam_db = sb().table("ilanlar").select("kod", count="exact").execute()
        pdf_db    = sb().table("pdf_dosyalari").select("id", count="exact").execute()
        st.sidebar.caption(
            f"📊 **{toplam_db.count}** ilan kayıtlı  \n"
            f"📄 **{pdf_db.count}** PDF belgesi  \n"
            f"☁️ Supabase Storage"
        )
    except Exception:
        st.sidebar.caption("DB bilgisi alınamadı")

    st.sidebar.markdown("---")
    with st.sidebar.expander("📖 Nasıl Çalışır?", expanded=False):
        st.sidebar.markdown("""
**Veri Akışı:**
1. İlanlar siteden çekilir
2. Yeniler detaylarıyla Supabase'e kaydedilir
3. Süresi dolanlar otomatik silinir
4. Arama artık **siteye istek atmaz** — DB'de arar

---
**🔬 Derin Arama**
İlan başlıklarında görünmeyen terimleri bulur.
Tüm PDF içerikleri de taranır.
Siteye istek atmaz → anında sonuç.

---
**🤖 AI Özet**
DB'de kayıtlı sayfa + PDF içeriklerini okur.
Üretilen özet DB'ye kaydedilir → bir daha Groq'a gitmez.

---
**🗑️ Otomatik Temizlik**
Siteden kalkan ilan → DB + Storage'dan silinir.
        """)

    return {
        "durum"        : durum,
        "kategori"     : kategori,
        "arama"        : arama.strip(),
        "sadece_favori": sadece_favori,
    }


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────
def main():
    st.set_page_config(
        page_title="Kamu Personel Alım İlanları",
        page_icon="📋",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(CSS, unsafe_allow_html=True)

    for k, v in [("son_groq_istegi",0), ("kamu_favoriler",set())]:
        if k not in st.session_state:
            st.session_state[k] = v

    if not PDF_DESTEKLI:
        st.info("ℹ️ PDF içerikleri için `PyPDF2` gerekli — requirements.txt'e ekle.")

    # ── Başlık ──
    col_b, col_btn = st.columns([5, 1])
    with col_b:
        st.title("📋 Kamu Personeli Alım İlanları")
    with col_btn:
        st.write("")
        if st.button("🔄 Güncelle", use_container_width=True):
            veri_yenile()
            st.success("Güncellendi!")
            st.rerun()

    ilanlar = veri_yukle()

    son = st.session_state.get("son_guncelleme")
    if son:
        st.caption(
            f"📡 Kaynak: kamuilan.sbb.gov.tr  ·  "
            f"Son güncelleme: {son.strftime('%d.%m.%Y %H:%M')}"
        )

    if not ilanlar:
        st.warning("Henüz ilan yok. 'Güncelle' butonuna tıklayın.")
        return

    # ── Değişiklik paneli ──
    degisiklik_paneli_goster()

    # ── Derin Arama ──
    derin_arama_bolumu(ilanlar)
    st.markdown("---")

    # ── Filtreler ──
    filtre = sidebar_filtre()

    if st.button("🏠 Filtreleri Sıfırla", use_container_width=True):
        for k in ["ki_durum","ki_kategori","ki_arama","ki_favori"]:
            st.session_state.pop(k, None)
        st.rerun()

    filtreli = ilan_filtrele(ilanlar, filtre)

    aktif_sayisi = sum(1 for d in ilanlar if d["durum"]=="aktif")
    c1,c2,c3,c4  = st.columns(4)
    c1.metric("📋 Toplam İlan",  len(ilanlar))
    c2.metric("🟢 Aktif İlan",   aktif_sayisi)
    c3.metric("🔍 Gösterilen",   len(filtreli))
    c4.metric("⭐ Favoriler",    len(st.session_state.get("kamu_favoriler",set())))

    st.markdown("---")

    if not filtreli:
        st.info("Seçilen filtrelere uygun ilan bulunamadı.")
        return

    # ── Favoriler üstte ──
    favs           = st.session_state.get("kamu_favoriler", set())
    favori_ilanlar = [d for d in ilanlar if d["kod"] in favs]
    if favori_ilanlar:
        with st.expander(f"⭐ Favorilerim — {len(favori_ilanlar)} ilan", expanded=True):
            for d in favori_ilanlar:
                ilan_karti_goster(d, hash(d["kod"] + "_fav"))
        st.markdown("---")

    # ── Kategorilere göre grupla veya düz liste ──
    if filtre["kategori"] == "Tümü" and not filtre["arama"] and not filtre["sadece_favori"]:
        gruplar = defaultdict(list)
        for d in filtreli:
            gruplar[d["kategori"]].append(d)
        for kat in MESLEK_KATEGORILERI:
            grup = gruplar.get(kat, [])
            if not grup:
                continue
            with st.expander(f"{kat} — {len(grup)} ilan", expanded=(kat != "📊 Diğer")):
                for d in grup:
                    ilan_karti_goster(d, hash(d["kod"]))
    else:
        with st.expander(f"📋 İlanlar — {len(filtreli)} sonuç", expanded=True):
            for d in filtreli:
                ilan_karti_goster(d, hash(d["kod"]))


if __name__ == "__main__":
    main()
