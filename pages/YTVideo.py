import streamlit as st
import yt_dlp
import os
import shutil
import platform
import requests
import zipfile
import tarfile
import io

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Ultra YouTube İndirici", page_icon="🚀")

st.title("🚀 Tam Otomatik YouTube İndirici")
st.markdown("Video linkini yapıştır, formatı seç, **gerisini bana bırak!** (FFmpeg otomatik kurulur)")

# --- GLOBAL AYARLAR ---
DOWNLOAD_FOLDER = "downloads"
FFMPEG_FOLDER = "ffmpeg_bin"  # FFmpeg'in kurulacağı klasör

# Klasörleri oluştur
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)
if not os.path.exists(FFMPEG_FOLDER):
    os.makedirs(FFMPEG_FOLDER)

# --- FFmpeg OTOMATİK KURUCU ---
def get_ffmpeg_path():
    """Sistemde veya yerel klasörde FFmpeg var mı bakar, yolunu döndürür."""
    # 1. Önce sistem genelinde var mı bakalım
    system_path = shutil.which("ffmpeg")
    if system_path:
        return system_path
    
    # 2. Yoksa bizim klasöre bakalım
    local_filename = "ffmpeg.exe" if platform.system() == "Windows" else "ffmpeg"
    local_path = os.path.join(FFMPEG_FOLDER, local_filename)
    
    if os.path.exists(local_path):
        return local_path
    
    return None

def auto_install_ffmpeg():
    """FFmpeg yoksa internetten indirip kurar."""
    os_name = platform.system()
    local_filename = "ffmpeg.exe" if os_name == "Windows" else "ffmpeg"
    final_path = os.path.join(FFMPEG_FOLDER, local_filename)

    status_text = st.empty()
    progress_bar = st.progress(0)
    
    status_text.info("⚙️ FFmpeg eksik! Otomatik indiriliyor (Bu işlem bir kez yapılır)...")

    try:
        if os_name == "Windows":
            # Windows için güvenilir bir build (Gyan.dev mirror)
            url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
            response = requests.get(url, stream=True)
            total_size = int(response.headers.get('content-length', 0))
            
            # İndirme işlemi
            content = io.BytesIO()
            downloaded = 0
            for chunk in response.iter_content(chunk_size=1024*1024):
                content.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    progress_bar.progress(min(downloaded / total_size, 1.0))
            
            status_text.info("📦 İndirme bitti, arşivden çıkarılıyor...")
            
            # Zip'i aç ve içindeki ffmpeg.exe'yi bul
            with zipfile.ZipFile(content) as z:
                for file_info in z.infolist():
                    if file_info.filename.endswith("bin/ffmpeg.exe"):
                        with z.open(file_info) as source, open(final_path, "wb") as target:
                            shutil.copyfileobj(source, target)
                        break

        elif os_name == "Linux":
            # Linux için statik build (John Van Sickle)
            url = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
            response = requests.get(url, stream=True)
            # Linux indirme barı simülasyonu
            content = io.BytesIO(response.content)
            progress_bar.progress(0.8)
            
            status_text.info("📦 Arşivden çıkarılıyor...")
            with tarfile.open(fileobj=content, mode="r:xz") as t:
                for member in t.getmembers():
                    if member.name.endswith("/ffmpeg"):
                        member.name = os.path.basename(member.name) # Klasör yapısını düzelt
                        t.extract(member, FFMPEG_FOLDER)
                        break
            
            # Çalıştırma izni ver (Linux için kritik)
            os.chmod(final_path, 0o755)

        status_text.success("✅ FFmpeg başarıyla kuruldu!")
        progress_bar.empty()
        return final_path

    except Exception as e:
        status_text.error(f"Kurulum hatası: {e}")
        return None

# --- BAŞLANGIÇ KONTROLÜ ---
ffmpeg_binary = get_ffmpeg_path()

if not ffmpeg_binary:
    # Eğer ffmpeg yoksa kurmayı dene
    ffmpeg_binary = auto_install_ffmpeg()
    if not ffmpeg_binary:
        st.error("🚨 FFmpeg kurulamadı. Lütfen internet bağlantınızı kontrol edin.")
        st.stop()
else:
    # Debug için (İsteğe bağlı kapatılabilir)
    # st.success(f"FFmpeg hazır: {ffmpeg_binary}")
    pass

# --- ARAYÜZ ---
col1, col2 = st.columns([3, 1])
with col1:
    video_url = st.text_input("YouTube Linki:", placeholder="https://www.youtube.com/watch?v=...")
with col2:
    format_choice = st.selectbox(
        "Format:",
        ("🎵 MP3 (Ses)", "📺 1080p (Video)", "🌟 4K (Video)", "🚀 En İyi (Video)")
    )

# İlerleme Çubuğu Fonksiyonu
def progress_hook(d):
    if d['status'] == 'downloading':
        try:
            p = d.get('_percent_str', '0%').replace('%','')
            progress_val = float(p) / 100
            my_bar.progress(progress_val)
            my_status.text(f"⏳ İndiriliyor... {d.get('_percent_str')} | Hız: {d.get('_speed_str')}")
        except:
            pass
    elif d['status'] == 'finished':
        my_status.text("🔨 Dosyalar birleştiriliyor (FFmpeg)... Lütfen bekleyin.")
        my_bar.progress(1.0)

# İŞLEM BUTONU
if st.button("İndirmeyi Başlat", type="primary"):
    if not video_url:
        st.warning("Lütfen bir link girin!")
    else:
        my_status = st.empty()
        my_bar = st.progress(0)
        
        # Yt-dlp Ayarları
        ydl_opts = {
            'outtmpl': f'{DOWNLOAD_FOLDER}/%(title)s.%(ext)s',
            'progress_hooks': [progress_hook],
            'restrictfilenames': True,
            'ffmpeg_location': ffmpeg_binary,  # <--- KRİTİK NOKTA: İndirdiğimiz FFmpeg'i kullan diyoruz
        }

        # Format Ayarları
        if format_choice.startswith("🎵"): # MP3
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })
        elif format_choice.startswith("📺"): # 1080p
            ydl_opts.update({
                'format': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
                'merge_output_format': 'mp4',
            })
        elif format_choice.startswith("🌟"): # 4K
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
            with st.spinner('Bağlantı kuruluyor...'):
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(video_url, download=True)
                    video_title = info.get('title', 'video')
                    
                    # İndirilen dosyayı bul
                    files = os.listdir(DOWNLOAD_FOLDER)
                    paths = [os.path.join(DOWNLOAD_FOLDER, basename) for basename in files]
                    if not paths:
                        raise Exception("Dosya bulunamadı.")
                    latest_file = max(paths, key=os.path.getctime)
                    file_name = os.path.basename(latest_file)

            my_status.success("✅ İşlem Tamamlandı!")
            
            # İndirme Butonu Oluştur
            with open(latest_file, "rb") as f:
                st.download_button(
                    label=f"💾 İndir: {file_name}",
                    data=f,
                    file_name=file_name,
                    mime="application/octet-stream"
                )

        except Exception as e:
            my_status.error(f"Hata oluştu: {e}")

st.markdown("---")
st.caption(f"Kullanılan FFmpeg Yolu: `{ffmpeg_binary}`")
