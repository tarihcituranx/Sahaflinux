#!/bin/bash
# Dijital Sahaf - Otomatik Kurulum Scripti
# Linux Dağıtımları için Otomatik Paket Yöneticisi Tespiti ve Kurulum

set -e

# Renkli çıktı için ANSI kodları
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Banner
echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════╗"
echo "║                                                       ║"
echo "║          📚 Dijital Sahaf Kurulum Scripti            ║"
echo "║     Tarihi Gazete ve Dergi Arşivi - Linux Sürümü     ║"
echo "║                                                       ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Root kontrolü
if [ "$EUID" -eq 0 ]; then 
    echo -e "${YELLOW}⚠ Uyarı: Bu script root kullanıcısı ile çalıştırılmamalıdır.${NC}"
    echo -e "${YELLOW}  Normal kullanıcı ile çalıştırın, gerektiğinde sudo şifresi istenecektir.${NC}"
    exit 1
fi

# Hata ayıklama fonksiyonu
error_exit() {
    echo -e "${RED}❌ Hata: $1${NC}" 1>&2
    exit 1
}

# Bilgi mesajı fonksiyonu
info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Başarı mesajı fonksiyonu
success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# Uyarı mesajı fonksiyonu
warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Dağıtım tespiti
detect_distro() {
    info "Linux dağıtımı tespit ediliyor..."
    
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO=$ID
        DISTRO_VERSION=$VERSION_ID
        DISTRO_NAME=$NAME
    elif [ -f /etc/lsb-release ]; then
        . /etc/lsb-release
        DISTRO=$DISTRIB_ID
        DISTRO_VERSION=$DISTRIB_RELEASE
        DISTRO_NAME=$DISTRIB_DESCRIPTION
    else
        error_exit "Dağıtım tespit edilemedi!"
    fi
    
    success "Tespit edilen dağıtım: $DISTRO_NAME"
}

# Paket yöneticisi tespiti
detect_package_manager() {
    info "Paket yöneticisi tespit ediliyor..."
    
    if command -v apt &> /dev/null; then
        PKG_MANAGER="apt"
        PKG_INSTALL="sudo apt install -y"
        PKG_UPDATE="sudo apt update"
        success "Paket yöneticisi: APT (Debian/Ubuntu)"
    elif command -v dnf &> /dev/null; then
        PKG_MANAGER="dnf"
        PKG_INSTALL="sudo dnf install -y"
        PKG_UPDATE="sudo dnf check-update || true"
        success "Paket yöneticisi: DNF (Fedora)"
    elif command -v yum &> /dev/null; then
        PKG_MANAGER="yum"
        PKG_INSTALL="sudo yum install -y"
        PKG_UPDATE="sudo yum check-update || true"
        success "Paket yöneticisi: YUM (RHEL/CentOS)"
    elif command -v pacman &> /dev/null; then
        PKG_MANAGER="pacman"
        PKG_INSTALL="sudo pacman -S --noconfirm"
        PKG_UPDATE="sudo pacman -Sy"
        success "Paket yöneticisi: Pacman (Arch/Manjaro)"
    elif command -v zypper &> /dev/null; then
        PKG_MANAGER="zypper"
        PKG_INSTALL="sudo zypper install -y"
        PKG_UPDATE="sudo zypper refresh"
        success "Paket yöneticisi: Zypper (openSUSE)"
    else
        error_exit "Desteklenen bir paket yöneticisi bulunamadı!"
    fi
}

# Python kontrolü
check_python() {
    info "Python kontrolü yapılıyor..."
    
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
        
        if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 8 ]; then
            success "Python sürümü uygun: $PYTHON_VERSION"
            PYTHON_CMD="python3"
            return 0
        else
            warning "Python sürümü eski: $PYTHON_VERSION (minimum 3.8 gerekli)"
            return 1
        fi
    else
        warning "Python3 bulunamadı"
        return 1
    fi
}

# Sistem paketlerini kur
install_system_packages() {
    info "Sistem paketleri kuruluyor..."
    
    # Paket listesini güncelle
    echo -e "${BLUE}📦 Paket listesi güncelleniyor...${NC}"
    eval $PKG_UPDATE || warning "Paket listesi güncellenemedi, devam ediliyor..."
    
    # Dağıtıma göre paket isimleri
    case $PKG_MANAGER in
        apt)
            PACKAGES="python3 python3-pip python3-tk python3-pil python3-pil.imagetk"
            ;;
        dnf|yum)
            PACKAGES="python3 python3-pip python3-tkinter python3-pillow python3-pillow-tk"
            ;;
        pacman)
            PACKAGES="python python-pip tk python-pillow"
            ;;
        zypper)
            PACKAGES="python3 python3-pip python3-tk python3-Pillow"
            ;;
    esac
    
    echo -e "${BLUE}📦 Gerekli paketler kuruluyor: $PACKAGES${NC}"
    eval $PKG_INSTALL $PACKAGES || error_exit "Sistem paketleri kurulamadı!"
    
    success "Sistem paketleri kuruldu"
}

# Python bağımlılıklarını kur
install_python_dependencies() {
    info "Python bağımlılıkları kuruluyor..."
    
    # pip kontrolü
    if ! command -v pip3 &> /dev/null; then
        warning "pip3 bulunamadı, kurulmaya çalışılıyor..."
        
        case $PKG_MANAGER in
            apt)
                sudo apt install -y python3-pip
                ;;
            dnf|yum)
                sudo $PKG_MANAGER install -y python3-pip
                ;;
            pacman)
                sudo pacman -S --noconfirm python-pip
                ;;
            zypper)
                sudo zypper install -y python3-pip
                ;;
        esac
    fi
    
    # requirements.txt kontrolü
    if [ -f "requirements.txt" ]; then
        echo -e "${BLUE}📦 requirements.txt'ten bağımlılıklar kuruluyor...${NC}"
        pip3 install --user -r requirements.txt || error_exit "Python bağımlılıkları kurulamadı!"
    else
        echo -e "${BLUE}📦 Manuel bağımlılık kurulumu yapılıyor...${NC}"
        pip3 install --user requests>=2.28.0 Pillow>=10.2.0 || error_exit "Python bağımlılıkları kurulamadı!"
    fi
    
    success "Python bağımlılıkları kuruldu"
}

# Uygulama dosyalarını kur
install_application() {
    info "Uygulama dosyaları kuruluyor..."
    
    # Ana uygulama dosyası kontrolü
    if [ ! -f "dijital_sahaf_linux.py" ]; then
        error_exit "dijital_sahaf_linux.py dosyası bulunamadı!"
    fi
    
    # Çalıştırma izni ver
    chmod +x dijital_sahaf_linux.py
    success "Uygulama dosyasına çalıştırma izni verildi"
    
    # Kullanıcının local bin dizinine kopyala
    LOCAL_BIN="$HOME/.local/bin"
    mkdir -p "$LOCAL_BIN"
    
    cp dijital_sahaf_linux.py "$LOCAL_BIN/dijital-sahaf"
    chmod +x "$LOCAL_BIN/dijital-sahaf"
    success "Uygulama $LOCAL_BIN dizinine kuruldu"
    
    # PATH kontrolü
    if [[ ":$PATH:" != *":$LOCAL_BIN:"* ]]; then
        warning "$LOCAL_BIN dizini PATH'e ekli değil"
        echo -e "${YELLOW}Aşağıdaki satırı ~/.bashrc veya ~/.zshrc dosyanıza ekleyin:${NC}"
        echo -e "${GREEN}export PATH=\"\$HOME/.local/bin:\$PATH\"${NC}"
        
        # Otomatik ekleme teklifi
        read -p "PATH'e otomatik olarak eklemek ister misiniz? (e/h): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Ee]$ ]]; then
            if [ -f "$HOME/.bashrc" ]; then
                echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
                success "PATH ~/.bashrc dosyasına eklendi"
            fi
            if [ -f "$HOME/.zshrc" ]; then
                echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.zshrc"
                success "PATH ~/.zshrc dosyasına eklendi"
            fi
            warning "Değişikliklerin aktif olması için terminal'i yeniden başlatın veya 'source ~/.bashrc' komutunu çalıştırın"
        fi
    fi
}

# Masaüstü kısayolu kur
install_desktop_entry() {
    info "Masaüstü kısayolu kuruluyor..."
    
    DESKTOP_DIR="$HOME/.local/share/applications"
    mkdir -p "$DESKTOP_DIR"
    
    if [ -f "dijital-sahaf.desktop" ]; then
        cp dijital-sahaf.desktop "$DESKTOP_DIR/"
        
        # Exec yolunu güncelle
        sed -i "s|Exec=.*|Exec=$HOME/.local/bin/dijital-sahaf|g" "$DESKTOP_DIR/dijital-sahaf.desktop"
        
        chmod +x "$DESKTOP_DIR/dijital-sahaf.desktop"
        success "Masaüstü kısayolu kuruldu"
        
        # Desktop database'i güncelle
        if command -v update-desktop-database &> /dev/null; then
            update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
        fi
    else
        warning "dijital-sahaf.desktop dosyası bulunamadı, kısayol oluşturulamadı"
    fi
}

# Kurulum doğrulama
verify_installation() {
    info "Kurulum doğrulanıyor..."
    
    # Python modülleri kontrolü
    python3 -c "import tkinter" 2>/dev/null || error_exit "Tkinter modülü çalışmıyor!"
    python3 -c "import PIL" 2>/dev/null || error_exit "PIL (Pillow) modülü çalışmıyor!"
    python3 -c "import requests" 2>/dev/null || error_exit "requests modülü çalışmıyor!"
    
    # Uygulama dosyası kontrolü
    if [ -f "$HOME/.local/bin/dijital-sahaf" ]; then
        success "Uygulama dosyası doğrulandı"
    else
        error_exit "Uygulama dosyası bulunamadı!"
    fi
    
    success "Kurulum doğrulaması başarılı!"
}

# Kurulum özeti
print_summary() {
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                       ║${NC}"
    echo -e "${GREEN}║          ✅ Kurulum Başarıyla Tamamlandı!             ║${NC}"
    echo -e "${GREEN}║                                                       ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}Dijital Sahaf uygulamasını başlatmak için:${NC}"
    echo -e "${GREEN}  Terminal'den: ${NC}dijital-sahaf"
    echo -e "${GREEN}  Uygulama Menüsü: ${NC}Dijital Sahaf'ı arayın"
    echo ""
    echo -e "${BLUE}Kurulum Bilgileri:${NC}"
    echo -e "  • Uygulama konumu: ${GREEN}$HOME/.local/bin/dijital-sahaf${NC}"
    echo -e "  • Yapılandırma: ${GREEN}$HOME/.config/dijital_sahaf/${NC}"
    echo -e "  • Önbellek: ${GREEN}$HOME/.cache/dijital_sahaf/${NC}"
    echo -e "  • Masaüstü kısayolu: ${GREEN}$HOME/.local/share/applications/${NC}"
    echo ""
    echo -e "${YELLOW}Not: PATH'e ekleme yaptıysanız, terminali yeniden başlatın!${NC}"
    echo ""
}

# Ana kurulum fonksiyonu
main() {
    echo ""
    
    # Dağıtım tespiti
    detect_distro
    echo ""
    
    # Paket yöneticisi tespiti
    detect_package_manager
    echo ""
    
    # Python kontrolü
    if ! check_python; then
        echo ""
        info "Python kurulumu yapılacak..."
    fi
    echo ""
    
    # Sistem paketlerini kur
    install_system_packages
    echo ""
    
    # Python bağımlılıklarını kur
    install_python_dependencies
    echo ""
    
    # Uygulamayı kur
    install_application
    echo ""
    
    # Masaüstü kısayolu kur
    install_desktop_entry
    echo ""
    
    # Kurulumu doğrula
    verify_installation
    echo ""
    
    # Özeti göster
    print_summary
}

# Script'i çalıştır
main
