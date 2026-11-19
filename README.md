# 📱 Phone Farm Dashboard (Zero-Lag)

Aplikasi Desktop terpadu untuk mengelola dan memantau **1 hingga 20 perangkat Android** secara bersamaan dalam satu jendela dashboard tanpa lag.

Menggunakan teknik **Native Win32 Docking** yang langsung meng-embed engine `scrcpy` asli ke dalam panel grid. Hasilnya, performa video rendering (Direct3D 11 Hardware Decoding) dan responsivitas remote sentuhan **100% identik dengan scrcpy asli (latensi ~35ms, bebas lag)**.

---

## 🚀 Cara Menjalankan

1. Hubungkan HP Android ke komputer via kabel USB atau Wi-Fi.
2. Pastikan **USB Debugging** sudah aktif di Opsi Pengembang (Developer Options) HP.
3. Jalankan aplikasi dengan salah satu cara berikut:
   - **📦 Portable EXE (Tanpa Perlu Python):**
     Klik ganda file [`dist\PhoneFarmDashboard.exe`](dist/PhoneFarmDashboard.exe). Dapat dipindahkan dan dijalankan di komputer Windows mana saja secara mandiri!
   - **⚡ Launcher Praktis:**
     Klik ganda file [`run_farm.bat`](run_farm.bat) (otomatis memilih Python atau Portable EXE).
   - **🐍 Lewat Terminal (Python Source):**
     ```powershell
     python src\main.py
     ```
4. Semua HP yang terhubung akan otomatis terdeteksi dan layarnya langsung muncul dalam grid!

---

## 🛠️ Kompilasi / Build Portable EXE

Jika Anda mengubah source code dan ingin mengompilasi ulang menjadi single-file executable portable:
1. Klik ganda file [`build_exe.bat`](build_exe.bat).
2. Skrip otomatis memeriksa dependensi (`pyinstaller`, `pillow`), mengenerate icon `app.ico`, dan mengemas seluruh binary ADB & scrcpy ke dalam satu file mandiri:
   ```
   dist\PhoneFarmDashboard.exe
   ```

---

## 🌟 Fitur Utama

### 1. Unified Grid Matrix (1 s/d 20 Device)
- Seluruh HP tertata rapi dalam satu jendela dashboard.
- Pilihan layout grid: **2 Kolom**, **3 Kolom**, **4 Kolom**, **5 Kolom**, atau **6 Kolom**.
- Masing-masing slot menampilkan:
  - Nama model HP & Serial.
  - Persentase baterai real-time & indikator charging ⚡.
  - Suhu perangkat (°C) real-time.
  - Tombol navigasi cepat di bawah layar: **◀ Back**, **🏠 Home**, **📱 Recents**, **⚡ Screen Off**, dan **👑 Set Master**.

### 2. Zero-Lag Remote Control
- Mengetik, klik, dan swipe mouse langsung direspons oleh engine scrcpy tanpa transcoding atau buffer video perantara.
- Latensi ultra-rendah ~35ms.

### 3. Sync Action / Broadcast Control (Multi-Control)
- Centang opsi **`🔴 Sync Action`** di toolbar atas.
- Pilih salah satu HP sebagai **Master** (klik tombol `👑 Master` pada HP tersebut).
- Semua tombol navigasi yang Anda tekan (Home, Back, Recents, Screen Off) serta teks yang Anda ketik akan diduplikasi serentak ke seluruh HP lainnya!

### 4. Manajemen Massal (Bulk Tools)
Di menu **`⚡ Manajemen Massal ▼`**:
- **📦 Bulk Install APK:** Pilih file `.apk` di PC, otomatis terinstall serentak ke 20 HP dengan status progress real-time.
- **💻 Bulk Shell Command:** Jalankan satu baris perintah `adb shell` (misal buka aplikasi, clear cache, cek konfigurasi) ke seluruh HP sekaligus.
- **📝 Broadcast Teks:** Ketik teks di PC dan tekan Enter untuk mengetikkannya ke seluruh HP.
- **⚡ Matikan Layar Fisik Semua HP:** Mematikan layar AMOLED/LCD fisik HP agar hemat daya dan tidak panas, namun mirroring di dashboard tetap hidup!
- **☀️ Hidupkan Layar Fisik Semua HP:** Membangunkan kembali layar HP.
- **🔄 Reboot Seluruh HP:** Merestart semua perangkat secara paralel.

---

## ⚙️ Optimasi Performa (Preset Kualitas)

Anda dapat memilih preset di dropdown toolbar atas sesuai jumlah HP yang Anda jalankan:

| Preset | Resolusi | FPS | Bitrate | Cocok Untuk |
| :--- | :--- | :--- | :--- | :--- |
| **High Quality** | 1080px | 60 fps | 4 Mbps | 1 – 4 HP |
| **Balanced** | 800px | 30 fps | 2 Mbps | 5 – 12 HP *(Rekomendasi)* |
| **Farm Max** | 540px | 25 fps | 1.2 Mbps | 13 – 20 HP *(Paling Ringan)* |

---

## 📁 Struktur Folder

```
android-farm/
├── dist/                      # Folder output Portable Executable
│   └── PhoneFarmDashboard.exe # 📦 Portable EXE Mandiri (Zero-Install)
├── bin/                       # Engine scrcpy v5.0.1 & ADB binaries (Win64)
│   ├── scrcpy.exe
│   ├── scrcpy-server
│   ├── adb.exe
│   └── *.dll
├── src/                       # Source Code Dashboard Python
│   ├── __init__.py
│   ├── config.py              # Konfigurasi preset, path portable & tema
│   ├── win32_dock.py          # Modul Windows API zero-lag docking
│   ├── adb_manager.py         # Modul komunikasi ADB & telemetri HP
│   ├── scrcpy_manager.py      # Pengelola proses scrcpy
│   ├── sync_engine.py         # Mesin sinkronisasi multi-device & broadcast
│   ├── ui_components.py       # Komponen visual (DeviceCard, Centered Modals)
│   └── main.py                # Jendela utama aplikasi & dynamic canvas
├── app.ico                    # Multi-resolution Windows App Icon
├── PhoneFarmDashboard.spec    # Konfigurasi build PyInstaller
├── build_exe.bat              # 🛠️ Skrip 1-Klik Kompilasi ke Portable EXE
├── run_farm.bat               # 🚀 Launcher Pintar (Python / EXE)
└── README.md                  # Dokumentasi Project
```
