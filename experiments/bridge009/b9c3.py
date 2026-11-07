import json
import time
from pathlib import Path

import modal

HERE = Path(__file__).parent
app = modal.App("cable-b9c3")
volume = modal.Volume.from_name("cable-data")
image = (modal.Image.debian_slim(python_version="3.12")
         .pip_install("numpy==2.2.6", "scipy==1.18.1", "torch==2.8.0")
         .add_local_file(HERE / "b9lib.py", "/root/b9lib.py")
         .add_local_file(HERE / "b9mel.py", "/root/b9mel.py")
         .add_local_file(HERE / "b9confirm.py", "/root/b9confirm.py"))
ROOT = "/evidence/bridge009/ds003768/cache3"


def load_ext(prefix=""):
    import numpy as np
    runs = []
    for f in sorted(Path(ROOT).glob("*.npz")):
        sub, run = f.stem.split("-run")
        name = f"sub{int(sub.split('-')[1]):02d}-scan{int(run):02d}"
        z = np.load(f)
        r = {"run": name, "sub": name.split("-scan")[0], "valid": np.isfinite(z[prefix + "cf2"]).all(1),
             "Y7": z["Y7"], "Ynb": z["Ynb"]}
        for k in z.files:
            if k.startswith(prefix) and not k.endswith("mel_zp"):
                r[k[len(prefix):]] = z[k]
        r["mel"] = z[prefix + "mel_zp"].reshape(len(z[prefix + "mel_zp"]), -1).astype(np.float64)
        runs.append(r)
    return runs


def score_ext(P, Ynb):
    import numpy as np
    import b9lib
    ks = np.arange(12, min(len(Ynb), len(P) + 12))
    return b9lib.corr_cols(P[:len(ks)], Ynb[ks]).tolist()


@app.function(image=image, cpu=8.0, memory=49152, timeout=7200, volumes={"/evidence": volume}, max_containers=40)
def ours_fold(fold: dict, prefix: str, allowed: list) -> dict:
    import numpy as np
    import b9confirm
    import b9lib
    runs = [r for r in load_ext(prefix) if r["run"] in allowed]
    b9confirm.KS = list(range(12, min(len(r["Ynb"]) for r in runs)))
    te = [i for i, r in enumerate(runs) if r["run"] in fold["test"]]
    tr = [i for i, r in enumerate(runs) if r["run"] not in fold["test"]]
    P, members = b9confirm.ours_predict(runs, tr, te)
    per = {runs[i]["run"]: b9lib.corr_cols(P[runs[i]["run"]], runs[i]["Ynb"][b9confirm.KS]).tolist() for i in te}
    return {"fold": fold["name"], "method": f"ours{prefix or '_native'}", "per_scan": per, "members": members}


@app.function(image=image, cpu=16.0, memory=32768, timeout=7200, volumes={"/evidence": volume}, max_containers=40)
def mel_fold(fold: dict, prefix: str, readout: str, allowed: list) -> dict:
    import torch
    import b9mel
    rl = [r for r in load_ext(prefix) if r["run"] in allowed]
    runs = {r["run"]: {"X": r["mel"], "Y": r["Ynb"].astype(float)} for r in rl}
    test = [s for s in runs if s in fold["test"]]; val = [s for s in runs if s in fold["val"]]
    train = [s for s in runs if s not in test and s not in val]
    res = b9mel.mel_fit_predict(runs, train, val, test, readout, dev="cuda" if torch.cuda.is_available() else "cpu")
    return {"fold": fold["name"], "method": f"mel_{readout}{prefix or '_native'}",
            "per_scan": {s: b9mel.pr(v[0], v[1]).tolist() for s, v in res.items()}}


@app.function(image=image, cpu=8.0, memory=65536, timeout=7200, volumes={"/evidence": volume})
def zeroshot(allowed: list) -> dict:
    import numpy as np
    import b9confirm
    import b9lib
    nb = b9lib.load_cache()
    for r in nb:
        r["Ynb"] = np.load(f"/evidence/bridge009/mel/{r['run']}.npz")["Ynb"]
    ext = [r for r in load_ext("v26_") if r["run"] in allowed]
    runs = nb + ext
    b9confirm.KS = list(range(12, min(len(r["Ynb"]) for r in ext)))
    tr = list(range(len(nb))); te = list(range(len(nb), len(runs)))
    P, members = b9confirm.ours_predict(runs, tr, te)
    per = {runs[i]["run"]: b9lib.corr_cols(P[runs[i]["run"]], runs[i]["Ynb"][b9confirm.KS]).tolist() for i in te}
    return {"fold": "all", "method": "zeroshot_ours_nb_to_ds003768", "per_scan": per, "members": members}


@app.local_entrypoint()
def main(methods: str = "ours,mel_ridge,mel_mlp,zeroshot"):
    cf = json.loads((HERE / "results" / "c3_folds.json").read_text())
    allowed = cf["runs"]; folds = cf["folds"]
    calls = []
    for m in methods.split(","):
        for prefix in ("", "v26_"):
            if m == "ours":
                calls += [(m, ours_fold.spawn(f, prefix, allowed)) for f in folds]
            elif m.startswith("mel"):
                calls += [(m, mel_fold.spawn(f, prefix, m.split("_")[1], allowed)) for f in folds]
        if m == "zeroshot":
            calls.append((m, zeroshot.spawn(allowed)))
    out = HERE / "results" / "c3_results.jsonl"
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
                print(r["method"], r["fold"], round(statistics.mean(statistics.mean(v) for v in r["per_scan"].values()), 4))
            else:
                print("ERR", r)
