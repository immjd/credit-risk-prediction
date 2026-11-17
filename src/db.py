"""Koneksi ke PostgreSQL untuk dipakai di notebook dan script.

Contoh:
    from src.db import get_engine
    engine = get_engine()
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

ROOT = Path(__file__).resolve().parents[1]


def get_engine():
    load_dotenv(ROOT / ".env")
    url = URL.create(
        "postgresql+psycopg2",
        username=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "credit_risk"),
    )
    return create_engine(url)
