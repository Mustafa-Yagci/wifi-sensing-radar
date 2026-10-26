# WiFi Motion Sensing: Sistem Mimarisi, Kurulum ve Sinyal İşleme Eğitim Tasarımı (Design Spec)

**Tarih:** 2026-10-22  
**Proje Konumu:** `E:\unipa kayıtları\unipa\proje`  
**Amaç:** WiFi Motion Sensing projesini yerel makinede (Windows) sıfırdan kurmak, çalıştırmak, test etmek ve tüm RF/Wi-Fi algılama matematiğini, yazılım mimarisini adım adım öğretmek.

---

## 1. Sistem Mimarisi & Bileşenler

WiFi Motion Sensing, tüketici sınıfı Wi-Fi kartlarının yaydığı ve aldığı elektromanyetik dalgalardaki **çok yollu sönümleme (multipath fading)** ve **faz/genlik bozulmalarını** analiz ederek oda içerisindeki hareketleri (insan yürümesi, nefes alma vb.) tespit eden cihazsız (device-free) bir radar sistemidir.

Mimari 4 ana katmandan oluşur:

```
[ Donanım Katmanı: Laptop Wi-Fi Kartı (wlanapi.dll) / ESP32 CSI Serial ]
                                │  ~10 Hz RSSI / CSI I-Q
                                ▼
[ Sinyal İşleme & Zeka Motoru: sensing/ ]
   ├── windows.py   : Native C-API ctypes bağlayıcı (WlanGetNetworkBssList)
   ├── detector.py  : Robust Baseline (Median + MAD), Z-skor, histeresis
   └── spectral.py  : Welch PSD Spektral Analizi (0.1-0.5 Hz Solunum, 1.0-4.0 Hz Hareket)
                                │
                                ▼
[ Backend & Olay Yönetimi: server.py ]
   ├── FastAPI REST API & WebSocket (/ws/radar @ 10 Hz)
   ├── aiosqlite Olay Günlüğü (Event Journal - Pre/Post Ring Buffer)
   └── Otomatik Kalibrasyon & Çift Sensör Füzyonu
                                │
                                ▼
[ Görselleştirme & Arayüz: frontend/ ]
   ├── React 19 + Vite SPA
   ├── Three.js (r160) 3D Gözlemevi (Observatory) - RF Dalga & Oda Simülasyonu
   └── Canlı İzleme Paneli (/monitor.html) - Gerçek Zamanlı Spektrogram & RSSI Grafikleri
```

---

## 2. RF Fiziği ve Odaya Yerleşim (Fresnel Bölgesi Prensibi)

Kullanıcının belirteceği telefon ve laptop konumlandırması şu fiziksel prensibe dayanır:

### Fresnel Bölgesi (Fresnel Zone) Mantığı:
- İki RF cihazı (örneğin telefon hotspot'ı verici - Tx, laptop Wi-Fi kartı alıcı - Rx) arasındaki en direkt yol **Line-of-Sight (Görüş Hattı)** olarak adlandırılır.
- Verici ve alıcı arasına elipsoit şeklinde enerji korunum bölgeleri (**Fresnel Zonları**) oturur.
- **Odada Karşılıklı Konumlandırma:** Telefon odanın bir ucunda, bilgisayar diğer ucunda olduğunda odanın tamamı 1. Fresnel Bölgesi'nin içine girer.
- Bir insan bu iki cihazın arasından geçtiğinde veya odada nefes alıp hareket ettiğinde, elektromanyetik dalgalar insan vücudundan yansıyarak doğrudan gelen dalgalarla yıkıcı veya yapıcı girişim (**Multipath Interference**) oluşturur.
- Bu girişim, alıcı kartın okuduğu **RSSI (Received Signal Strength Indicator)** değerinde ve **CSI (Channel State Information)** alt taşıyıcılarında milisaniyelik dalgalanmalar yaratır.

---

## 3. Kod Modüllerinin Öğretim Planı

1. **`sensing/windows.py`:**
   - Windows Native Wi-Fi API (`wlanapi.dll`) kütüphanesine `ctypes` ile struct tanımlanarak nasıl doğrudan ulaşıldığı incelenecektir.
   - `netsh` komut satırı hantallığı yerine C-seviyesi bellek çağrısıyla saniyede 10 örnek (10 Hz) alınmasının sırrı açıklanacaktır.
2. **`sensing/detector.py`:**
   - Neden standart sapma (std) ve ortalama (mean) yerine **Median ve MAD (Median Absolute Deviation)** kullanıldığı (aykırı gürültülere karşı dayanıklılık).
   - Çift yönlü histeresis (trigger/release) eşikleri: Yanlış alarmları önlemek için hareketin en az ~0.6 sn sürmesi ve sakinleşmenin en az 2 sn beklemesi kuralı.
3. **`sensing/spectral.py`:**
   - **Welch Power Spectral Density (PSD):** 30 saniyelik hareketli pencerede sinyalin FFT'sinin alınıp gürültüsüz güç spektrumuna dönüştürülmesi.
   - **Bant Ayrımı:**
     - Slow Band (0.1 - 0.5 Hz): Tipik göğüs kafesi nefes alma ritmi (dakikada 6-30 nefes).
     - Mid/Fast Band (1.0 - 4.0 Hz): Bacak ve kol hareketleri, oda içi adımlama frekansı.
4. **`server.py`:**
   - Asenkron FastAPI döngüsü, WebSocket yayıncısı ve SQLite'a olay anı öncesi/sonrası 30 saniyelik tamponun (pre/post buffer) yazılması.
5. **`frontend/`:**
   - Three.js tabanlı sanal oda, partikül ve dalga animasyonu, shader efektleri.

---

## 4. Kurulum ve Çalıştırma Adımları

- **Adım 1:** Python Sanal Ortam (.venv) oluşturulması, `requirements.txt` kurulumu (FastAPI, uvicorn, scipy, numpy, aiosqlite).
- **Adım 2:** `tests/` klasöründeki birim testlerin çalıştırılması (`pytest`) ile sinyal algılama motorunun doğrulanması.
- **Adım 3:** Frontend paketlerinin `npm.cmd ci` ile kurulması ve `npm.cmd run build` ile `frontend/dist/` dizinine derlenmesi.
- **Adım 4:** İlk yerel simülasyon testi ile sistemin 3D UI ve WebSocket iletişiminin test edilmesi.
- **Adım 5:** Kullanıcıya haber verilerek telefonun ve bilgisayarın odada konumlandırılması, canlı donanım modunun başlatılması ve 20 saniyelik arka plan kalibrasyonunun yapılması.

---

## 5. Doğrulama Kriterleri (Success Criteria)

- [ ] Python bağımlılıkları eksiksiz kurulmuş ve `.venv` içinde aktif olmalı.
- [ ] `tests/test_engine_v6.py`, `tests/test_live_sensing.py`, `tests/test_live_api.py` testleri başarıyla geçmeli.
- [ ] Frontend `dist/index.html` hatasız derlenmeli.
- [ ] `http://127.0.0.1:8000` açıldığında WebSocket bağlantısı kurulmalı, 3D Gözlemevi ve `/monitor.html` canlı veri göstermeli.
- [ ] Her aşamada RF fiziği, C/ctypes donanım çağrıları ve sinyal işleme formülleri kullanıcıya detaylıca açıklanmalı.
