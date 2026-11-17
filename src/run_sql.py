"""Jalankan satu file SQL ke PostgreSQL, lalu tampilkan isi schema features.

Dari folder utama project:
    python src\\run_sql.py sql\\01_bureau_features.sql
"""
import os
import sys
import time
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Pemakaian: python src\\run_sql.py sql\\01_bureau_features.sql")

    path = Path(sys.argv[1])
    if not path.is_absolute():
        path = ROOT / path
    if not path.exists():
        raise SystemExit(f"File SQL tidak ditemukan: {path}")

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

    sql = path.read_text(encoding="utf-8")
    print(f"Menjalankan {path.name} ... (bisa beberapa menit untuk tabel besar)", flush=True)
    start = time.time()
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()
    print(f"Selesai dalam {time.time() - start:.0f} detik\n")

    with conn.cursor() as cur:
        cur.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'features' ORDER BY tablename"
        )
        tables = [row[0] for row in cur.fetchall()]
        print("Tabel di schema features:")
        for table in tables:
            cur.execute(f"SELECT COUNT(*) FROM features.{table}")
            print(f"  features.{table}: {cur.fetchone()[0]:,} baris")

    conn.close()


if __name__ == "__main__":
    main()
