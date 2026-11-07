import json
import time
from pathlib import Path

import modal

HERE = Path(__file__).parent
app = modal.App("cable-b9mlp")
volume = modal.Volume.from_name("cable-data")
image = (modal.Image.debian_slim(python_version="3.12")
         .pip_install("numpy==2.2.6", "scipy==1.18.1", "torch==2.8.0")
         .add_local_file(HERE / "b9lib.py", "/root/b9lib.py"))

F = dict(hp=0.002, lp=None, n_lags=30, lag0=2, winsor=3.0)
F1 = dict(hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0)
BATCHES = {
    "a1": {
        "mlpA_fa_rc_h128": dict(fams=["fa_cf2", "rc_cc7_2"], pca_k=40, hid=128, layers=1, drop=0.5, in_drop=0.2, wd=1e-2, aux=0.3, lr=3e-4, **F1),
        "mlpA_fa_rc_h512": dict(fams=["fa_cf2", "rc_cc7_2"], pca_k=40, hid=512, layers=1, drop=0.6, in_drop=0.3, wd=5e-2, aux=0.3, lr=3e-4, **F1),
        "mlpA_fa_rc_lin": dict(fams=["fa_cf2", "rc_cc7_2"], pca_k=40, hid=0, layers=0, drop=0.0, in_drop=0.2, wd=1e-2, aux=0.3, lr=3e-4, **F1),
        "mlpA_fa_h128": dict(fams=["fa_cf2_s2"], pca_k=20, hid=128, layers=1, drop=0.5, in_drop=0.2, wd=1e-2, aux=0.3, lr=3e-4, **F1),
    },
    "m1": {
        "mlp_fc7_h256": dict(fams=["fine", "cov7"], pca_k=60, hid=256, layers=1, drop=0.5, in_drop=0.2, wd=1e-2, aux=0.3, **F),
        "mlp_fc7_h512_d6": dict(fams=["fine", "cov7"], pca_k=60, hid=512, layers=1, drop=0.6, in_drop=0.3, wd=1e-2, aux=0.3, **F),
        "mlp_fc7_h256_l2": dict(fams=["fine", "cov7"], pca_k=60, hid=256, layers=2, drop=0.5, in_drop=0.2, wd=1e-2, aux=0.3, **F),
        "mlp_fc7_h64": dict(fams=["fine", "cov7"], pca_k=60, hid=64, layers=1, drop=0.3, in_drop=0.2, wd=1e-2, aux=0.3, **F),
        "mlp_fc7_h256_noaux": dict(fams=["fine", "cov7"], pca_k=60, hid=256, layers=1, drop=0.5, in_drop=0.2, wd=1e-2, aux=0.0, **F),
        "mlp_fc7_lin": dict(fams=["fine", "cov7"], pca_k=60, hid=0, layers=0, drop=0.0, in_drop=0.2, wd=1e-2, aux=0.3, **F),
        "mlp_fc4_h256": dict(fams=["fine", "cov4"], pca_k=40, hid=256, layers=1, drop=0.5, in_drop=0.2, wd=1e-2, aux=0.3, **F),
        "mlp_c7_h256": dict(fams=["cov7"], pca_k=40, hid=256, layers=1, drop=0.5, in_drop=0.2, wd=1e-2, aux=0.3, **F),
    },
}


def train_mlp(Xtr, Ytr, Xva_runs, Yva_runs, Xte, cfg, seed, dev):
    import numpy as np
    import torch
    import torch.nn as nn
    torch.manual_seed(seed); np.random.seed(seed)
    din, dout = Xtr.shape[1], Ytr.shape[1]
    layers, h = [nn.Dropout(cfg["in_drop"])], din
    for _ in range(cfg["layers"]):
        layers += [nn.Linear(h, cfg["hid"]), nn.GELU(), nn.Dropout(cfg["drop"])]; h = cfg["hid"]
    layers += [nn.Linear(h, dout)]
    net = nn.Sequential(*layers).to(dev)
    opt = torch.optim.AdamW(net.parameters(), lr=cfg.get("lr", 1e-3), weight_decay=cfg["wd"])
    Xt = torch.tensor(Xtr, dtype=torch.float32, device=dev); Yt = torch.tensor(Ytr, dtype=torch.float32, device=dev)
    w = torch.ones(dout, device=dev); w[7:] = cfg["aux"]
    Xv = [torch.tensor(x, dtype=torch.float32, device=dev) for x in Xva_runs]
    best, best_state, bad = -9, None, 0
    n = len(Xt); bs = cfg.get("bs", 256)
    for ep in range(cfg.get("epochs", 80)):
        net.train()
        perm = torch.randperm(n, device=dev)
        for k in range(0, n, bs):
            idx = perm[k:k + bs]
            xb = Xt[idx]
            if cfg.get("noise", 0):
                xb = xb + cfg["noise"] * torch.randn_like(xb)
            loss = (((net(xb) - Yt[idx]) ** 2) * w).mean()
            opt.zero_grad(); loss.backward(); opt.step()
        net.eval()
        with torch.no_grad():
            rs = []
            for xv, yv in zip(Xv, Yva_runs):
                p = net(xv)[:, :7].cpu().numpy()
                rs.append(np.mean([np.corrcoef(p[:, j], yv[:, j])[0, 1] for j in range(7)]))
        v = float(np.mean(rs))
        if v > best:
            best, bad = v, 0
            best_state = {k: t.detach().clone() for k, t in net.state_dict().items()}; best_ep = ep
        else:
            bad += 1
            if bad >= cfg.get("patience", 10):
                break
    net.load_state_dict(best_state); net.eval()
    with torch.no_grad():
        P = [net(torch.tensor(x, dtype=torch.float32, device=dev))[:, :7].cpu().numpy() for x in Xte]
    return P, best, best_ep


@app.function(image=image, cpu=16.0, memory=32768, timeout=7200, volumes={"/evidence": volume}, max_containers=80)
def run_fold(name: str, cfg: dict, held: str) -> dict:
    import numpy as np
    import torch
    import b9lib
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    runs = [r for r in b9lib.load_cache() if r["sub"] not in b9lib.NB_TEST_SUBS]
    subs = sorted({r["sub"] for r in runs})
    feats = {i: b9lib.featurize(r, cfg) for i, r in enumerate(runs)}
    te = [i for i, r in enumerate(runs) if r["sub"] == held]
    tr = [i for i, r in enumerate(runs) if r["sub"] != held]
    D, minrow = b9lib.build_designs(runs, feats, tr, cfg)
    Yk = {i: np.c_[runs[i]["Y7"], runs[i]["Yall"]] for i in range(len(runs))}
    rows = {i: np.where(runs[i]["valid"] & (np.arange(len(D[i])) >= minrow))[0] for i in range(len(runs))}
    trr = {i: b9lib.tr_rows(len(D[i]), runs[i]["valid"], minrow) for i in range(len(runs))}
    trsubs = [s for s in subs if s != held]
    nf = cfg.get("inner_folds", 4)
    Xte = [D[i][trr[i]] for i in te]
    preds, info = [], []
    for f in range(nf):
        va_s = {s for j, s in enumerate(trsubs) if j % nf == f}
        fi = [i for i in tr if runs[i]["sub"] not in va_s]; vi = [i for i in tr if runs[i]["sub"] in va_s]
        Xtr = np.concatenate([D[i][rows[i]] for i in fi]); Ytr = np.concatenate([Yk[i][rows[i]] for i in fi])
        for seed in range(cfg.get("seeds", 3)):
            P, best, ep = train_mlp(Xtr, Ytr, [D[i][trr[i]] for i in vi], [runs[i]["Y7"][trr[i]] for i in vi], Xte, cfg,
                                    seed + 100 * f, dev)
            preds.append(P); info.append((round(best, 3), ep))
    out = {}
    for j, i in enumerate(te):
        P = np.mean([b9lib._zs(p[j]) for p in preds], 0)
        out[runs[i]["run"]] = {"P": P.astype(np.float32), "Y": runs[i]["Y7"][trr[i]].astype(np.float32), "rows": trr[i]}
    return {"held": held, "preds": {k: {f: v[f].tolist() for f in v} for k, v in out.items()}, "info": info}


@app.function(image=image, cpu=2.0, memory=8192, timeout=600, volumes={"/evidence": volume})
def save(name: str, preds: dict) -> dict:
    import numpy as np
    import b9lib
    P = {k: {f: np.array(v[f]) for f in v} for k, v in preds.items()}
    out = Path("/evidence/bridge009/dev"); out.mkdir(parents=True, exist_ok=True)
    np.savez(out / f"{name}.npz", **{f"{k}__{f}": v[f] for k, v in P.items() for f in ("P", "Y", "rows")})
    volume.commit()
    return b9lib.score(P)


@app.local_entrypoint()
def main(batch: str = "m1", only: str = ""):
    subs = ["sub01", "sub02", "sub03", "sub04", "sub05", "sub06", "sub08", "sub09", "sub10", "sub12", "sub13", "sub14",
            "sub15", "sub17", "sub19", "sub20", "sub22"]
    cfgs = {k: v for k, v in BATCHES[batch].items() if not only or k in only.split(",")}
    jobs = [(n, c, s) for n, c in cfgs.items() for s in subs]
    res = list(run_fold.starmap(jobs, return_exceptions=True))
    log = HERE / "results" / "dev_log.jsonl"
    with log.open("a", encoding="utf-8") as fh:
        for n, c in cfgs.items():
            got = [r for (jn, _, _), r in zip(jobs, res) if jn == n and isinstance(r, dict)]
            errs = [repr(r)[:300] for (jn, _, _), r in zip(jobs, res) if jn == n and not isinstance(r, dict)]
            if errs:
                print(n, "ERRORS", len(errs), errs[0])
            if len(got) != len(subs):
                continue
            preds = {k: v for r in got for k, v in r["preds"].items()}
            sc = save.remote(n, preds)
            eps = [e for r in got for _, e in r["info"]]
            rec = {"name": n, "cfg": c, **sc, "median_best_epoch": sorted(eps)[len(eps) // 2], "logged": time.strftime("%Y-%m-%d %H:%M")}
            fh.write(json.dumps(rec) + "\n")
            print(f"{n:<40} {sc['mean']:.4f}  med_ep {rec['median_best_epoch']}  roi {sc['by_roi']}")
