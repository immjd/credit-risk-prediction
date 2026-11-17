# Interpretasi Bisnis: Prediksi Risiko Kredit (Home Credit)

Ringkasan dari hasil model LightGBM yang dilatih pada dataset Home Credit Default Risk (307.511 pemohon, gagal bayar 8,07%). Semua angka performa dihitung di **test set** (46.127 pemohon) yang tidak dipakai untuk memilih model maupun parameter.

> **Catatan versi model:** analisis di bagian 2 sampai 5 dilakukan pada model LightGBM tuning yang masih memakai `code_gender` (ROC-AUC test 0,7913). Model final yang dipakai API dilatih ulang **tanpa** `code_gender` (ROC-AUC test 0,7893, lihat bagian 6). Selisihnya kecil, tetapi angka kelompok risiko dan profit di bawah belum dihitung ulang untuk model final. Batas kelompok model final: D ≤ 0,027, C ≤ 0,082, B ≤ 0,190.

> **Penting:** angka finansial (margin untung 10%, kerugian 60% dari jumlah kredit) adalah **asumsi ilustrasi**, bukan data Home Credit. Yang bisa dipegang adalah pola dan arah keputusannya, bukan nilai rupiah atau mata uangnya.

## 1. Ringkasan

- Model memisahkan risiko dengan baik: ROC-AUC 0,791, PR-AUC 0,285 (garis dasar 0,081), dan probabilitasnya **terkalibrasi** (prediksi 30,6% pada kelompok paling berisiko vs kenyataan 30,7%).
- 30% pemohon dengan risiko tertinggi (kelompok A dan B) menyumbang sekitar 70% dari seluruh gagal bayar. 30% pemohon paling aman (kelompok D) hanya menyumbang 5,3%.
- Faktor yang paling memengaruhi risiko: skor kredit eksternal, beban cicilan, keterlambatan cicilan sebelumnya, dan tunggakan di lembaga lain.
- Dengan asumsi ilustrasi, menolak pemohon di atas ambang `p = 0,143` (sekitar 15% pemohon) menurunkan default rate pemohon yang disetujui dari 8,07% ke 4,85% dan menaikkan profit sekitar 21% dibanding menyetujui semua.
- Kebijakan berbasis model tidak lebih buruk dari "setujui semua" di 9 skenario asumsi yang diuji.

## 2. Kelompok risiko (test set)

Batas probabilitas ditentukan dari validation set: D ≤ 0,027 < C ≤ 0,082 < B ≤ 0,188 < A.

| Kelompok | Pemohon | % pemohon | Default rate | Lift | % dari semua gagal bayar | Tindakan yang diusulkan |
|---|---|---|---|---|---|---|
| A - Sangat tinggi | 4.711 | 10,2% | 30,65% | 3,80 | 38,8% | Tolak, atau setujui hanya dengan uang muka/jaminan tinggi |
| B - Tinggi | 8.985 | 19,5% | 12,98% | 1,61 | 31,3% | Tinjau manual; batasi plafon dan tenor |
| C - Sedang | 18.520 | 40,2% | 4,96% | 0,61 | 24,7% | Setujui standar dengan pemantauan pembayaran |
| D - Rendah | 13.911 | 30,2% | 1,41% | 0,17 | 5,3% | Jalur cepat otomatis; kandidat penawaran limit lebih tinggi |

Default rate turun mulus dari A ke D, dan rata-rata prediksi tiap kelompok dekat dengan kenyataannya (A: 30,6% vs 30,65%; D: 1,7% vs 1,41%).

## 3. Faktor yang memengaruhi risiko dan tindakannya

Berdasarkan analisis SHAP pada 10.000 pemohon test. SHAP menjelaskan perilaku model, **bukan sebab-akibat**, jadi tindakan di bawah sebaiknya diuji lewat pilot sebelum diterapkan penuh.

| Faktor | Arah pengaruh | Tindakan yang masuk akal |
|---|---|---|
| Skor kredit eksternal rendah (`ext_source_1/2/3`, gabungan 17% dari total pengaruh) | Skor tinggi menurunkan risiko; lonjakan risiko terutama pada skor sangat rendah | Jadikan penyaring utama; eskalasi pemohon dengan skor sangat rendah ke tinjauan manual atau persyaratan lebih ketat |
| Beban cicilan tinggi (`amt_annuity` tinggi, `credit_term_months` rendah / tenor pendek) | Cicilan besar dan tenor pendek menaikkan risiko | Batasi rasio cicilan terhadap penghasilan; uji penawaran tenor lebih panjang |
| Kredit melebihi harga barang (`credit_goods_ratio` tinggi) | Menaikkan risiko | Batasi pembiayaan di atas harga barang, atau minta uang muka |
| Keterlambatan cicilan setahun terakhir (`inst_n_late_last_year`) | Makin sering telat, makin berisiko | Sistem peringatan dini: pengingat lebih awal dan penagihan proaktif; tahan kenaikan limit |
| Utang dan tunggakan di lembaga lain (`bureau_debt_credit_ratio`, `bureau_overdue_sum`) | Rasio utang dan tunggakan tinggi menaikkan risiko | Cek tunggakan di biro kredit saat penilaian; batasi plafon bagi yang rasio utangnya tinggi |

Sekitar 42% dari seluruh pengaruh model berasal dari fitur agregat lima tabel selain data aplikasi (riwayat pengajuan sebelumnya, cicilan, biro kredit, kartu kredit, POS), jadi riwayat perilaku nyata menambah nilai di luar data aplikasi.

## 4. Kebijakan persetujuan berdasarkan nilai finansial

Jika kredit disetujui: untung `PROFIT_RATE x kredit` bila lunas, rugi `LOSS_RATE x kredit` bila gagal bayar. Karena probabilitas terkalibrasi, kredit layak disetujui selama `p < PROFIT_RATE / (PROFIT_RATE + LOSS_RATE)`.

Pada asumsi 10% / 60% (ambang `p* = 0,143`):

| Kebijakan | % disetujui | Default rate disetujui | Profit (juta, unit data) |
|---|---|---|---|
| Setujui semua | 100% | 8,07% | 1.328,7 |
| Ambang teoretis (p < 0,143) | 84,7% | 4,85% | 1.611,4 |
| Ambang optimal dari validation (p <= 0,142) | 84,6% | 4,85% | 1.610,1 |

- Ambang teoretis hampir identik dengan ambang optimal yang dicari dari data, sebagai bukti kalibrasi yang baik.
- Ambang 0,143 jatuh di dalam kelompok B: kebijakan ini setara menolak seluruh kelompok A (10,2%) dan bagian atas kelompok B (sekitar 5%).
- Kurva profit landai di sekitar puncak (sekitar 80% sampai 88% persetujuan), jadi hasilnya tidak sensitif terhadap pergeseran ambang kecil.
- Sekitar separuh dari seluruh gagal bayar berada di antara pemohon yang ditolak (perkiraan dari tabel di atas).

**Sensitivitas.** Manfaat model paling besar saat margin tipis dan kerugian besar (untung 5%, rugi 80%: setujui semua rugi 357,3 juta, kebijakan model untung 466,1 juta, dengan 59,4% disetujui) dan paling kecil saat margin tinggi dan kerugian kecil (untung 20%, rugi 40%: tambahan hanya sekitar 0,9%, dengan 96,9% disetujui). Rasio kerugian terhadap margin menentukan seberapa besar model berguna.

## 5. Alasan di balik keputusan

Pada tiga pemohon berisiko tertinggi (prediksi 79% sampai 84%, ketiganya memang gagal bayar), faktor pendorong utamanya adalah skor eksternal yang sangat rendah, dan pada dua di antaranya juga tunggakan besar di lembaga lain. Untuk dipakai sebagai alasan penolakan kepada pemohon, hal ini perlu dibenahi:

- Skor eksternal asalnya tidak dijelaskan dan tidak bisa ditindaklanjuti pemohon.
- `ext_source_mean` adalah turunan dari tiga skor eksternal, sehingga alasan jadi redundan. Kelompokkan fitur yang berkorelasi menjadi satu alasan.
- Prioritaskan faktor yang bisa ditindaklanjuti (misalnya tunggakan, keterlambatan cicilan) dalam penjelasan.

## 6. Keterbatasan

- **Asumsi finansial** hanya ilustrasi; biaya dana, biaya operasional, dan faktor waktu tidak dihitung.
- **Kemungkinan bias seleksi:** dataset kemungkinan hanya berisi pinjaman yang sudah disetujui, sehingga model belum pernah melihat pemohon yang dulu ditolak (belum diverifikasi di dokumentasi sumber data).
- **Keadilan:** `code_gender` termasuk 5 fitur terpenting pada model awal. Eksperimen melatih ulang tanpa fitur ini (parameter, split, dan seed sama) menurunkan ROC-AUC test dari 0,7913 ke 0,7893 (selisih 0,0019, interval bootstrap 95% +0,0004 sampai +0,0033), PR-AUC dari 0,2845 ke 0,2822, dan Brier naik dari 0,0657 ke 0,0659. Pada ambang 0,143, tingkat persetujuan hampir sama (84,7% ke 84,8%) dan default rate yang disetujui naik dari 4,85% ke 4,90%. Selisih tingkat persetujuan antara perempuan dan laki-laki menyempit dari 9,7 ke 7,2 poin persentase (perempuan 88,0% ke 87,2%, laki-laki 78,3% ke 80,0%), tetapi tidak hilang: default rate aktual kedua kelompok memang berbeda (6,96% vs 10,23%), dan fitur lain bisa menjadi proxy gender. Membuang atribut ini tidak membuktikan model bebas bias, dan keputusan akhir tetap perlu tinjauan hukum dan audit fairness.
- **Evaluasi satu kali split.** Selisih antar model boosting kecil dan belum diuji signifikansinya.
- **Data historis (2018).** Perilaku nasabah dan kalibrasi dapat bergeser seiring waktu.
- **Skor eksternal** bergantung pada pihak ketiga yang tidak transparan.

## 7. Rekomendasi lanjutan

1. Audit proxy gender (misalnya pekerjaan, pendapatan) dan uji metrik fairness yang lebih lengkap. Tahap tanpa `code_gender` sudah dikerjakan dan dipakai pada model final.
2. Pantau kalibrasi dan distribusi fitur secara berkala; latih ulang saat bergeser.
3. Jalankan pilot untuk tindakan di bagian 3 (batas cicilan, tenor, peringatan dini) sebelum diterapkan penuh.
4. Dokumentasikan alasan keputusan yang bisa dipahami pemohon.
