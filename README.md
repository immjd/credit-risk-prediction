# Prediksi Risiko Kredit (Home Credit Default Risk)

**Demo:** [creditriskcounter.onrender.com](https://creditriskcounter.onrender.com)

Project machine learning tabular end-to-end untuk memprediksi nasabah yang berpotensi gagal bayar, memakai dataset [Home Credit Default Risk](https://www.kaggle.com/competitions/home-credit-default-risk) dari Kaggle. Cakupannya: data multi-tabel di PostgreSQL, fitur agregat lewat SQL, kelas tidak seimbang, perbandingan model, tuning Optuna, penjelasan SHAP, kebijakan keputusan berbasis nilai finansial, dan API prediksi (FastAPI + Docker).

## Hasil utama

Model final: LightGBM hasil tuning, **tanpa** atribut `code_gender`, dievaluasi pada test set (46.127 nasabah, tidak disentuh selama pemilihan model).

| Metrik (test)             | Nilai  |
| ------------------------- | ------ |
| ROC-AUC                   | 0,7893 |
| PR-AUC (baseline = 0,081) | 0,2822 |
| Brier score               | 0,0659 |

- Probabilitas terkalibrasi, sehingga bisa langsung dipakai untuk keputusan berbasis nilai finansial.
- Pada model dengan `code_gender` (ROC-AUC 0,7913), 30% nasabah berisiko tertinggi memuat sekitar 70% dari semua gagal bayar.
- Membuang `code_gender` hanya menurunkan ROC-AUC 0,002; hasil kebijakan hampir tidak berubah.

### Perbandingan model (validation set)

| Model               | Penanganan imbalance | ROC-AUC | PR-AUC |
| ------------------- | -------------------- | ------- | ------ |
| LightGBM            | tanpa bobot          | 0,7844  | 0,2829 |
| XGBoost             | scale_pos_weight     | 0,7835  | 0,2766 |
| LightGBM            | scale_pos_weight     | 0,7833  | 0,2781 |
| Logistic Regression | class_weight         | 0,7712  | 0,2580 |
| Random Forest       | class_weight         | 0,7658  | 0,2490 |

Pembobotan kelas tidak memperbaiki ROC-AUC dan tidak dibutuhkan untuk peringkat risiko. Tanpa pembobotan, probabilitas tetap terkalibrasi.

### Faktor risiko dan tindakan (ringkas)

Berdasarkan SHAP (menjelaskan perilaku model, bukan sebab-akibat):

- Skor kredit eksternal rendah adalah faktor terkuat. Jadikan penyaring utama.
- Beban cicilan tinggi, tenor pendek, dan kredit melebihi harga barang menaikkan risiko. Batasi rasio cicilan dan minta uang muka.
- Keterlambatan cicilan setahun terakhir dan tunggakan di lembaga lain menaikkan risiko. Pasang peringatan dini.
- Sekitar 42% pengaruh model berasal dari fitur agregat tabel selain data aplikasi.

Kebijakan ilustrasi (asumsi untung 10%, rugi 60%): menolak pemohon dengan `p ≥ 0,143` menurunkan default rate yang disetujui dari 8,07% ke 4,85% dan menaikkan profit sekitar 21% dibanding menyetujui semua. Asumsi finansial ini bukan data Home Credit. Laporan lengkap, termasuk sensitivitas dan keterbatasan: [`reports/business_interpretation.md`](reports/business_interpretation.md).

## Tech stack

Python, pandas, scikit-learn, XGBoost, LightGBM, Optuna, SHAP, PostgreSQL + SQL, FastAPI, Docker.

## Dataset

Home Credit Default Risk (Kaggle), 8 tabel:

| Tabel                 | Jumlah baris |
| --------------------- | ------------ |
| application_train     | 307.511      |
| application_test      | 48.744       |
| bureau                | 1.716.428    |
| bureau_balance        | 27.299.925   |
| previous_application  | 1.670.214    |
| pos_cash_balance      | 10.001.358   |
| installments_payments | 13.605.401   |
| credit_card_balance   | 3.840.312    |

Data mentah **tidak** disertakan. Unduh dari halaman kompetisi Kaggle dan ekstrak ke `data/raw/`.

## Alur kerja

1. **Data:** CSV dimuat ke PostgreSQL (schema `raw`).
2. **Fitur (SQL):** agregasi per nasabah dari bureau, previous_application, POS, cicilan, dan kartu kredit ke schema `features`, lalu digabung menjadi `features.model_train` (307.511 baris, 165 kolom termasuk fitur turunan rasio).
3. **Pemodelan:** split stratified 70/15/15, perbandingan lima konfigurasi model, tuning Optuna (30 percobaan, 3-fold CV).
4. **Interpretasi:** SHAP (beeswarm, dependence, waterfall) dan analisis bisnis.
5. **Eksperimen fairness:** retrain tanpa `code_gender`.
6. **Serving:** model final diekspor dan dilayani lewat FastAPI di Docker.

## Struktur project

```
credit-risk-project/
├── data/raw/                  # CSV Home Credit (tidak di-commit)
├── notebooks/
│   ├── 01_eda.ipynb
│   ├── 02_modeling.ipynb
│   ├── 03_tuning_final.ipynb
│   ├── 04_shap_interpretation.ipynb
│   ├── 05_business_interpretation.ipynb
│   └── 06_no_gender_experiment.ipynb
├── sql/                       # 01-04: pembuatan fitur dan features.model_train
├── src/                       # db, loader, data, run_sql, train_final
├── api/main.py                # FastAPI
├── api/static/index.html      # halaman web uji coba
├── models/                    # lgbm_final.txt, metadata.json, best_params.json
├── reports/                   # business_interpretation.md
├── Dockerfile                 # image API
├── docker-compose.yml         # PostgreSQL
└── requirements.txt
```

## Cara menjalankan

### 1. Persiapan dan database

```
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt python-dotenv
```

Buat `.env` di folder utama (jangan di-commit):

```
POSTGRES_USER=isi_username
POSTGRES_PASSWORD=isi_password
POSTGRES_DB=credit_risk
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

```
docker compose up -d
python src\load_to_postgres.py
python src\run_sql.py sql\01_bureau_features.sql
python src\run_sql.py sql\02_previous_application_features.sql
python src\run_sql.py sql\03_payment_features.sql
python src\run_sql.py sql\04_model_train.sql
```

### 2. Notebook dan model final

Jalankan notebook 01 sampai 06 berurutan (kernel `.venv`), lalu ekspor model final:

```
python -m src.train_final
```

### 3. API

Tanpa Docker:

```
pip install fastapi uvicorn
uvicorn api.main:app --reload
```

Dengan Docker:

```
docker build -t credit-risk-api .
docker run --rm -p 8000:8000 credit-risk-api
```

Halaman web uji coba (form, contoh profil, hasil dan faktor risiko) ada di `http://localhost:8000/`. Dokumentasi interaktif API di `http://localhost:8000/docs`. Endpoint: `GET /health`, `GET /model-info`, `GET /features`, `POST /predict`.

Contoh permintaan `POST /predict` (fitur yang tidak diisi dianggap kosong, fitur turunan seperti rasio kredit terhadap pendapatan dan rata-rata skor eksternal dihitung otomatis):

```json
{
  "features": {
    "name_contract_type": "Cash loans",
    "amt_income_total": 90000,
    "amt_credit": 900000,
    "amt_annuity": 45000,
    "amt_goods_price": 700000,
    "days_birth": -9500,
    "days_employed": -200,
    "cnt_fam_members": 4,
    "ext_source_1": 0.1,
    "ext_source_2": 0.15,
    "ext_source_3": 0.12
  }
}
```

Respons berisi probabilitas gagal bayar, kelompok risiko (A sampai D), keputusan, tiga faktor risiko teratas, dan peringatan bila fitur yang diisi terlalu sedikit.

## Hosting

Image Docker membaca port dari variabel `PORT` (default 8000), jadi bisa langsung dipakai di Render, Railway, atau Cloud Run. Contoh di Render: _New > Web Service_, hubungkan repositori GitHub, pilih runtime **Docker**, plan Free. Halaman web dan API tersedia di satu URL. Plan gratis akan tidur saat tidak dipakai, sehingga permintaan pertama bisa lambat.

## Keterbatasan

- Asumsi finansial (untung 10%, rugi 60%) hanya ilustrasi.
- Dataset kemungkinan hanya memuat pinjaman yang pernah disetujui (potensi bias seleksi, belum diverifikasi).
- Evaluasi memakai satu kali split; selisih antar model boosting kecil dan belum diuji signifikansinya.
- Skor eksternal tidak transparan, dan tiga skor itu menghasilkan alasan yang redundan pada penjelasan per nasabah.
- Membuang `code_gender` tidak menjamin bebas bias karena fitur lain bisa menjadi proxy. Diperlukan audit fairness lebih lanjut.
- API menerima input parsial; semakin sedikit fitur yang diisi, semakin kurang andal prediksinya. Fitur agregat dari tabel riwayat (bureau, cicilan, dll.) harus diisi pemanggil.
- Data historis; kalibrasi dan distribusi fitur perlu dipantau jika dipakai nyata.

## Progres

- [x] Setup project, PostgreSQL (Docker), dan loader data
- [x] EDA
- [x] Fitur agregat multi-tabel lewat SQL
- [x] Perbandingan model dan penanganan imbalance
- [x] Tuning Optuna
- [x] Interpretasi SHAP
- [x] Interpretasi bisnis
- [x] Eksperimen tanpa `code_gender`
- [x] API prediksi (FastAPI) dan Docker
