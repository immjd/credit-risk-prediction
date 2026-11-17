"""Muat CSV Home Credit dari data/raw ke PostgreSQL (schema: raw).

Jalankan dari folder utama project:
    python src\\load_to_postgres.py

Script ini aman dijalankan ulang: tabel lama di schema raw akan dihapus
lalu dimuat ulang.
"""
import io
import os
import time
from pathlib import Path

import pandas as pd
import psycopg2
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
CHUNK_SIZE = 500_000

FILES = [
    "application_train.csv",
    "application_test.csv",
    "bureau.csv",
    "bureau_balance.csv",
    "previous_application.csv",
    "POS_CASH_balance.csv",
    "installments_payments.csv",
    "credit_card_balance.csv",
]

KEY_COLUMNS = ["sk_id_curr", "sk_id_prev", "sk_id_bureau"]
RANK = {"int": 0, "float": 1, "text": 2}
PG_TYPE = {"int": "BIGINT", "float": "DOUBLE PRECISION", "text": "TEXT"}


def kind_of(dtype):
    if dtype.kind in "iu":
        return "int"
    if dtype.kind == "f":
        return "float"
    return "text"


def read_chunks(path):
    for chunk in pd.read_csv(path, chunksize=CHUNK_SIZE, low_memory=False):
        chunk.columns = [c.lower() for c in chunk.columns]
        yield chunk


def infer_schema(path):
    """Baca file sekali untuk menentukan tipe kolom yang aman di semua chunk."""
    kinds = {}
    for chunk in read_chunks(path):
        for col, dtype in chunk.dtypes.items():
            k = kind_of(dtype)
            if col not in kinds or RANK[k] > RANK[kinds[col]]:
                kinds[col] = k
    return kinds


def load_file(conn, filename):
    path = RAW_DIR / filename
    table = path.stem.lower()
    start = time.time()

    print(f"[{table}] membaca skema ...", flush=True)
    kinds = infer_schema(path)
    columns_sql = ", ".join(f'"{col}" {PG_TYPE[k]}' for col, k in kinds.items())
    col_list = ", ".join(f'"{col}"' for col in kinds)

    with conn.cursor() as cur:
        cur.execute(f"DROP TABLE IF EXISTS raw.{table}")
        cur.execute(f"CREATE TABLE raw.{table} ({columns_sql})")
    conn.commit()

    total = 0
    for chunk in read_chunks(path):
        buf = io.StringIO()
        chunk.to_csv(buf, index=False, header=False)
        buf.seek(0)
        with conn.cursor() as cur:
            cur.copy_expert(
                f"COPY raw.{table} ({col_list}) FROM STDIN WITH (FORMAT csv)", buf
            )
        conn.commit()
        total += len(chunk)
        print(f"[{table}] {total:,} baris dimuat", flush=True)

    with conn.cursor() as cur:
        for col in KEY_COLUMNS:
            if col in kinds:
                cur.execute(
                    f"CREATE INDEX IF NOT EXISTS idx_{table}_{col} "
                    f"ON raw.{table} ({col})"
                )
        cur.execute(f"ANALYZE raw.{table}")
    conn.commit()

    print(f"[{table}] selesai: {total:,} baris, {time.time() - start:.0f} detik\n", flush=True)
    return total


def main():
    missing = [f for f in FILES if not (RAW_DIR / f).exists()]
    if missing:
        raise SystemExit(f"File tidak ditemukan di {RAW_DIR}: {', '.join(missing)}")

    load_dotenv(ROOT / ".env")
    password = os.getenv("POSTGRES_PASSWORD")
    if not password:
        raise SystemExit("POSTGRES_PASSWORD belum diisi. Cek file .env kamu.")

    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB", "credit_risk"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=password,
    )

    with conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS raw")
    conn.commit()

    counts = {}
    for filename in FILES:
        counts[Path(filename).stem.lower()] = load_file(conn, filename)

    conn.close()
    print("Ringkasan jumlah baris:")
    for table, n in counts.items():
        print(f"  raw.{table}: {n:,}")


if __name__ == "__main__":
    main()