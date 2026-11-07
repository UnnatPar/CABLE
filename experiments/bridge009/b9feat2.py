import json
from pathlib import Path

import modal

app = modal.App("cable-b9feat2")
volume = modal.Volume.from_name("cable-data")
image = modal.Image.debian_slim(python_version="3.12").pip_install("numpy==2.2.6", "scipy==1.18.1", "mne==1.13.2",
                                                                   "pymatreader==1.1.0")
COMMON = ['Fp1', 'Fp2', 'F3', 'F4', 'C3', 'C4', 'P3', 'P4', 'O1', 'O2', 'F7', 'F8', 'T7', 'T8', 'P7', 'P8', 'Fpz', 'Fz',
          'Cz', 'Pz', 'POz', 'Oz', 'FT9', 'FT10', 'TP9', 'TP10']
B7 = [(1, 4), (4, 8), (8, 10), (10, 13), (13, 20), (20, 30), (30, 45)]


def cov_family(x, sf, nb, w, mode):
    import mne
    import numpy as np
    from scipy.signal import butter, sosfilt, sosfiltfilt
    ends = np.round((np.arange(nb) + 1) * 0.8 * sf).astype(int)
    xa = x - x.mean(0, keepdims=True)
    C = x.shape[0]; iu = np.triu_indices(C); scale = np.where(iu[0] == iu[1], 1.0, np.sqrt(2.0))
    L = int(round(w * sf)); fam = []
    for lo, hi in B7:
        if mode == "zpfir":
            y = mne.filter.filter_data(xa, sf, lo, hi, verbose="ERROR")
        elif mode == "butter8":
            y = sosfilt(butter(8, [lo, hi], btype="band", fs=sf, output="sos"), xa, axis=1)
        else:
            y = sosfiltfilt(butter(4, [lo, hi], btype="band", fs=sf, output="sos"), xa, axis=1)
        T = np.full((nb, len(iu[0])), np.nan)
        for k, e in enumerate(ends):
            if e - L < 0 or e > x.shape[1]:
                continue
            cv = np.cov(y[:, e - L:e]) + 1e-12 * np.eye(C); cv = cv / np.trace(cv)
            wv, V = np.linalg.eigh(cv)
            T[k] = ((V * np.log(np.clip(wv, 1e-12, None))) @ V.T)[iu[0], iu[1]] * scale
        fam.append(T)
    return np.stack(fam, 2).reshape(nb, -1)


def features(x, sf, nb):
    import numpy as np
    from scipy.signal import butter, sosfilt
    out = {}
    ends = np.round((np.arange(nb) + 1) * 0.8 * sf).astype(int)
    bad = np.zeros(nb, bool)
    xb = sosfilt(butter(4, [1, 45], btype="band", fs=sf, output="sos"), x, axis=1)
    for w in (1, 2, 4):
        L = int(round(w * sf)); han = np.hanning(L)
        f = np.fft.rfftfreq(L, 1 / sf)
        masks = [(f >= lo) & (f < lo + 2) for lo in range(1, 45, 2)]
        F = np.full((nb, x.shape[0], 22), np.nan)
        for k, e in enumerate(ends):
            if e - L < 0 or e > x.shape[1]:
                continue
            seg = xb[:, e - L:e]
            if w == 2:
                bad[k] = (np.abs(x[:, max(0, e - int(0.8 * sf)):e]) > 500).any()
            P = np.abs(np.fft.rfft(seg * han, axis=1)) ** 2
            F[k] = np.log(np.stack([P[:, m].mean(1) for m in masks], 1) + 1e-30)
        out[f"cf{w}"] = F.reshape(nb, -1)
    b5 = [(1, 4), (4, 8), (8, 13), (13, 30), (30, 45)]
    L = int(round(2 * sf)); han = np.hanning(L); f = np.fft.rfftfreq(L, 1 / sf)
    G = np.full((nb, x.shape[0], 5), np.nan)
    for k, e in enumerate(ends):
        if e - L >= 0 and e <= x.shape[1]:
            P = np.abs(np.fft.rfft(xb[:, e - L:e] * han, axis=1)) ** 2
            G[k] = np.log(np.stack([P[:, (f >= lo) & (f < hi)].mean(1) for lo, hi in b5], 1) + 1e-30)
    out["cb5_2"] = G.reshape(nb, -1)
    xa = x - x.mean(0, keepdims=True)
    C = x.shape[0]; iu = np.triu_indices(C); scale = np.where(iu[0] == iu[1], 1.0, np.sqrt(2.0))
    for w in (2, 4):
        L = int(round(w * sf))
        fam = []
        for lo, hi in B7:
            y = sosfilt(butter(4, [lo, hi], btype="band", fs=sf, output="sos"), xa, axis=1)
            Lc = np.full((nb, C, C), np.nan)
            for k, e in enumerate(ends):
                if e - L < 0 or e > x.shape[1]:
                    continue
                cv = np.cov(y[:, e - L:e]) + 1e-12 * np.eye(C)
                cv = cv / np.trace(cv)
                wv, V = np.linalg.eigh(cv)
                Lc[k] = (V * np.log(np.clip(wv, 1e-12, None))) @ V.T
            T = Lc
            fam.append((T[:, iu[0], iu[1]] * scale))
        out[f"cc7_{w}"] = np.stack(fam, 2).reshape(nb, -1)
    for k in out:
        out[k][bad] = np.nan
    return out


def euclidean_align(x, sf, upd_s=8.0):
    import numpy as np
    from scipy.signal import butter, sosfilt
    xa = x - x.mean(0, keepdims=True)
    xb = sosfilt(butter(4, [1, 45], btype="band", fs=sf, output="sos"), xa, axis=1)
    L = int(round(upd_s * sf)); C = x.shape[0]
    out = np.empty_like(xa); acc = np.zeros((C, C)); n = 0
    Wm = np.eye(C) / np.sqrt(np.trace(np.cov(xb[:, :L])) / C)
    for s0 in range(0, x.shape[1], L):
        out[:, s0:s0 + L] = Wm @ xa[:, s0:s0 + L]
        seg = xb[:, s0:s0 + L]
        if seg.shape[1] == L:
            acc += np.cov(seg); n += 1
            R = acc / n + 1e-3 * np.trace(acc / n) / C * np.eye(C)
            w, V = np.linalg.eigh(R); Wm = (V / np.sqrt(w)) @ V.T
    return out


def recentred_cov(x, sf, nb, w=2.0, upd_s=8.0, bands=None):
    import numpy as np
    from scipy.signal import butter, sosfilt
    bands = bands or B7
    ends = np.round((np.arange(nb) + 1) * 0.8 * sf).astype(int)
    xa = x - x.mean(0, keepdims=True)
    C = x.shape[0]; iu = np.triu_indices(C); scale = np.where(iu[0] == iu[1], 1.0, np.sqrt(2.0))
    L = int(round(w * sf)); step = max(1, int(round(upd_s / 0.8)))
    fam = []
    for lo, hi in bands:
        y = sosfilt(butter(4, [lo, hi], btype="band", fs=sf, output="sos"), xa, axis=1)
        covs = np.full((nb, C, C), np.nan)
        for k, e in enumerate(ends):
            if e - L >= 0 and e <= x.shape[1]:
                cv = np.cov(y[:, e - L:e]); covs[k] = cv / np.trace(cv) + 1e-6 * np.eye(C)
        T = np.full((nb, len(iu[0])), np.nan); acc = np.zeros((C, C)); n = 0; Wm = np.eye(C) * np.sqrt(C)
        for k in range(nb):
            if k % step == 0 and n > 0:
                R = acc / n; wv, V = np.linalg.eigh(R); Wm = (V / np.sqrt(np.maximum(wv, 1e-9))) @ V.T
            if np.isfinite(covs[k, 0, 0]):
                M = Wm @ covs[k] @ Wm
                wv, V = np.linalg.eigh(M)
                T[k] = ((V * np.log(np.clip(wv, 1e-9, None))) @ V.T)[iu[0], iu[1]] * scale
                acc += covs[k]; n += 1
        fam.append(T)
    return np.stack(fam, 2).reshape(nb, -1)


def freq_aligned_spectra(x, sf, nb, w=2.0, upd_s=8.0, binw=2, fmax=45, shrink=1e-3, half_life_s=None, full=False):
    import numpy as np
    from scipy.signal import butter, sosfilt
    xa = x - x.mean(0, keepdims=True)
    xb = sosfilt(butter(4, [1, fmax], btype="band", fs=sf, output="sos"), xa, axis=1)
    ends = np.round((np.arange(nb) + 1) * 0.8 * sf).astype(int)
    L = int(round(w * sf)); han = np.hanning(L); f = np.fft.rfftfreq(L, 1 / sf)
    edges = list(range(1, fmax, binw)); masks = [(f >= lo) & (f < lo + binw) for lo in edges]
    C = x.shape[0]; step = max(1, int(round(upd_s / 0.8)))
    iu = np.triu_indices(C); scale = np.where(iu[0] == iu[1], 1.0, np.sqrt(2.0))
    out = np.full((nb, len(iu[0]) if full else C, len(edges)), np.nan)
    acc = np.zeros((len(edges), C, C)); n = 0.0; Wm = None
    lam = 0.5 ** (0.8 / half_life_s) if half_life_s else 1.0
    for k, e in enumerate(ends):
        if k % step == 0 and n > 0:
            Wm = []
            for b in range(len(edges)):
                R = acc[b] / n; R = R + shrink * np.trace(R) / C * np.eye(C)
                wv, V = np.linalg.eigh(R); Wm.append((V / np.sqrt(wv)) @ V.T)
        if e - L < 0 or e > x.shape[1]:
            continue
        Z = np.fft.rfft(xb[:, e - L:e] * han, axis=1)
        for b, m in enumerate(masks):
            S = np.real(Z[:, m] @ Z[:, m].conj().T) / m.sum()
            if full:
                M = (Wm[b] @ S @ Wm[b]) if Wm is not None else S / (np.trace(S) / C)
                M = M + 1e-6 * np.trace(M) / C * np.eye(C)
                wv, V = np.linalg.eigh(M)
                out[k, :, b] = ((V * np.log(np.clip(wv, 1e-12, None))) @ V.T)[iu[0], iu[1]] * scale
            elif Wm is not None:
                out[k, :, b] = np.log(np.maximum(np.einsum("ij,jk,ik->i", Wm[b], S, Wm[b]), 1e-30))
            else:
                out[k, :, b] = np.log(np.maximum(np.diag(S) / (np.trace(S) / C), 1e-30))
            acc[b] = lam * acc[b] + S
        n = lam * n + 1
    return out.reshape(nb, -1)


POSTERIOR = ["O1", "O2", "Oz", "P3", "P4", "Pz", "POz", "P7", "P8"]


def iaf_aligned_spectra(x, sf, nb, chans, w=4.0, upd_s=8.0, shrink=1e-2, offsets=None, half=1.0):
    import numpy as np
    from scipy.signal import butter, sosfilt
    offsets = offsets if offsets is not None else list(range(-8, 34, 2))
    xa = x - x.mean(0, keepdims=True)
    xb = sosfilt(butter(4, [1, 45], btype="band", fs=sf, output="sos"), xa, axis=1)
    ends = np.round((np.arange(nb) + 1) * 0.8 * sf).astype(int)
    L = int(round(w * sf)); han = np.hanning(L); f = np.fft.rfftfreq(L, 1 / sf)
    post = [chans.index(c) for c in POSTERIOR if c in chans]
    C = x.shape[0]; step = max(1, int(round(upd_s / 0.8)))
    out = np.full((nb, C, len(offsets)), np.nan); iafs = np.full(nb, np.nan)
    acc = np.zeros((len(offsets), C, C)); n = 0; Wm = None
    pacc = np.zeros(len(f)); pn = 0; iaf = 10.0
    for k, e in enumerate(ends):
        if k % step == 0 and n > 0:
            ps = np.log(pacc / pn + 1e-30); band = (f >= 7) & (f <= 13)
            fit = ((f >= 2) & (f < 7)) | ((f > 14) & (f <= 30))
            co = np.polyfit(np.log(f[fit]), ps[fit], 1)
            res = np.convolve(ps - np.polyval(co, np.log(np.maximum(f, 1e-3))), np.ones(3) / 3, mode="same")
            iaf = float(f[band][np.argmax(res[band])]) if res[band].max() > 0.1 else 10.0
            Wm = []
            for b in range(len(offsets)):
                R = acc[b] / n; R = R + shrink * np.trace(R) / C * np.eye(C)
                wv, V = np.linalg.eigh(R); Wm.append((V / np.sqrt(wv)) @ V.T)
        if e - L < 0 or e > x.shape[1]:
            continue
        Z = np.fft.rfft(xb[:, e - L:e] * han, axis=1)
        pacc += (np.abs(Z[post]) ** 2).mean(0); pn += 1
        iafs[k] = iaf
        for b, o in enumerate(offsets):
            m = (f >= iaf + o - half) & (f < iaf + o + half)
            if not m.any():
                continue
            S = np.real(Z[:, m] @ Z[:, m].conj().T) / m.sum()
            if Wm is not None:
                out[k, :, b] = np.log(np.maximum(np.einsum("ij,jk,ik->i", Wm[b], S, Wm[b]), 1e-30))
            else:
                out[k, :, b] = np.log(np.maximum(np.diag(S) / (np.trace(S) / C), 1e-30))
            acc[b] += S
        n += 1
    return out.reshape(nb, -1), iafs


def frozen_families(x, sf, nb):
    out = {k: v for k, v in features(x, sf, nb).items() if k in ("cf2", "cf4", "cc7_2", "cc7_4")}
    ea = features(euclidean_align(x, sf), sf, nb)
    out.update({f"ea_{k}": v for k, v in ea.items() if k in ("cf2", "cc7_2", "cf4", "cc7_4")})
    out["fa_cf2"] = freq_aligned_spectra(x, sf, nb, 2.0)
    out["fa_cf4"] = freq_aligned_spectra(x, sf, nb, 4.0)
    out["fa1_cf4"] = freq_aligned_spectra(x, sf, nb, 4.0, binw=1)
    out["fa_cf2_s2"] = freq_aligned_spectra(x, sf, nb, 2.0, shrink=1e-2)
    out["rc_cc7_2"] = recentred_cov(x, sf, nb, 2.0)
    out["rc_cc7_4"] = recentred_cov(x, sf, nb, 4.0)
    return out


@app.function(image=image, cpu=4.0, memory=16384, timeout=3600, volumes={"/evidence": volume}, max_containers=30)
def feat(stem: str) -> str:
    import mne
    import numpy as np
    raw = mne.io.read_raw_eeglab(f"/evidence/neurobolt_data/EEG/{stem}_eeg.set", preload=True, verbose="ERROR")
    sf = float(raw.info["sfreq"])
    names = [c.replace("'", "").replace("FPz", "Fpz") for c in raw.ch_names]
    x = raw.get_data(picks=[names.index(c) for c in COMMON]) * 1e6
    n_tr = len([d for d in raw.annotations.description if d.strip() == "R149"])
    nb = int(np.floor(n_tr * 2.1 / 0.8))
    out = features(x, sf, nb)
    for mode in ("zpfir", "butter8", "zpbutter"):
        out[f"dc7_{mode}"] = cov_family(x, sf, nb, 2, mode)
    ea = features(euclidean_align(x, sf), sf, nb)
    out.update({f"ea_{k}": v for k, v in ea.items() if k in ("cf2", "cc7_2", "cf4", "cc7_4", "cf1", "cb5_2")})
    ea4 = features(euclidean_align(x, sf, upd_s=4.0), sf, nb)
    out.update({f"ea4_{k}": v for k, v in ea4.items() if k in ("cf2", "cc7_2")})
    ea30 = features(euclidean_align(x, sf, upd_s=30.0), sf, nb)
    out.update({f"ea30_{k}": v for k, v in ea30.items() if k in ("cf2", "cc7_2")})
    out["fa_cf2"] = freq_aligned_spectra(x, sf, nb, 2.0)
    out["fa_cf4"] = freq_aligned_spectra(x, sf, nb, 4.0)
    out["fa1_cf4"] = freq_aligned_spectra(x, sf, nb, 4.0, binw=1)
    out["fa_cf2_s2"] = freq_aligned_spectra(x, sf, nb, 2.0, shrink=1e-2)
    out["fa_cf2_s1"] = freq_aligned_spectra(x, sf, nb, 2.0, shrink=1e-1)
    out["fa_cf2_h120"] = freq_aligned_spectra(x, sf, nb, 2.0, half_life_s=120)
    out["fa_cf2_h300"] = freq_aligned_spectra(x, sf, nb, 2.0, half_life_s=300)
    out["faf_cc4"] = freq_aligned_spectra(x, sf, nb, 2.0, binw=4, full=True)
    out["rc_cc7_2"] = recentred_cov(x, sf, nb, 2.0)
    out["rc_cc7_4"] = recentred_cov(x, sf, nb, 4.0)
    out["iaf_fa4"], iafs = iaf_aligned_spectra(x, sf, nb, COMMON, w=4.0)
    out["iaf_fa2"], _ = iaf_aligned_spectra(x, sf, nb, COMMON, w=2.0)
    out["iaf_track"] = iafs[:, None]
    Path("/evidence/bridge009/feat2").mkdir(parents=True, exist_ok=True)
    np.savez(f"/evidence/bridge009/feat2/{stem}.npz", **{k: v.astype(np.float32) for k, v in out.items()})
    volume.commit()
    return json.dumps({"stem": stem, "nb": nb, "iaf_final": float(iafs[-1]), "dims": {k: int(v.shape[1]) for k, v in out.items()},
                       "nan_frac": {k: round(float(np.isnan(v).any(1).mean()), 3) for k, v in out.items()}})


@app.function(image=image, cpu=4.0, memory=16384, timeout=1800, volumes={"/evidence": volume})
def causal_test() -> str:
    import mne
    import numpy as np
    raw = mne.io.read_raw_eeglab("/evidence/neurobolt_data/EEG/sub06-scan01_eeg.set", preload=True, verbose="ERROR")
    sf = float(raw.info["sfreq"]); names = [c.replace("'", "").replace("FPz", "Fpz") for c in raw.ch_names]
    x = raw.get_data(picks=[names.index(c) for c in COMMON])[:, :int(200 * sf)] * 1e6
    nb = int(200 / 0.8)
    def allf(xx):
        o = features(xx, sf, nb)
        o.update({f"ea_{k}": v for k, v in features(euclidean_align(xx, sf), sf, nb).items()})
        o["fa_cf2"] = freq_aligned_spectra(xx, sf, nb, 2.0)
        o["fa_cf2_s2"] = freq_aligned_spectra(xx, sf, nb, 2.0, shrink=1e-2)
        o["rc_cc7_2"] = recentred_cov(xx, sf, nb, 2.0)
        o["rc_cc7_4"] = recentred_cov(xx, sf, nb, 4.0)
        o["fa_cf4"] = freq_aligned_spectra(xx, sf, nb, 4.0)
        o["iaf_fa4"] = iaf_aligned_spectra(xx, sf, nb, COMMON, w=4.0)[0]
        return o
    a = allf(x)
    t_s = 120.0; x2 = x.copy(); x2[:, int(t_s * sf):] += np.random.default_rng(0).normal(0, 20, x2[:, int(t_s * sf):].shape)
    b = allf(x2)
    kmax = int(t_s / 0.8) - 1
    return json.dumps({k: [float(np.nanmax(np.abs(a[k][:kmax + 1] - b[k][:kmax + 1]))),
                           float(np.nanmax(np.abs(a[k][kmax + 1:] - b[k][kmax + 1:])))] for k in a})


@app.local_entrypoint()
def main(test: bool = False):
    if test:
        print("causal test [max diff up to t, after t]:", causal_test.remote())
        return
    stems = sorted({e.path.split("/")[-1].replace("_eeg.set", "") for e in volume.listdir("/neurobolt_data/EEG") if e.path.endswith(".set")})
    for r in feat.map(stems, return_exceptions=True):
        print(r if isinstance(r, str) else repr(r)[:300])
