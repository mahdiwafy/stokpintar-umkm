# StokPintar UMKM — Asisten Operasional Stok & Kasir Cerdas Berbasis Google AI

> **Kompetisi:** LOGICODIX 2026 — HIMTI Universitas Negeri Surabaya (UNESA)  
> **Kategori:** Web App  
> **Subtema 03:** Local MSME & Creative Economy (Digitalisasi Bisnis UMKM)  
> **Nama Tim:** **ADUH KEPENCETT**

---

## 📌 Latar Belakang Masalah (Problem Statement)

Berdasarkan studi lapangan langsung pada pedagang toko kelontong dan warung makan mikro:
1. **Desinkronisasi Kas dan Stok Barang:** Pedagang sibuk melayani pembeli dan menerima uang tunai, sehingga tidak sempat mengurangi stok di buku catatan. Akibatnya, stok yang tercatat selalu berselisih dengan kondisi fisik di rak.
2. **Waktu Pelayanan Lambat & Pengecekan Berulang:** Saat ada pembeli ingin membeli suatu barang, pedagang harus mondar-mandir mengecek rak fisik karena data catatan tidak dapat dipercaya, menyebabkan antrean panjang dan risiko pelanggan batal membeli.
3. **Pencatatan Kulakan Manual:** Belanja barang baru dari pasar grosir dicatat dengan mengetik ulang nota belanja kertas, yang rentan salah hitung dan memakan waktu istirahat pedagang.

---

## 💡 Solusi: StokPintar UMKM

**StokPintar UMKM** adalah purwarupa aplikasi web (*Minimum Viable Product / MVP*) responsif yang menyatukan arus kasir penjualan dengan mutasi stok fisik secara atomik dalam satu ketukan, didukung oleh kecerdasan buatan **Google Gemini AI**.

### 🌟 Fitur Utama
1. **Kasir Cepat POS & Pengurangan Stok Otomatis:**
   - Kasir memilih barang atau menggunakan pendiktean suara santai (misal: *"laku beras 5kg 1 karung"*).
   - Setiap transaksi penjualan secara **otomatis dan seketika langsung memotong stok fisik** di database dalam satu transaksi atomik.
   - Sistem menolak penjualan jika stok fisik tidak mencukupi, mencegah janji palsu ke pembeli.
2. **Audit Fisik Cepat (*1-Tap Stock Reconciliation*):**
   - Jika ada barang rusak, susut, atau kemasan bocor, pedagang cukup menekan tombol "Audit Fisik" untuk menyamakan stok sistem dengan rak tanpa perlu rumus matematika rumit.
3. **Scan Nota Kulakan Otomatis (Google Gemini Vision):**
   - Cukup foto nota/struk belanja grosir, model Vision AI mengekstrak daftar barang, kuantitas, dan harga beli, lalu menambahkan stok ke gudang secara instan.
4. **Google Gemini Smart Inventory Advisor:**
   - Menganalisis barang-barang yang mendekati batas minimum (`min_stock`) dan memberikan rekomendasi taktis daftar belanja kulakan prioritas serta estimasi modal kas yang harus disiapkan.

---

## 🛠️ Arsitektur Teknologi & Prinsip Green IT

* **Frontend:** Responsive Web App (HTML5, Tailwind CSS, Vanilla JS responsif untuk viewport mobile 390px).
* **Backend:** Python FastAPI (Asynchronous, performa tinggi, sub-25ms latency).
* **Database:** SQLite dengan Write-Ahead Logging (`WAL Mode`) & Foreign Key Constraints aktif untuk jaminan konsistensi transaksi keuangan.
* **AI Engine:** Google Gemini 1.5 Flash via REST API resmi (`generativelanguage.googleapis.com`) dengan structured JSON outputs.
* **Prinsip Green IT & Efisiensi:**
  - Tanpa dependensi runtime berat.
  - Caching katalog barang di sisi klien untuk meminimalisir payload jaringan dan menghemat konsumsi energi perangkat pedagang.

---

## 🚀 Panduan Menjalankan di Localhost

### 1. Persyaratan Sistem
- Python 3.10 atau versi lebih baru
- Pip package manager

### 2. Instalasi Dependensi
```bash
# Clone repositori
git clone https://github.com/mahdiwafy/stokpintar-umkm.git
cd stokpintar-umkm

# Install pustaka yang dibutuhkan
pip install fastapi uvicorn pydantic httpx pytest
```

### 3. Menjalankan Aplikasi
```bash
# Jalankan runner script
./run.sh

# Atau jalankan via uvicorn langsung
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8090 --reload
```

Buka peramban di:
- **Aplikasi Web:** `http://localhost:8090`
- **Dokumentasi Interaktif API (Swagger UI):** `http://localhost:8090/docs`

### 4. Menjalankan Pengujian Otomatis (*Automated Tests*)
```bash
python3 -m pytest tests/ -v
```

---

## 👥 Profil Tim Pengembang (ADUH KEPENCETT)

* **Rafi Yusuf Pratama Herdiyanto** (Ketua — S1 Teknik Informatika UNESA)
* **Muhammad Guntur Cahyadi Putra** (Anggota — S1 Teknik Informatika UNESA)
* **Muhammad Dzikri Arsyad** (Anggota — S1 Teknik Informatika UNESA)
* **Taufiq Mahdi Wafy** (Anggota — S1 Pendidikan Teknologi Informasi UNESA)

---
*Dibuat untuk Hackathon LOGICODIX 2026 — “NextGen Digital Innovation: Crafting Creative Solutions for a Better Society”.*
