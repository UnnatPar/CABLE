import json
from pathlib import Path

import modal

HERE = Path(__file__).parent
app = modal.App("cable-b8rev")
volume = modal.Volume.from_name("cable-data")
image = (modal.Image.debian_slim(python_version="3.12")
         .pip_install("numpy==2.2.6", "scipy==1.18.1")
         .add_local_file(HERE.parent / "bridge003" / "b3lib.py", "/root/b3lib.py")
         .add_local_file(HERE / "b8lib.py", "/root/b8lib.py"))
LEADS = list(range(21))
GRID = [1, 10, 100, 1000, 1e4, 1e5, 1e6, 1e7]
VARIANTS = {"nets7": dict(pred="nets", k=None), "difumo_k10": dict(pred="difumo", k=10),
            "difumo_k20": dict(pred="difumo", k=20), "difumo_k40": dict(pred="difumo", k=40)}


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
        g = np.load(f"/evidence/bridge008/nb_fine/{f.stem}.npz", allow_pickle=True); gch = [str(c) for c in g["channels"]]
        EF = g["eeg_fine"][:, [gch.index(c) for c in common], :].astype(float)
        n = min(len(E5), len(EF), len(z["roi_all"]))
        valid = np.isfinite(E5[:n].reshape(n, -1)).all(1) & np.isfinite(EF[:n].reshape(n, -1)).all(1)
        e5 = filt(E5[:n].reshape(n, -1), "bp"); ef = filt(EF[:n].reshape(n, -1), "bp")
        ga = zs(e5.reshape(n, len(common), 5)[:, :, 2].mean(1))[:, None]
        R = filt(z["roi_all"][:n].astype(float), "lp")
        N = filt(z["fmri8"][:n][:, [0, 1, 2, 3, 5, 6, 7]].astype(float), "lp")
        runs.append({"sub": f.stem.split("-scan")[0], "e5": e5, "ef": ef, "ga": ga, "R": R, "N": N, "valid": valid})
    return runs


@app.function(image=image, cpu=16.0, memory=65536, timeout=7200, volumes={"/evidence": volume})
def run_variant(name: str) -> dict:
    import numpy as np
    from b3lib import corr_cols, lag_design, pca_fit, zs
    cfg = VARIANTS[name]; rng = np.random.default_rng(3)
    runs = load()
    subs = sorted({r["sub"] for r in runs})
    out = {"band5": [], "global_alpha": [], "fine_pcs": []}
    for s in subs:
        te = [i for i, r in enumerate(runs) if r["sub"] == s]; tr = [i for i, r in enumerate(runs) if r["sub"] != s]
        if cfg["pred"] == "difumo":
            mu, V = pca_fit(np.concatenate([runs[i]["R"][runs[i]["valid"]] for i in tr]), cfg["k"])
            P = {i: zs((runs[i]["R"] - mu) @ V.T) for i in tr + te}
        else:
            P = {i: runs[i]["N"] for i in tr + te}
        fm, fV = pca_fit(np.concatenate([runs[i]["ef"][runs[i]["valid"]] for i in tr]), 20)
        Y = {i: np.c_[runs[i]["e5"], runs[i]["ga"], zs((runs[i]["ef"] - fm) @ fV.T)] for i in tr + te}
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
        R = np.mean([corr_cols((D[i] @ W)[rows[i]], Y[i][rows[i]]) for i in te], 0)
        nb5 = runs[0]["e5"].shape[1]
        out["band5"].append(float(np.nanmedian(R[:nb5]))); out["global_alpha"].append(float(R[nb5]))
        out["fine_pcs"].append(float(np.nanmedian(R[nb5 + 1:nb5 + 6])))
    return {"variant": name, **{k: float(np.mean(v)) for k, v in out.items()}, "n_subjects": len(subs)}


@app.local_entrypoint()
def main(variants: str = "nets7,difumo_k10,difumo_k20,difumo_k40"):
    res = [r for r in run_variant.map(variants.split(","), return_exceptions=True)]
    for r in res:
        print(r if isinstance(r, dict) else repr(r)[:400])
    (HERE / "results" / "reverse_nb_loso.json").write_text(json.dumps([r for r in res if isinstance(r, dict)], indent=1))
