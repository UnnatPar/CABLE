import json
import time
from pathlib import Path

import modal

HERE = Path(__file__).parent
app = modal.App("cable-b9gbm")
volume = modal.Volume.from_name("cable-data")
image = (modal.Image.debian_slim(python_version="3.12")
         .pip_install("numpy==2.2.6", "scipy==1.18.1", "lightgbm==4.6.0", "scikit-learn==1.7.2")
         .add_local_file(HERE / "b9lib.py", "/root/b9lib.py"))
K = dict(hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0)
CFGS = {
    "gbm_cf2cc72_40": dict(fams=["cf2", "cc7_2"], pca_k=40, lag_step=2, leaves=7, lr=0.03, ff=0.3, **K),
    "gbm_cf2_20": dict(fams=["cf2"], pca_k=20, lag_step=2, leaves=7, lr=0.03, ff=0.3, **K),
    "gbm_cf2cc72_40_l15": dict(fams=["cf2", "cc7_2"], pca_k=40, lag_step=2, leaves=15, lr=0.03, ff=0.3, **K),
}


@app.function(image=image, cpu=16.0, memory=32768, timeout=3600, volumes={"/evidence": volume}, max_containers=60)
def fold(name: str, cfg: dict, held: str):
    import traceback
    try:
        return _fold(name, cfg, held)
    except Exception:
        return "TB " + traceback.format_exc()[-1500:]


def _fold(name, cfg, held):
    import numpy as np
    import lightgbm as lgb
    import b9lib
    runs = [r for r in b9lib.load_cache() if r["sub"] not in b9lib.NB_TEST_SUBS]
    feats = {i: b9lib.featurize(r, cfg) for i, r in enumerate(runs)}
    te = [i for i, r in enumerate(runs) if r["sub"] == held]
    tr = [i for i, r in enumerate(runs) if r["sub"] != held]
    D, minrow = b9lib.build_designs(runs, feats, tr, cfg)
    k = cfg["pca_k"]; nl = cfg["n_lags"]
    keep = np.concatenate([np.arange(j * k, (j + 1) * k) for j in range(0, nl, cfg["lag_step"])])
    subs = sorted({runs[i]["sub"] for i in tr}); va_s = set(subs[j] for j in range(len(subs)) if j % 4 == 0)
    rows = {i: np.where(runs[i]["valid"] & (np.arange(len(D[i])) >= minrow))[0] for i in range(len(runs))}
    fi = [i for i in tr if runs[i]["sub"] not in va_s]; vi = [i for i in tr if runs[i]["sub"] in va_s]
    Xtr = np.concatenate([D[i][rows[i]][:, keep] for i in fi]); Xva = np.concatenate([D[i][rows[i]][:, keep] for i in vi])
    out = {}
    P = {i: np.zeros((len(b9lib.tr_rows(len(D[i]), runs[i]["valid"], minrow)), 7)) for i in te}
    for j in range(7):
        ytr = np.concatenate([runs[i]["Y7"][rows[i], j] for i in fi]); yva = np.concatenate([runs[i]["Y7"][rows[i], j] for i in vi])
        m = lgb.LGBMRegressor(n_estimators=2000, learning_rate=cfg["lr"], num_leaves=cfg["leaves"], min_child_samples=200,
                              subsample=0.5, subsample_freq=1, colsample_bytree=cfg["ff"], reg_lambda=10.0, verbose=-1, n_jobs=16)
        m.fit(Xtr, ytr, eval_set=[(Xva, yva)], callbacks=[lgb.early_stopping(100, verbose=False)])
        for i in te:
            rr = b9lib.tr_rows(len(D[i]), runs[i]["valid"], minrow)
            P[i][:, j] = m.predict(D[i][rr][:, keep])
    for i in te:
        rr = b9lib.tr_rows(len(D[i]), runs[i]["valid"], minrow)
        out[runs[i]["run"]] = {"P": P[i].tolist(), "Y": runs[i]["Y7"][rr].tolist(), "rows": rr.tolist()}
    return out


@app.function(image=image, cpu=2.0, memory=8192, timeout=600, volumes={"/evidence": volume})
def save(name: str, preds: dict) -> dict:
    import numpy as np
    import b9lib
    P = {k: {f: np.array(v[f]) for f in v} for k, v in preds.items()}
    np.savez(f"/evidence/bridge009/dev/{name}.npz", **{f"{k}__{f}": v[f] for k, v in P.items() for f in ("P", "Y", "rows")})
    volume.commit()
    return b9lib.score(P)


@app.local_entrypoint()
def main():
    subs = ["sub01", "sub02", "sub03", "sub04", "sub05", "sub06", "sub08", "sub09", "sub10", "sub12", "sub13", "sub14",
            "sub15", "sub17", "sub19", "sub20", "sub22"]
    jobs = [(n, c, s) for n, c in CFGS.items() for s in subs]
    res = list(fold.starmap(jobs, return_exceptions=True))
    with (HERE / "results" / "dev_log.jsonl").open("a", encoding="utf-8") as fh:
        for n, c in CFGS.items():
            got = [r for (jn, _, _), r in zip(jobs, res) if jn == n and isinstance(r, dict)]
            if len(got) != len(subs):
                print(n, "ERR", [str(r)[-900:] for (jn, _, _), r in zip(jobs, res) if jn == n and not isinstance(r, dict)][:1]); continue
            sc = save.remote(n, {k: v for r in got for k, v in r.items()})
            fh.write(json.dumps({"name": n, "cfg": c, **sc, "logged": time.strftime("%Y-%m-%d %H:%M")}) + "\n")
            print(f"{n:<36} {sc['mean']:.4f} roi {sc['by_roi']}")
