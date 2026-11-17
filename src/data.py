"""Memuat dan menyiapkan features.model_train untuk pemodelan.

Dipakai di notebook:
    from src.data import load_model_table, prepare, split
"""
import pandas as pd
from sklearn.model_selection import train_test_split

TARGET = "target"
ID_COL = "sk_id_curr"
RANDOM_STATE = 42


def load_model_table():
    """Baca tabel features.model_train dari PostgreSQL."""
    from src.db import get_engine

    return pd.read_sql("SELECT * FROM features.model_train", get_engine())


def prepare(df):
    """Pisahkan X dan y, buang kolom redundan, ubah kolom teks menjadi category.

    Kolom bangunan datang dalam tiga versi (_avg, _mode, _medi) dengan informasi hampir
    sama. Kita simpan _avg saja.
    """
    df = df.copy()
    y = df[TARGET].astype(int)
    redundant = [c for c in df.columns if c.endswith("_mode") or c.endswith("_medi")]
    X = df.drop(columns=[TARGET, ID_COL] + redundant)
    for col in X.columns:
        if not pd.api.types.is_numeric_dtype(X[col]):
            X[col] = X[col].astype("category")
    return X, y


def split(X, y):
    """Split stratified 70/15/15 (train / valid / test), reproducible."""
    X_train, X_tmp, y_train, y_tmp = train_test_split(
        X, y, test_size=0.30, stratify=y, random_state=RANDOM_STATE
    )
    X_valid, X_test, y_valid, y_test = train_test_split(
        X_tmp, y_tmp, test_size=0.50, stratify=y_tmp, random_state=RANDOM_STATE
    )
    return X_train, X_valid, X_test, y_train, y_valid, y_test
