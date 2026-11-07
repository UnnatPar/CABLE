import json
from pathlib import Path

import modal

HERE = Path(__file__).parent
app = modal.App("cable-b9feat3")
volume = modal.Volume.from_name("cable-data")
image = (modal.Image.debian_slim(python_version="3.12").pip_install("numpy==2.2.6", "scipy==1.18.1", "mne==1.13.2",
                                                                    "pymatreader==1.1.0")
         .add_local_file(HERE / "b9feat2.py", "/root/b9feat2.py"))


def families(x, sf, nb):
    import numpy as np
    from scipy.signal import butter, hilbert, sosfilt
    import b9feat2
    out = {}
    ends = np.round((np.arange(nb) + 1) * 0.8 * sf).astype(int)
    xa = x - x.mean(0, keepdims=True)
    xb = sosfilt(butter(4, [1, 45], btype="band", fs=sf, output="sos"), xa, axis=1)
    L = int(round(4 * sf)); han = np.hanning(L); f = np.fft.rfftfreq(L, 1 / sf)
    m = (f >= 2) & (f <= 40) & ~((f >= 7) & (f <= 14)); lf = np.log10(f[m]); A = np.c_[lf, np.ones_like(lf)]
    pinv = np.linalg.pinv(A)
    ap = np.full((nb, x.shape[0], 2), np.nan)
    for k, e in enumerate(ends):
        if e - L < 0 or e > x.shape[1]:
            continue
        P = np.abs(np.fft.rfft(xb[:, e - L:e] * han, axis=1)) ** 2
        ap[k] = (pinv @ np.log10(P[:, m] + 1e-30).T).T
    out["ap4"] = ap.reshape(nb, -1)
    C = x.shape[0]; iu = np.triu_indices(C, 1)
    def aec(sig):
        fam = []
        for lo, hi in b9feat2.B7:
            y = sosfilt(butter(4, [lo, hi], btype="band", fs=sf, output="sos"), sig, axis=1)
            F = np.full((nb, len(iu[0])), np.nan)
            for k, e in enumerate(ends):
                if e - L < 0 or e > x.shape[1]:
                    continue
                env = np.abs(hilbert(y[:, e - L:e], axis=1))
                F[k] = np.corrcoef(env)[iu]
            fam.append(np.arctanh(np.clip(F, -0.999, 0.999)))
        return np.concatenate(fam, 1)
    out["aec7_4"] = aec(xa)
    out["ea_aec7_4"] = aec(b9feat2.euclidean_align(x, sf))
    return out


def load(stem):
    import mne
    import numpy as np
    import b9feat2
    raw = mne.io.read_raw_eeglab(f"/evidence/neurobolt_data/EEG/{stem}_eeg.set", preload=True, verbose="ERROR")
    sf = float(raw.info["sfreq"]); names = [c.replace("'", "").replace("FPz", "Fpz") for c in raw.ch_names]
    x = raw.get_data(picks=[names.index(c) for c in b9feat2.COMMON]) * 1e6
    n_tr = len([d for d in raw.annotations.description if d.strip() == "R149"])
    return x, sf, int(np.floor(n_tr * 2.1 / 0.8))


@app.function(image=image, cpu=4.0, memory=16384, timeout=3600, volumes={"/evidence": volume}, max_containers=30)
def feat(stem: str) -> str:
    import numpy as np
    x, sf, nb = load(stem)
    out = families(x, sf, nb)
    p = Path(f"/evidence/bridge009/fm/{stem}.npz")
    old = dict(np.load(p)) if p.exists() else {}
    old.update({k: v.astype(np.float32) for k, v in out.items()})
    p.parent.mkdir(parents=True, exist_ok=True); np.savez(p, **old); volume.commit()
    return json.dumps({"stem": stem, "keys": sorted(old), "nan": {k: round(float(np.isnan(v).any(1).mean()), 3) for k, v in out.items()}})


@app.function(image=image, cpu=4.0, memory=16384, timeout=1800, volumes={"/evidence": volume})
def causal_test() -> str:
    import numpy as np
    x, sf, nb = load("sub06-scan01")
    x = x[:, :int(200 * sf)]; nb = int(200 / 0.8)
    a = families(x, sf, nb)
    t_s = 120.0; x2 = x.copy(); x2[:, int(t_s * sf):] += np.random.default_rng(0).normal(0, 20, x2[:, int(t_s * sf):].shape)
    b = families(x2, sf, nb); kmax = int(t_s / 0.8) - 1
    return json.dumps({k: [float(np.nanmax(np.abs(a[k][:kmax + 1] - b[k][:kmax + 1]))),
                           float(np.nanmax(np.abs(a[k][kmax + 1:] - b[k][kmax + 1:])))] for k in a})


@app.local_entrypoint()
def main(test: bool = False):
    if test:
        print("causal test [max diff up to t, after t]:", causal_test.remote()); return
    stems = sorted({e.path.split("/")[-1].replace("_eeg.set", "") for e in volume.listdir("/neurobolt_data/EEG") if e.path.endswith(".set")})
    for r in feat.map(stems, return_exceptions=True):
        print(r if isinstance(r, str) else repr(r)[:400])
