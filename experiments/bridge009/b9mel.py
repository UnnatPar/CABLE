import json
import time
from pathlib import Path

import modal

HERE = Path(__file__).parent
app = modal.App("cable-b9mel")
volume = modal.Volume.from_name("cable-data")
image = (modal.Image.debian_slim(python_version="3.12")
         .pip_install("numpy==2.2.6", "scipy==1.18.1", "torch==2.8.0")
         .add_local_file(HERE / "b9lib.py", "/root/b9lib.py"))
FIRST, SCORE_FROM = 8, 12


def load_mel(variant="mel_zp"):
    import numpy as np
    runs = {}
    for f in sorted(Path("/evidence/bridge009/mel").glob("*.npz")):
        z = np.load(f)
        X = z[variant].reshape(len(z[variant]), -1).astype(np.float64)
        runs[f.stem] = {"X": X, "Y": z["Ynb"].astype(np.float64)}
    return runs


def pr(P, Y):
    import numpy as np
    Pz = (P - P.mean(0)) / (P.std(0) + 1e-9); Yz = (Y - Y.mean(0)) / (Y.std(0) + 1e-9)
    return (Pz * Yz).mean(0)


def mel_fit_predict(runs, train, val, test, readout="ridge", seeds=(1, 2, 3, 4, 5), mlp_cfg=None, dev="cpu"):
    import numpy as np
    Xtr = np.concatenate([runs[s]["X"][FIRST:] for s in train]); Ytr = np.concatenate([runs[s]["Y"][FIRST:] for s in train])
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-6
    Z = lambda X: (X - mu) / sd
    Xtr = Z(Xtr)
    Vx = [Z(runs[s]["X"][SCORE_FROM:]) for s in val]; Vy = [runs[s]["Y"][SCORE_FROM:] for s in val]
    Tx = [Z(runs[s]["X"][SCORE_FROM:]) for s in test]
    if readout == "ridge":
        XX = Xtr.T @ Xtr; XY = Xtr.T @ (Ytr - Ytr.mean(0))
        ev, EV = np.linalg.eigh(XX); B = EV.T @ XY
        grid = 10.0 ** np.linspace(-1, 7, 31)
        sc = np.zeros((len(grid), 7))
        for ai, a in enumerate(grid):
            W = EV @ (B / (ev + a)[:, None])
            sc[ai] = np.mean([pr(x @ W, y) for x, y in zip(Vx, Vy)], 0)
        best = sc.argmax(0)
        W = np.stack([EV @ (B[:, j] / (ev + grid[best[j]])) for j in range(7)], 1)
        P = [x @ W for x in Tx]
    else:
        import torch
        import torch.nn as nn
        cfg = dict(hid=256, drop=0.2, lr=1e-3, wd=1e-4, bs=256, epochs=200, patience=20)
        cfg.update(mlp_cfg or {})
        Pall = []
        Xt = torch.tensor(Xtr, dtype=torch.float32, device=dev); Yt = torch.tensor(Ytr, dtype=torch.float32, device=dev)
        Vt = [torch.tensor(x, dtype=torch.float32, device=dev) for x in Vx]
        for seed in seeds:
            torch.manual_seed(seed); np.random.seed(seed)
            net = nn.Sequential(nn.Linear(Xt.shape[1], cfg["hid"]), nn.GELU(), nn.Dropout(cfg["drop"]), nn.Linear(cfg["hid"], 7)).to(dev)
            opt = torch.optim.AdamW(net.parameters(), lr=cfg["lr"], weight_decay=cfg["wd"])
            best, bad, state = -9, 0, None
            for ep in range(cfg["epochs"]):
                net.train(); perm = torch.randperm(len(Xt), device=dev)
                for k in range(0, len(Xt), cfg["bs"]):
                    idx = perm[k:k + cfg["bs"]]
                    loss = ((net(Xt[idx]) - Yt[idx]) ** 2).mean()
                    opt.zero_grad(); loss.backward(); opt.step()
                net.eval()
                with torch.no_grad():
                    v = float(np.mean([pr(net(x).cpu().numpy(), y).mean() for x, y in zip(Vt, Vy)]))
                if v > best:
                    best, bad, state = v, 0, {k: t.detach().clone() for k, t in net.state_dict().items()}
                else:
                    bad += 1
                    if bad >= cfg["patience"]:
                        break
            net.load_state_dict(state); net.eval()
            with torch.no_grad():
                Pall.append([net(torch.tensor(x, dtype=torch.float32, device=dev)).cpu().numpy() for x in Tx])
        P = [np.mean([p[i] for p in Pall], 0) for i in range(len(Tx))]
        P1 = [Pall[0][i] for i in range(len(Tx))]
        return {s: (P[i], runs[s]["Y"][SCORE_FROM:], P1[i]) for i, s in enumerate(test)}
    return {s: (P[i], runs[s]["Y"][SCORE_FROM:]) for i, s in enumerate(test)}


@app.function(image=image, gpu="L4", cpu=4.0, memory=16384, timeout=3600, volumes={"/evidence": volume}, max_containers=60)
def dev_fold(held: str, readout: str, variant: str = "mel_zp") -> dict:
    import numpy as np
    import b9lib
    import torch
    runs = load_mel(variant)
    scans = [s for s in runs if s.split("-scan")[0] not in b9lib.NB_TEST_SUBS]
    subs = sorted({s.split("-scan")[0] for s in scans})
    trs = [s for s in subs if s != held]
    vsubs = set(trs[j] for j in range(len(trs)) if j % 4 == subs.index(held) % 4)
    train = [s for s in scans if s.split("-scan")[0] in trs and s.split("-scan")[0] not in vsubs]
    val = [s for s in scans if s.split("-scan")[0] in vsubs]
    test = [s for s in scans if s.startswith(held + "-")]
    res = mel_fit_predict(runs, train, val, test, readout, dev="cuda" if torch.cuda.is_available() else "cpu")
    return {s: [float(x) for x in pr(v[0], v[1])] for s, v in res.items()}


@app.local_entrypoint()
def main(mode: str = "dev"):
    import statistics
    subs = ["sub01", "sub02", "sub03", "sub04", "sub05", "sub06", "sub08", "sub09", "sub10", "sub12", "sub13", "sub14",
            "sub15", "sub17", "sub19", "sub20", "sub22"]
    jobs = [(s, ro, v) for ro in ("ridge", "mlp") for v in ("mel_zp", "mel_causal") for s in subs]
    res = list(dev_fold.starmap(jobs, return_exceptions=True))
    log = HERE / "results" / "dev_log.jsonl"
    with log.open("a", encoding="utf-8") as fh:
        for ro in ("ridge", "mlp"):
            for v in ("mel_zp", "mel_causal"):
                got = {}
                for (s, r_, v_), r in zip(jobs, res):
                    if r_ == ro and v_ == v and isinstance(r, dict):
                        got.update(r)
                    elif r_ == ro and v_ == v:
                        print("ERR", repr(r)[:300])
                rois = [statistics.mean(x[j] for x in got.values()) for j in range(7)]
                rec = {"name": f"MEL_{ro}_{v}_dev", "mean": statistics.mean(rois), "by_roi": [round(x, 4) for x in rois],
                       "n_scans": len(got), "note": "MEL reimplementation, scored vs NeuroBOLT-exact TR targets",
                       "logged": time.strftime("%Y-%m-%d %H:%M")}
                fh.write(json.dumps(rec) + "\n")
                print(f"{rec['name']:<34} {rec['mean']:.4f} n={len(got)} roi {rec['by_roi']}")
