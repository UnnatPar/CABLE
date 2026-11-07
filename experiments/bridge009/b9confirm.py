import json
import time
from pathlib import Path

import modal

HERE = Path(__file__).parent
app = modal.App("cable-b9confirm")
volume = modal.Volume.from_name("cable-data")
image = (modal.Image.debian_slim(python_version="3.12")
         .pip_install("numpy==2.2.6", "scipy==1.18.1", "torch==2.8.0")
         .add_local_file(HERE / "b9lib.py", "/root/b9lib.py")
         .add_local_file(HERE / "b9mel.py", "/root/b9mel.py")
         .add_local_file(HERE / "b9c3.py", "/root/b9c3.py")
         .add_local_file(HERE / "results" / "c3_folds.json", "/root/c3_folds.json"))
K = dict(hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0)
FROZEN = {
    "m01": dict(fams=["fa_cf2", "rc_cc7_2"], pca_k=40, **K),
    "m02": dict(fams=["fa_cf2", "ea_cc7_2"], pca_k=40, **K),
    "m03": dict(fams=["ea_cf2", "rc_cc7_2"], pca_k=40, **K),
    "m04": dict(fams=["fa_cf4", "rc_cc7_4"], pca_k=40, **K),
    "m05": dict(fams=["fa_cf2_s2"], pca_k=20, **K),
    "m06": dict(fams=["ea_cf2", "ea_cc7_2"], pca_k=40, **K),
    "m07": dict(fams=["fa1_cf4"], pca_k=25, **K),
    "m08": dict(fams=["ea_cf4", "ea_cc7_4"], pca_k=40, **K),
    "m09": dict(fams=["cf2", "cc7_2"], pca_k=40, **K),
    "m10": dict(fams=["cf4", "cc7_4"], pca_k=40, **K),
    "m11": dict(fams=["cf2"], pca_k=20, **K),
    "m12": dict(fams=["cc7_2"], pca_k=30, **K),
}
KS = list(range(12, 575))


def ours_predict(runs, train_idx, test_idx, members=FROZEN, test_tr=None):
    import numpy as np
    import b9lib
    rows = np.clip(np.round(np.array(KS) * (test_tr or b9lib.TR) / 0.8 - 0.5).astype(int), 0, None)
    acc = {runs[i]["run"]: [] for i in test_idx}
    member_r = {}
    for name, cfg in members.items():
        feats = feats_full(runs, {i: b9lib.featurize(runs[i], cfg) for i in train_idx + test_idx})
        D, minrow = b9lib.build_designs(runs, feats, train_idx, cfg)
        W, alpha, _ = b9lib.ridge_nested(runs, D, "Y7", train_idx, minrow)
        for i in test_idx:
            P = (D[i] @ W)[rows]
            acc[runs[i]["run"]].append(b9lib._zs(P))
            member_r.setdefault(name, []).append(float(np.mean(b9lib.corr_cols(P, runs[i]["Ynb"][KS]))))
    return {k: np.mean(v, 0) for k, v in acc.items()}, {k: float(np.mean(v)) for k, v in member_r.items()}


def feats_full(runs, feats):
    import numpy as np
    d = next(iter(feats.values())).shape[1]
    return {i: feats[i] if i in feats else np.zeros((len(runs[i]["valid"]), d)) for i in range(len(runs))}


@app.function(image=image, cpu=8.0, memory=49152, timeout=7200, volumes={"/evidence": volume}, max_containers=60)
def ours_split(split: dict) -> dict:
    import numpy as np
    import b9lib
    runs = b9lib.load_cache()
    for r in runs:
        r["Ynb"] = np.load(f"/evidence/bridge009/mel/{r['run']}.npz")["Ynb"]
    te = [i for i, r in enumerate(runs) if r["run"] in split["test"]]
    tr = [i for i, r in enumerate(runs) if r["run"] not in split["test"]]
    P, member_r = ours_predict(runs, tr, te)
    per = {runs[i]["run"]: b9lib.corr_cols(P[runs[i]["run"]], runs[i]["Ynb"][KS]).tolist() for i in te}
    Path("/evidence/bridge009/confirm_ours").mkdir(parents=True, exist_ok=True)
    np.savez(f"/evidence/bridge009/confirm_ours/{split['name']}.npz", **{k: v for k, v in P.items()})
    volume.commit()
    return {"split": split["name"], "method": "ours", "per_scan": per, "members": member_r}


PHYS_MEMBERS = {"p_ecg": dict(fams=["ecg"], pca_k=4, **K), "p_eogemg": dict(fams=["eogemg"], pca_k=15, **K)}


@app.function(image=image, cpu=8.0, memory=49152, timeout=7200, volumes={"/evidence": volume}, max_containers=60)
def phys_split(split: dict) -> dict:
    import numpy as np
    import b9lib
    runs = b9lib.load_cache()
    for r in runs:
        r["Ynb"] = np.load(f"/evidence/bridge009/mel/{r['run']}.npz")["Ynb"]
    te = [i for i, r in enumerate(runs) if r["run"] in split["test"]]
    tr = [i for i, r in enumerate(runs) if r["run"] not in split["test"]]
    Pp, _ = ours_predict(runs, tr, te, members=PHYS_MEMBERS)
    saved = np.load(f"/evidence/bridge009/confirm_ours/{split['name']}.npz")
    per = {}
    for i in te:
        k = runs[i]["run"]
        P = (12 * saved[k] + 2 * Pp[k]) / 14
        per[k] = b9lib.corr_cols(P, runs[i]["Ynb"][KS]).tolist()
    return {"split": split["name"], "method": "phys", "per_scan": per}


def ext_runs(prefix="v26_"):
    import b9c3
    allowed = set(json.loads(Path("/root/c3_folds.json").read_text())["runs"])
    out = []
    for r in b9c3.load_ext(prefix):
        if r["run"] in allowed:
            r["sub"] = "ext_" + r["sub"]; r["run"] = "ext_" + r["run"]; out.append(r)
    return out


@app.function(image=image, cpu=8.0, memory=65536, timeout=10800, volumes={"/evidence": volume}, max_containers=60)
def final2_split(split: dict) -> dict:
    import numpy as np
    import b9lib
    runs = b9lib.load_cache()
    for r in runs:
        r["Ynb"] = np.load(f"/evidence/bridge009/mel/{r['run']}.npz")["Ynb"]
    ext = ext_runs()
    allr = runs + ext
    te = [i for i, r in enumerate(allr) if r["run"] in split["test"]]
    tr = [i for i, r in enumerate(allr) if r["run"] not in split["test"]]
    Pext, member_r = ours_predict(allr, tr, te)
    saved = np.load(f"/evidence/bridge009/confirm_ours/{split['name']}.npz")
    per = {}
    for i in te:
        k = allr[i]["run"]
        per[k] = b9lib.corr_cols((saved[k] + Pext[k]) / 2, allr[i]["Ynb"][KS]).tolist()
    return {"split": split["name"], "method": "final2", "per_scan": per, "members_ext": member_r}


@app.function(image=image, cpu=16.0, memory=32768, timeout=7200, volumes={"/evidence": volume}, max_containers=60)
def mel_ext_split(split: dict, readout: str) -> dict:
    import torch
    import b9mel
    runs = b9mel.load_mel("mel_zp")
    for r in ext_runs():
        runs[r["run"]] = {"X": r["mel"], "Y": r["Ynb"].astype(float)}
    test = split["test"]; val = split["val"]; train = [s for s in runs if s not in test and s not in val]
    res = b9mel.mel_fit_predict(runs, train, val, test, readout, dev="cuda" if torch.cuda.is_available() else "cpu")
    return {"split": split["name"], "method": f"mel_{readout}_ext", "per_scan": {s: b9mel.pr(v[0], v[1]).tolist() for s, v in res.items()}}


@app.function(image=image, cpu=8.0, memory=49152, timeout=7200, volumes={"/evidence": volume})
def sanity(held: str) -> dict:
    import numpy as np
    import b9lib
    runs = [r for r in b9lib.load_cache() if r["sub"] not in b9lib.NB_TEST_SUBS]
    for r in runs:
        r["Ynb"] = np.load(f"/evidence/bridge009/mel/{r['run']}.npz")["Ynb"]
    te = [i for i, r in enumerate(runs) if r["sub"] == held]; tr = [i for i, r in enumerate(runs) if r["sub"] != held]
    P, member_r = ours_predict(runs, tr, te)
    return {"held": held, "ens": {runs[i]["run"]: float(np.mean(b9lib.corr_cols(P[runs[i]["run"]], runs[i]["Ynb"][KS]))) for i in te},
            "members": member_r}


@app.function(image=image, cpu=16.0, memory=32768, timeout=7200, volumes={"/evidence": volume}, max_containers=60)
def mel_split(split: dict, readout: str) -> dict:
    import numpy as np
    import torch
    import b9mel
    runs = b9mel.load_mel("mel_zp")
    test = split["test"]; val = split["val"]; train = [s for s in runs if s not in test and s not in val]
    res = b9mel.mel_fit_predict(runs, train, val, test, readout, dev="cuda" if torch.cuda.is_available() else "cpu")
    out = {"split": split["name"], "method": f"mel_{readout}", "per_scan": {s: b9mel.pr(v[0], v[1]).tolist() for s, v in res.items()}}
    if readout == "mlp":
        out["per_scan_single_seed"] = {s: b9mel.pr(v[2], v[1]).tolist() for s, v in res.items()}
    return out


@app.local_entrypoint()
def main(sets: str = "C1a,C1b", methods: str = "ours,mel_ridge,mel_mlp", check: str = ""):
    if check:
        for r in sanity.map(check.split(",")):
            print(json.dumps(r))
        return
    sp = json.loads((HERE / "results" / "confirm_splits.json").read_text())
    splits = [s for st in sets.split(",") for s in sp[st]]
    calls = []
    for m in methods.split(","):
        if m == "ours":
            calls += [("ours", ours_split.spawn(s)) for s in splits]
        elif m == "phys":
            calls += [("phys", phys_split.spawn(s)) for s in splits]
        elif m == "final2":
            calls += [("final2", final2_split.spawn(s)) for s in splits]
        elif m in ("mel_ridge_ext", "mel_mlp_ext"):
            calls += [(m, mel_ext_split.spawn(s, m.split("_")[1])) for s in splits]
        else:
            calls += [(m, mel_split.spawn(s, m.split("_")[1])) for s in splits]
    out = HERE / "results" / "confirm_results.jsonl"
    with out.open("a", encoding="utf-8") as fh:
        for m, c in calls:
            try:
                r = c.get()
            except Exception as e:
                r = {"method": m, "error": repr(e)[:400]}
            r["logged"] = time.strftime("%Y-%m-%d %H:%M")
            fh.write(json.dumps(r) + "\n"); fh.flush()
            if "per_scan" in r:
                import statistics
                print(r["method"], r["split"], round(statistics.mean(statistics.mean(v) for v in r["per_scan"].values()), 4))
            else:
                print("ERR", r)
