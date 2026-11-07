from pathlib import Path

import modal

app = modal.App("cable-b9melfeat")
volume = modal.Volume.from_name("cable-data")
image = modal.Image.debian_slim(python_version="3.12").pip_install("numpy==2.2.6", "scipy==1.18.1", "mne==1.13.2",
                                                                   "pymatreader==1.1.0", "pandas==2.3.3")
BANDS = [(1, 4), (4, 8), (8, 13), (13, 30), (30, 45)]
ROIS = ["Cuneus", "Heschl’s gyrus", "Middle frontal gyrus anterior", "Precuneus anterior", "Putamen", "Thalamus",
        "global signal clean"]


@app.function(image=image, cpu=4.0, memory=16384, timeout=1800, volumes={"/evidence": volume}, max_containers=30)
def mel(stem: str, common: list) -> str:
    import json
    import mne
    import numpy as np
    import pandas as pd
    from scipy.signal import butter, filtfilt, sosfilt, sosfiltfilt
    raw = mne.io.read_raw_eeglab(f"/evidence/neurobolt_data/EEG/{stem}_eeg.set", preload=True, verbose="ERROR")
    sf = float(raw.info["sfreq"])
    names = [c.replace("'", "").replace("FPz", "Fpz") for c in raw.ch_names]
    x = raw.get_data(picks=[names.index(c) for c in common]) * 1e6
    ann = raw.annotations
    trig = np.array([o for o, d in zip(ann.onset, ann.description) if d.strip() == "R149"])
    n_tr = len(trig)
    out = {}
    for mode in ("zp", "causal"):
        cube = np.full((n_tr, 8, len(common), len(BANDS)), np.nan, np.float32)
        for b, (lo, hi) in enumerate(BANDS):
            sos = butter(4, [lo, hi], btype="band", fs=sf, output="sos")
            xb = sosfiltfilt(sos, x, axis=1) if mode == "zp" else sosfilt(sos, x, axis=1)
            sq = xb ** 2
            cs = np.concatenate([np.zeros((sq.shape[0], 1)), np.cumsum(sq, 1)], 1)
            for k, t in enumerate(trig):
                end = int(round(t * sf))
                for j in range(8):
                    a, e = end - int(round((j + 1) * 2 * sf)), end - int(round(j * 2 * sf))
                    if a >= 0:
                        cube[k, j, :, b] = np.log1p((cs[:, e] - cs[:, a]) / (e - a))
        out[mode] = cube
    df = pd.read_pickle(f"/evidence/neurobolt_data/fMRI_difumo/{stem}_difumo64_roi.pkl")
    cols = {str(c).lower().replace("'", "’"): c for c in df.columns}
    Y = df[[cols[r.lower()] for r in ROIS]].to_numpy().T.astype(float)
    b, a = butter(N=5, Wn=0.15 / (0.5 / 2.1), btype="low")
    Y = filtfilt(b, a, Y, axis=1)
    Y = Y - Y.mean(1, keepdims=True)
    Y = Y / (np.quantile(np.abs(Y), 0.95, axis=1, keepdims=True) + 1e-8)
    Path("/evidence/bridge009/mel").mkdir(parents=True, exist_ok=True)
    np.savez(f"/evidence/bridge009/mel/{stem}.npz", mel_zp=out["zp"], mel_causal=out["causal"], Ynb=Y.T.astype(np.float32),
             trig=trig, channels=np.array(common))
    volume.commit()
    return json.dumps({"stem": stem, "n_trig": int(n_tr), "n_vol": int(Y.shape[1]), "first_full": int(np.argmax(np.isfinite(out["zp"]).all((1, 2, 3)))),
                       "cols_found": len(ROIS)})


@app.local_entrypoint()
def main():
    common = ['Fp1', 'Fp2', 'F3', 'F4', 'C3', 'C4', 'P3', 'P4', 'O1', 'O2', 'F7', 'F8', 'T7', 'T8', 'P7', 'P8', 'Fpz', 'Fz',
              'Cz', 'Pz', 'POz', 'Oz', 'FT9', 'FT10', 'TP9', 'TP10']
    stems = sorted({e.path.split("/")[-1].replace("_eeg.set", "") for e in volume.listdir("/neurobolt_data/EEG") if e.path.endswith(".set")})
    for r in mel.starmap([(s, common) for s in stems], return_exceptions=True):
        print(r if isinstance(r, str) else repr(r)[:400])
