-- Fitur dari riwayat kredit di lembaga lain (bureau + bureau_balance).
-- Hasil: features.bureau_agg, satu baris per nasabah (sk_id_curr).
-- Aman dijalankan ulang: tabel lama dihapus dan dibuat ulang.

CREATE SCHEMA IF NOT EXISTS features;

-- Langkah 1: ringkas riwayat bulanan (bureau_balance) per kredit (sk_id_bureau).
-- status: 0 = tidak telat, 1 = telat 1-30 hari, 2 = 31-60, 3 = 61-90,
--         4 = 91-120, 5 = lebih dari 120 hari / dihapus buku, C = ditutup, X = tidak diketahui.
DROP TABLE IF EXISTS features.bureau_balance_agg;
CREATE TABLE features.bureau_balance_agg AS
SELECT
    sk_id_bureau,
    COUNT(*)                                                          AS bb_n_months,
    COUNT(*) FILTER (WHERE status IN ('1', '2', '3', '4', '5'))       AS bb_n_dpd,
    COUNT(*) FILTER (WHERE status IN ('2', '3', '4', '5'))            AS bb_n_dpd_31plus,
    MAX(CASE WHEN status IN ('0', '1', '2', '3', '4', '5')
             THEN CAST(status AS INTEGER) END)                        AS bb_worst_status
FROM raw.bureau_balance
GROUP BY sk_id_bureau;

CREATE INDEX idx_bb_agg_bureau ON features.bureau_balance_agg (sk_id_bureau);

-- Langkah 2: gabungkan ke level nasabah.
DROP TABLE IF EXISTS features.bureau_agg;
CREATE TABLE features.bureau_agg AS
SELECT
    b.sk_id_curr,
    COUNT(*)                                                          AS bureau_n_credits,
    COUNT(*) FILTER (WHERE b.credit_active = 'Active')                AS bureau_n_active,
    COUNT(*) FILTER (WHERE b.credit_active = 'Closed')                AS bureau_n_closed,
    COUNT(*) FILTER (WHERE b.credit_day_overdue > 0)                  AS bureau_n_overdue,
    COUNT(DISTINCT b.credit_type)                                     AS bureau_n_credit_types,
    SUM(b.amt_credit_sum)                                             AS bureau_credit_sum,
    SUM(b.amt_credit_sum_debt)                                        AS bureau_debt_sum,
    CAST(SUM(b.amt_credit_sum_debt) AS DOUBLE PRECISION)
        / NULLIF(CAST(SUM(b.amt_credit_sum) AS DOUBLE PRECISION), 0)  AS bureau_debt_credit_ratio,
    SUM(b.amt_credit_sum_overdue)                                     AS bureau_overdue_sum,
    MAX(b.amt_credit_max_overdue)                                     AS bureau_max_overdue,
    MAX(b.credit_day_overdue)                                         AS bureau_max_day_overdue,
    SUM(b.cnt_credit_prolong)                                         AS bureau_n_prolong,
    AVG(b.days_credit)                                                AS bureau_avg_days_credit,
    MIN(b.days_credit)                                                AS bureau_oldest_days_credit,
    MAX(b.days_credit)                                                AS bureau_newest_days_credit,
    SUM(bb.bb_n_months)                                               AS bureau_bb_n_months,
    SUM(bb.bb_n_dpd)                                                  AS bureau_bb_n_dpd,
    CAST(SUM(bb.bb_n_dpd) AS DOUBLE PRECISION)
        / NULLIF(CAST(SUM(bb.bb_n_months) AS DOUBLE PRECISION), 0)    AS bureau_bb_dpd_share,
    MAX(bb.bb_worst_status)                                           AS bureau_bb_worst_status
FROM raw.bureau AS b
LEFT JOIN features.bureau_balance_agg AS bb
       ON b.sk_id_bureau = bb.sk_id_bureau
GROUP BY b.sk_id_curr;

CREATE INDEX idx_bureau_agg_curr ON features.bureau_agg (sk_id_curr);
ANALYZE features.bureau_balance_agg;
ANALYZE features.bureau_agg;
