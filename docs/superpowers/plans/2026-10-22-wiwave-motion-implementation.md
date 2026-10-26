# WiWave Motion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** WiWave Motion projesini yerel Windows makinesinde tamamen kurmak, test etmek, çalıştırmak ve kullanıcının her modülün RF/yazılım mantığını öğrenmesini sağlamak.

**Architecture:** Python 3.13 venv üzerinde FastAPI + ctypes Windows Native WLAN + Welch PSD sinyal analizi backend'i ve React 19 + Three.js 3D Gözlemevi frontend'i.

**Tech Stack:** Python 3.13, FastAPI, uvicorn, scipy, numpy, aiosqlite, React 19, Three.js, Vite, Node.js.

**Spec:** `docs/superpowers/specs/2026-10-22-wiwave-motion-design.md`

## Global Constraints

- Proje dizini: `E:\unipa kayıtları\unipa\proje`
- Python versiyonu: Python 3.13.1
- Node / npm: Windows PowerShell üzerinde `npm.cmd` kullanılmalı (`.ps1` script execution policy kısıtlamasına takılmamak için).
- Canlı donanım testi öncesinde kullanıcıya telefon ve PC'yi konumlandırması için bildirim verilmeli.
- Her adımda teorik ve kodlama mantığı öğretilerek ilerlenmeli.

---

### Task 1: Python Sanal Ortam (.venv) ve Bağımlılıkların Kurulumu

**Files:**
- Create/Initialize: `E:\unipa kayıtları\unipa\proje\.venv`
- Read: `E:\unipa kayıtları\unipa\proje\requirements.txt`
- Read: `E:\unipa kayıtları\unipa\proje\requirements-dev.txt`

**Interfaces:**
- Consumes: Sistem Python 3.13 yorumlayıcısı
- Produces: `.venv\Scripts\python.exe` ve kurulu Python kütüphaneleri (FastAPI, scipy, numpy, aiosqlite, pytest)

- [ ] **Step 1: Sanal ortamı (.venv) oluştur**
  Run: `python -m venv "E:\unipa kayıtları\unipa\proje\.venv"`
- [ ] **Step 2: Pip'i güncelle ve temel bağımlılıkları yükle**
  Run: `.\.venv\Scripts\python.exe -m pip install --upgrade pip`
  Run: `.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt`
- [ ] **Step 3: Paketlerin kurulumunu doğrula**
  Run: `.\.venv\Scripts\python.exe -c "import fastapi, uvicorn, scipy, numpy, aiosqlite, pytest; print('ALL PACKAGES OK')"`

---

### Task 2: Birim Testlerin Koşulması ve Sinyal Analiz Motorunun Doğrulanması

**Files:**
- Test: `tests/test_live_sensing.py`
- Test: `tests/test_engine_v6.py`
- Test: `tests/test_live_api.py`

**Interfaces:**
- Consumes: `sensing/detector.py`, `sensing/spectral.py`, `sensing/sources.py`, `server.py`
- Produces: Test raporu ve matematiksel doğrulama

- [ ] **Step 1: Testleri çalıştır**
  Run: `.\.venv\Scripts\python.exe -m pytest tests/ -v`
- [ ] **Step 2: Test sonuçlarını doğrula ve olası platform/kütüphane uyumsuzluklarını incele**
  Expected: Tüm testlerin yeşil (PASSED) olması.

---

### Task 3: Kod Mimarisi ve Sinyal İşleme Matematiğinin Öğretici Analizi

**Files:**
- Read/Explain: `sensing/windows.py`
- Read/Explain: `sensing/detector.py`
- Read/Explain: `sensing/spectral.py`
- Read/Explain: `server.py`

**Interfaces:**
- Consumes: Projenin Python kaynak kodları
- Produces: Kullanıcıya yönelik detaylı mühendislik ve RF öğretim içeriği

- [ ] **Step 1: `sensing/windows.py` - ctypes ile Windows WLAN API İncelemesi**
  Açıklanacaklar: `wlanapi.dll`, `WlanOpenHandle`, `WlanGetNetworkBssList`, C struct'ları ve 10 Hz okuma hızı.
- [ ] **Step 2: `sensing/detector.py` - Robust Baseline & Histeresis Algoritması**
  Açıklanacaklar: Medyan, MAD (Median Absolute Deviation), dinamik Z-skoru, histeresis penceresi.
- [ ] **Step 3: `sensing/spectral.py` - Welch Spektral Güç Yoğunluğu (PSD)**
  Açıklanacaklar: FFT pencereleme, 0.1-0.5 Hz (solunum) ve 1.0-4.0 Hz (yürüme) frekans analizi.
- [ ] **Step 4: `server.py` - WebSocket, Çift Sensör Füzyonu ve Olay Kaydı**
  Açıklanacaklar: Asenkron döngü, pre/post olay halka tamponu (ring buffer), SQLite veritabanı.

---

### Task 4: Frontend Paketlerinin Kurulumu ve Dashboard Derlemesi (React 19 + Three.js)

**Files:**
- Read: `frontend/package.json`
- Target: `frontend/dist/index.html`

**Interfaces:**
- Consumes: `frontend/src/`, `frontend/observatory/`
- Produces: `frontend/dist/` statik web varlıkları (HTML/JS/CSS/Three.js bundle)

- [ ] **Step 1: Frontend bağımlılıklarını kur**
  Run: `npm.cmd ci` (veya `npm.cmd install` `frontend/` dizininde)
- [ ] **Step 2: Üretim (production) sürümünü derle**
  Run: `npm.cmd run build` `frontend/` dizininde
- [ ] **Step 3: `dist/index.html` ve varlıkların oluştuğunu doğrula**
  Run: `Test-Path "E:\unipa kayıtları\unipa\proje\frontend\dist\index.html"`

---

### Task 5: Uçtan Uca Simülasyon Testi ve Sistem Doğrulaması

**Files:**
- Execute: `server.py` (simülasyon modunda)
- Test script: `scripts/verify-stream.py`

**Interfaces:**
- Consumes: `server.py`, `frontend/dist/`
- Produces: Canlı HTTP ve WebSocket yayını (`http://127.0.0.1:8000`)

- [ ] **Step 1: Arka planda simülasyon modunda sunucuyu başlat**
  Run: `$env:SIMULATION_MODE='true'; $env:WIWAVE_SOURCE='rssi_simulation'; .\.venv\Scripts\python.exe -B server.py`
- [ ] **Step 2: Sağlık endpoint'ini ve WebSocket akışını doğrula**
  Run: `curl.exe http://127.0.0.1:8000/api/health`
  Run: `.\.venv\Scripts\python.exe scripts/verify-stream.py`
- [ ] **Step 3: Tarayıcı ile arayüzün (Three.js 3D Observatory ve Live Monitor) açıldığını teyit et**

---

### Task 6: Canlı Donanım Modu, Fresnel Bölgesi Konumlandırması ve Kalibrasyon

**Files:**
- Execute: `scripts/start-live.ps1`

**Interfaces:**
- Consumes: Gerçek fiziksel Wi-Fi adaptörü ve telefon bağlantısı
- Produces: Gerçek ortam RF hareket algılama

- [ ] **Step 1: Kullanıcıyı telefon ve PC yerleşimi için bilgilendir**
  Açıklama: Telefonun hotspot'ını açıp odanın bir ucuna, laptop'ı diğer ucuna yerleştirme yönergesi.
- [ ] **Step 2: Kullanıcı onayından sonra canlı modu başlat**
  Run: `.\scripts\start-live.ps1`
- [ ] **Step 3: 20 saniyelik oda arka plan kalibrasyonunu izle ve ilk hareket testini doğrula**
