"""API prediksi risiko gagal bayar.

Jalankan lokal:   uvicorn api.main:app --reload
Dokumentasi:      http://localhost:8000/docs
"""
import json
import os
from pathlib import Path
from typing import Optional, Union

import lightgbm as lgb
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

MODEL_DIR = Path(os.getenv("MODEL_DIR", Path(__file__).resolve().parents[1] / "models"))
booster = lgb.Booster(model_file=str(MODEL_DIR / "lgbm_final.txt"))
meta = json.loads((MODEL_DIR / "metadata.json").read_text(encoding="utf-8"))
FEATURES = meta["features"]
CAT_COLS = set(meta["categorical_columns"])
CUTS = meta["tier_cutoffs"]
THRESHOLD = meta["decision_threshold"]
MIN_INPUTS = 20  # di bawah ini, beri peringatan bahwa input terlalu sedikit

app = FastAPI(title="Credit Risk API", version="1.0")


class Applicant(BaseModel):
    features: dict[str, Optional[Union[float, str]]] = Field(
        description="Pasangan nama_fitur: nilai. Fitur yang tidak diisi dianggap kosong (NaN).",
        examples=[{"amt_income_total": 180000, "amt_credit": 450000, "amt_annuity": 22000,
                   "ext_source_2": 0.45, "name_contract_type": "Cash loans"}],
    )


def tier_of(p: float) -> str:
    if p <= CUTS["D_max"]:
        return "D"
    if p <= CUTS["C_max"]:
        return "C"
    if p <= CUTS["B_max"]:
        return "B"
    return "A"


def derive(values: dict) -> dict:
    """Hitung fitur turunan seperti di sql/04_model_train.sql, bila inputnya ada dan fitur belum diisi."""
    d = dict(values)

    def g(k):
        x = d.get(k)
        return float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) else None

    def put(k, v):
        if k in FEATURES and d.get(k) is None and v is not None:
            d[k] = v

    def ratio(a, b):
        return a / b if a is not None and b not in (None, 0) else None

    inc, cred, ann, goods = g("amt_income_total"), g("amt_credit"), g("amt_annuity"), g("amt_goods_price")
    put("credit_income_ratio", ratio(cred, inc))
    put("annuity_income_ratio", ratio(ann, inc))
    put("credit_term_months", ratio(cred, ann))
    put("credit_goods_ratio", ratio(cred, goods))
    put("income_per_person", ratio(inc, g("cnt_fam_members")))

    birth, emp = g("days_birth"), g("days_employed")
    put("age_years", -birth / 365.25 if birth is not None else None)
    if emp is not None:
        anomaly = emp == 365243
        put("days_employed_anomaly", 1 if anomaly else 0)
        if not anomaly:
            put("employed_years", -emp / 365.25)
            put("employed_to_age_ratio", ratio(emp, birth))

    ext = [v for v in (g("ext_source_1"), g("ext_source_2"), g("ext_source_3")) if v is not None]
    put("ext_source_mean", sum(ext) / len(ext) if ext else None)
    return d


def to_frame(values: dict) -> pd.DataFrame:
    unknown = sorted(set(values) - set(FEATURES))
    if unknown:
        raise HTTPException(422, f"Fitur tidak dikenal: {unknown[:10]}")
    row = {c: values.get(c) for c in FEATURES}
    df = pd.DataFrame([row], columns=FEATURES)
    for c in FEATURES:
        if c in CAT_COLS:
            df[c] = df[c].astype("object").where(df[c].notna(), None).astype("category")
        else:
            try:
                df[c] = pd.to_numeric(df[c], errors="raise").astype(float)
            except (ValueError, TypeError):
                raise HTTPException(422, f"Fitur '{c}' harus berupa angka")
    return df


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/model-info")
def model_info():
    return {k: meta[k] for k in ["n_trees", "test_metrics", "tier_cutoffs", "decision_threshold",
                                 "excluded_features"]} | {"n_features": len(FEATURES)}


@app.get("/features")
def features():
    return {"numeric": [c for c in FEATURES if c not in CAT_COLS], "categorical": sorted(CAT_COLS)}


# Fitur yang berasal dari sumber yang sama digabung menjadi satu alasan (kontribusi log-odds dijumlahkan).
REASON_GROUPS = {
    "ext_source (skor kredit eksternal)": ["ext_source_1", "ext_source_2", "ext_source_3", "ext_source_mean"],
}


def top_reasons(df, contrib, k=3):
    """k alasan teratas yang menaikkan risiko, hanya dari fitur yang terisi; fitur sekelompok digabung."""
    member_of = {f: g for g, members in REASON_GROUPS.items() for f in members}
    items = {}
    for i, f in enumerate(FEATURES):
        v = df.iloc[0, i]
        if pd.isna(v):
            continue
        v = v.item() if hasattr(v, "item") else v
        key = member_of.get(f, f)
        item = items.setdefault(key, {"feature": key, "values": {}, "contribution_log_odds": 0.0})
        item["values"][f] = v
        item["contribution_log_odds"] += float(contrib[i])
    out = []
    for item in sorted(items.values(), key=lambda x: -x["contribution_log_odds"])[:k]:
        if item["contribution_log_odds"] <= 0:
            continue
        vals = item["values"]
        out.append({"feature": item["feature"],
                    "value": next(iter(vals.values())) if len(vals) == 1 and item["feature"] in vals else vals,
                    "contribution_log_odds": round(item["contribution_log_odds"], 3)})
    return out


@app.post("/predict")
def predict(applicant: Applicant):
    provided = {k: v for k, v in applicant.features.items() if v is not None}
    df = to_frame(derive(applicant.features))
    p = float(booster.predict(df)[0])
    contrib = booster.predict(df, pred_contrib=True)[0][:-1]  # log-odds; kolom terakhir = bias
    reasons = top_reasons(df, contrib)
    approve = p < THRESHOLD
    warning = None
    if len(provided) < MIN_INPUTS:
        warning = (f"Hanya {len(provided)} dari {len(FEATURES)} fitur diisi; fitur kosong dianggap tidak tersedia "
                   "sehingga prediksi kurang andal. Isi lebih banyak fitur untuk hasil yang representatif.")
    return {
        "default_probability": round(p, 4),
        "risk_tier": tier_of(p),
        "decision": "approve" if approve else "review_or_decline",
        "decision_threshold": round(THRESHOLD, 4),
        "inputs_provided": len(provided),
        "inputs_total": len(FEATURES),
        "warning": warning,
        "top_risk_factors": reasons,
        "note": "Keputusan memakai asumsi finansial ilustrasi; faktor risiko menjelaskan model, bukan sebab-akibat.",
    }
