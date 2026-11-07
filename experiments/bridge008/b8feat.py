import json
import urllib.request
from pathlib import Path

import modal

HERE = Path(__file__).parent
app = modal.App("cable-b8feat")
volume = modal.Volume.from_name("cable-data")
image = modal.Image.debian_slim(python_version="3.12").pip_install("numpy==2.2.6", "scipy==1.18.1", "mne==1.13.2",
                                                                   "pymatreader==1.1.0")
HF = "https://huggingface.co/datasets/NeurdyLab/NeuroBOLT/resolve/main"
EDGES = list(range(1, 47, 2))


@app.function(image=image, cpu=2.0, memory=8192, timeout=1800, retries=1, volumes={"/evidence": volume}, max_containers=30)
def nb_fine(scan: str) -> dict:
    import urllib.request
    import mne
    import numpy as np
    from scipy.signal import stft
    d = Path("/tmp/nb"); d.mkdir(exist_ok=True)
    for suf in ("_eeg.set", "_eeg.fdt"):
        (d / f"{scan}{suf}").write_bytes(urllib.request.urlopen(f"{HF}/EEG_set/{scan}{suf}", timeout=600).read())
    raw = mne.io.read_raw_eeglab(d / f"{scan}_eeg.set", preload=True, verbose="ERROR")
    sf = float(raw.info["sfreq"])
    chans = [c for c in raw.ch_names if not c.upper().startswith(("EOG", "EMG", "ECG"))]
    x = raw.get_data(picks=chans)
    x = mne.filter.filter_data(x, sf, 1.0, 45.0, verbose="ERROR")
    hop = int(round(0.8 * sf)); win = int(round(2.0 * sf))
    pad = (win - hop) // 2
    xp = np.pad(x, ((0, 0), (pad, pad)), mode="reflect")
    f, t, Z = stft(xp, fs=sf, window="hann", nperseg=win, noverlap=win - hop, boundary=None, padded=False)
    P = np.abs(Z) ** 2
    n_tr = int(round(x.shape[1] / sf / 2.1))
    nb = int(np.floor(n_tr * 2.1 / 0.8))
    P = P[:, :, :nb]
    bands = np.stack([P[:, (f >= lo) & (f < lo + 2), :].mean(1) for lo in EDGES[:-1]], 1)
    lp = np.log(bands + 1e-30).transpose(2, 0, 1).astype(np.float32)
    big = np.zeros(nb, bool)
    for k in range(nb):
        seg = x[:, k * hop:(k + 1) * hop]
        big[k] = seg.size == 0 or (np.abs(seg) * 1e6 > 500).any()
    lp[big] = np.nan
    chans = [c.replace("'", "").replace("FPz", "Fpz") for c in chans]
    out = Path("/evidence/bridge008/nb_fine"); out.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out / f"{scan}.npz", eeg_fine=lp, channels=np.array(chans), freqs=np.array(EDGES[:-1]))
    volume.commit()
    return {"scan": scan, "shape": list(lp.shape), "artifact_frac": float(big.mean())}


@app.local_entrypoint()
def main():
    tree = json.loads(urllib.request.urlopen("https://huggingface.co/api/datasets/NeurdyLab/NeuroBOLT/tree/main/fMRI_difumo64").read())
    paths = [e["path"] for e in (tree if isinstance(tree, list) else tree.get("tree", tree.get("siblings", []))) if isinstance(e, dict) and "path" in e]
    scans = sorted({p.split("/")[1].replace("_difumo64_roi.pkl", "") for p in paths if p.startswith("fMRI_difumo64/")})
    res = list(nb_fine.map(scans, return_exceptions=True))
    for r in res:
        print(r if isinstance(r, dict) else repr(r)[:200])
