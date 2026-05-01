# ⛏ MAPEG Öteleme Aracı

Maden sahalarının İşletme Faaliyet Raporları için **İmalat Haritası** çizimlerinde kullanılan otomatik öteleme ve numaralama aracı.

MAPEG harita standartlarına göre şev altı noktalarına dik yönde 20cm öteleme yaparak, NetCAD'e import edilecek dosyaları otomatik oluşturur.

## 🎯 Ne İşe Yarar?

Maden sahalarında her yıl Nisan ayında MAPEG'e sunulan İşletme Faaliyet Raporları için İmalat Haritası çizimlerinde:

- **Şev altı** çizgilerindeki noktaların 20cm dışarı ötelenmesi
- Ötelenmiş noktaya orijinal noktayla **aynı numara** verilmesi  
- Tüm "0" adlı noktalara **sıralı numara** atanması

işlemlerini **otomatik** yapar. NetCAD + DXF üzerinden elle yapılan bu işlem saatler sürerken, bu araçla **saniyeler** içinde tamamlanır.

## 🖥️ Ekran Görüntüsü

Programı çalıştırdığınızda karşınıza gelen arayüz:

- DXF ve TXT dosyalarını seçin
- Öteleme mesafesini ayarlayın
- BAŞLAT'a tıklayın
- NCN + DXF dosyaları otomatik oluşur

## 📋 Gereksinimler

- **Python 3.6+** (sadece .exe oluşturmak için)
- Ek kütüphane gerektirmez (tkinter, math, re — hepsi built-in)
- .exe oluşturduktan sonra Python'a ihtiyaç kalmaz

## 🚀 Kurulum

### Yöntem 1 — EXE olarak (Önerilen)

```bash
# 1. Python yükleyin (python.org)
# 2. Repoyu indirin
git clone https://github.com/KULLANICI_ADINIZ/mapeg-oteleme.git
cd mapeg-oteleme

# 3. EXE oluşturun
exe_olustur.bat
```

Artık `MAPEG_Oteleme.exe` dosyasını kullanabilirsiniz. Python gerekmez.

### Yöntem 2 — Python ile

```bash
python MAPEG_Oteleme.py
```

## 📖 Kullanım

### 1. Dosya Hazırlığı

NetCAD'den iki dosya export edin:
- **DXF dosyası** — `TELKESME`, `SEVALT`, `SEVUST` layerları içermeli
- **TXT koordinat dosyası** — TELKESME noktaları: `NoktaNo Y X Z`

### 2. Programı Çalıştırın

1. `MAPEG_Oteleme.exe`'yi açın
2. DXF dosyasını seçin
3. TXT koordinat dosyasını seçin  
4. Öteleme mesafesini ayarlayın (varsayılan: 0.20m)
5. **BAŞLAT**'a tıklayın

### 3. Çıktıları NetCAD'e Import Edin

Program iki dosya üretir:

| Dosya | İçerik |
|-------|--------|
| `*_TUMU.ncn` | Tüm noktalar (numaralı) + ötelenmiş noktalar |
| `*_otelenmis.dxf` | Sadece ötelenmiş POINT entity'leri |

**NetCAD'de import:**
1. Orijinal NCZ projesini açın
2. **Nokta Editörü → Dosya → Yükle** → `_TUMU.ncn` dosyasını seçin
3. **Çizime Sakla**

## ⚙️ Teknik Detaylar

### Algoritma

1. **DXF Parse** — TELKESME, SEVALT, SEVUST layerlarındaki LINE entity'leri okunur
2. **Zincir Oluşturma** — Uç uca bağlı LINE'lar polyline zincirlerine dönüştürülür
3. **Şev Altı Filtresi** — Her TELKESME noktası SEVALT koordinatlarıyla karşılaştırılır
4. **Koordinat Eşleştirme** — Nokta numaraları sıralı değil, koordinat bazlı eşleştirilir
5. **Akıllı Yön** — Öteleme yönü otomatik: en yakın SEVUST noktasından uzağa (dışarıya)
6. **Dik Öteleme** — Zincir üzerinde her noktanın normal vektörü hesaplanır, köşelerde ortalaması alınır

### Dosya Formatları

- **Girdi DXF**: AutoCAD DXF (AC1018+), cp1254 encoding
- **Girdi TXT**: `NoktaNo Y X Z` (boşluk/virgül/tab ayrımlı)
- **Çıktı NCN**: `NoktaAdi Y X Z` (NetCAD native format)
- **Çıktı DXF**: Orijinal DXF + OTELEME layerında POINT entity'leri

## 📁 Dosya Yapısı

```
mapeg-oteleme/
├── MAPEG_Oteleme.py    # Ana program (GUI + işlem mantığı)
├── exe_olustur.bat     # Tek tıkla .exe oluşturucu
├── BENIOKU.txt         # Türkçe kurulum rehberi
└── README.md           # Bu dosya
```

## 🤝 Katkıda Bulunma

Pull request'ler memnuniyetle karşılanır. Büyük değişiklikler için lütfen önce bir issue açın.

## 📄 Lisans

[MIT](LICENSE)

## 🏗️ Geliştirici Notları

Bu araç, maden mühendisleri için NetCAD üzerinden yapılan MAPEG İmalat Haritası öteleme işlemini otomatikleştirmek amacıyla geliştirilmiştir. Sadece Python standart kütüphanelerini kullanır, harici bağımlılık yoktur.
