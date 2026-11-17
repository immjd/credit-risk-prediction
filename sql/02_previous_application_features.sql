-- Fitur dari riwayat pengajuan kredit sebelumnya di Home Credit (previous_application).
-- Hasil: features.prev_agg, satu baris per nasabah (sk_id_curr).
-- Aman dijalankan ulang: tabel lama dihapus dan dibuat ulang.

CREATE SCHEMA IF NOT EXISTS features;

DROP TABLE IF EXISTS features.prev_agg;
CREATE TABLE features.prev_agg AS
SELECT
    sk_id_curr,
    COUNT(*)                                                           AS prev_n_apps,
    COUNT(*) FILTER (WHERE name_contract_status = 'Approved')          AS prev_n_approved,
    COUNT(*) FILTER (WHERE name_contract_status = 'Refused')           AS prev_n_refused,
    COUNT(*) FILTER (WHERE name_contract_status = 'Canceled')          AS prev_n_canceled,
    CAST(COUNT(*) FILTER (WHERE name_contract_status = 'Refused') AS DOUBLE PRECISION)
        / COUNT(*)                                                     AS prev_refused_share,
    COUNT(*) FILTER (WHERE name_contract_type = 'Cash loans')          AS prev_n_cash,
    COUNT(*) FILTER (WHERE name_contract_type = 'Consumer loans')      AS prev_n_consumer,
    COUNT(*) FILTER (WHERE name_contract_type = 'Revolving loans')     AS prev_n_revolving,
    AVG(amt_application)                                               AS prev_avg_amt_application,
    AVG(amt_credit)                                                    AS prev_avg_amt_credit,
    SUM(amt_credit) FILTER (WHERE name_contract_status = 'Approved')   AS prev_sum_credit_approved,
    AVG(CAST(amt_credit AS DOUBLE PRECISION)
        / NULLIF(CAST(amt_application AS DOUBLE PRECISION), 0))        AS prev_avg_credit_to_application,
    AVG(amt_annuity)                                                   AS prev_avg_annuity,
    AVG(cnt_payment)                                                   AS prev_avg_cnt_payment,
    AVG(rate_down_payment)                                             AS prev_avg_rate_down_payment,
    MAX(days_decision)                                                 AS prev_last_days_decision,
    MIN(days_decision)                                                 AS prev_first_days_decision
FROM raw.previous_application
GROUP BY sk_id_curr;

CREATE INDEX idx_prev_agg_curr ON features.prev_agg (sk_id_curr);
ANALYZE features.prev_agg;
