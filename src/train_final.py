"""Latih model final TANPA code_gender, lalu ekspor artefak untuk API.

Jalankan dari folder proyek:
    python -m src.train_final

Hasil di folder models/:
    lgbm_final.txt   model LightGBM (format teks, memuat daftar kategori)
    metadata.json    daftar fitur, kolom kategori, batas kelompok risiko, ambang keputusan, metrik test
"""
import json
import sys
from pathlib import Path

import numpy as np
import lightgbm as lgb
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

EXCLUDE = ["code_gender"]          # atribut sensitif yang tidak dipakai model final
TIER_QUANTILES = [0.30, 0.70, 0.90]  # batas D|C|B|A dari distribusi prediksi validation
PROFIT_RATE, LOSS_RATE = 0.10, 0.60  # asumsi ilustrasi (lihat laporan bisnis)
BASE = dict(n_estimators=2000, subsample_freq=1, metric="auc", random_state=42, n_jobs=-1, verbose=-1)


def fit_and_export(X_train, X_valid, X_test, y_train, y_valid, y_test, params, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(exist_ok=True)
    cols = [c for c in X_train.columns if c not in EXCLUDE]

    model = lgb.LGBMClassifier(**BASE, **params)
    model.fit(X_train[cols], y_train, eval_set=[(X_valid[cols], y_valid)],
              callbacks=[lgb.early_stopping(100, verbose=False)])

    p_valid = model.predict_proba(X_valid[cols])[:, 1]
    p_test = model.predict_proba(X_test[cols])[:, 1]
    cuts = [float(np.quantile(p_valid, q)) for q in TIER_QUANTILES]

    metadata = {
        "features": cols,
        "categorical_columns": [c for c in cols if str(X_train[c].dtype) == "category"],
        "tier_cutoffs": {"D_max": cuts[0], "C_max": cuts[1], "B_max": cuts[2]},
        "decision_threshold": PROFIT_RATE / (PROFIT_RATE + LOSS_RATE),
        "excluded_features": EXCLUDE,
        "n_trees": int(model.best_iteration_),
        "test_metrics": {
            "roc_auc": round(float(roc_auc_score(y_test, p_test)), 4),
            "pr_auc": round(float(average_precision_score(y_test, p_test)), 4),
            "brier": round(float(brier_score_loss(y_test, p_test)), 4),
        },
    }
    model.booster_.save_model(str(out_dir / "lgbm_final.txt"), num_iteration=model.best_iteration_)
    (out_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


if __name__ == "__main__":
    from src.data import load_model_table, prepare, split

    X, y = prepare(load_model_table())
    parts = split(X, y)
    params = json.loads((ROOT / "models" / "best_params.json").read_text(encoding="utf-8"))["best_params"]
    meta = fit_and_export(*parts, params, ROOT / "models")
    print("Fitur:", len(meta["features"]), "| pohon:", meta["n_trees"])
    print("Metrik test:", meta["test_metrics"])
    print("Batas kelompok:", meta["tier_cutoffs"])
