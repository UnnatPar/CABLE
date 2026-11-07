import json
import random
import time
from pathlib import Path

import modal

HERE = Path(__file__).parent
app = modal.App("cable-b9eff")
volume = modal.Volume.from_name("cable-data")
image = (modal.Image.debian_slim(python_version="3.12")
         .pip_install("numpy==2.2.6", "scipy==1.18.1", "torch==2.8.0")
         .add_local_file(HERE / "b9lib.py", "/root/b9lib.py")
         .add_local_file(HERE / "b9mel.py", "/root/b9mel.py")
         .add_local_file(HERE / "b9confirm.py", "/root/b9confirm.py")
         .add_local_file(HERE / "b9c3.py", "/root/b9c3.py")
         .add_local_file(HERE / "results" / "c3_folds.json", "/root/c3_folds.json"))
DEV = ["sub01", "sub02", "sub03", "sub04", "sub05", "sub06", "sub08", "sub09", "sub10", "sub12", "sub13", "sub14",
       "sub15", "sub17", "sub19", "sub20", "sub22"]


@app.function(image=image, cpu=8.0, memory=49152, timeout=7200, volumes={"/evidence": volume}, max_containers=80)
def job(held: str, n: int, draw: int) -> dict:
    import numpy as np
    import b9confirm
    import b9lib
    import b9mel
    rng = random.Random(f"{held}-{n}-{draw}")
    pool = [s for s in DEV if s != held]
    pick = sorted(rng.sample(pool, n)) if n < len(pool) else pool
    runs = [r for r in b9lib.load_cache() if r["sub"] in pick + [held]]
    for r in runs:
        r["Ynb"] = np.load(f"/evidence/bridge009/mel/{r['run']}.npz")["Ynb"]
    te = [i for i, r in enumerate(runs) if r["sub"] == held]; tr = [i for i, r in enumerate(runs) if r["sub"] != held]
    P, _ = b9confirm.ours_predict(runs, tr, te)
    ours = float(np.mean([np.mean(b9lib.corr_cols(P[runs[i]["run"]], runs[i]["Ynb"][b9confirm.KS])) for i in te]))
    mruns = b9mel.load_mel("mel_zp")
    nval = max(1, round(0.25 * n)); vs = set(pick[:nval]) if n > 1 else set()
    train = [s for s in mruns if s.split("-scan")[0] in pick and s.split("-scan")[0] not in vs]
    val = [s for s in mruns if s.split("-scan")[0] in vs]
    test = [s for s in mruns if s.startswith(held + "-")]
    res = b9mel.mel_fit_predict(mruns, train, val, test, "ridge")
    mel = float(np.mean([np.mean(b9mel.pr(v[0], v[1])) for v in res.values()]))
    return {"held": held, "n": n, "draw": draw, "ours": ours, "mel_ridge": mel}


@app.local_entrypoint()
def main():
    import statistics as st
    jobs = [(h, n, d) for h in DEV for n in (4, 8, 12, 16) for d in (range(3) if n < 16 else [0])]
    res = [r for r in job.starmap(jobs, return_exceptions=True) if isinstance(r, dict)]
    (HERE / "results" / "data_efficiency.json").write_text(json.dumps(res, indent=1))
    for n in (4, 8, 12, 16):
        R = [r for r in res if r["n"] == n]
        o = st.mean(r["ours"] for r in R); m = st.mean(r["mel_ridge"] for r in R)
        print(f"n={n:2d}  ours {o:.4f}  mel_ridge {m:.4f}  gain {o - m:+.4f} ({(o - m) / m:+.0%})  jobs {len(R)}")
