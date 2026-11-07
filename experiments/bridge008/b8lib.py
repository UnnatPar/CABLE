import json
from pathlib import Path

TEST = {"sub07-scan01", "sub07-scan02", "sub11-scan01", "sub16-scan01", "sub18-scan01", "sub21-scan01"}
ROIS = ["cuneus", "heschl’s gyrus", "middle frontal gyrus anterior", "precuneus anterior", "putamen", "thalamus",
        "global signal clean"]
LAGS = list(range(21))
GRID = [1, 10, 100, 1000, 1e4, 1e5, 1e6, 1e7]


def causal_zs(x, warm=1):
    import numpy as np
    n = np.arange(1, len(x) + 1)[:, None]
    m = np.cumsum(x, 0) / n
    v = np.maximum(np.cumsum(x ** 2, 0) / n - m ** 2, 0)
    s = np.sqrt(v); s[:warm] = 1.0
    return (x - m) / (s + 1e-9)


def filt(x, kind):
    import numpy as np
    from b3lib import bandpass, fill_nan, zs
    from scipy.signal import butter, filtfilt, lfilter
    if kind == "bpc":
        x = x.copy()
        for j in range(x.shape[1]):
            v = x[:, j]; m = np.isfinite(v)
            if not m.any():
                v[:] = 0.0; continue
            idx = np.where(m, np.arange(len(v)), 0); np.maximum.accumulate(idx, out=idx)
            v[:] = np.where(np.arange(len(v)) < np.argmax(m), 0.0, v[idx])
        x = causal_zs(x, warm=2)
        b, a = butter(2, [0.01 / 0.625, 0.15 / 0.625], btype="band")
        return causal_zs(lfilter(b, a, x, axis=0), warm=2)
    x = fill_nan(zs(x))
    if kind == "bp":
        return zs(bandpass(x, lo=0.01, hi=0.15))
    b, a = butter(2, 0.15 / (1.25 / 2), btype="low")
    return zs(filtfilt(b, a, x, axis=0))


def bspline_basis(n_lags=21, n_basis=7):
    import numpy as np
    from scipy.interpolate import BSpline
    k = 3
    inner = np.linspace(0, n_lags - 1, n_basis - k + 1)
    t = np.r_[[inner[0]] * k, inner, [inner[-1]] * k]
    x = np.arange(n_lags)
    B = np.stack([BSpline(t, np.eye(n_basis)[j], k)(x) for j in range(n_basis)], 1)
    B[-1, -1] = 1.0
    return B


def load_runs(feature, eeg_filter):
    import numpy as np
    from b3lib import zs
    base = sorted(Path("/evidence/bridge005/nb").glob("*.npz"))
    chs = None
    for f in base:
        c = set(str(x) for x in np.load(f, allow_pickle=True)["channels"]); chs = c if chs is None else chs & c
    common = [c for c in [str(x) for x in np.load(base[0], allow_pickle=True)["channels"]] if c in chs]
    runs = []
    for f in base:
        z = np.load(f, allow_pickle=True); ch = [str(c) for c in z["channels"]]
        names = [str(n).lower().replace("'", "’") for n in z["roi_names"]]
        Y = filt(z["roi_all"][:, [names.index(r) for r in ROIS]].astype(float), "lp")
        if feature == "bands5":
            X = z["eeg_logpow"][:, [ch.index(c) for c in common], :].astype(float)
        else:
            g = np.load(f"/evidence/bridge008/nb_fine/{f.stem}.npz", allow_pickle=True)
            gch = [str(c) for c in g["channels"]]
            X = g["eeg_fine"][:, [gch.index(c) for c in common], :].astype(float)
            n = min(len(X), len(Y)); X, Y = X[:n], Y[:n]
        valid = np.isfinite(X.reshape(len(X), -1)).all(1)
        Xf = filt(X.reshape(len(X), -1), eeg_filter)
        if feature in ("cov", "finecov", "cov7", "finecov7"):
            cv = np.load(f"/evidence/bridge008/{'nb_cov7' if feature.endswith('7') else 'nb_cov'}/{f.stem}.npz", allow_pickle=True)
            cch = [str(c).replace("'", "").replace("FPz", "Fpz") for c in cv["channels"]]
            n_c = len(cch); iu = np.triu_indices(n_c)
            pos = {(int(a), int(b)): k for k, (a, b) in enumerate(zip(*iu))}
            ci = sorted(cch.index(c) for c in common)
            sel = [pos[(a, b)] for ai, a in enumerate(ci) for b in ci[ai:]]
            C = cv["cov_tangent"][:, sel, :].astype(float).reshape(len(cv["cov_tangent"]), -1)
            n = min(len(C), len(Xf)); C = filt(C[:n], eeg_filter)
            Xf, Y, valid = Xf[:n], Y[:n], valid[:n]
            Xf = C if feature.startswith("cov") else np.c_[Xf, C * np.sqrt(Xf.shape[1] / C.shape[1])]
        runs.append({"run": f.stem, "sub": f.stem.split("-scan")[0], "X": Xf, "Y": Y, "valid": valid})
    return runs


def tr_rows(T, valid):
    import numpy as np
    k = np.arange(int(T * 0.8 / 2.1))
    r = np.clip(np.round(k * 2.1 / 0.8 - 0.5).astype(int), 0, T - 1)
    return r[(r >= LAGS[-1]) & valid[r]]


