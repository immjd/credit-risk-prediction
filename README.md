Prediksi Risiko Kredit (Home Credit Default Risk)

Project machine learning tabular end-to-end untuk memprediksi nasabah yang berpotensi gagal bayar, memakai dataset Home Credit Default Risk dari Kaggle. Fokusnya mendekati kebutuhan nyata di bank dan fintech: data multi-tabel, kelas tidak seimbang, model yang bisa dijelaskan, dan tindakan bisnis dari hasilnya.

Status: dalam pengerjaan. Bagian yang sudah selesai ditandai di bagian "Progres" di bawah.

Tujuan
Memprediksi probabilitas gagal bayar tiap nasabah.
Menangani data tidak seimbang dan membandingkan beberapa model.
Menjelaskan prediksi dengan SHAP.
Menutup dengan interpretasi bisnis: faktor apa yang paling memengaruhi risiko dan apa tindakannya.
Tech stack

Python, pandas, scikit-learn, XGBoost, LightGBM, Optuna, SHAP, PostgreSQL + SQL, FastAPI, Docker.

Dataset

Home Credit Default Risk (Kaggle), terdiri dari 8 tabel data:

Tabel Jumlah baris
application_train 307.511
application_test 48.744
bureau 1.716.428
bureau_balance 27.299.925
previous_application 1.670.214
pos_cash_balance 10.001.358
installments_payments 13.605.401
credit_card_balance 3.840.312

Data mentah tidak disertakan di repositori ini. Unduh dari halaman kompetisi Kaggle (tab Data, Download as zip) dan ekstrak ke data/raw/.
