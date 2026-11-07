import json
import urllib.request
from pathlib import Path

import modal

HERE = Path(__file__).parent
app = modal.App("cable-b8cov")
volume = modal.Volume.from_name("cable-data")
image = modal.Image.debian_slim(python_version="3.12").pip_install("numpy==2.2.6", "scipy==1.18.1", "mne==1.13.2",
                                                                   "pymatreader==1.1.0")
HF = "https://huggingface.co/datasets/NeurdyLab/NeuroBOLT/resolve/main"
BANDS = {"delta": (1, 4), "theta": (4, 8), "alpha": (8, 13), "beta": (13, 30)}


@app.function(image=image, cpu=4.0, memory=16384, timeout=3600, retries=1, volumes={"/evidence": volume}, max_containers=30)
def nb_cov(scan: str) -> dict:
    import urllib.request
    import mne
    import numpy as np
    d = Path("/tmp/nb"); d.mkdir(exist_ok=True)
    for suf in ("_eeg.set", "_eeg.fdt"):
        (d / f"{scan}{suf}").write_bytes(urllib.request.urlopen(f"{HF}/EEG_set/{scan}{suf}", timeout=600).read())
    raw = mne.io.read_raw_eeglab(d / f"{scan}_eeg.set", preload=True, verbose="ERROR")
    sf = float(raw.info["sfreq"])
    chans = [c for c in raw.ch_names if not c.upper().startswith(("EOG", "EMG", "ECG"))]
    x = raw.get_data(picks=chans)
    x = x - x.mean(0, keepdims=True)
    hop = int(round(0.8 * sf)); win = int(round(2.0 * sf)); pad = (win - hop) // 2
    n_tr = int(round(x.shape[1] / sf / 2.1)); nb = int(np.floor(n_tr * 2.1 / 0.8))
    iu = np.triu_indices(len(chans))
    feats = []
    for lo, hi in BANDS.values():
        xb = mne.filter.filter_data(x, sf, lo, hi, verbose="ERROR")
        xb = np.pad(xb, ((0, 0), (pad, pad)), mode="reflect")
        covs = np.stack([np.cov(xb[:, k * hop: k * hop + win]) + 1e-12 * np.eye(len(chans)) for k in range(nb)])
        covs = covs / np.trace(covs, axis1=1, axis2=2)[:, None, None]
        w, V = np.linalg.eigh(covs)
        logc = np.einsum("kij,kj,klj->kil", V, np.log(np.clip(w, 1e-12, None)), V)
        ref = logc.mean(0)
        T = logc - ref
        scale = np.where(iu[0] == iu[1], 1.0, np.sqrt(2.0))
        feats.append((T[:, iu[0], iu[1]] * scale).astype(np.float32))
    F = np.stack(feats, 2)
    out = Path("/evidence/bridge008/nb_cov"); out.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out / f"{scan}.npz", cov_tangent=F, channels=np.array(chans))
    volume.commit()
    return {"scan": scan, "shape": list(F.shape)}


@app.local_entrypoint()
def main():
    tree = json.loads(urllib.request.urlopen("https://huggingface.co/api/datasets/NeurdyLab/NeuroBOLT/tree/main/fMRI_difumo64").read())
    paths = [e["path"] for e in (tree if isinstance(tree, list) else tree.get("tree", tree.get("siblings", []))) if isinstance(e, dict) and "path" in e]
    scans = sorted({p.split("/")[1].replace("_difumo64_roi.pkl", "") for p in paths if p.startswith("fMRI_difumo64/")})
    for r in nb_cov.map(scans, return_exceptions=True):
        print(r if isinstance(r, dict) else repr(r)[:200])
