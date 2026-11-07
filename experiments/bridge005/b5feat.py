import json
import urllib.request
from pathlib import Path

import modal

HERE = Path(__file__).parent
app = modal.App("cable-b5feat")
volume = modal.Volume.from_name("cable-data")
image = (modal.Image.debian_slim(python_version="3.12")
         .pip_install("numpy==2.2.6", "scipy==1.18.1", "mne==1.13.2", "pymatreader==1.1.0", "pandas==2.3.3",
                      "nilearn==0.12.1")
         .add_local_file(HERE.parent / "bridge004" / "Schaefer2018_100Parcels_7Networks_order_FSLMNI152_2mm.Centroid_RAS.csv",
                         "/root/schaefer100.csv"))
TR_BIN = 0.8
BANDS = {"delta": (1, 4), "theta": (4, 8), "alpha": (8, 13), "beta": (13, 30), "gamma": (30, 45)}
NETS = ["Vis", "SomMot", "DorsAttn", "SalVentAttn", "Limbic", "Cont", "Default"]
HF = "https://huggingface.co/datasets/NeurdyLab/NeuroBOLT/resolve/main"


def bandpower_bins(x, sf, times, nb, seg_bounds):
    import mne
    import numpy as np
    from scipy.signal import hilbert
    sums = np.zeros((nb, x.shape[0], len(BANDS))); counts = np.zeros(nb); art = np.zeros(nb, bool)
    for lo, hi in seg_bounds:
        if hi - lo < 10 * sf:
            continue
        xs = x[:, lo:hi]; bins = np.floor(times[lo:hi] / TR_BIN).astype(int); ok = (bins >= 0) & (bins < nb)
        np.add.at(counts, bins[ok], 1)
        art[np.unique(bins[ok & (np.abs(xs) * 1e6 > 500).any(0)])] = True
        for bi, (f0, f1) in enumerate(BANDS.values()):
            p = np.abs(hilbert(mne.filter.filter_data(xs, sf, f0, f1, verbose="ERROR"), axis=1)) ** 2
            np.add.at(sums[:, :, bi], bins[ok], p[:, ok].T)
    enough = counts >= 0.5 * TR_BIN * sf
    with np.errstate(invalid="ignore", divide="ignore"):
        lp = np.where(enough[:, None, None], np.log(sums / np.maximum(counts, 1)[:, None, None] + 1e-30), np.nan)
    lp[art] = np.nan
    return lp.astype(np.float32), float(art.mean())


@app.function(image=image, cpu=2.0, memory=8192, timeout=1800, retries=1, volumes={"/evidence": volume}, max_containers=30)
def nb_scan(scan: str) -> dict:
    import urllib.request
    import mne
    import numpy as np
    import pandas as pd
    from nilearn.datasets import fetch_atlas_difumo
    d = Path("/tmp/nb"); d.mkdir(exist_ok=True)
    for suf in ("_eeg.set", "_eeg.fdt"):
        (d / f"{scan}{suf}").write_bytes(urllib.request.urlopen(f"{HF}/EEG_set/{scan}{suf}", timeout=600).read())
    pk = d / f"{scan}_difumo64_roi.pkl"
    pk.write_bytes(urllib.request.urlopen(f"{HF}/fMRI_difumo64/{scan}_difumo64_roi.pkl", timeout=300).read())
    df = pd.read_pickle(pk)
    raw = mne.io.read_raw_eeglab(d / f"{scan}_eeg.set", preload=True, verbose="ERROR")
    sf = raw.info["sfreq"]
    chans = [c for c in raw.ch_names if not c.upper().startswith(("EOG", "EMG", "ECG"))]
    x = raw.get_data(picks=chans)
    amp_pct = [float(v) for v in np.percentile(np.abs(x) * 1e6, [50, 95, 99, 99.9])]
    chans = [c.replace("'", "").replace("FPz", "Fpz") for c in chans]
    n_tr = df.shape[0] if df.shape[0] > df.shape[1] else df.shape[1]
    Y = df.values if df.shape[0] == n_tr else df.values.T
    cols = [str(c) for c in (df.columns if df.shape[0] == n_tr else df.index)]
    lab = fetch_atlas_difumo(dimension=64, resolution_mm=2).labels
    yeo = [str(v) for v in lab["yeo_networks7"]]
    names = [str(v) for v in lab["difumo_names"]]
    key = {"Vis": "Vis", "SomMot": "Som", "DorsAttn": "DorsAttn", "SalVentAttn": "VentAttn|SalVent|Sal",
           "Limbic": "Limbic", "Cont": "Cont|Frontoparietal", "Default": "Default"}
    import re
    roi_cols = [i for i, c in enumerate(cols) if c in names]
    netmask = np.array([[bool(re.search(key[n], yeo[names.index(cols[i])])) for i in roi_cols] for n in NETS])
    R = Y[:, roi_cols].astype(float)
    N = np.stack([R[:, m].mean(1) if m.any() else np.full(len(R), np.nan) for m in netmask] + [R.mean(1)], 1)
    tr = 2.1
    nb = int(np.floor(n_tr * tr / TR_BIN))
    times = np.arange(x.shape[1]) / sf
    lp, artf = bandpower_bins(x, sf, times, nb, [(0, x.shape[1])])
    centers = (np.arange(nb) + 0.5) * TR_BIN
    F = np.stack([np.interp(centers, np.arange(n_tr) * tr, N[:, j], left=np.nan, right=np.nan) for j in range(8)], 1)
    out = Path("/evidence/bridge005/nb"); out.mkdir(parents=True, exist_ok=True)
    Yall = Y.astype(float)
    ROI = np.stack([np.interp(centers, np.arange(n_tr) * tr, Yall[:, j], left=np.nan, right=np.nan)
                    for j in range(Yall.shape[1])], 1)
    np.savez_compressed(out / f"{scan}.npz", eeg_logpow=lp, fmri8=F.astype(np.float32), channels=np.array(chans),
                        roi_all=ROI.astype(np.float32), roi_names=np.array(cols))
    volume.commit()
    return {"scan": scan, "sfreq": sf, "n_ch": len(chans), "channels": chans, "n_tr": int(n_tr),
            "eeg_seconds": x.shape[1] / sf, "fmri_seconds": n_tr * tr, "roi_cols_matched": len(roi_cols),
            "nonroi_cols": [c for c in cols if c not in names], "net_counts": netmask.sum(1).tolist(),
            "yeo_values": sorted(set(yeo)), "artifact_frac": artf, "abs_uV_p50_p95_p99_p999": amp_pct}


@app.local_entrypoint()
def nb_only():
    tree = json.loads(urllib.request.urlopen("https://huggingface.co/api/datasets/NeurdyLab/NeuroBOLT/tree/main/fMRI_difumo64").read())
    paths = [e["path"] for e in (tree if isinstance(tree, list) else tree.get("tree", tree.get("siblings", [])))
             if isinstance(e, dict) and "path" in e]
    scans = sorted({p.split("/")[1].replace("_difumo64_roi.pkl", "") for p in paths if p.startswith("fMRI_difumo64/")})
    nb = list(nb_scan.map(scans, return_exceptions=True))
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / "featurize_nb.json").write_text(json.dumps([r if isinstance(r, dict) else repr(r)[:300] for r in nb], indent=1))
    for r in nb:
        if isinstance(r, dict):
            print(r["scan"], r["n_ch"], "art", round(r["artifact_frac"], 3), "uV", [round(v) for v in r["abs_uV_p50_p95_p99_p999"]])
        else:
            print(repr(r)[:200])
