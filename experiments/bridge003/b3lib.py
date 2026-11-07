import json
from pathlib import Path

TR = 0.8
BANDS = ["delta", "theta", "alpha", "beta", "gamma"]
FILMS = {"ThePresent": {"nbins": 250, "nvol": 250}, "DespicableMe": {"nbins": 222, "nvol": 750}}

def bandpass(x, lo=0.01, hi=0.08, fs=1 / TR):
    from scipy.signal import butter, filtfilt
    b, a = butter(2, [lo / (fs / 2), hi / (fs / 2)], btype="band")
    return filtfilt(b, a, x, axis=0)


def zs(x, axis=0):
    import numpy as np
    return (x - np.nanmean(x, axis, keepdims=True)) / (np.nanstd(x, axis, keepdims=True) + 1e-9)


def fill_nan(x):
    import numpy as np
    x = x.copy(); t = np.arange(x.shape[0])
    for idx in np.ndindex(x.shape[1:]):
        v = x[(slice(None),) + idx]; m = np.isfinite(v)
        if m.sum() >= 2 and (~m).any():
            v[~m] = np.interp(t[~m], t[m], v[m])
        elif m.sum() < 2:
            v[:] = 0.0
    return x


def load_children(split, film, offset_bins=0):
    import numpy as np
    feats = Path("/evidence/bridge003/features")
    T = FILMS[film]["nbins"]
    out = []
    chans_ref = None
    for f in sorted(feats.glob(f"*_{film}.npz")):
        sid = f.name.split("_")[0]
        rec = json.loads((feats / f"{sid}_receipt.json").read_text())
        if rec.get("split") != split or rec["films"].get(film, {}).get("status") != "ok":
            continue
        d = np.load(f, allow_pickle=True)
        if str(d["motion_exclude"]) != "0":
            continue
        chans = [str(c) for c in d["eeg_channels"]]
        if chans_ref is None:
            chans_ref = chans
        if chans != chans_ref or d["eeg_logpow"].shape[0] < T:
            continue
        e = d["eeg_logpow"][:T].astype(float)
        art = d["eeg_artifact"][:T]
        e[art] = np.nan
        e = zs(e); e = fill_nan(e); e = zs(bandpass(e))
        fm = {}
        for key in ("fmri456", "fmri156"):
            x = d[key].astype(float)
            full = np.full((T, x.shape[1]), np.nan)
            k0 = int(d["dummy"]) - offset_bins
            src = np.arange(T) - k0
            ok = (src >= 0) & (src < x.shape[0])
            full[ok] = x[src[ok]]
            fm[key] = zs(full)
        out.append({"sid": sid, "site": str(d["site"]), "eeg": e.astype(np.float32),
                    "f456": fm["fmri456"].astype(np.float32), "f156": fm["fmri156"].astype(np.float32),
                    "fmri_valid": float(np.isfinite(fm["fmri456"][:, 0]).mean())})
    d0 = np.load(sorted(feats.glob(f"*_{film}.npz"))[0], allow_pickle=True)
    meta = {"channels": chans_ref, "parcels456": [str(p) for p in d0["parcels456"]],
            "parcels156": [str(p) for p in d0["parcels156"]]}
    return out, meta


def split_half_rel(stack, n_splits=200, seed=0):
    import numpy as np
    rng = np.random.default_rng(seed)
    N = stack.shape[0]
    flat = stack.reshape(N, stack.shape[1], -1)
    rs = []
    for _ in range(n_splits):
        p = rng.permutation(N); a = np.nanmean(flat[p[:N // 2]], 0); b = np.nanmean(flat[p[N // 2:]], 0)
        a = zs(a); b = zs(b)
        r = np.nanmean(a * b, 0)
        rs.append(2 * r / (1 + r))
    rs = np.array(rs)
    shp = stack.shape[2:]
    return (np.median(rs, 0).reshape(shp), np.percentile(rs, 2.5, 0).reshape(shp),
            np.percentile(rs, 97.5, 0).reshape(shp))


def hrf(dt=TR, length=32.0):
    import numpy as np
    from scipy.stats import gamma
    t = np.arange(0, length, dt)
    h = gamma.pdf(t, 6) - gamma.pdf(t, 16) / 6.0
    return h / h.sum()


def stim_matrix(vis_npz, aud_npz, pca=None, fine_dt=0.1):
    import numpy as np
    v = np.load(vis_npz); a = np.load(aud_npz, allow_pickle=True)
    s = v["siglip"].astype(float); s /= np.linalg.norm(s, axis=1, keepdims=True)
    if pca is None:
        mu = s.mean(0); _, _, vt = np.linalg.svd(s - mu, full_matrices=False); pca = (mu, vt[:20])
    pcs = (s - pca[0]) @ pca[1].T
    fc = np.r_[0.0, 1.0 - np.sum(s[1:] * s[:-1], 1)]
    n = min(len(s), len(a["features"]))
    tv = np.arange(len(s)) + 0.5; ta = a["times"].astype(float) - 0.5
    tf = np.arange(0, n, fine_dt)
    cols = [np.interp(tf, tv, c) for c in np.c_[pcs, v["lowlevel"], fc].T]
    cols += [np.interp(tf, ta, c) for c in a["features"].astype(float).T]
    X = np.stack(cols, 1)
    X = (X - X.mean(0)) / (X.std(0) + 1e-9)
    return tf, X, pca


def corr_cols(a, b):
    import numpy as np
    pass
    return np.nanmean(zs(a) * zs(b), 0)


def lag_design(Z, lags, lead=False):
    import numpy as np
    T, K = Z.shape
    D = np.zeros((T, K * len(lags)))
    for i, l in enumerate(lags):
        if lead:
            D[:T - l, i * K:(i + 1) * K] = Z[l:]
        else:
            D[l:, i * K:(i + 1) * K] = Z[:T - l]
    return D


def ridge_fit(X, Y, a):
    import numpy as np
    return np.linalg.solve(X.T @ X + a * np.eye(X.shape[1]), X.T @ Y)


def choose_alpha(X, Y, rows, grid, gap=10):
    import numpy as np
    folds = np.array_split(rows, 5)
    scores = {}
    for a in grid:
        P = np.full(Y.shape, np.nan)
        for te in folds:
            tr = rows[(rows < te[0] - gap) | (rows > te[-1] + gap)]
            P[te] = X[te] @ ridge_fit(X[tr], Y[tr], a)
        scores[a] = float(np.nanmedian(corr_cols(P[rows], Y[rows])))
    return max(scores, key=scores.get), scores


def phase_surrogate(X, rng):
    import numpy as np
    T = X.shape[0]
    Fx = np.fft.rfft(X, axis=0)
    ph = np.exp(1j * rng.uniform(0, 2 * np.pi, Fx.shape[0]))
    ph[0] = 1
    if T % 2 == 0:
        ph[-1] = 1
    return np.fft.irfft(Fx * ph[:, None], n=T, axis=0)


def pca_fit(X, k):
    import numpy as np
    mu = X.mean(0)
    _, _, vt = np.linalg.svd(X - mu, full_matrices=False)
    return mu, vt[:k]


