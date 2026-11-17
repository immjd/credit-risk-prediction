-- Fitur dari riwayat pembayaran: pos_cash_balance, installments_payments, credit_card_balance.
-- Hasil: features.pos_agg, features.inst_agg, features.cc_agg (satu baris per nasabah).
-- Aman dijalankan ulang: tabel lama dihapus dan dibuat ulang.

CREATE SCHEMA IF NOT EXISTS features;

-- 1. POS cash: riwayat bulanan pinjaman konsumtif / tunai Home Credit.
DROP TABLE IF EXISTS features.pos_agg;
CREATE TABLE features.pos_agg AS
SELECT
    sk_id_curr,
    COUNT(DISTINCT sk_id_prev)                                         AS pos_n_loans,
    COUNT(*)                                                           AS pos_n_months,
    MAX(sk_dpd)                                                        AS pos_max_dpd,
    AVG(sk_dpd)                                                        AS pos_avg_dpd,
    COUNT(*) FILTER (WHERE sk_dpd > 0)                                 AS pos_n_dpd_months,
    CAST(COUNT(*) FILTER (WHERE sk_dpd > 0) AS DOUBLE PRECISION)
        / COUNT(*)                                                     AS pos_dpd_share,
    MAX(months_balance)                                                AS pos_latest_month,
    AVG(cnt_instalment)                                                AS pos_avg_cnt_instalment
FROM raw.pos_cash_balance
GROUP BY sk_id_curr;

CREATE INDEX idx_pos_agg_curr ON features.pos_agg (sk_id_curr);
ANALYZE features.pos_agg;

-- 2. Installments: cicilan yang jatuh tempo vs pembayaran sebenarnya.
-- Keterlambatan (hari) = days_entry_payment - days_instalment; positif berarti telat.
DROP TABLE IF EXISTS features.inst_agg;
CREATE TABLE features.inst_agg AS
SELECT
    sk_id_curr,
    COUNT(DISTINCT sk_id_prev)                                         AS inst_n_loans,
    COUNT(*)                                                           AS inst_n_payments,
    AVG(days_entry_payment - days_instalment)                          AS inst_avg_days_late,
    MAX(days_entry_payment - days_instalment)                          AS inst_max_days_late,
    COUNT(*) FILTER (WHERE days_entry_payment > days_instalment)       AS inst_n_late,
    CAST(COUNT(*) FILTER (WHERE days_entry_payment > days_instalment) AS DOUBLE PRECISION)
        / COUNT(*)                                                     AS inst_late_share,
    COUNT(*) FILTER (WHERE days_entry_payment > days_instalment
                       AND days_instalment >= -365)                    AS inst_n_late_last_year,
    SUM(amt_instalment)                                                AS inst_total_due,
    SUM(amt_payment)                                                   AS inst_total_paid,
    CAST(SUM(amt_payment) AS DOUBLE PRECISION)
        / NULLIF(CAST(SUM(amt_instalment) AS DOUBLE PRECISION), 0)     AS inst_paid_ratio,
    COUNT(*) FILTER (WHERE amt_payment < amt_instalment)               AS inst_n_underpaid,
    SUM(CASE WHEN amt_payment < amt_instalment
             THEN amt_instalment - amt_payment ELSE 0 END)             AS inst_sum_shortfall
FROM raw.installments_payments
GROUP BY sk_id_curr;

CREATE INDEX idx_inst_agg_curr ON features.inst_agg (sk_id_curr);
ANALYZE features.inst_agg;

-- 3. Kartu kredit: saldo, limit, penarikan, dan keterlambatan bulanan.
DROP TABLE IF EXISTS features.cc_agg;
CREATE TABLE features.cc_agg AS
SELECT
    sk_id_curr,
    COUNT(DISTINCT sk_id_prev)                                         AS cc_n_cards,
    COUNT(*)                                                           AS cc_n_months,
    AVG(amt_balance)                                                   AS cc_avg_balance,
    MAX(amt_balance)                                                   AS cc_max_balance,
    AVG(amt_credit_limit_actual)                                       AS cc_avg_limit,
    AVG(CAST(amt_balance AS DOUBLE PRECISION)
        / NULLIF(CAST(amt_credit_limit_actual AS DOUBLE PRECISION), 0)) AS cc_avg_utilization,
    MAX(sk_dpd)                                                        AS cc_max_dpd,
    COUNT(*) FILTER (WHERE sk_dpd > 0)                                 AS cc_n_dpd_months,
    AVG(amt_drawings_atm_current)                                      AS cc_avg_drawings_atm,
    AVG(amt_drawings_current)                                          AS cc_avg_drawings,
    AVG(amt_payment_total_current)                                     AS cc_avg_payment_total,
    AVG(amt_inst_min_regularity)                                       AS cc_avg_min_regularity
FROM raw.credit_card_balance
GROUP BY sk_id_curr;

CREATE INDEX idx_cc_agg_curr ON features.cc_agg (sk_id_curr);
ANALYZE features.cc_agg;
