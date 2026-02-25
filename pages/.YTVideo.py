import streamlit as st
import yt_dlp
import os
import shutil
import platform
import requests
import zipfile
import tarfile
import io
import time

# --- SAYFA YAPILANDIRMASI ---
st.set_page_config(
    page_title="Ultimate YouTube Downloader",
    page_icon="🎬",
    layout="centered"
)

# --- SABİTLER ---
DOWNLOAD_FOLDER = "downloads"
FFMPEG_FOLDER = "ffmpeg_bin"

# Klasörleri oluştur
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)
if not os.path.exists(FFMPEG_FOLDER):
    os.makedirs(FFMPEG_FOLDER)

# --- YARDIMCI FONKSİYONLAR ---

def get_ffmpeg_path():
    """Sistemde veya yerel klasörde FFmpeg var mı kontrol eder."""
    # 1. Sistem genelinde kontrol
    system_path = shutil.which("ffmpeg")
    if system_path:
        return system_path
    
    # 2. Yerel klasörde kontrol
    os_name = platform.system()
    exe_name = "ffmpeg.exe" if os_name == "Windows" else "ffmpeg"
    local_path = os.path.join(FFMPEG_FOLDER, exe_name)
    
    if os.path.exists(local_path):
        return local_path
    
    return None

def auto_install_ffmpeg():
    """FFmpeg'i otomatik indirir ve kurar."""
    os_name = platform.system()
    exe_name = "ffmpeg.exe" if os_name == "Windows" else "ffmpeg"
    final_path = os.path.join(FFMPEG_FOLDER, exe_name)
    
    status_container = st.empty()
    progress_bar = st.progress(0)
    
    try:
        status_container.info("⚙️ FFmpeg bulunamadı, otomatik indiriliyor... (Bu işlem tek seferliktir)")
        
        if os_name == "Windows":
            url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
            response = requests.get(url, stream=True)
            total_size = int(response.headers.get('content-length', 0))
            
            content = io.BytesIO()
            downloaded = 0
            for chunk in response.iter_content(chunk_size=1024*1024):
                content.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    progress_bar.progress(min(downloaded / total_size, 1.0))
            
            status_container.info("📦 Arşivden çıkarılıyor...")
            with zipfile.ZipFile(content) as z:
                for file_info in z.infolist():
                    if file_info.filename.endswith("bin/ffmpeg.exe"):
                        with z.open(file_info) as source, open(final_path, "wb") as target:
                            shutil.copyfileobj(source, target)
                        break
                        
        elif os_name == "Linux":
            url = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
            response = requests.get(url, stream=True)
            content = io.BytesIO(response.content)
            progress_bar.progress(0.8)
            
            status_container.info("📦 Arşivden çıkarılıyor...")
            with tarfile.open(fileobj=content, mode="r:xz") as t:
                for member in t.getmembers():
                    if member.name.endswith("/ffmpeg"):
                        member.name = os.path.basename(member.name)
                        t.extract(member, FFMPEG_FOLDER)
                        break
            os.chmod(final_path, 0o755)

        status_container.success("✅ FFmpeg başarıyla kuruldu!")
        time.sleep(1)
        status_container.empty()
        progress_bar.empty()
        return final_path

    except Exception as e:
        status_container.error(f"FFmpeg kurulum hatası: {e}")
        return None

# --- ARAYÜZ BAŞLANGICI ---

st.title("🎬 Ultimate YouTube Downloader")
st.markdown("Link yapıştır, format seç, indir. **403 Hatası Korumalı.**")

# 1. FFmpeg Kontrolü
ffmpeg_path = get_ffmpeg_path()
if not ffmpeg_path:
    ffmpeg_path = auto_install_ffmpeg()
    if not ffmpeg_path:
        st.stop()

# 2. Sidebar (Ayarlar)
with st.sidebar:
    st.header("⚙️ Gelişmiş Ayarlar")
    st.caption(f"FFmpeg Yolu: `{os.path.basename(ffmpeg_path)}`")
    
    st.markdown("---")
    st.write("**🔐 403 / Erişim Hatası Alırsanız:**")
    st.info("YouTube bazen botları engeller. Eğer indirme başarısız olursa, tarayıcınızdan alacağınız 'cookies.txt' dosyasını buraya yükleyin.")
    cookie_file = st.file_uploader("Cookies.txt Yükle", type=["txt"])

# 3. Ana Form
col1, col2 = st.columns([3, 1])

with col1:
    url = st.text_input("YouTube Linki:", placeholder="https://www.youtube.com/watch?v=...")

with col2:
    format_type = st.selectbox(
        "Format:",
        ("🎵 MP3 (Ses)", "📺 1080p (Video)", "🌟 4K (Video)", "🚀 En İyi Kalite")
    )

# İlerleme Çubuğu Hook'u
def progress_hook(d):
    if d['status'] == 'downloading':
        try:
            p = d.get('_percent_str', '0%').replace('%','')
            prog_val = float(p) / 100
            my_bar.progress(min(prog_val, 1.0))
            status_text.text(f"⏳ {d.get('_percent_str')} | Hız: {d.get('_speed_str')} | Kalan: {d.get('_eta_str')}")
        except:
            pass
    elif d['status'] == 'finished':
        status_text.text("🔨 Dosyalar birleştiriliyor (FFmpeg)...")
        my_bar.progress(1.0)

# --- İNDİRME MANTIĞI ---

if st.button("İndirmeyi Başlat", type="primary"):
    if not url:
        st.warning("Lütfen bir link girin.")
    else:
        status_text = st.empty()
        my_bar = st.progress(0)
        
        # Cookie Dosyası İşleme
        cookie_path = None
        if cookie_file:
            cookie_path = os.path.join(DOWNLOAD_FOLDER, "cookies.txt")
            with open(cookie_path, "wb") as f:
                f.write(cookie_file.getbuffer())
        
        # Temel Ayarlar (Anti-Bot Headerları Dahil)
        ydl_opts = {
            'outtmpl': f'{DOWNLOAD_FOLDER}/%(title)s.%(ext)s',
            'progress_hooks': [progress_hook],
            'restrictfilenames': True,
            'ffmpeg_location': ffmpeg_path,
            'nocheckcertificate': True,
            'ignoreerrors': False,
            'logtostderr': False,
            'quiet': True,
            'no_warnings': True,
            # Bot Korumasını Aşmak İçin Kritik Headerlar
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://www.youtube.com/',
            }
        }

        # Eğer cookie yüklendiyse ayarlara ekle
        if cookie_path:
            ydl_opts['cookiefile'] = cookie_path

        # Format Seçimleri
        if format_type.startswith("🎵"):
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })
        elif format_type.startswith("📺"):
            ydl_opts.update({
                'format': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
                'merge_output_format': 'mp4',
            })
        elif format_type.startswith("🌟"):
            ydl_opts.update({
                'format': 'bestvideo[height<=2160]+bestaudio/best[height<=2160]',
                'merge_output_format': 'mp4',
            })
        else: # En İyi
            ydl_opts.update({
                'format': 'bestvideo+bestaudio/best',
                'merge_output_format': 'mp4',
            })

        try:
            with st.spinner('Bağlantı kuruluyor ve analiz ediliyor...'):
                # Önce bilgi çekip başlığı alalım
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    video_title = info.get('title', 'video')
                    
                    # Sonra indirmeyi başlatalım
                    ydl.download([url])
            
            # İndirilen dosyayı bulma algoritması
            files = os.listdir(DOWNLOAD_FOLDER)
            paths = [os.path.join(DOWNLOAD_FOLDER, basename) for basename in files if not basename.endswith('cookies.txt')]
            
            if paths:
                latest_file = max(paths, key=os.path.getctime)
                file_name = os.path.basename(latest_file)
                
                status_text.success("✅ İşlem Tamamlandı!")
                
                with open(latest_file, "rb") as f:
                    st.download_button(
                        label=f"💾 İndir: {file_name}",
                        data=f,
                        file_name=file_name,
                        mime="application/octet-stream"
                    )
            else:
                st.error("Dosya indirildi ancak klasörde bulunamadı.")

        except yt_dlp.utils.DownloadError as e:
            if "Sign in to confirm you're not a bot" in str(e) or "HTTP Error 403" in str(e):
                st.error("⛔ YOUTUBE BOT KORUMASI DEVREDE!")
                st.warning("Çözüm: Sol menüdeki 'Cookies.txt Yükle' alanını kullanın.")
                st.markdown("[Cookies.txt Nasıl Alınır? (Eklenti Linki)](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)")
            else:
                st.error(f"Bir hata oluştu: {e}")
        except Exception as e:
            st.error(f"Beklenmeyen hata: {e}")
