#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dijital Sahaf - Tarihi Gazete ve Dergi Arşivi
Linux GTK Tarzı Modern Arayüz
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import os
import sys
import json
import threading
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
import requests
from io import BytesIO
from PIL import Image, ImageTk
import time
import re
import shutil
import webbrowser
import platform

# XDG Base Directory Specification
XDG_CONFIG_HOME = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))
XDG_CACHE_HOME = Path(os.environ.get('XDG_CACHE_HOME', Path.home() / '.cache'))

CONFIG_DIR = XDG_CONFIG_HOME / 'dijital_sahaf'
CACHE_DIR = XDG_CACHE_HOME / 'dijital_sahaf'
CONFIG_FILE = CONFIG_DIR / 'config.json'

# Dizinleri oluştur
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Tarihi gazete ve dergi veritabanı
GAZETE_DATABASE = {
    "Cumhuriyet": {
        "url_pattern": "https://www.cumhuriyet.com.tr/Archive/{year}/{month:02d}/{day:02d}/",
        "type": "gazete",
        "years": (1924, 2024)
    },
    "Milliyet": {
        "url_pattern": "https://www.milliyet.com.tr/galeri/milliyet-gazetesi-arsivi-{day}-{month}-{year}",
        "type": "gazete",
        "years": (1950, 2024)
    },
    "Hürriyet": {
        "url_pattern": "https://www.hurriyet.com.tr/mahmure/arsiv/{year}/{month:02d}/{day:02d}",
        "type": "gazete",
        "years": (1948, 2024)
    },
    "Sabah": {
        "url_pattern": "https://www.sabah.com.tr/arsiv/{year}/{month:02d}/{day:02d}",
        "type": "gazete",
        "years": (1985, 2024)
    },
    "Sözcü": {
        "url_pattern": "https://www.sozcu.com.tr/kategori/arsiv/{year}/{month:02d}/{day:02d}",
        "type": "gazete",
        "years": (2007, 2024)
    },
    "Yeni Şafak": {
        "url_pattern": "https://www.yenisafak.com/arsiv/{year}/{month:02d}/{day:02d}",
        "type": "gazete",
        "years": (1970, 2024)
    },
    "Türkiye": {
        "url_pattern": "https://www.turkiyegazetesi.com.tr/arsiv/{year}/{month:02d}/{day:02d}",
        "type": "gazete",
        "years": (1970, 2024)
    },
    "Star": {
        "url_pattern": "https://www.star.com.tr/arsiv/{year}-{month:02d}-{day:02d}",
        "type": "gazete",
        "years": (2005, 2024)
    },
    "Posta": {
        "url_pattern": "https://www.posta.com.tr/arsiv/{year}/{month:02d}/{day:02d}",
        "type": "gazete",
        "years": (2003, 2024)
    },
    "Habertürk": {
        "url_pattern": "https://www.haberturk.com/arsiv/{year}/{month:02d}/{day:02d}",
        "type": "gazete",
        "years": (2001, 2024)
    },
    "Akşam": {
        "url_pattern": "https://www.aksam.com.tr/arsiv/{year}/{month:02d}/{day:02d}",
        "type": "gazete",
        "years": (1918, 2024)
    },
    "Vatan": {
        "url_pattern": "https://www.gazetevatan.com/arsiv/{year}-{month:02d}-{day:02d}",
        "type": "gazete",
        "years": (2002, 2024)
    },
    "Takvim": {
        "url_pattern": "https://www.takvim.com.tr/arsiv/{year}/{month:02d}/{day:02d}",
        "type": "gazete",
        "years": (2000, 2024)
    },
    "Birgün": {
        "url_pattern": "https://www.birgun.net/haber-detay/arsiv-{year}-{month:02d}-{day:02d}",
        "type": "gazete",
        "years": (2004, 2024)
    },
    "Evrensel": {
        "url_pattern": "https://www.evrensel.net/arsiv/{year}/{month:02d}/{day:02d}",
        "type": "gazete",
        "years": (1995, 2024)
    },
    "Yeniçağ": {
        "url_pattern": "https://www.yenicaggazetesi.com.tr/arsiv/{year}/{month:02d}/{day:02d}",
        "type": "gazete",
        "years": (2002, 2024)
    },
    "Aydınlık": {
        "url_pattern": "https://www.aydinlik.com.tr/arsiv/{year}-{month:02d}-{day:02d}",
        "type": "gazete",
        "years": (1968, 2024)
    },
    "Söz": {
        "url_pattern": "https://www.sozgazetesi.com/arsiv/{year}/{month:02d}/{day:02d}",
        "type": "gazete",
        "years": (2010, 2024)
    },
    "Haber7": {
        "url_pattern": "https://www.haber7.com/arsiv/{year}{month:02d}{day:02d}",
        "type": "portal",
        "years": (2003, 2024)
    },
    "Mynet": {
        "url_pattern": "https://www.mynet.com/arsiv/{year}/{month:02d}/{day:02d}",
        "type": "portal",
        "years": (2000, 2024)
    },
    "Hürriyet Daily News": {
        "url_pattern": "https://www.hurriyetdailynews.com/archive/{year}/{month:02d}/{day:02d}",
        "type": "gazete",
        "years": (1961, 2024)
    },
    "Daily Sabah": {
        "url_pattern": "https://www.dailysabah.com/archive/{year}/{month:02d}/{day:02d}",
        "type": "gazete",
        "years": (2014, 2024)
    },
    "Economist": {
        "url_pattern": "https://www.ekonomist.com.tr/arsiv/{year}/{month:02d}/{day:02d}",
        "type": "dergi",
        "years": (1985, 2024)
    },
    "Capital": {
        "url_pattern": "https://www.capital.com.tr/arsiv/{year}/{month:02d}",
        "type": "dergi",
        "years": (1993, 2024)
    },
    "Para": {
        "url_pattern": "https://www.paraanaliz.com/arsiv/{year}/{month:02d}",
        "type": "dergi",
        "years": (1992, 2024)
    },
    "Fortune Turkey": {
        "url_pattern": "https://www.fortuneturkey.com/arsiv/{year}/{month:02d}",
        "type": "dergi",
        "years": (2005, 2024)
    },
    "Aksiyon": {
        "url_pattern": "https://www.aksiyon.com.tr/arsiv/{year}/{month:02d}",
        "type": "dergi",
        "years": (1995, 2024)
    },
    "Atlas": {
        "url_pattern": "https://www.atlasdergisi.com/arsiv/{year}/{month:02d}",
        "type": "dergi",
        "years": (1993, 2024)
    },
    "National Geographic Türkiye": {
        "url_pattern": "https://www.nationalgeographic.com.tr/arsiv/{year}/{month:02d}",
        "type": "dergi",
        "years": (2001, 2024)
    },
    "Bilim ve Teknik": {
        "url_pattern": "https://bilimteknik.tubitak.gov.tr/arsiv/{year}/{month:02d}",
        "type": "dergi",
        "years": (1967, 2024)
    },
    "Bilim ve Ütopya": {
        "url_pattern": "https://bilimveutopya.com.tr/arsiv/{year}/{month:02d}",
        "type": "dergi",
        "years": (1992, 2024)
    },
    "Popular Science Türkiye": {
        "url_pattern": "https://www.popsci.com.tr/arsiv/{year}/{month:02d}",
        "type": "dergi",
        "years": (2004, 2024)
    },
    "Chip": {
        "url_pattern": "https://www.chip.com.tr/arsiv/{year}/{month:02d}",
        "type": "dergi",
        "years": (1992, 2024)
    },
    "PC Net": {
        "url_pattern": "https://www.pcnet.com.tr/arsiv/{year}/{month:02d}",
        "type": "dergi",
        "years": (1995, 2024)
    },
    "Level": {
        "url_pattern": "https://www.leveldergisi.com/arsiv/{year}/{month:02d}",
        "type": "dergi",
        "years": (2004, 2024)
    },
    "Otomobil": {
        "url_pattern": "https://www.otomobil.com.tr/arsiv/{year}/{month:02d}",
        "type": "dergi",
        "years": (2005, 2024)
    },
    "Motor Trend": {
        "url_pattern": "https://www.motortrend.com.tr/arsiv/{year}/{month:02d}",
        "type": "dergi",
        "years": (2008, 2024)
    },
    "GQ Turkey": {
        "url_pattern": "https://www.gqturkiye.com/arsiv/{year}/{month:02d}",
        "type": "dergi",
        "years": (2010, 2024)
    },
    "Esquire Turkey": {
        "url_pattern": "https://www.esquire.com.tr/arsiv/{year}/{month:02d}",
        "type": "dergi",
        "years": (2011, 2024)
    },
    "Cosmopolitan Türkiye": {
        "url_pattern": "https://www.cosmopolitan.com.tr/arsiv/{year}/{month:02d}",
        "type": "dergi",
        "years": (1999, 2024)
    },
    "Elle": {
        "url_pattern": "https://www.elle.com.tr/arsiv/{year}/{month:02d}",
        "type": "dergi",
        "years": (1988, 2024)
    },
    "Marie Claire": {
        "url_pattern": "https://www.marieclaire.com.tr/arsiv/{year}/{month:02d}",
        "type": "dergi",
        "years": (2001, 2024)
    },
    "Vogue Türkiye": {
        "url_pattern": "https://www.vogue.com.tr/arsiv/{year}/{month:02d}",
        "type": "dergi",
        "years": (2010, 2024)
    },
    "Kafa": {
        "url_pattern": "https://www.kafadergi.com/arsiv/{year}/{month:02d}",
        "type": "dergi",
        "years": (2005, 2024)
    },
    "Virgül": {
        "url_pattern": "https://www.virguldergisi.com/arsiv/{year}/{month:02d}",
        "type": "dergi",
        "years": (2008, 2024)
    },
    "Ot": {
        "url_pattern": "https://www.otdergi.com/arsiv/{year}/{month:02d}",
        "type": "dergi",
        "years": (2010, 2024)
    },
    "Notos": {
        "url_pattern": "https://www.notosdergi.com/arsiv/{year}/{month:02d}",
        "type": "dergi",
        "years": (2015, 2024)
    },
    "Derin Tarih": {
        "url_pattern": "https://www.derintarih.gov.tr/arsiv/{year}/{month:02d}",
        "type": "dergi",
        "years": (2012, 2024)
    },
    "Popüler Tarih": {
        "url_pattern": "https://www.populertarih.com/arsiv/{year}/{month:02d}",
        "type": "dergi",
        "years": (2000, 2024)
    },
    "Tarih ve Düşünce": {
        "url_pattern": "https://tarihvedusunce.com/arsiv/{year}/{month:02d}",
        "type": "dergi",
        "years": (2000, 2024)
    },
    "Cogito": {
        "url_pattern": "https://www.cogitodergi.com/arsiv/{year}/{month:02d}",
        "type": "dergi",
        "years": (1995, 2024)
    }
}

# GasteArsivi.com Gazete Veritabanı
GASTE_ARSIVI_DATABASE = [
    {"id": "ahali-filibe", "name": "Ahali (Filibe)", "publication_dates": "1895-1908", "issue_count": 3000, "description": "Filibe'de yayımlanan Türkçe gazete"},
    {"id": "akbaba", "name": "Akbaba", "publication_dates": "1922-1977", "issue_count": 2800, "description": "Mizah ve karikatür dergisi"},
    {"id": "akis", "name": "Akis", "publication_dates": "1954-1977", "issue_count": 1200, "description": "Haber ve siyaset dergisi"},
    {"id": "aksam", "name": "Akşam", "publication_dates": "1918-Günümüz", "issue_count": 38000, "description": "Türk günlük gazetesi"},
    {"id": "anadolu", "name": "Anadolu", "publication_dates": "1924-1945", "issue_count": 7500, "description": "Ankara'da yayımlanan gazete"},
    {"id": "ant", "name": "Ant", "publication_dates": "1967-1980", "issue_count": 450, "description": "Sol görüşlü dergi"},
    {"id": "aydede", "name": "Aydede", "publication_dates": "1922-1923", "issue_count": 85, "description": "Mizah dergisi"},
    {"id": "agac", "name": "Ağaç", "publication_dates": "1936-1949", "issue_count": 650, "description": "Kültür ve sanat dergisi"},
    {"id": "balkan", "name": "Balkan", "publication_dates": "1904-1912", "issue_count": 2100, "description": "Balkanlarda yayımlanan gazete"},
    {"id": "bilim-teknik", "name": "Bilim ve Teknik", "publication_dates": "1967-Günümüz", "issue_count": 650, "description": "TÜBİTAK bilim dergisi"},
    {"id": "birgun", "name": "Birgün", "publication_dates": "2004-Günümüz", "issue_count": 7000, "description": "Sol görüşlü günlük gazete"},
    {"id": "bugun", "name": "Bugün", "publication_dates": "1973-1992", "issue_count": 6500, "description": "Günlük gazete"},
    {"id": "buyuk-dogu", "name": "Büyük Doğu", "publication_dates": "1943-1978", "issue_count": 350, "description": "Fikir ve sanat dergisi"},
    {"id": "commodore", "name": "Commodore", "publication_dates": "1988-1996", "issue_count": 95, "description": "Bilgisayar dergisi"},
    {"id": "cumhuriyet", "name": "Cumhuriyet", "publication_dates": "1924-Günümüz", "issue_count": 35000, "description": "Türkiye'nin en köklü gazetelerinden"},
    {"id": "demokrat-izmir", "name": "Demokrat İzmir", "publication_dates": "1946-1960", "issue_count": 4200, "description": "İzmir'de yayımlanan gazete"},
    {"id": "diyojen", "name": "Diyojen", "publication_dates": "1869-1871", "issue_count": 85, "description": "İlk Türk mizah dergisi"},
    {"id": "dunya", "name": "Dünya", "publication_dates": "1952-Günümüz", "issue_count": 25000, "description": "Ekonomi ve finans gazetesi"},
    {"id": "girgir", "name": "Gırgır", "publication_dates": "1972-2017", "issue_count": 2300, "description": "Mizah dergisi"},
    {"id": "hakimiyet-i-milliye", "name": "Hakimiyet-i Milliye", "publication_dates": "1920-1934", "issue_count": 5000, "description": "Milli mücadele dönemi gazetesi"},
    {"id": "hayat", "name": "Hayat", "publication_dates": "1926-1963", "issue_count": 1400, "description": "Haftalık haber ve kültür dergisi"},
    {"id": "kadro", "name": "Kadro", "publication_dates": "1932-1935", "issue_count": 38, "description": "Fikir ve sanat dergisi"},
    {"id": "kurun", "name": "Kurun", "publication_dates": "1933-1945", "issue_count": 4300, "description": "Günlük gazete"},
    {"id": "markopasa", "name": "Markopaşa", "publication_dates": "1946-1947", "issue_count": 54, "description": "Mizah gazetesi"},
    {"id": "milli-gazete", "name": "Milli Gazete", "publication_dates": "1973-Günümüz", "issue_count": 18000, "description": "İslami görüşlü günlük gazete"},
    {"id": "nokta", "name": "Nokta", "publication_dates": "1982-1999", "issue_count": 850, "description": "Haftalık haber dergisi"},
    {"id": "peyam", "name": "Peyam", "publication_dates": "1914-1918", "issue_count": 1200, "description": "Osmanlı dönemi gazetesi"},
    {"id": "resimli-ay", "name": "Resimli Ay", "publication_dates": "1929-1931", "issue_count": 28, "description": "Kültür ve sanat dergisi"},
    {"id": "sebilurresad", "name": "Sebilürreşad", "publication_dates": "1908-1925", "issue_count": 600, "description": "İslami dergi"},
    {"id": "serbes-cumhuriyet", "name": "Serbes Cumhuriyet", "publication_dates": "1930-1930", "issue_count": 65, "description": "Muhalif gazete"},
    {"id": "servet-i-funun", "name": "Servet-i Fünun", "publication_dates": "1891-1944", "issue_count": 2000, "description": "Edebiyat ve sanat dergisi"},
    {"id": "son-posta", "name": "Son Posta", "publication_dates": "1930-1960", "issue_count": 10000, "description": "Günlük gazete"},
    {"id": "tan", "name": "Tan", "publication_dates": "1935-1945", "issue_count": 3500, "description": "Günlük gazete"},
    {"id": "tanin", "name": "Tanin", "publication_dates": "1908-1925", "issue_count": 6000, "description": "İttihat ve Terakki gazetesi"},
    {"id": "taraf", "name": "Taraf", "publication_dates": "2007-2016", "issue_count": 3100, "description": "Günlük gazete"},
    {"id": "tasviri-efkar", "name": "Tasviri Efkar", "publication_dates": "1862-1925", "issue_count": 22000, "description": "Osmanlı dönemi gazetesi"},
    {"id": "ulus", "name": "Ulus", "publication_dates": "1934-2009", "issue_count": 26000, "description": "CHP gazetesi"},
    {"id": "vakit", "name": "Vakit", "publication_dates": "1917-1955", "issue_count": 13000, "description": "Günlük gazete"},
    {"id": "vatan", "name": "Vatan", "publication_dates": "1923-Günümüz", "issue_count": 28000, "description": "Günlük gazete"},
    {"id": "yarim-ay", "name": "Yarım Ay", "publication_dates": "1935-1945", "issue_count": 240, "description": "Edebiyat dergisi"},
    {"id": "yarin", "name": "Yarın", "publication_dates": "1948-1967", "issue_count": 950, "description": "Fikir ve sanat dergisi"},
    {"id": "yeni-asir", "name": "Yeni Asır", "publication_dates": "1895-Günümüz", "issue_count": 42000, "description": "İzmir'in köklü gazetesi"},
    {"id": "zaman", "name": "Zaman", "publication_dates": "1986-2016", "issue_count": 10500, "description": "Günlük gazete"},
    {"id": "irade-i-milliye", "name": "İrade-i Milliye", "publication_dates": "1919-1922", "issue_count": 800, "description": "Milli mücadele gazetesi"},
    {"id": "gunaydin", "name": "Günaydın", "publication_dates": "1968-Günümüz", "issue_count": 19000, "description": "Günlük gazete"},
    {"id": "haberturk", "name": "Habertürk", "publication_dates": "2001-Günümüz", "issue_count": 8000, "description": "Günlük gazete"},
    {"id": "hurriyet", "name": "Hürriyet", "publication_dates": "1948-Günümüz", "issue_count": 27000, "description": "Türkiye'nin en çok satan gazetesi"},
    {"id": "milliyet", "name": "Milliyet", "publication_dates": "1950-Günümüz", "issue_count": 26000, "description": "Köklü günlük gazete"},
    {"id": "sabah", "name": "Sabah", "publication_dates": "1985-Günümüz", "issue_count": 14000, "description": "Günlük gazete"},
    {"id": "sozcu", "name": "Sözcü", "publication_dates": "2007-Günümüz", "issue_count": 6200, "description": "Muhalif günlük gazete"},
    {"id": "yeni-safak", "name": "Yeni Şafak", "publication_dates": "1970-Günümüz", "issue_count": 19000, "description": "İslami görüşlü günlük gazete"},
    {"id": "takvim-i-vekayi", "name": "Takvim-i Vekayi", "publication_dates": "1831-1922", "issue_count": 4200, "description": "Osmanlı resmi gazetesi"},
    {"id": "tercuman-i-ahval", "name": "Tercüman-ı Ahval", "publication_dates": "1860-1866", "issue_count": 450, "description": "İlk özel Türk gazetesi"},
    {"id": "ceride-i-havadis", "name": "Ceride-i Havadis", "publication_dates": "1840-1864", "issue_count": 1200, "description": "İlk Türk gazetesi"}
]


class DigitalSahafApp:
    """Ana uygulama sınıfı"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Dijital Sahaf - Tarihi Gazete ve Dergi Arşivi")
        self.root.geometry("1200x800")
        
        # Modern Linux GTK renk paleti
        self.colors = {
            'bg': '#f6f5f4',
            'fg': '#2e3436',
            'primary': '#3584e4',
            'secondary': '#62a0ea',
            'success': '#26a269',
            'warning': '#f5c211',
            'danger': '#c01c28',
            'panel': '#ffffff',
            'border': '#c0bfbc'
        }
        
        # Font ayarları - Ubuntu/DejaVu Sans
        self.fonts = {
            'title': ('DejaVu Sans', 14, 'bold'),
            'heading': ('DejaVu Sans', 11, 'bold'),
            'normal': ('DejaVu Sans', 10),
            'small': ('DejaVu Sans', 9)
        }
        
        # Stil ayarları
        self.setup_styles()
        
        # Ana frame
        self.root.configure(bg=self.colors['bg'])
        
        # İndirme durumu
        self.is_downloading = False
        self.cancel_download = False
        
        # GasteArsivi verileri
        self.raw_data = GASTE_ARSIVI_DATABASE
        self.veri_havuzu = {item["name"]: item for item in GASTE_ARSIVI_DATABASE}
        
        # Cache sistemi
        self.cache_file = CACHE_DIR / "tarama_gecmisi.json"
        self.tarama_onbellegi = self.cache_yukle()
        
        # Yasal uyarı metni
        self.yasal_metin = (
            "YASAL UYARI:\n\n"
            "1. Bu yazılım sadece akademik araştırma, kişisel arşivleme ve eğitim amaçlıdır.\n"
            "2. İndirilen materyallerin telif hakları ilgili yayıncı kuruluşlara veya arşiv sahiplerine aittir.\n"
            "3. Bu materyallerin ticari amaçla kullanımı, yeniden dağıtımı kullanıcının sorumluluğundadır.\n"
            "4. Yazılım geliştiricisi, kullanıcıların eylemlerinden sorumlu tutulamaz."
        )
        
        # Config yükle
        self.config = self.load_config()
        
        # Arayüzü oluştur
        self.create_widgets()
        
        # Varsayılan indirme dizini
        if 'download_dir' not in self.config:
            self.config['download_dir'] = str(Path.home() / 'İndirilenler' / 'Dijital_Sahaf')
            self.save_config()
        
        Path(self.config['download_dir']).mkdir(parents=True, exist_ok=True)
    
    def setup_styles(self):
        """TTK stilleri ayarla"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Frame stilleri
        style.configure('Card.TFrame', background=self.colors['panel'], 
                       relief='flat', borderwidth=1)
        
        # Button stilleri
        style.configure('Primary.TButton', 
                       background=self.colors['primary'],
                       foreground='white',
                       borderwidth=0,
                       font=self.fonts['normal'])
        
        style.map('Primary.TButton',
                 background=[('active', self.colors['secondary'])])
        
        # Label stilleri
        style.configure('Heading.TLabel',
                       font=self.fonts['heading'],
                       background=self.colors['panel'],
                       foreground=self.colors['fg'])
        
        style.configure('Card.TLabel',
                       font=self.fonts['normal'],
                       background=self.colors['panel'],
                       foreground=self.colors['fg'])
        
        # Progressbar
        style.configure('Custom.Horizontal.TProgressbar',
                       background=self.colors['primary'],
                       troughcolor=self.colors['bg'],
                       borderwidth=0,
                       thickness=20)
    
    def create_widgets(self):
        """Arayüz bileşenlerini oluştur"""
        # Ana container
        main_container = tk.Frame(self.root, bg=self.colors['bg'])
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Başlık
        header_frame = tk.Frame(main_container, bg=self.colors['bg'])
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        title_label = tk.Label(header_frame, 
                              text="📚 Dijital Sahaf",
                              font=self.fonts['title'],
                              bg=self.colors['bg'],
                              fg=self.colors['fg'])
        title_label.pack(side=tk.LEFT)
        
        subtitle_label = tk.Label(header_frame,
                                 text="Tarihi Gazete ve Dergi Arşivi",
                                 font=self.fonts['normal'],
                                 bg=self.colors['bg'],
                                 fg='#5e5c64')
        subtitle_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Yasal uyarı butonu
        tk.Button(header_frame,
                 text="⚖ Yasal Uyarı",
                 command=self.yasal_uyari_goster,
                 bg=self.colors['warning'],
                 fg='white',
                 font=self.fonts['small'],
                 relief=tk.FLAT,
                 padx=10,
                 pady=5,
                 cursor='hand2').pack(side=tk.RIGHT)
        
        # Ana içerik paneli
        content_frame = ttk.Frame(main_container, style='Card.TFrame')
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Notebook (tabs)
        self.notebook = ttk.Notebook(content_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Tab 1: Toplu İndirme
        self.create_bulk_download_tab()
        
        # Tab 2: Link ile İndirme
        self.create_link_download_tab()
        
        # Tab 3: Gazete Listesi
        self.create_newspaper_list_tab()
        
        # Tab 4: Ayarlar
        self.create_settings_tab()
        
        # Alt panel - Progress ve Log
        bottom_frame = ttk.Frame(main_container, style='Card.TFrame')
        bottom_frame.pack(fill=tk.BOTH, expand=False, pady=(10, 0))
        
        # Progress bar
        progress_frame = tk.Frame(bottom_frame, bg=self.colors['panel'])
        progress_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.progress_label = ttk.Label(progress_frame, 
                                       text="Hazır",
                                       style='Card.TLabel')
        self.progress_label.pack(anchor=tk.W, pady=(0, 5))
        
        self.progress_bar = ttk.Progressbar(progress_frame,
                                           style='Custom.Horizontal.TProgressbar',
                                           mode='determinate')
        self.progress_bar.pack(fill=tk.X)
        
        # Log alanı
        log_frame = tk.Frame(bottom_frame, bg=self.colors['panel'])
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        log_label = ttk.Label(log_frame, text="İşlem Kayıtları:", style='Heading.TLabel')
        log_label.pack(anchor=tk.W, pady=(0, 5))
        
        self.log_text = scrolledtext.ScrolledText(log_frame,
                                                  height=6,
                                                  bg='#ffffff',
                                                  fg=self.colors['fg'],
                                                  font=self.fonts['small'],
                                                  wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
    
    def create_bulk_download_tab(self):
        """Toplu indirme tab'ı oluştur"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="📥 Toplu İndirme")
        
        # İçerik frame'i
        content = tk.Frame(tab, bg=self.colors['panel'])
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Gazete seçimi
        select_frame = tk.LabelFrame(content, text="Gazete/Dergi Seçimi",
                                    bg=self.colors['panel'],
                                    fg=self.colors['fg'],
                                    font=self.fonts['heading'])
        select_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Listbox ve scrollbar
        list_frame = tk.Frame(select_frame, bg=self.colors['panel'])
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.newspaper_listbox = tk.Listbox(list_frame,
                                           selectmode=tk.MULTIPLE,
                                           yscrollcommand=scrollbar.set,
                                           font=self.fonts['normal'],
                                           height=8)
        self.newspaper_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.newspaper_listbox.yview)
        
        # Gazete listesini doldur
        for name in sorted(GAZETE_DATABASE.keys()):
            self.newspaper_listbox.insert(tk.END, name)
        
        # Hızlı seçim butonları
        button_frame = tk.Frame(select_frame, bg=self.colors['panel'])
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        ttk.Button(button_frame, text="Tümünü Seç",
                  command=self.select_all_newspapers).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Seçimi Temizle",
                  command=self.clear_newspaper_selection).pack(side=tk.LEFT)
        
        # Tarih aralığı
        date_frame = tk.LabelFrame(content, text="Tarih Aralığı",
                                  bg=self.colors['panel'],
                                  fg=self.colors['fg'],
                                  font=self.fonts['heading'])
        date_frame.pack(fill=tk.X, pady=(0, 15))
        
        date_content = tk.Frame(date_frame, bg=self.colors['panel'])
        date_content.pack(fill=tk.X, padx=10, pady=10)
        
        # Başlangıç tarihi
        start_frame = tk.Frame(date_content, bg=self.colors['panel'])
        start_frame.pack(side=tk.LEFT, expand=True, fill=tk.X)
        
        ttk.Label(start_frame, text="Başlangıç:", style='Card.TLabel').pack(anchor=tk.W)
        
        start_inputs = tk.Frame(start_frame, bg=self.colors['panel'])
        start_inputs.pack(fill=tk.X, pady=5)
        
        self.start_day = tk.Spinbox(start_inputs, from_=1, to=31, width=5, font=self.fonts['normal'])
        self.start_day.pack(side=tk.LEFT, padx=2)
        self.start_day.delete(0, tk.END)
        self.start_day.insert(0, "1")
        
        self.start_month = tk.Spinbox(start_inputs, from_=1, to=12, width=5, font=self.fonts['normal'])
        self.start_month.pack(side=tk.LEFT, padx=2)
        self.start_month.delete(0, tk.END)
        self.start_month.insert(0, "1")
        
        self.start_year = tk.Spinbox(start_inputs, from_=1900, to=2024, width=8, font=self.fonts['normal'])
        self.start_year.pack(side=tk.LEFT, padx=2)
        self.start_year.delete(0, tk.END)
        self.start_year.insert(0, "2020")
        
        # Bitiş tarihi
        end_frame = tk.Frame(date_content, bg=self.colors['panel'])
        end_frame.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(20, 0))
        
        ttk.Label(end_frame, text="Bitiş:", style='Card.TLabel').pack(anchor=tk.W)
        
        end_inputs = tk.Frame(end_frame, bg=self.colors['panel'])
        end_inputs.pack(fill=tk.X, pady=5)
        
        self.end_day = tk.Spinbox(end_inputs, from_=1, to=31, width=5, font=self.fonts['normal'])
        self.end_day.pack(side=tk.LEFT, padx=2)
        self.end_day.delete(0, tk.END)
        self.end_day.insert(0, "31")
        
        self.end_month = tk.Spinbox(end_inputs, from_=1, to=12, width=5, font=self.fonts['normal'])
        self.end_month.pack(side=tk.LEFT, padx=2)
        self.end_month.delete(0, tk.END)
        self.end_month.insert(0, "12")
        
        self.end_year = tk.Spinbox(end_inputs, from_=1900, to=2024, width=8, font=self.fonts['normal'])
        self.end_year.pack(side=tk.LEFT, padx=2)
        self.end_year.delete(0, tk.END)
        self.end_year.insert(0, "2020")
        
        # Seçenekler
        options_frame = tk.LabelFrame(content, text="İndirme Seçenekleri",
                                     bg=self.colors['panel'],
                                     fg=self.colors['fg'],
                                     font=self.fonts['heading'])
        options_frame.pack(fill=tk.X, pady=(0, 15))
        
        options_content = tk.Frame(options_frame, bg=self.colors['panel'])
        options_content.pack(fill=tk.X, padx=10, pady=10)
        
        self.create_pdf_var = tk.BooleanVar(value=True)
        tk.Checkbutton(options_content, text="PDF oluştur",
                      variable=self.create_pdf_var,
                      bg=self.colors['panel'],
                      font=self.fonts['normal']).pack(anchor=tk.W)
        
        self.use_cache_var = tk.BooleanVar(value=True)
        tk.Checkbutton(options_content, text="Önbellek kullan",
                      variable=self.use_cache_var,
                      bg=self.colors['panel'],
                      font=self.fonts['normal']).pack(anchor=tk.W)
        
        # İndirme butonu
        button_container = tk.Frame(content, bg=self.colors['panel'])
        button_container.pack(fill=tk.X)
        
        self.download_button = tk.Button(button_container,
                                        text="📥 İndirmeyi Başlat",
                                        command=self.start_bulk_download,
                                        bg=self.colors['primary'],
                                        fg='white',
                                        font=self.fonts['heading'],
                                        relief=tk.FLAT,
                                        padx=20,
                                        pady=10,
                                        cursor='hand2')
        self.download_button.pack(side=tk.LEFT, padx=5)
        
        self.cancel_button = tk.Button(button_container,
                                       text="⏹ İptal",
                                       command=self.cancel_download_process,
                                       bg=self.colors['danger'],
                                       fg='white',
                                       font=self.fonts['heading'],
                                       relief=tk.FLAT,
                                       padx=20,
                                       pady=10,
                                       cursor='hand2',
                                       state=tk.DISABLED)
        self.cancel_button.pack(side=tk.LEFT)
    
    def create_link_download_tab(self):
        """Link ile indirme tab'ı oluştur"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="🔗 Link ile İndirme")
        
        content = tk.Frame(tab, bg=self.colors['panel'])
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Açıklama
        info_label = tk.Label(content,
                            text="Gazete veya dergi sayfasının direkt linkini yapıştırın:",
                            font=self.fonts['normal'],
                            bg=self.colors['panel'],
                            fg=self.colors['fg'])
        info_label.pack(anchor=tk.W, pady=(0, 10))
        
        # URL girişi
        self.url_entry = tk.Entry(content, font=self.fonts['normal'])
        self.url_entry.pack(fill=tk.X, pady=(0, 20))
        
        # Butonlar
        button_frame = tk.Frame(content, bg=self.colors['panel'])
        button_frame.pack(fill=tk.X)
        
        tk.Button(button_frame,
                 text="📥 İndir",
                 command=self.download_from_link,
                 bg=self.colors['primary'],
                 fg='white',
                 font=self.fonts['heading'],
                 relief=tk.FLAT,
                 padx=20,
                 pady=10,
                 cursor='hand2').pack(side=tk.LEFT, padx=5)
        
        tk.Button(button_frame,
                 text="🔍 Aynı Tarihteki Diğer Gazeteleri Bul",
                 command=self.find_same_date_newspapers,
                 bg=self.colors['secondary'],
                 fg='white',
                 font=self.fonts['normal'],
                 relief=tk.FLAT,
                 padx=15,
                 pady=10,
                 cursor='hand2').pack(side=tk.LEFT)
        
        tk.Button(button_frame,
                 text="🌐 Web Sitesine Git",
                 command=self.siteye_git,
                 bg=self.colors['success'],
                 fg='white',
                 font=self.fonts['normal'],
                 relief=tk.FLAT,
                 padx=15,
                 pady=10,
                 cursor='hand2').pack(side=tk.LEFT, padx=5)
    
    def create_newspaper_list_tab(self):
        """Gazete listesi tab'ı oluştur"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="📰 Gazete/Dergi Listesi")
        
        content = tk.Frame(tab, bg=self.colors['panel'])
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Arama
        search_frame = tk.Frame(content, bg=self.colors['panel'])
        search_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(search_frame, text="🔍 Ara:", style='Card.TLabel').pack(side=tk.LEFT, padx=(0, 5))
        
        self.search_entry = tk.Entry(search_frame, font=self.fonts['normal'])
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.search_entry.bind('<KeyRelease>', self.filter_newspaper_list)
        
        # Filtre
        filter_frame = tk.Frame(content, bg=self.colors['panel'])
        filter_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(filter_frame, text="Filtre:", style='Card.TLabel').pack(side=tk.LEFT, padx=(0, 10))
        
        self.filter_var = tk.StringVar(value="all")
        
        tk.Radiobutton(filter_frame, text="Tümü", variable=self.filter_var, value="all",
                      command=self.filter_newspaper_list,
                      bg=self.colors['panel'],
                      font=self.fonts['normal']).pack(side=tk.LEFT, padx=5)
        
        tk.Radiobutton(filter_frame, text="Gazeteler", variable=self.filter_var, value="gazete",
                      command=self.filter_newspaper_list,
                      bg=self.colors['panel'],
                      font=self.fonts['normal']).pack(side=tk.LEFT, padx=5)
        
        tk.Radiobutton(filter_frame, text="Dergiler", variable=self.filter_var, value="dergi",
                      command=self.filter_newspaper_list,
                      bg=self.colors['panel'],
                      font=self.fonts['normal']).pack(side=tk.LEFT, padx=5)
        
        # Liste
        list_frame = tk.Frame(content, bg=self.colors['panel'])
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.newspaper_text = scrolledtext.ScrolledText(list_frame,
                                                       yscrollcommand=scrollbar.set,
                                                       font=self.fonts['normal'],
                                                       wrap=tk.WORD)
        self.newspaper_text.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.newspaper_text.yview)
        
        # Listeyi doldur
        self.update_newspaper_list()
    
    def create_settings_tab(self):
        """Ayarlar tab'ı oluştur"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="⚙ Ayarlar")
        
        content = tk.Frame(tab, bg=self.colors['panel'])
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # İndirme dizini
        dir_frame = tk.LabelFrame(content, text="İndirme Dizini",
                                 bg=self.colors['panel'],
                                 fg=self.colors['fg'],
                                 font=self.fonts['heading'])
        dir_frame.pack(fill=tk.X, pady=(0, 15))
        
        dir_content = tk.Frame(dir_frame, bg=self.colors['panel'])
        dir_content.pack(fill=tk.X, padx=10, pady=10)
        
        self.dir_label = ttk.Label(dir_content,
                                  text=self.config.get('download_dir', ''),
                                  style='Card.TLabel')
        self.dir_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        tk.Button(dir_content,
                 text="📁 Değiştir",
                 command=self.change_download_dir,
                 bg=self.colors['secondary'],
                 fg='white',
                 font=self.fonts['normal'],
                 relief=tk.FLAT,
                 padx=15,
                 pady=5,
                 cursor='hand2').pack(side=tk.LEFT, padx=(10, 0))
        
        tk.Button(dir_content,
                 text="🗀 Aç",
                 command=self.open_download_dir,
                 bg=self.colors['primary'],
                 fg='white',
                 font=self.fonts['normal'],
                 relief=tk.FLAT,
                 padx=15,
                 pady=5,
                 cursor='hand2').pack(side=tk.LEFT, padx=(5, 0))
        
        # Önbellek
        cache_frame = tk.LabelFrame(content, text="Önbellek",
                                   bg=self.colors['panel'],
                                   fg=self.colors['fg'],
                                   font=self.fonts['heading'])
        cache_frame.pack(fill=tk.X, pady=(0, 15))
        
        cache_content = tk.Frame(cache_frame, bg=self.colors['panel'])
        cache_content.pack(fill=tk.X, padx=10, pady=10)
        
        cache_size = self.get_cache_size()
        self.cache_label = ttk.Label(cache_content,
                                    text=f"Önbellek boyutu: {cache_size}",
                                    style='Card.TLabel')
        self.cache_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        tk.Button(cache_content,
                 text="🗑 Önbelleği Temizle",
                 command=self.clear_cache,
                 bg=self.colors['warning'],
                 fg='white',
                 font=self.fonts['normal'],
                 relief=tk.FLAT,
                 padx=15,
                 pady=5,
                 cursor='hand2').pack(side=tk.LEFT)
        
        # Hakkında
        about_frame = tk.LabelFrame(content, text="Hakkında",
                                   bg=self.colors['panel'],
                                   fg=self.colors['fg'],
                                   font=self.fonts['heading'])
        about_frame.pack(fill=tk.BOTH, expand=True)
        
        about_content = tk.Frame(about_frame, bg=self.colors['panel'])
        about_content.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        about_text = """
Dijital Sahaf v1.0

Tarihi gazete ve dergi arşivleri için geliştirilmiş
modern bir Linux uygulamasıdır.

📚 50+ gazete ve dergi arşivi
📥 Toplu indirme desteği
📄 Otomatik PDF oluşturma
💾 Akıllı önbellek sistemi
🔗 Link ile direkt indirme

Geliştirici: Tarihi İçerik Arşiv Sistemi
Lisans: GPL-3.0
        """
        
        tk.Label(about_content,
                text=about_text,
                font=self.fonts['normal'],
                bg=self.colors['panel'],
                fg=self.colors['fg'],
                justify=tk.LEFT).pack(anchor=tk.W)
    
    def load_config(self):
        """Yapılandırma dosyasını yükle"""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
    
    def save_config(self):
        """Yapılandırma dosyasını kaydet"""
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
    
    def log(self, message):
        """Thread-safe log mesajı ekle"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_message = f"[{timestamp}] {message}\n"
        
        self.root.after(0, lambda: self._append_log(log_message))
    
    def _append_log(self, message):
        """Log mesajını ekle (main thread)"""
        self.log_text.insert(tk.END, message)
        self.log_text.see(tk.END)
    
    def update_progress(self, value, message):
        """Progress bar'ı güncelle"""
        self.root.after(0, lambda: self._update_progress_ui(value, message))
    
    def _update_progress_ui(self, value, message):
        """Progress UI güncelle (main thread)"""
        self.progress_bar['value'] = value
        self.progress_label['text'] = message
    
    def select_all_newspapers(self):
        """Tüm gazeteleri seç"""
        self.newspaper_listbox.select_set(0, tk.END)
    
    def clear_newspaper_selection(self):
        """Gazete seçimini temizle"""
        self.newspaper_listbox.selection_clear(0, tk.END)
    
    def start_bulk_download(self):
        """Toplu indirmeyi başlat"""
        # Seçili gazeteleri al
        selected_indices = self.newspaper_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Uyarı", "Lütfen en az bir gazete/dergi seçin!")
            return
        
        selected_newspapers = [self.newspaper_listbox.get(i) for i in selected_indices]
        
        # Tarihleri al
        try:
            start_date = datetime(
                int(self.start_year.get()),
                int(self.start_month.get()),
                int(self.start_day.get())
            )
            end_date = datetime(
                int(self.end_year.get()),
                int(self.end_month.get()),
                int(self.end_day.get())
            )
            
            if start_date > end_date:
                messagebox.showerror("Hata", "Başlangıç tarihi bitiş tarihinden sonra olamaz!")
                return
                
        except ValueError:
            messagebox.showerror("Hata", "Geçersiz tarih!")
            return
        
        # İndirme thread'ini başlat
        self.is_downloading = True
        self.cancel_download = False
        self.download_button.config(state=tk.DISABLED)
        self.cancel_button.config(state=tk.NORMAL)
        
        thread = threading.Thread(
            target=self._bulk_download_worker,
            args=(selected_newspapers, start_date, end_date),
            daemon=True
        )
        thread.start()
    
    def _bulk_download_worker(self, newspapers, start_date, end_date):
        """Toplu indirme işlemi (worker thread) - GasteArsivi.com CDN entegrasyonu"""
        try:
            total_days = (end_date - start_date).days + 1
            total_tasks = len(newspapers) * total_days
            completed_tasks = 0
            
            self.log(f"İndirme başlatıldı: {len(newspapers)} yayın, {total_days} gün")
            
            for newspaper in newspapers:
                if self.cancel_download:
                    break
                
                # GasteArsivi veritabanından gazete bilgisini al
                if newspaper not in self.veri_havuzu:
                    self.log(f"⚠ {newspaper} GasteArsivi veritabanında bulunamadı, atlanıyor...")
                    completed_tasks += total_days
                    continue
                
                newspaper_data = self.veri_havuzu[newspaper]
                gid = newspaper_data["id"]
                folder_name = newspaper_data["name"].replace("/", "-")
                
                # Yıl klasörü oluştur
                yil_klasor = os.path.join(self.config['download_dir'], folder_name)
                os.makedirs(yil_klasor, exist_ok=True)
                
                current_date = start_date
                while current_date <= end_date:
                    if self.cancel_download:
                        break
                    
                    tarih_str = current_date.strftime('%Y-%m-%d')
                    
                    # Yıl filtresi kontrolü
                    if not self.yil_araligi_kontrol(newspaper_data["publication_dates"], current_date.year):
                        self.log(f"Atlandı (yayın aralığı dışı): {newspaper} - {tarih_str}")
                        completed_tasks += 1
                        current_date += timedelta(days=1)
                        continue
                    
                    # Mevcut PDF kontrolü
                    pdf_path = os.path.join(yil_klasor, f"{folder_name}_{tarih_str}.pdf")
                    if os.path.exists(pdf_path):
                        self.log(f"Atlandı (mevcut): {tarih_str}")
                        completed_tasks += 1
                        progress = (completed_tasks / total_tasks) * 100
                        self.update_progress(progress, f"{completed_tasks}/{total_tasks} işlem tamamlandı")
                        current_date += timedelta(days=1)
                        continue
                    
                    # İndir ve PDF oluştur
                    self.log(f"{newspaper} - {tarih_str} indiriliyor...")
                    success = self.indir_ve_pdf_olustur(gid, folder_name, tarih_str, yil_klasor)
                    
                    if success:
                        self.log(f"✅ Tamamlandı: {newspaper} - {tarih_str}")
                    else:
                        self.log(f"⚠ Bulunamadı: {newspaper} - {tarih_str}")
                    
                    completed_tasks += 1
                    progress = (completed_tasks / total_tasks) * 100
                    self.update_progress(
                        progress,
                        f"{completed_tasks}/{total_tasks} işlem tamamlandı"
                    )
                    
                    current_date += timedelta(days=1)
            
            if not self.cancel_download:
                self.log("✅ İndirme tamamlandı!")
                self.update_progress(100, "Tamamlandı")
                messagebox.showinfo("Başarılı", "İndirme işlemi tamamlandı!")
            
            # Cache'i kaydet
            self.cache_kaydet()
            
        except Exception as e:
            self.log(f"❌ Hata: {str(e)}")
            messagebox.showerror("Hata", f"İndirme sırasında hata oluştu:\n{str(e)}")
        
        finally:
            self.is_downloading = False
            self.root.after(0, lambda: self.download_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.cancel_button.config(state=tk.DISABLED))
    
    def cancel_download_process(self):
        """İndirme işlemini iptal et"""
        if self.is_downloading:
            self.cancel_download = True
            self.log("İndirme iptal ediliyor...")
    
    def download_from_link(self):
        """Link'ten indirme yap - URL parsing ve otomatik indirme"""
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Uyarı", "Lütfen bir URL girin!")
            return
        
        self.log(f"Link'ten indirme: {url}")
        
        # URL'den bilgileri parse et
        match = re.search(r"gazete\/([^\/]+)\/(\d{4}-\d{2}-\d{2})\/?(\d+)?", url)
        if not match:
            messagebox.showerror("Hata", "Geçersiz URL formatı!\nÖrnek: https://www.gastearsivi.com/gazete/cumhuriyet/2020-01-15/1")
            return
        
        gid = match.group(1)
        tarih = match.group(2)
        page = match.group(3) if match.group(3) else "1"
        
        # Gazete adını bul
        gname = None
        for item in self.raw_data:
            if item["id"] == gid:
                gname = item["name"]
                break
        
        if not gname:
            gname = gid
        
        self.log(f"Gazete: {gname}, Tarih: {tarih}, Sayfa: {page}")
        
        # Tek sayfa mı yoksa tüm sayılar mı?
        result = messagebox.askyesnocancel(
            "İndirme Seçeneği",
            f"Sadece sayfa {page} indirilsin mi?\n\n"
            f"Evet: Sadece bu sayfayı indir\n"
            f"Hayır: Tüm sayfaları indir ve PDF oluştur\n"
            f"İptal: İşlemi iptal et"
        )
        
        if result is None:  # Cancel
            return
        elif result:  # Yes - tek sayfa
            thread = threading.Thread(
                target=lambda: self.tek_sayfa_indir(gid, gname, tarih, page),
                daemon=True
            )
            thread.start()
        else:  # No - tüm sayfalar
            folder_name = gname.replace("/", "-")
            yil_klasor = os.path.join(self.config['download_dir'], folder_name)
            os.makedirs(yil_klasor, exist_ok=True)
            
            thread = threading.Thread(
                target=lambda: self.indir_ve_pdf_olustur(gid, folder_name, tarih, yil_klasor),
                daemon=True
            )
            thread.start()
    
    def find_same_date_newspapers(self):
        """Aynı tarihteki diğer gazeteleri bul - gerçek implementasyon"""
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Uyarı", "Lütfen bir URL girin!")
            return
        
        # URL'den tarihi parse et
        match = re.search(r"gazete\/([^\/]+)\/(\d{4}-\d{2}-\d{2})", url)
        if not match:
            messagebox.showerror("Hata", "Geçersiz URL formatı!")
            return
        
        tarih_str = match.group(2)
        self.log(f"Aynı tarihteki gazeteler aranıyor: {tarih_str}")
        
        # Thread ile ara
        def arama_worker():
            bulunan = self.gunu_tara(tarih_str)
            if bulunan:
                mesaj = f"{tarih_str} tarihinde {len(bulunan)} gazete bulundu:\n\n"
                mesaj += "\n".join(f"• {g}" for g in bulunan)
                self.root.after(0, lambda: messagebox.showinfo("Sonuçlar", mesaj))
                self.log(f"✅ {len(bulunan)} gazete bulundu")
            else:
                self.root.after(0, lambda: messagebox.showinfo("Sonuç", "Bu tarihte gazete bulunamadı."))
                self.log("⚠ Gazete bulunamadı")
        
        thread = threading.Thread(target=arama_worker, daemon=True)
        thread.start()
    
    def filter_newspaper_list(self, event=None):
        """Gazete listesini filtrele"""
        self.update_newspaper_list()
    
    def update_newspaper_list(self):
        """Gazete listesini güncelle"""
        self.newspaper_text.delete('1.0', tk.END)
        
        search_term = self.search_entry.get().lower() if hasattr(self, 'search_entry') else ""
        filter_type = self.filter_var.get() if hasattr(self, 'filter_var') else "all"
        
        for name, info in sorted(GAZETE_DATABASE.items()):
            # Filtrele
            if search_term and search_term not in name.lower():
                continue
            
            if filter_type != "all" and info['type'] != filter_type:
                continue
            
            # Listeye ekle
            years = f"{info['years'][0]}-{info['years'][1]}"
            type_emoji = "📰" if info['type'] == "gazete" else "📖"
            self.newspaper_text.insert(tk.END, f"{type_emoji} {name}\n")
            self.newspaper_text.insert(tk.END, f"   Yıllar: {years}\n")
            self.newspaper_text.insert(tk.END, f"   Tip: {info['type'].capitalize()}\n\n")
    
    def change_download_dir(self):
        """İndirme dizinini değiştir"""
        from tkinter import filedialog
        new_dir = filedialog.askdirectory(initialdir=self.config.get('download_dir', ''))
        if new_dir:
            self.config['download_dir'] = new_dir
            self.save_config()
            self.dir_label['text'] = new_dir
            self.log(f"İndirme dizini değiştirildi: {new_dir}")
    
    def open_download_dir(self):
        """İndirme dizinini aç - platform bağımsız"""
        download_dir = self.config.get('download_dir', '')
        if download_dir and Path(download_dir).exists():
            self.dosya_ac(download_dir)
        else:
            messagebox.showwarning("Uyarı", "İndirme dizini bulunamadı!")
    
    def get_cache_size(self):
        """Önbellek boyutunu hesapla"""
        try:
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(CACHE_DIR):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    total_size += os.path.getsize(filepath)
            
            # MB cinsinden
            size_mb = total_size / (1024 * 1024)
            return f"{size_mb:.2f} MB"
        except Exception:
            return "0 MB"
    
    def clear_cache(self):
        """Önbelleği temizle"""
        result = messagebox.askyesno(
            "Onay",
            "Önbellek temizlenecek. Devam etmek istiyor musunuz?"
        )
        
        if result:
            try:
                import shutil
                if CACHE_DIR.exists():
                    shutil.rmtree(CACHE_DIR)
                    CACHE_DIR.mkdir(parents=True, exist_ok=True)
                
                self.cache_label['text'] = "Önbellek boyutu: 0 MB"
                self.log("✅ Önbellek temizlendi")
                messagebox.showinfo("Başarılı", "Önbellek temizlendi!")
            except Exception as e:
                self.log(f"❌ Önbellek temizleme hatası: {str(e)}")
                messagebox.showerror("Hata", f"Önbellek temizlenemedi:\n{str(e)}")
    
    def cache_yukle(self):
        """Önbellek dosyasını yükle"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
    
    def cache_kaydet(self):
        """Önbelleği kaydet"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.tarama_onbellegi, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log(f"Önbellek kaydetme hatası: {str(e)}")
    
    def yil_araligi_kontrol(self, tarih_metni, hedef_yil):
        """Yayın tarihlerine göre filtreleme"""
        try:
            hedef_yil = int(hedef_yil)
            bitis_limit = datetime.now().year if "Günümüz" in tarih_metni else 0
            yillar = [int(y) for y in re.findall(r'\d{4}', tarih_metni)]
            
            if not yillar:
                return True
            
            baslangic = min(yillar)
            bitis = bitis_limit if bitis_limit > 0 else max(yillar)
            
            return (baslangic - 1) <= hedef_yil <= (bitis + 1)
        except (ValueError, TypeError, AttributeError):
            return True
    
    def dosya_ac(self, path):
        """Platform bağımsız dosya açma"""
        system = platform.system()
        try:
            if system == 'Windows':
                os.startfile(path)
            elif system == 'Darwin':  # macOS
                subprocess.call(['open', path])
            else:  # Linux
                subprocess.call(['xdg-open', path])
        except Exception as e:
            self.log(f"Dosya açma hatası: {str(e)}")
            messagebox.showerror("Hata", f"Dosya açılamadı:\n{str(e)}")
    
    def yasal_uyari_goster(self):
        """Yasal uyarı dialogunu göster"""
        messagebox.showinfo("Yasal Uyarı", self.yasal_metin)
    
    def get_selected_newspaper(self):
        """Seçili gazeteyi al (listbox'tan)"""
        selected_indices = self.newspaper_listbox.curselection()
        if selected_indices:
            return self.newspaper_listbox.get(selected_indices[0])
        return None
    
    def siteye_git(self):
        """Seçili gazete için gastearsivi.com'a yönlendir"""
        # URL alanından parse et
        url = self.url_entry.get().strip()
        if url:
            # Eğer URL varsa direkt aç
            webbrowser.open(url)
            self.log(f"Web sitesi açılıyor: {url}")
            return
        
        # Yoksa seçili gazeteden oluştur
        secilen = self.get_selected_newspaper()
        if not secilen or secilen not in self.veri_havuzu:
            messagebox.showwarning("Uyarı", "Lütfen bir gazete seçin veya URL girin!")
            return
        
        gid = self.veri_havuzu[secilen]["id"]
        yil = self.start_year.get()
        ay = self.start_month.get()
        gun = self.start_day.get()
        url = f"https://www.gastearsivi.com/gazete/{gid}/{yil}-{ay.zfill(2)}-{gun.zfill(2)}/1"
        webbrowser.open(url)
        self.log(f"Web sitesi açılıyor: {url}")
    
    def gunu_tara(self, tarih_str):
        """Aynı tarihteki gazeteleri bul (gerçek implementasyon)"""
        bulunan = []
        self.log(f"Taranan tarih: {tarih_str}")
        
        for item in self.raw_data:
            if self.cancel_download:
                break
                
            gid = item["id"]
            url = f"https://dzp35pmd4yqn4.cloudfront.net/sayfalar/{gid}/{tarih_str}-1.jpg"
            try:
                r = requests.head(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=2)
                if r.status_code == 200:
                    bulunan.append(item["name"])
                    self.log(f"✓ Bulundu: {item['name']}")
            except (requests.RequestException, ConnectionError, TimeoutError):
                pass
        
        return bulunan
    
    def tek_sayfa_indir(self, gid, gname, tarih, sayfa):
        """Tek sayfa indirme"""
        folder = os.path.join(self.config['download_dir'], "Tekil_Indirmeler")
        os.makedirs(folder, exist_ok=True)
        
        url = f"https://dzp35pmd4yqn4.cloudfront.net/sayfalar/{gid}/{tarih}-{sayfa}.jpg"
        local = os.path.join(folder, f"{gname}_{tarih}_Sayfa{sayfa}.jpg")
        
        try:
            self.log(f"Tek sayfa indiriliyor: {gname} - {tarih} - Sayfa {sayfa}")
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            if r.status_code == 200:
                with open(local, "wb") as f:
                    f.write(r.content)
                self.log(f"✅ İndirildi: {local}")
                messagebox.showinfo("Başarılı", f"Sayfa indirildi:\n{local}")
                return True
            else:
                messagebox.showerror("Hata", f"Sayfa bulunamadı (HTTP {r.status_code})")
                return False
        except Exception as e:
            self.log(f"❌ Hata: {str(e)}")
            messagebox.showerror("Hata", f"İndirme hatası:\n{str(e)}")
            return False
    
    def indir_ve_pdf_olustur(self, gid, folder_name, tarih_str, yil_klasor):
        """CDN'den resim indir ve PDF oluştur"""
        temp = os.path.join(yil_klasor, "temp")
        os.makedirs(temp, exist_ok=True)
        
        sayfa = 1
        images = []
        tolerance = 0
        base_cdn = "https://dzp35pmd4yqn4.cloudfront.net/sayfalar"
        
        while sayfa <= 99:
            if self.cancel_download or tolerance >= 2:
                break
            
            url = f"{base_cdn}/{gid}/{tarih_str}-{sayfa}.jpg"
            try:
                r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
                if r.status_code == 200:
                    fpath = os.path.join(temp, f"{sayfa}.jpg")
                    with open(fpath, "wb") as f:
                        f.write(r.content)
                    images.append(fpath)
                    tolerance = 0
                    self.log(f"  Sayfa {sayfa} indirildi")
                    time.sleep(0.5)
                else:
                    tolerance += 1
            except (requests.RequestException, ConnectionError, IOError):
                tolerance += 1
            sayfa += 1
        
        if images:
            try:
                pdf_path = os.path.join(yil_klasor, f"{folder_name}_{tarih_str}.pdf")
                img_list = [Image.open(x).convert("RGB") for x in images]
                if img_list:  # Double check list is not empty
                    img_list[0].save(pdf_path, save_all=True, append_images=img_list[1:] if len(img_list) > 1 else [])
                    for img in img_list:
                        img.close()
                    self.log(f"✅ PDF oluşturuldu: {pdf_path}")
            except Exception as e:
                self.log(f"❌ PDF oluşturma hatası: {str(e)}")
        
        shutil.rmtree(temp, ignore_errors=True)
        return len(images) > 0


def main():
    """Ana fonksiyon"""
    root = tk.Tk()
    app = DigitalSahafApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
