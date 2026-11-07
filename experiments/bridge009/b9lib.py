import numpy as np

ROIS = ["cuneus", "heschl’s gyrus", "middle frontal gyrus anterior", "precuneus anterior", "putamen", "thalamus",
        "global signal clean"]
NB_TEST_SUBS = {"sub07", "sub11", "sub16", "sub18", "sub21"}
GRID = [1, 10, 100, 1000, 1e4, 1e5, 1e6, 1e7]
FS = 1.25
TR = 2.1


def _zs(x):
    return (x - np.nanmean(x, 0, keepdims=True)) / (np.nanstd(x, 0, keepdims=True) + 1e-9)


def target_lp(Y):
    from scipy.signal import butter, filtfilt
    Y = _zs(Y)
    t = np.arange(len(Y))
    for j in range(Y.shape[1]):
        v = Y[:, j]; m = np.isfinite(v)
        if m.sum() >= 2 and (~m).any():
            v[~m] = np.interp(t[~m], t[m], v[m])
        elif m.sum() < 2:
            v[:] = 0.0
    b, a = butter(2, 0.15 / (FS / 2), btype="low")
    return _zs(filtfilt(b, a, Y, axis=0))


def causal_zs(x, warm=2):
    n = np.arange(1, len(x) + 1)[:, None]
    m = np.cumsum(x, 0) / n
    v = np.maximum(np.cumsum(x ** 2, 0) / n - m ** 2, 0)
    s = np.sqrt(v); s[:warm] = 1.0
    out = (x - m) / (s + 1e-9)
    out[:warm] = 0.0
    return out


def ffill(x):
    x = x.copy()
    m = np.isfinite(x)
    idx = np.where(m, np.arange(len(x))[:, None], 0)
    np.maximum.accumulate(idx, axis=0, out=idx)
    out = np.take_along_axis(x, idx, 0)
    first = np.argmax(m, 0)
    out[np.arange(len(x))[:, None] < first[None, :]] = 0.0
    out[:, ~m.any(0)] = 0.0
    return out


def causal_filter(x, hp=0.01, lp=0.15, order=2):
    from scipy.signal import butter, lfilter
    x = causal_zs(ffill(x))
    if hp and lp:
        b, a = butter(order, [hp / (FS / 2), lp / (FS / 2)], btype="band")
    elif hp:
        b, a = butter(order, hp / (FS / 2), btype="high")
    elif lp:
        b, a = butter(order, lp / (FS / 2), btype="low")
    else:
        return x
    return causal_zs(lfilter(b, a, x, axis=0))


def lag_design(Z, lags):
    T, K = Z.shape
    D = np.zeros((T, K * len(lags)), dtype=np.float64)
    for i, l in enumerate(lags):
        D[l:, i * K:(i + 1) * K] = Z[:T - l]
    return D


def tr_rows(T, valid, min_row):
    k = np.arange(int(T * 0.8 / TR))
    r = np.clip(np.round(k * TR / 0.8 - 0.5).astype(int), 0, T - 1)
    return r[(r >= min_row) & valid[r]]


def corr_cols(a, b):
    return np.nanmean(_zs(a) * _zs(b), 0)


def load_cache(stems=None, root="/evidence/bridge009/cache"):
    from pathlib import Path
    runs = []
    for f in sorted(Path(root).glob("*.npz")):
        if stems is not None and f.stem not in stems:
            continue
        z = np.load(f, allow_pickle=True)
        r = {k: z[k] for k in z.files}
        r["run"] = f.stem; r["sub"] = f.stem.split("-scan")[0]
        for extra in ("phys", "feat2", "fm"):
          ph = Path(root).parent / extra / f"{f.stem}.npz"
          if ph.exists():
            zp = np.load(ph); n = len(r["valid"])
            for k in zp.files:
                a = zp[k][:n]
                r[k] = np.vstack([a, np.full((n - len(a), a.shape[1]), np.nan, a.dtype)]) if len(a) < n else a
            if extra == "feat2":
                r["valid"] = np.isfinite(r["cf2"]).all(1)
        runs.append(r)
    return runs


def featurize(run, cfg):
    blocks = []
    keep_ch = cfg.get("channels")
    for fam in cfg["fams"]:
        X = run[fam].astype(np.float64)
        if keep_ch is not None:
            if fam.startswith(("cf", "cb5", "fine", "b5")):
                nf = X.shape[1] // 26
                X = X.reshape(len(X), 26, nf)[:, keep_ch, :].reshape(len(X), -1)
            elif fam.startswith("cc7"):
                iu = np.triu_indices(26); ks = set(keep_ch)
                pair = np.array([(a in ks) and (b in ks) for a, b in zip(*iu)])
                X = X.reshape(len(X), len(pair), -1)[:, pair, :].reshape(len(X), -1)
        X = np.where(run["valid"][:, None], X, np.nan)
        blocks.append(causal_filter(X, hp=cfg.get("hp", 0.01), lp=cfg.get("lp", 0.15), order=cfg.get("order", 2)))
    d0 = blocks[0].shape[1]
    X = np.concatenate([b * np.sqrt(d0 / b.shape[1]) for b in blocks], 1)
    if cfg.get("ma"):
        from scipy.signal import lfilter
        X = lfilter(np.ones(cfg["ma"]) / cfg["ma"], [1.0], X, axis=0)
    return X


def build_designs(runs, feats, train_idx, cfg):
    k = cfg["pca_k"]
    pca_idx = list(range(len(runs))) if cfg.get("pca_all") else train_idx
    Xtr = np.concatenate([feats[i][runs[i]["valid"]] for i in pca_idx])
    mu = Xtr.mean(0)
    C = (Xtr - mu).T @ (Xtr - mu)
    w, V = np.linalg.eigh(C)
    V = V[:, ::-1][:, :k]
    lags = list(range(cfg.get("lag0", 2), cfg.get("lag0", 2) + cfg.get("n_lags", 30)))
    D = {}
    for i in range(len(runs)):
        Z = causal_zs((feats[i] - mu) @ V)
        if cfg.get("whiten"):
            Zw = np.zeros_like(Z); S = np.eye(k); m = np.zeros(k); lam = cfg["whiten"]
            for t in range(len(Z)):
                m = m + (Z[t] - m) / (t + 1)
                S = S + (np.outer(Z[t] - m, Z[t] - m) - S) / (t + 2)
                if t % 25 == 0:
                    w_, v_ = np.linalg.eigh((1 - lam) * S + lam * np.eye(k)); Wh = (v_ / np.sqrt(np.maximum(w_, 1e-6))) @ v_.T
                Zw[t] = Wh @ (Z[t] - m)
            Z = Zw
        if cfg.get("winsor"):
            Z = np.clip(Z, -cfg["winsor"], cfg["winsor"])
        D[i] = lag_design(Z, lags)
        if cfg.get("ema"):
            Zl = lag_design(Z, [lags[0]])
            E = []
            for tau in cfg["ema"]:
                from scipy.signal import lfilter
                a = np.exp(-1.0 / tau)
                E.append(causal_zs(lfilter([1 - a], [1, -a], Zl, axis=0)))
            D[i] = np.c_[D[i], np.concatenate(E, 1) * cfg.get("ema_w", 1.0)]
    return D, lags[-1]


def ridge_nested(runs, D, ytrain_key, train_idx, minrow, inner_folds=4, per_roi=False, grid=GRID, score_cols=None):
    subs = sorted({runs[i]["sub"] for i in train_idx})
    fold_of = {s: j % inner_folds for j, s in enumerate(subs)}
    XX, XY = {}, {}
    for i in train_idx:
        rows = np.where(runs[i]["valid"] & (np.arange(len(D[i])) >= minrow))[0]
        Xi = D[i][rows]; Yi = runs[i][ytrain_key][rows].astype(np.float64)
        XX[i] = Xi.T @ Xi; XY[i] = Xi.T @ Yi
    XXa = sum(XX.values()); XYa = sum(XY.values())
    p = XXa.shape[0]
    nout = XYa.shape[1]
    sc = np.zeros((len(grid), nout))
    for f in range(inner_folds):
        va = [i for i in train_idx if fold_of[runs[i]["sub"]] == f]
        if not va:
            continue
        XXf = XXa - sum(XX[i] for i in va); XYf = XYa - sum(XY[i] for i in va)
        ev, EV = np.linalg.eigh(XXf)
        B = EV.T @ XYf
        for ai, a in enumerate(grid):
            W = EV @ (B / (ev + a)[:, None])
            rs = []
            for i in va:
                rr = tr_rows(len(D[i]), runs[i]["valid"], minrow)
                rs.append(corr_cols(D[i][rr] @ W, runs[i][ytrain_key][rr]))
            sc[ai] += np.nanmean(rs, 0) / inner_folds
    ev, EV = np.linalg.eigh(XXa)
    B = EV.T @ XYa
    if per_roi:
        best = sc.argmax(0)
        W = np.zeros((p, nout))
        for j in range(nout):
            W[:, j] = EV @ (B[:, j] / (ev + grid[best[j]]))
        alpha = [grid[b] for b in best]
    else:
        cols = score_cols if score_cols is not None else slice(None)
        b = sc[:, cols].mean(1).argmax()
        W = EV @ (B / (ev + grid[b])[:, None])
        alpha = grid[b]
    return W, alpha, sc


def ridge_robust(runs, D, ykey, train_idx, minrow, gamma=1.0, floor=0.05):
    W0, alpha, _ = ridge_nested(runs, D, ykey, train_idx, minrow)
    subs = sorted({runs[i]["sub"] for i in train_idx})
    XX, XY = {}, {}
    for i in train_idx:
        rows = np.where(runs[i]["valid"] & (np.arange(len(D[i])) >= minrow))[0]
        XX[i] = D[i][rows].T @ D[i][rows]; XY[i] = D[i][rows].T @ runs[i][ykey][rows].astype(np.float64)
    XXa = sum(XX.values()); XYa = sum(XY.values()); p = XXa.shape[0]
    rs = {}
    for s in subs:
        own = [i for i in train_idx if runs[i]["sub"] == s]
        W = np.linalg.solve(XXa - sum(XX[i] for i in own) + alpha * np.eye(p), XYa - sum(XY[i] for i in own))
        vals = []
        for i in own:
            rr = tr_rows(len(D[i]), runs[i]["valid"], minrow)
            vals.append(np.nanmean(corr_cols(D[i][rr] @ W, runs[i][ykey][rr])[:7]))
        rs[s] = float(np.mean(vals))
    w = {s: max(v, floor) ** gamma for s, v in rs.items()}; m = np.mean(list(w.values())); w = {s: v / m for s, v in w.items()}
    A = sum(w[runs[i]["sub"]] * XX[i] for i in train_idx); B = sum(w[runs[i]["sub"]] * XY[i] for i in train_idx)
    return np.linalg.solve(A + alpha * np.eye(p), B), alpha, rs


def loso_dev(runs, cfg, subjects, ykey="Y7"):
    feats = {i: featurize(r, cfg) for i, r in enumerate(runs)}
    if ykey == "Yall":
        for r in runs:
            r["Y7all"] = np.c_[r["Y7"], r["Yall"]]
        ykey = "Y7all"
    out = {}
    for s in subjects:
        te = [i for i, r in enumerate(runs) if r["sub"] == s]
        tr = [i for i, r in enumerate(runs) if r["sub"] != s and (r["sub"] in subjects or r.get("extra"))]
        D, minrow = build_designs(runs, feats, tr, cfg)
        if cfg.get("bags"):
            rng = np.random.default_rng(abs(hash(s)) % 2**32)
            trs = sorted({runs[i]["sub"] for i in tr}); Ps = {i: [] for i in te}
            for b in range(cfg["bags"]):
                pick = set(rng.choice(trs, int(round(cfg.get("bag_frac", 0.75) * len(trs))), replace=False))
                tb = [i for i in tr if runs[i]["sub"] in pick]
                Wb, _, _ = ridge_nested(runs, D, ykey, tb, minrow)
                for i in te:
                    rr = tr_rows(len(D[i]), runs[i]["valid"], minrow)
                    Ps[i].append(_zs((D[i] @ Wb)[rr][:, :7]))
            for i in te:
                rr = tr_rows(len(D[i]), runs[i]["valid"], minrow)
                out[runs[i]["run"]] = {"P": np.mean(Ps[i], 0).astype(np.float32), "Y": runs[i]["Y7"][rr].astype(np.float32),
                                       "rows": rr, "alpha": "bag"}
            continue
        if cfg.get("robust"):
            W, alpha, _ = ridge_robust(runs, D, ykey, tr, minrow, gamma=cfg["robust"])
        else:
            W, alpha, _ = ridge_nested(runs, D, ykey, tr, minrow, per_roi=cfg.get("per_roi", False),
                                       score_cols=list(range(7)) if ykey != "Y7" else None)
        if cfg.get("rrr"):
            F = np.concatenate([D[i][runs[i]["valid"] & (np.arange(len(D[i])) >= minrow)] @ W for i in tr])
            F = (F - F.mean(0)) / (F.std(0) + 1e-9)
            _, _, vt = np.linalg.svd(F, full_matrices=False)
            Vr = vt[:cfg["rrr"]].T
            sd = np.concatenate([D[i][runs[i]["valid"] & (np.arange(len(D[i])) >= minrow)] @ W for i in tr]).std(0) + 1e-9
            W = ((W / sd) @ Vr @ Vr.T) * sd
        for i in te:
            rr = tr_rows(len(D[i]), runs[i]["valid"], minrow)
            Pfull = D[i] @ W
            if cfg.get("post_ma"):
                from scipy.signal import lfilter
                Pfull = lfilter(np.ones(cfg["post_ma"]) / cfg["post_ma"], [1.0], Pfull, axis=0)
            P = Pfull[rr]
            if ykey != "Y7":
                P = P[:, :7]
            out[runs[i]["run"]] = {"P": P.astype(np.float32), "Y": runs[i]["Y7"][rr].astype(np.float32),
                                   "rows": rr, "alpha": alpha}
    return out


def score(preds):
    per_run = {k: corr_cols(v["P"], v["Y"]) for k, v in preds.items()}
    M = np.array(list(per_run.values()))
    subs = {}
    for k, v in per_run.items():
        subs.setdefault(k.split("-scan")[0], []).append(np.mean(v))
    return {"mean": float(M.mean()), "by_roi": M.mean(0).round(4).tolist(),
            "by_sub": {s: round(float(np.mean(v)), 4) for s, v in sorted(subs.items())}}


def ensemble(pred_list, weights=None):
    keys = pred_list[0].keys()
    out = {}
    for k in keys:
        n = min(len(p[k]["P"]) for p in pred_list)
        w = weights or [1.0] * len(pred_list)
        P = sum(wi * _zs(p[k]["P"][:n]) for wi, p in zip(w, pred_list)) / sum(w)
        out[k] = {"P": P, "Y": pred_list[0][k]["Y"][:n], "rows": pred_list[0][k]["rows"][:n]}
    return out
