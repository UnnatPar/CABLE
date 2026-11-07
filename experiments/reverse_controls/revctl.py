import json
from pathlib import Path

import modal

EXP = Path(__file__).resolve().parent.parent
OUT = Path(__file__).parent
app = modal.App("cable-revctl")
volume = modal.Volume.from_name("cable-data")
image = (modal.Image.debian_slim(python_version="3.12")
         .pip_install("numpy==2.2.6", "scipy==1.18.1")
         .add_local_file(EXP / "bridge003" / "b3lib.py", "/root/b3lib.py")
         .add_local_file(EXP / "bridge008" / "b8lib.py", "/root/b8lib.py"))
LEADS = list(range(21))
GRID = [1, 10, 100, 1000, 1e4, 1e5, 1e6, 1e7]
VARIANTS = {"full_k20": dict(cols="all", k=20), "regional_k20": dict(cols="regional", k=20),
            "globals_only": dict(cols="globals", k=None)}


def load():
    import numpy as np
    from b3lib import zs
    from b8lib import filt
    base = sorted(Path("/evidence/bridge005/nb").glob("*.npz"))
    chs = None
    for f in base:
        c = set(str(x) for x in np.load(f, allow_pickle=True)["channels"]); chs = c if chs is None else chs & c
    common = [c for c in [str(x) for x in np.load(base[0], allow_pickle=True)["channels"]] if c in chs]
    runs = []
    for f in base:
        z = np.load(f, allow_pickle=True); ch = [str(c) for c in z["channels"]]
        E5 = z["eeg_logpow"][:, [ch.index(c) for c in common], :].astype(float)
        n = min(len(E5), len(z["roi_all"]))
        valid = np.isfinite(E5[:n].reshape(n, -1)).all(1)
        e5 = filt(E5[:n].reshape(n, -1), "bp")
        ga = zs(e5.reshape(n, len(common), 5)[:, :, 2].mean(1))[:, None]
        R = filt(z["roi_all"][:n].astype(float), "lp")
        runs.append({"sub": f.stem.split("-scan")[0], "e5": e5, "ga": ga, "R": R, "valid": valid})
    return runs


@app.function(image=image, cpu=16.0, memory=65536, timeout=7200, volumes={"/evidence": volume})
def run_variant(name: str) -> dict:
    import numpy as np
    from b3lib import corr_cols, lag_design, pca_fit, zs
    cfg = VARIANTS[name]; rng = np.random.default_rng(3); nrng = np.random.default_rng(11)
    runs = load()
    ncol = runs[0]["R"].shape[1]
    sel = {"all": slice(None), "regional": slice(0, 64), "globals": slice(64, ncol)}[cfg["cols"]]
    subs = sorted({r["sub"] for r in runs})
    per = {"band5": {}, "global_alpha": {}, "null_band5": {}, "null_alpha": {}, "null_band5_p95": {}, "null_alpha_p95": {}}
    for s in subs:
        te = [i for i, r in enumerate(runs) if r["sub"] == s]; tr = [i for i, r in enumerate(runs) if r["sub"] != s]
        if cfg["k"]:
            mu, V = pca_fit(np.concatenate([runs[i]["R"][runs[i]["valid"]][:, sel] for i in tr]), cfg["k"])
            P = {i: zs((runs[i]["R"][:, sel] - mu) @ V.T) for i in tr + te}
        else:
            P = {i: zs(runs[i]["R"][:, sel]) for i in tr + te}
        Y = {i: np.c_[runs[i]["e5"], runs[i]["ga"]] for i in tr + te}
        D = {i: lag_design(P[i], LEADS, lead=True) for i in tr + te}
        rows = {i: np.where(runs[i]["valid"] & (np.arange(len(D[i])) < len(D[i]) - LEADS[-1]))[0] for i in tr + te}
        pre = {i: (D[i][rows[i]].T @ D[i][rows[i]], D[i][rows[i]].T @ Y[i][rows[i]]) for i in tr}
        XX = sum(v[0] for v in pre.values()); XY = sum(v[1] for v in pre.values())
        trs = sorted({runs[i]["sub"] for i in tr}); rng.shuffle(trs); folds = [set(trs[j::4]) for j in range(4)]
        sc = {a: [] for a in GRID}
        for fs in folds:
            ti = [i for i in tr if runs[i]["sub"] in fs]
            xx = XX - sum(pre[i][0] for i in ti); xy = XY - sum(pre[i][1] for i in ti)
            for a in GRID:
                W = np.linalg.solve(xx + a * np.eye(len(xx)), xy)
                sc[a].append(np.mean([np.nanmedian(corr_cols((D[i] @ W)[rows[i]], Y[i][rows[i]])) for i in ti]))
        a = max(GRID, key=lambda k: np.mean(sc[k]))
        W = np.linalg.solve(XX + a * np.eye(len(XX)), XY)
        nb5 = runs[0]["e5"].shape[1]
        real, nb, na = [], [], []
        for i in te:
            pr, y = (D[i] @ W)[rows[i]], Y[i][rows[i]]
            real.append(corr_cols(pr, y))
            n = len(pr); shifts = nrng.integers(30, n - 30, 50)
            rr = np.array([corr_cols(np.roll(pr, int(k), 0), y) for k in shifts])
            nb.append(np.nanmedian(rr[:, :nb5], 1)); na.append(rr[:, nb5])
        R = np.mean(real, 0); nb = np.mean(nb, 0); na = np.mean(na, 0)
        per["band5"][s] = float(np.nanmedian(R[:nb5])); per["global_alpha"][s] = float(R[nb5])
        per["null_band5"][s] = float(nb.mean()); per["null_alpha"][s] = float(na.mean())
        per["null_band5_p95"][s] = float(np.quantile(nb, .95)); per["null_alpha_p95"][s] = float(np.quantile(na, .95))
    return {"variant": name, "n_pred_cols": int(ncol), "per_subject": per,
            **{k: float(np.mean(list(v.values()))) for k, v in per.items()}}


@app.local_entrypoint()
def main(variants: str = "full_k20,regional_k20,globals_only"):
    res = [r for r in run_variant.map(variants.split(","), return_exceptions=True)]
    for r in res:
        print({k: v for k, v in r.items() if k != "per_subject"} if isinstance(r, dict) else repr(r)[:400])
    (OUT / "reverse_controls.json").write_text(json.dumps([r for r in res if isinstance(r, dict)], indent=1))
