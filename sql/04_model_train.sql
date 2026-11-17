-- Tabel akhir siap model: application_train + semua fitur agregat + beberapa fitur turunan.
-- Hasil: features.model_train, satu baris per nasabah di application_train (harus 307.511 baris).
-- Aman dijalankan ulang: tabel lama dihapus dan dibuat ulang.
--
-- Nasabah tanpa riwayat di suatu tabel (mis. tidak punya kartu kredit) akan bernilai NULL
-- pada fitur tabel itu. Itu disengaja: XGBoost/LightGBM menangani NULL, dan
-- "tidak ada riwayat" sendiri adalah informasi.

CREATE SCHEMA IF NOT EXISTS features;

DROP TABLE IF EXISTS features.model_train;
CREATE TABLE features.model_train AS
SELECT
    *,

    -- Rasio keuangan
    amt_credit / NULLIF(amt_income_total, 0)                           AS credit_income_ratio,
    amt_annuity / NULLIF(amt_income_total, 0)                          AS annuity_income_ratio,
    amt_credit / NULLIF(amt_annuity, 0)                                AS credit_term_months,
    amt_credit / NULLIF(amt_goods_price, 0)                            AS credit_goods_ratio,
    amt_income_total / NULLIF(CAST(cnt_fam_members AS DOUBLE PRECISION), 0)
                                                                       AS income_per_person,

    -- Umur dan lama kerja (days_* bernilai negatif; 365243 = placeholder anomali)
    -days_birth / 365.25                                               AS age_years,
    CASE WHEN days_employed = 365243 THEN 1 ELSE 0 END                 AS days_employed_anomaly,
    CASE WHEN days_employed = 365243 THEN NULL ELSE -days_employed / 365.25 END
                                                                       AS employed_years,
    CASE WHEN days_employed = 365243 THEN NULL
         ELSE CAST(days_employed AS DOUBLE PRECISION) / NULLIF(days_birth, 0) END
                                                                       AS employed_to_age_ratio,

    -- Rata-rata skor eksternal dari yang tersedia
    (COALESCE(ext_source_1, 0) + COALESCE(ext_source_2, 0) + COALESCE(ext_source_3, 0))
        / NULLIF((CASE WHEN ext_source_1 IS NOT NULL THEN 1 ELSE 0 END
                + CASE WHEN ext_source_2 IS NOT NULL THEN 1 ELSE 0 END
                + CASE WHEN ext_source_3 IS NOT NULL THEN 1 ELSE 0 END), 0)
                                                                       AS ext_source_mean
FROM raw.application_train
LEFT JOIN features.bureau_agg USING (sk_id_curr)
LEFT JOIN features.prev_agg   USING (sk_id_curr)
LEFT JOIN features.pos_agg    USING (sk_id_curr)
LEFT JOIN features.inst_agg   USING (sk_id_curr)
LEFT JOIN features.cc_agg     USING (sk_id_curr);

CREATE INDEX idx_model_train_curr ON features.model_train (sk_id_curr);
ANALYZE features.model_train;
