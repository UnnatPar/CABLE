import json
from pathlib import Path

import modal

app = modal.App("cable-b9phys")
volume = modal.Volume.from_name("cable-data")
image = modal.Image.debian_slim(python_version="3.12").pip_install("numpy==2.2.6", "scipy==1.18.1", "mne==1.13.2",
                                                                   "pymatreader==1.1.0")
COMMON = ['Fp1', 'Fp2', 'F3', 'F4', 'C3', 'C4', 'P3', 'P4', 'O1', 'O2', 'F7', 'F8', 'T7', 'T8', 'P7', 'P8', 'Fpz', 'Fz',
          'Cz', 'Pz', 'POz', 'Oz', 'FT9', 'FT10', 'TP9', 'TP10']


def causal_bandpower(x, sf, nb, lo, hi, win_s):
    import numpy as np
    from scipy.signal import butter, sosfilt
    sos = butter(2, [lo, hi], btype="band", fs=sf, output="sos") if lo > 0 else butter(2, hi, btype="low", fs=sf, output="sos")
    y = sosfilt(sos, x, axis=-1) ** 2
    cs = np.concatenate([np.zeros(y.shape[:-1] + (1,)), np.cumsum(y, -1)], -1)
    ends = np.minimum(np.round((np.arange(nb) + 1) * 0.8 * sf).astype(int), y.shape[-1])
    starts = np.maximum(ends - int(round(win_s * sf)), 0)
    return np.log((cs[..., ends] - cs[..., starts]) / np.maximum(ends - starts, 1) + 1e-30)


@app.function(image=image, cpu=2.0, memory=8192, timeout=1800, volumes={"/evidence": volume}, max_containers=30)
def phys(stem: str) -> str:
    import mne
    import numpy as np
    from scipy.signal import butter, find_peaks, sosfilt, sosfiltfilt
    raw = mne.io.read_raw_eeglab(f"/evidence/neurobolt_data/EEG/{stem}_eeg.set", preload=True, verbose="ERROR")
    sf = float(raw.info["sfreq"])
    names = [c.replace("'", "").replace("FPz", "Fpz") for c in raw.ch_names]
    x = raw.get_data() * 1e6
    n_tr = len([d for d in raw.annotations.description if d.strip() == "R149"])
    nb = int(np.floor(n_tr * 2.1 / 0.8))
    scalp = x[[names.index(c) for c in COMMON]]
    slow = np.concatenate([causal_bandpower(scalp, sf, nb, lo, hi, 12.0) for lo, hi in ((0.03, 0.1), (0.1, 0.5), (0.5, 1.0))], 0).T
    aux = x[[names.index(c) for c in ("EOG1", "EOG2", "EMG1", "EMG2", "EMG3")]]
    eogemg = np.concatenate([causal_bandpower(aux, sf, nb, lo, hi, 4.0) for lo, hi in ((0.1, 1), (1, 4), (4, 15), (15, 45))], 0).T
    e = x[names.index("ECG")]
    eb = sosfiltfilt(butter(3, [5, 20], btype="band", fs=sf, output="sos"), e)
    raw.set_channel_types({raw.ch_names[names.index("ECG")]: "ecg"})
    ev, _, _ = mne.preprocessing.find_ecg_events(raw, ch_name=raw.ch_names[names.index("ECG")], verbose="ERROR")
    pk = np.sort(ev[:, 0] - raw.first_samp)
    keep = [pk[0]]
    for p_ in pk[1:]:
        if p_ - keep[-1] >= 0.5 * sf:
            keep.append(p_)
    pk = np.array(keep)
    t_pk = pk / sf; amp = eb[pk]; rr = np.diff(t_pk)
    ok = (rr > 0.33) & (rr < 2.0)
    ecg = np.full((nb, 4), np.nan)
    for k in range(nb):
        end = (k + 1) * 0.8
        j = np.searchsorted(t_pk, end) - 1
        if j < 2:
            continue
        sel = np.where((t_pk[1:j + 1] > end - 12) & ok[:j])[0]
        hr = 60.0 / rr[j - 1] if ok[j - 1] else np.nan
        rmssd = np.sqrt(np.mean(np.diff(rr[sel]) ** 2)) if len(sel) > 2 else np.nan
        a = amp[1:j + 1][(t_pk[1:j + 1] > end - 12)]
        ecg[k] = [hr, rmssd, amp[j], a.std() if len(a) > 2 else np.nan]
    Path("/evidence/bridge009/phys").mkdir(parents=True, exist_ok=True)
    np.savez(f"/evidence/bridge009/phys/{stem}.npz", slow=slow.astype(np.float32), eogemg=eogemg.astype(np.float32),
             ecg=ecg.astype(np.float32))
    volume.commit()
    return json.dumps({"stem": stem, "nb": nb, "n_beats": int(len(pk)), "hr_med": round(float(np.nanmedian(ecg[:, 0])), 1),
                       "ecg_nan": round(float(np.isnan(ecg).mean()), 3)})


@app.local_entrypoint()
def main():
    stems = sorted({e.path.split("/")[-1].replace("_eeg.set", "") for e in volume.listdir("/neurobolt_data/EEG") if e.path.endswith(".set")})
    for r in phys.map(stems, return_exceptions=True):
        print(r if isinstance(r, str) else repr(r)[:300])
