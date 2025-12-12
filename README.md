# 📚 Dijital Sahaf - Tarihi Gazete ve Dergi Arşivi

Linux için geliştirilmiş modern Python/Tkinter tabanlı tarihi gazete ve dergi arşivi uygulaması.

![License](https://img.shields.io/badge/license-GPL--3.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![Platform](https://img.shields.io/badge/platform-Linux-green.svg)

## 🎯 Özellikler

- 📰 **50+ Gazete ve Dergi Arşivi**: Cumhuriyet, Milliyet, Hürriyet ve daha fazlası
- 📅 **Tarih Aralığına Göre Toplu İndirme**: İstediğiniz tarih aralığındaki tüm yayınları toplu indirin
- 📄 **Otomatik PDF Oluşturma**: İndirilen içerikler otomatik olarak PDF formatında kaydedilir
- 💾 **Akıllı Önbellek Sistemi**: Tekrar indirme yapmadan önbellekteki içerikleri kullanın
- 🔗 **Link ile Direkt İndirme**: Doğrudan gazete/dergi sayfası linkini yapıştırarak indirin
- 🔍 **Aynı Tarihteki Diğer Gazeteleri Bulma**: Bir tarih için diğer tüm gazeteleri keşfedin
- 🎨 **Modern GTK Tarzı Arayüz**: Linux masaüstü ortamlarına uyumlu modern tasarım
- 🧵 **Thread-Safe İşlemler**: Kesintisiz ve güvenli indirme deneyimi
- 📊 **İlerleme Takibi**: Detaylı progress bar ile işlem durumunu takip edin
- 🌐 **XDG Uyumlu**: Linux standartlarına uygun dizin yapısı

## 📋 Desteklenen Gazeteler ve Dergiler

### Gazeteler
- Cumhuriyet (1924-2024)
- Milliyet (1950-2024)
- Hürriyet (1948-2024)
- Sabah (1985-2024)
- Sözcü (2007-2024)
- Yeni Şafak (1970-2024)
- Türkiye (1970-2024)
- Star (2005-2024)
- Posta (2003-2024)
- Habertürk (2001-2024)
- Akşam (1918-2024)
- Vatan (2002-2024)
- Takvim (2000-2024)
- Birgün (2004-2024)
- Evrensel (1995-2024)
- Yeniçağ (2002-2024)
- Aydınlık (1968-2024)
- Söz (2010-2024)
- Ve daha fazlası...

### Dergiler
- Capital
- Economist
- Para
- Fortune Turkey
- Aksiyon
- Atlas
- National Geographic Türkiye
- Bilim ve Teknik (TÜBİTAK)
- Bilim ve Ütopya
- Popular Science Türkiye
- Chip
- Level
- Otomobil
- GQ Turkey
- Elle
- Vogue Türkiye
- Ve daha fazlası...

**Toplam: 50+ yayın**

## 🚀 Hızlı Kurulum

### Otomatik Kurulum (Önerilen)

Tek komut ile tüm bağımlılıkları ve uygulamayı kurun:

```bash
# Repository'yi klonlayın
git clone https://github.com/tarihcituranx/Sahaflinux.git
cd Sahaflinux

# Kurulum scriptini çalıştırın
chmod +x kurulum.sh
./kurulum.sh
```

Kurulum scripti otomatik olarak:
- ✅ Linux dağıtımınızı tespit eder
- ✅ Gerekli sistem paketlerini kurar
- ✅ Python bağımlılıklarını kurar
- ✅ Uygulamayı sisteme kurar
- ✅ Masaüstü kısayolu oluşturur

### Desteklenen Dağıtımlar

- 🐧 **Ubuntu/Debian** (apt)
- 🎩 **Fedora** (dnf)
- 🐉 **Arch Linux/Manjaro** (pacman)
- 🦎 **openSUSE** (zypper)
- 📦 **RHEL/CentOS** (yum)

## 📥 Manuel Kurulum

### 1. Sistem Gereksinimleri

- Python 3.8 veya üzeri
- Tkinter
- İnternet bağlantısı

### 2. Dağıtıma Göre Kurulum

#### Ubuntu/Debian/Linux Mint

```bash
sudo apt update
sudo apt install python3 python3-pip python3-tk python3-pil python3-pil.imagetk
pip3 install --user -r requirements.txt
```

#### Fedora

```bash
sudo dnf install python3 python3-pip python3-tkinter python3-pillow python3-pillow-tk
pip3 install --user -r requirements.txt
```

#### Arch Linux/Manjaro

```bash
sudo pacman -S python python-pip tk python-pillow
pip3 install --user -r requirements.txt
```

#### openSUSE

```bash
sudo zypper install python3 python3-pip python3-tk python3-Pillow
pip3 install --user -r requirements.txt
```

### 3. Uygulamayı Çalıştırma

```bash
# Dizinde çalıştırma
python3 dijital_sahaf_linux.py

# Veya çalıştırma izni vererek
chmod +x dijital_sahaf_linux.py
./dijital_sahaf_linux.py
```

## 🎮 Kullanım

### Toplu İndirme

1. **Gazete/Dergi Seçimi**: Listeden indirmek istediğiniz yayınları seçin
2. **Tarih Aralığı**: Başlangıç ve bitiş tarihlerini belirleyin
3. **Seçenekler**: PDF oluşturma ve önbellek kullanımı seçeneklerini ayarlayın
4. **İndirmeyi Başlat**: Butona tıklayarak indirmeyi başlatın

### Link ile İndirme

1. **Link ile İndirme** sekmesine gidin
2. Gazete veya dergi sayfasının URL'sini yapıştırın
3. **İndir** butonuna tıklayın

### Aynı Tarihteki Gazeteleri Bulma

1. Bir gazete linkini yapıştırın
2. **Aynı Tarihteki Diğer Gazeteleri Bul** butonuna tıklayın
3. O tarihteki tüm mevcut gazetelerin listesini görün

## ⚙️ Yapılandırma

### Dizin Yapısı

Uygulama XDG Base Directory Specification'a uygun olarak çalışır:

```
~/.config/dijital_sahaf/     # Yapılandırma dosyaları
~/.cache/dijital_sahaf/      # Önbellek dosyaları
~/İndirilenler/Dijital_Sahaf/ # İndirilen dosyalar (varsayılan)
```

### Ayarlar

- **İndirme Dizini**: İndirilen dosyaların kaydedileceği konumu değiştirin
- **Önbellek**: Önbellek boyutunu görün ve temizleyin
- **Tema**: Modern GTK tarzı arayüz otomatik olarak sistem temanıza uyum sağlar

## 🖥️ Masaüstü Kısayolu

### Otomatik Kurulum

Kurulum scripti masaüstü kısayolunu otomatik olarak oluşturur.

### Manuel Kurulum

```bash
# Desktop entry dosyasını kopyalayın
mkdir -p ~/.local/share/applications
cp dijital-sahaf.desktop ~/.local/share/applications/

# Exec yolunu güncelleyin
sed -i "s|Exec=.*|Exec=$HOME/.local/bin/dijital-sahaf|g" \
    ~/.local/share/applications/dijital-sahaf.desktop

# İzinleri ayarlayın
chmod +x ~/.local/share/applications/dijital-sahaf.desktop

# Desktop database'i güncelleyin (opsiyonel)
update-desktop-database ~/.local/share/applications/
```

## 🐛 Sorun Giderme

### Tkinter Hatası

```bash
# Ubuntu/Debian
sudo apt install python3-tk

# Fedora
sudo dnf install python3-tkinter

# Arch
sudo pacman -S tk
```

### Pillow Hatası

```bash
# Ubuntu/Debian
sudo apt install python3-pil python3-pil.imagetk

# Fedora
sudo dnf install python3-pillow python3-pillow-tk

# Arch
sudo pacman -S python-pillow
```

### Font Hatası

Uygulama DejaVu Sans ve Ubuntu fontlarını kullanır. Eğer bu fontlar sisteminizde yoksa:

```bash
# Ubuntu/Debian
sudo apt install fonts-dejavu fonts-ubuntu

# Fedora
sudo dnf install dejavu-sans-fonts

# Arch
sudo pacman -S ttf-dejavu
```

## 📸 Ekran Görüntüleri

_(Ekran görüntüleri eklenecek)_

## 🛠️ Geliştirme

### Gereksinimler

- Python 3.8+
- Tkinter
- Pillow >= 9.0.0
- requests >= 2.28.0

### Katkıda Bulunma

1. Bu repository'yi fork edin
2. Feature branch oluşturun (`git checkout -b feature/YeniOzellik`)
3. Değişikliklerinizi commit edin (`git commit -am 'Yeni özellik eklendi'`)
4. Branch'inizi push edin (`git push origin feature/YeniOzellik`)
5. Pull Request oluşturun

## 📜 Lisans

Bu proje GPL-3.0 lisansı altında lisanslanmıştır. Detaylar için [LICENSE](LICENSE) dosyasına bakın.

## ⚖️ Yasal Bildirim

Bu uygulama, kamuya açık gazete ve dergi arşivlerine erişim sağlamak amacıyla geliştirilmiştir. İndirilen içerikler:

- Sadece kişisel kullanım ve araştırma amaçlıdır
- Telif hakları ilgili yayın kuruluşlarına aittir
- Ticari amaçla kullanılamaz, paylaşılamaz veya dağıtılamaz
- Kullanıcılar içeriklerin kullanımından sorumludur

**Not**: Bu uygulama yalnızca eğitim ve arşivleme amaçlı geliştirilmiştir. Lütfen ilgili gazete ve dergilerin telif hakkı politikalarına uyun.

## 🤝 Destek

Sorularınız veya sorunlarınız için:

- 🐛 [Issue açın](https://github.com/tarihcituranx/Sahaflinux/issues)
- 💬 [Discussions](https://github.com/tarihcituranx/Sahaflinux/discussions)

## 🙏 Teşekkürler

Bu proje aşağıdaki açık kaynak projelerden yararlanmaktadır:

- [Python](https://www.python.org/)
- [Tkinter](https://docs.python.org/3/library/tkinter.html)
- [Pillow](https://python-pillow.org/)
- [Requests](https://requests.readthedocs.io/)

## 📊 İstatistikler

- 50+ gazete ve dergi
- 100+ yıllık arşiv erişimi
- Modern GTK uyumlu arayüz
- Çoklu dağıtım desteği

---

**Dijital Sahaf ile tarihe yolculuk yapın! 📚✨**