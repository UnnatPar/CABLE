import json
import time
from pathlib import Path

import modal

HERE = Path(__file__).parent
app = modal.App("cable-b9c2")
volume = modal.Volume.from_name("cable-data")
image = (modal.Image.debian_slim(python_version="3.12")
         .pip_install("numpy==2.2.6", "scipy==1.18.1", "torch==2.8.0")
         .add_local_file(HERE / "b9lib.py", "/root/b9lib.py")
         .add_local_file(HERE / "b9mel.py", "/root/b9mel.py")
         .add_local_file(HERE / "b9confirm.py", "/root/b9confirm.py"))
TRAIN_V, VAL_V, TEST_V = (8, 460), (471, 516), (527, 574)


def row_of(k):
    import numpy as np
    return np.clip(np.round(np.asarray(k) * 2.1 / 0.8 - 0.5).astype(int), 0, None)


@app.function(image=image, cpu=8.0, memory=49152, timeout=7200, volumes={"/evidence": volume}, max_containers=20)
def ours_member(name: str) -> dict:
    import numpy as np
    import b9confirm
    import b9lib
    cfg = b9confirm.FROZEN[name]
    runs = b9lib.load_cache()
    ynb = {r["run"]: np.load(f"/evidence/bridge009/mel/{r['run']}.npz")["Ynb"] for r in runs}
    feats = {i: b9lib.featurize(r, cfg) for i, r in enumerate(runs)}
    D, minrow = b9lib.build_designs(runs, feats, list(range(len(runs))), cfg)
    r_tr = {}
    for i in range(len(runs)):
        v = np.arange(max(row_of(TRAIN_V[0]), minrow), row_of(TRAIN_V[1]) + 1); r_tr[i] = v[runs[i]["valid"][v]]
    kv = np.arange(VAL_V[0], VAL_V[1] + 1); kt = np.arange(TEST_V[0], TEST_V[1] + 1)
    XX = {i: D[i][r_tr[i]].T @ D[i][r_tr[i]] for i in range(len(runs))}
    XY = {i: D[i][r_tr[i]].T @ runs[i]["Y7"][r_tr[i]] for i in range(len(runs))}
    XXa, XYa = sum(XX.values()), sum(XY.values())
    out = {}
    for i, r in enumerate(runs):
        Dv, Dt = D[i][row_of(kv)], D[i][row_of(kt)]
        yv = ynb[r["run"]][kv]
        res = {}
        ev, EV = np.linalg.eigh(XX[i]); C = EV.T @ XY[i]; best = (-9, None)
        for a in b9lib.GRID:
            W = EV @ (C / (ev + a)[:, None]); v = np.mean(b9lib.corr_cols(Dv @ W, yv))
            if v > best[0]:
                best = (v, W)
        res["own"] = (Dt @ best[1]).tolist()
        best = (-9, None)
        for w in (1, 3, 10, 30):
            ev, EV = np.linalg.eigh(XXa + (w - 1) * XX[i]); C = EV.T @ (XYa + (w - 1) * XY[i])
            for a in b9lib.GRID:
                W = EV @ (C / (ev + a)[:, None]); v = np.mean(b9lib.corr_cols(Dv @ W, yv))
                if v > best[0]:
                    best = (v, W)
        res["pooled"] = (Dt @ best[1]).tolist()
        res["y"] = ynb[r["run"]][kt].tolist()
        out[r["run"]] = res
    return {"member": name, "preds": out}


@app.function(image=image, cpu=16.0, memory=32768, timeout=7200, volumes={"/evidence": volume}, max_containers=20)
def mel_intra(readout: str) -> dict:
    import numpy as np
    import torch
    import b9mel
    runs = b9mel.load_mel("mel_zp")
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    out = {}
    for mode in ("own", "pooled"):
        for s in runs:
            cut = lambda r, lo, hi: {"X": r["X"][:hi + 1], "Y": r["Y"][:hi + 1]}
            tr = {}
            for q in (runs if mode == "pooled" else [s]):
                tr[q + "_tr"] = {"X": np.vstack([np.full((b9mel.FIRST, runs[q]["X"].shape[1]), np.nan), runs[q]["X"][b9mel.FIRST:TRAIN_V[1] + 1]]),
                                 "Y": runs[q]["Y"][:TRAIN_V[1] + 1]}
            va = {"val": {"X": np.vstack([np.zeros((b9mel.SCORE_FROM, runs[s]["X"].shape[1])), runs[s]["X"][VAL_V[0]:VAL_V[1] + 1]]),
                          "Y": np.vstack([np.zeros((b9mel.SCORE_FROM, 7)), runs[s]["Y"][VAL_V[0]:VAL_V[1] + 1]])}}
            te = {"test": {"X": np.vstack([np.zeros((b9mel.SCORE_FROM, runs[s]["X"].shape[1])), runs[s]["X"][TEST_V[0]:TEST_V[1] + 1]]),
                           "Y": np.vstack([np.zeros((b9mel.SCORE_FROM, 7)), runs[s]["Y"][TEST_V[0]:TEST_V[1] + 1]])}}
            allr = {**tr, **va, **te}
            res = b9mel.mel_fit_predict(allr, list(tr), ["val"], ["test"], readout, dev=dev)
            out.setdefault(mode, {})[s] = b9mel.pr(res["test"][0], res["test"][1]).tolist()
    return {"method": f"mel_{readout}", "per_scan": out}


@app.function(image=image, cpu=4.0, memory=16384, timeout=10800, volumes={"/evidence": volume})
def ours_ensemble() -> dict:
    import numpy as np
    import b9confirm
    import b9lib
    mem = list(ours_member.map(list(b9confirm.FROZEN)))
    out = {}
    for mode in ("own", "pooled"):
        per = {}
        for r in mem[0]["preds"]:
            P = np.mean([b9lib._zs(np.array(m["preds"][r][mode])) for m in mem], 0)
            per[r] = b9lib.corr_cols(P, np.array(mem[0]["preds"][r]["y"])).tolist()
        out[mode] = per
    return {"method": "ours", "per_scan": out}


@app.local_entrypoint()
def main(methods: str = "ours,mel_ridge,mel_mlp"):
    import statistics
    calls = []
    if "ours" in methods:
        calls.append(ours_ensemble.spawn())
    for m in [x for x in methods.split(",") if x.startswith("mel")]:
        calls.append(mel_intra.spawn(m.split("_")[1]))
    log = HERE / "results" / "c2_results.jsonl"
    with log.open("a", encoding="utf-8") as fh:
        for c in calls:
            try:
                r = c.get()
            except Exception as e:
                r = {"error": repr(e)[:500]}
            r["logged"] = time.strftime("%Y-%m-%d %H:%M")
            fh.write(json.dumps(r) + "\n"); fh.flush()
            if "per_scan" in r:
                for mode, per in r["per_scan"].items():
                    print(r["method"], mode, round(statistics.mean(statistics.mean(v) for v in per.values()), 4), len(per))
            else:
                print("ERR", r)
