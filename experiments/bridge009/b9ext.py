import json
from pathlib import Path

import modal

HERE = Path(__file__).parent
app = modal.App("cable-b9ext")
volume = modal.Volume.from_name("cable-data")
S3 = "https://s3.amazonaws.com/openneuro.org/ds003768"
image = (modal.Image.debian_slim(python_version="3.12")
         .pip_install("numpy==2.2.6", "scipy==1.15.3", "mne==1.13.2", "nibabel==5.3.2", "nilearn==0.12.1",
                      "antspyx==0.6.1", "pandas==2.3.3", "eeglabio==0.0.3")
         .add_local_file(HERE / "b9lib.py", "/root/b9lib.py")
         .add_local_file(HERE / "b9feat2.py", "/root/b9feat2.py"))
OUT = "/evidence/bridge009/ds003768"
SCALP = ['Fp1', 'Fp2', 'F3', 'F4', 'C3', 'C4', 'P3', 'P4', 'O1', 'O2', 'F7', 'F8', 'T7', 'T8', 'P7', 'P8', 'Fz', 'Cz',
         'Pz', 'Oz', 'FC1', 'FC2', 'CP1', 'CP2', 'FC5', 'FC6', 'CP5', 'CP6', 'TP9', 'TP10']


def fetch(rel, dest):
    import urllib.request
    dest = Path(dest); dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        urllib.request.urlretrieve(f"{S3}/{rel}", dest)
    return dest


@app.function(image=image, cpu=4.0, memory=32768, timeout=3600, volumes={"/evidence": volume}, max_containers=40)
def eeg(sub: str, run: int) -> str:
    try:
        return json.dumps(_eeg(sub, run))
    except Exception as e:
        import traceback
        return json.dumps({"sub": sub, "run": run, "error": repr(e)[:300], "tb": traceback.format_exc()[-800:]})


def _obs_subtract(E, n_pc):
    import numpy as np
    m = E.mean(0)
    R = E - m
    _, _, vt = np.linalg.svd(R, full_matrices=False)
    B = np.vstack([m, vt[:n_pc]]).T
    coef = np.linalg.lstsq(B, E.T, rcond=None)[0]
    return E - (B @ coef).T


def _eeg(sub, run):
    import mne
    import numpy as np
    from scipy.signal import resample_poly, welch
    stem = f"{sub}/eeg/{sub}_task-rest_run-{run}_eeg"
    d = Path("/tmp/ds")
    for ext in (".vhdr", ".vmrk", ".eeg"):
        fetch(stem + ext, d / (Path(stem).name + ext))
    raw = mne.io.read_raw_brainvision(d / (Path(stem).name + ".vhdr"), preload=True, verbose="ERROR")
    sf = raw.info["sfreq"]
    on = np.array([o for o, s in zip(raw.annotations.onset, raw.annotations.description) if s.endswith("R128")])
    idx = np.round(on * sf).astype(int)
    tr_samp = int(round(2.1 * sf))
    dts = np.diff(idx)
    X = raw.get_data()
    n_vol = len(idx)
    U = 4
    L = tr_samp * U
    a0, a1 = idx[0], min(idx[-1] + tr_samp, X.shape[1])
    ref_c = int(np.argmax(np.abs(X[:30, a0:a1]).mean(1)))
    xu = resample_poly(X[ref_c, a0:a1], U, 1)
    ep_start = (idx - a0) * U
    ok = [k for k in range(n_vol) if ep_start[k] + L + 8 <= len(xu) and ep_start[k] - 8 >= 0]
    ref = xu[ep_start[ok[min(10, len(ok) - 1)]]:ep_start[ok[min(10, len(ok) - 1)]] + L]
    shifts = {}
    for k in ok:
        best, bs = -np.inf, 0
        for sh in range(-8, 9):
            seg = xu[ep_start[k] + sh:ep_start[k] + sh + L]
            v = float(np.dot(seg[::7], ref[::7]))
            if v > best:
                best, bs = v, sh
        shifts[k] = bs
    for c in range(X.shape[0]):
        xu = resample_poly(X[c, a0:a1], U, 1)
        E = np.stack([xu[ep_start[k] + shifts[k]:ep_start[k] + shifts[k] + L] for k in ok])
        cs = np.cumsum(np.vstack([np.zeros((1, L)), E]), 0)
        A = np.empty_like(E)
        for j in range(len(E)):
            lo, hi = max(0, j - 15), min(len(E), j + 16)
            A[j] = E[j] - (cs[hi] - cs[lo]) / (hi - lo)
        A = _obs_subtract(A[:, ::U].copy(), 4)
        Au = np.repeat(A, U, axis=1)
        out = xu.copy()
        corr = E - np.repeat(A, U, axis=1)[:, :L]
        for j, k in enumerate(ok):
            out[ep_start[k] + shifts[k]:ep_start[k] + shifts[k] + L] -= corr[j]
        X[c, a0:a1] = resample_poly(out, 1, U)[:a1 - a0]
    raw._data = X
    raw.notch_filter([35 / 2.1, 2 * 35 / 2.1, 3 * 35 / 2.1], notch_widths=1.0, verbose="ERROR")
    raw.filter(None, 70.0, verbose="ERROR")
    raw.resample(250.0, verbose="ERROR")
    sf2 = 250.0
    t0 = on[0]
    raw.set_channel_types({"ECG": "ecg", "EOG": "eog"})
    ev, _, hr = mne.preprocessing.find_ecg_events(raw, ch_name="ECG", verbose="ERROR")
    rp = ev[:, 0] - raw.first_samp
    rr = int(np.median(np.diff(rp)))
    pre, post = int(0.3 * rr), int(0.7 * rr)
    Y = raw.get_data(picks=SCALP)
    keep = [r for r in rp if r - pre >= 0 and r + post <= Y.shape[1]]
    for c in range(Y.shape[0]):
        E = np.stack([Y[c, r - pre:r + post] for r in keep])
        A = _obs_subtract(E, 3)
        for k, r in enumerate(keep):
            Y[c, r - pre:r + post] = A[k]
    s0 = int(round(t0 * sf2)); s1 = int(round((on[-1] + 2.1) * sf2))
    Y = Y[:, s0:s1]
    ecg = raw.get_data(picks=["ECG"])[0, s0:s1]
    trig = on - t0
    amp = np.percentile(np.abs(Y) * 1e6, [50, 95, 99, 99.9]).round(1).tolist()
    f, Pw = welch(Y, fs=sf2, nperseg=1024)
    band = lambda lo, hi: Pw[:, (f >= lo) & (f < hi)].mean(1)
    occ = [SCALP.index(c) for c in ("O1", "O2", "Oz")]
    alpha_ratio = float((band(8, 12)[occ] / (0.5 * (band(4, 7)[occ] + band(14, 20)[occ]))).mean())
    slice_f = 35 / 2.1
    grad_idx = float(np.mean([band(m * slice_f - 0.3, m * slice_f + 0.3) / band(m * slice_f - 2, m * slice_f - 1) for m in (1, 2)]))
    Path(f"{OUT}/eeg").mkdir(parents=True, exist_ok=True)
    np.savez_compressed(f"{OUT}/eeg/{sub}_run-{run}.npz", eeg=Y.astype(np.float32), ecg=ecg.astype(np.float32),
                        sfreq=sf2, channels=np.array(SCALP), trig=trig, rpeaks=(np.array(keep) - s0) / sf2)
    volume.commit()
    return {"sub": sub, "run": run, "n_trig": int(n_vol), "dt_unique": sorted(set(int(x) for x in dts))[:5],
            "shift_range": [int(min(shifts.values())), int(max(shifts.values()))], "hr_bpm": round(float(hr), 1),
            "n_beats": len(keep), "eeg_s": round(Y.shape[1] / sf2, 1), "abs_uV_pcts": amp,
            "occ_alpha_ratio": round(alpha_ratio, 2), "slice_freq_residual": round(grad_idx, 2)}


def _retry(fn, n=8):
    import time
    for k in range(n):
        try:
            return fn()
        except Exception:
            if k == n - 1:
                raise
            time.sleep(20 * (k + 1))


TF = "https://templateflow.s3.amazonaws.com/tpl-MNI152NLin2009cAsym/tpl-MNI152NLin2009cAsym_"


def _templateflow():
    import urllib.request
    files = {"t1": "res-01_T1w.nii.gz", "mask": "res-01_desc-brain_mask.nii.gz",
             "difumo": "res-02_atlas-DiFuMo_desc-64dimensions_probseg.nii.gz",
             "labels": "atlas-DiFuMo_desc-64dimensions_probseg.tsv"}
    out = {}
    for k, f in files.items():
        dest = Path("/evidence/atlas/templateflow") / f
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            _retry(lambda: urllib.request.urlretrieve(TF + f, dest))
        out[k] = str(dest)
    return out


@app.function(image=image, cpu=8.0, memory=32768, timeout=5400, volumes={"/evidence": volume}, max_containers=40)
def fmri(sub: str, run: int) -> str:
    try:
        return json.dumps(_fmri(sub, run))
    except Exception as e:
        import traceback
        return json.dumps({"sub": sub, "run": run, "error": repr(e)[:300], "tb": traceback.format_exc()[-800:]})


def _fmri(sub, run):
    import ants
    import nibabel as nib
    import numpy as np
    from nilearn import image as nimg
    from nilearn.maskers import NiftiMapsMasker
    d = Path("/tmp/ds")
    bold_p = fetch(f"{sub}/func/{sub}_task-rest_run-{run}_bold.nii.gz", d / f"{sub}_run-{run}_bold.nii.gz")
    meta = json.loads(fetch(f"{sub}/func/{sub}_task-rest_run-{run}_bold.json", d / f"{sub}_run-{run}_bold.json").read_text())
    t1_p = fetch(f"{sub}/anat/{sub}_T1w.nii.gz", d / f"{sub}_T1w.nii.gz")
    img = nib.load(bold_p)
    data = img.get_fdata(dtype=np.float32)
    tr = float(meta["RepetitionTime"]); st = np.array(meta["SliceTiming"])
    nt = data.shape[3]
    freqs = np.fft.rfftfreq(nt, d=tr)
    F = np.fft.rfft(data, axis=3)
    for z in range(data.shape[2]):
        shift = st[z] - tr / 2
        F[:, :, z, :] *= np.exp(2j * np.pi * freqs * shift)
    data = np.fft.irfft(F, n=nt, axis=3).astype(np.float32)
    stc = nib.Nifti1Image(data, img.affine, img.header)
    nib.save(stc, "/tmp/stc.nii.gz")
    a_img = ants.image_read("/tmp/stc.nii.gz")
    mean0 = ants.get_average_of_timeseries(a_img)
    mc = ants.motion_correction(a_img, fixed=mean0, type_of_transform="Rigid")
    mot = np.array(mc["FD"]) if "FD" in mc else None
    params = []
    for tx in mc["motion_parameters"]:
        p = ants.read_transform(tx[0]).parameters
        params.append(np.asarray(p[:6], float))
    params = np.array(params)
    mc_img = mc["motion_corrected"]
    mean_epi = ants.get_average_of_timeseries(mc_img)
    tf = _templateflow()
    tpl = ants.image_read(tf["t1"]); tpl_mask = ants.image_read(tf["mask"])
    t1 = ants.n4_bias_field_correction(ants.image_read(str(t1_p)))
    reg_t1 = ants.registration(fixed=tpl, moving=t1, type_of_transform="SyN")
    reg_epi = ants.registration(fixed=t1, moving=ants.n4_bias_field_correction(mean_epi), type_of_transform="Rigid",
                                aff_metric="mattes")
    inv = reg_t1["invtransforms"] + reg_epi["invtransforms"]
    whichinv = [True, False, True]
    maps4 = nib.load(tf["difumo"])
    native_maps = []
    for j in range(maps4.shape[3]):
        nib.save(nimg.index_img(maps4, j), "/tmp/map.nii.gz")
        m = ants.image_read("/tmp/map.nii.gz")
        native_maps.append(ants.apply_transforms(fixed=mean_epi, moving=m, transformlist=inv, whichtoinvert=whichinv,
                                                 interpolator="linear").numpy())
    bmask = ants.apply_transforms(fixed=mean_epi, moving=tpl_mask, transformlist=inv, whichtoinvert=whichinv,
                                  interpolator="nearestNeighbor").numpy() > 0.5
    ants.image_write(mc_img, "/tmp/mc.nii.gz")
    epi_nib = nib.load("/tmp/mc.nii.gz")
    aff = epi_nib.affine
    maps_img = nib.Nifti1Image(np.stack(native_maps, 3).astype(np.float32), aff)
    mask_img = nib.Nifti1Image(bmask.astype(np.uint8), aff)
    tt = np.linspace(-1, 1, nt)
    polys = np.stack([tt ** p for p in range(5)], 1)
    deriv = np.vstack([np.zeros((1, 6)), np.diff(params, axis=0)])
    conf = np.c_[params, deriv, polys]
    sm = nimg.smooth_img(epi_nib, 3.0)
    masker = NiftiMapsMasker(maps_img=maps_img, mask_img=mask_img, standardize=False, detrend=False)
    R = masker.fit_transform(sm, confounds=conf[:, :12])
    beta = np.linalg.lstsq(polys, R, rcond=None)[0]; R = R - polys @ beta
    V = sm.get_fdata(dtype=np.float32)[bmask]
    gs_raw = V.mean(0)
    B = np.linalg.lstsq(conf, V.T, rcond=None)[0]
    gs_clean = (V.T - conf @ B).mean(1)
    import pandas as pd
    names = [str(n) for n in pd.read_csv(tf["labels"], sep="	")["Difumo_names"]]
    Yall = np.c_[R, gs_raw - gs_raw.mean(), gs_clean]
    fd = np.r_[0, np.abs(np.diff(params[:, 3:], axis=0)).sum(1) + 50 * np.abs(np.diff(params[:, :3], axis=0)).sum(1)]
    Path(f"{OUT}/fmri").mkdir(parents=True, exist_ok=True)
    np.savez_compressed(f"{OUT}/fmri/{sub}_run-{run}.npz", roi=Yall.astype(np.float32),
                        roi_names=np.array(names + ["global signal", "global signal clean"]), motion=params, fd=fd, tr=tr)
    volume.commit()
    return {"sub": sub, "run": run, "n_vol": int(nt), "mean_fd_mm": round(float(fd.mean()), 3), "max_fd": round(float(fd.max()), 2),
            "mask_vox": int(bmask.sum()), "native_map_mass": round(float(np.stack(native_maps).sum() / 1e3), 1)}


@app.function(image=image, cpu=4.0, memory=16384, timeout=3600, volumes={"/evidence": volume}, max_containers=40)
def feat(sub: str, run: int) -> str:
    try:
        return json.dumps(_feat(sub, run))
    except Exception as e:
        import traceback
        return json.dumps({"sub": sub, "run": run, "error": repr(e)[:300], "tb": traceback.format_exc()[-800:]})


def _feat(sub, run):
    import mne
    import numpy as np
    from scipy.signal import stft
    import b9lib
    e = np.load(f"{OUT}/eeg/{sub}_run-{run}.npz"); f = np.load(f"{OUT}/fmri/{sub}_run-{run}.npz")
    x = e["eeg"].astype(np.float64); sf = float(e["sfreq"]); chans = [str(c) for c in e["channels"]]
    n_tr = min(len(f["roi"]), len(e["trig"]))
    nb = int(np.floor(n_tr * 2.1 / 0.8))
    hop = int(round(0.8 * sf)); win = int(round(2.0 * sf)); pad = (win - hop) // 2
    xf = mne.filter.filter_data(x, sf, 1.0, 45.0, verbose="ERROR")
    xp = np.pad(xf, ((0, 0), (pad, pad)), mode="reflect")
    fr, _, Z = stft(xp, fs=sf, window="hann", nperseg=win, noverlap=win - hop, boundary=None, padded=False)
    P = (np.abs(Z) ** 2)[:, :, :nb]
    fine = np.stack([P[:, (fr >= lo) & (fr < lo + 2), :].mean(1) for lo in range(1, 45, 2)], 1)
    b5 = np.stack([P[:, (fr >= lo) & (fr < hi), :].mean(1) for lo, hi in [(1, 4), (4, 8), (8, 13), (13, 30), (30, 45)]], 1)
    big = np.array([(np.abs(x[:, k * hop:(k + 1) * hop]) * 1e6 > 500).any() for k in range(nb)])
    fine = np.log(fine + 1e-30).transpose(2, 0, 1); b5 = np.log(b5 + 1e-30).transpose(2, 0, 1)
    fine[big] = np.nan; b5[big] = np.nan
    xa = x - x.mean(0, keepdims=True)
    iu = np.triu_indices(len(chans)); scale = np.where(iu[0] == iu[1], 1.0, np.sqrt(2.0))
    covs = {}
    for name, bands in (("cov4", [(1, 4), (4, 8), (8, 13), (13, 30)]),
                        ("cov7", [(1, 4), (4, 8), (8, 10), (10, 13), (13, 20), (20, 30), (30, 45)])):
        fs_ = []
        for lo, hi in bands:
            xb = np.pad(mne.filter.filter_data(xa, sf, lo, hi, verbose="ERROR"), ((0, 0), (pad, pad)), mode="reflect")
            C = np.stack([np.cov(xb[:, k * hop:k * hop + win]) + 1e-12 * np.eye(len(chans)) for k in range(nb)])
            C = C / np.trace(C, axis1=1, axis2=2)[:, None, None]
            w, V = np.linalg.eigh(C)
            L = np.einsum("kij,kj,klj->kil", V, np.log(np.clip(w, 1e-12, None)), V)
            T = L - L.mean(0)
            fs_.append((T[:, iu[0], iu[1]] * scale).astype(np.float32))
        covs[name] = np.stack(fs_, 2).reshape(nb, -1)
    centers = (np.arange(nb) + 0.5) * 0.8
    R = f["roi"][:n_tr].astype(float)
    Yb = np.stack([np.interp(centers, np.arange(n_tr) * 2.1, R[:, j], left=np.nan, right=np.nan) for j in range(R.shape[1])], 1)
    names = [str(n).lower().replace("'", "’") for n in f["roi_names"]]
    Y = b9lib.target_lp(Yb)
    import b9feat2
    f2 = b9feat2.features(x * 1e6, sf, nb)
    covs.update({k: v.astype(np.float32) for k, v in f2.items()})
    valid = np.isfinite(fine.reshape(nb, -1)).all(1) & np.isfinite(f2["cf2"]).all(1)
    Path(f"{OUT}/cache").mkdir(parents=True, exist_ok=True)
    np.savez(f"{OUT}/cache/{sub}-run{run}.npz", valid=valid, Y7=Y[:, [names.index(r) for r in b9lib.ROIS]].astype(np.float32),
             Yall=Y.astype(np.float32), roi_names=np.array(names), channels=np.array(chans),
             b5=b5.reshape(nb, -1).astype(np.float32), fine=fine.reshape(nb, -1).astype(np.float32), **covs)
    volume.commit()
    return {"sub": sub, "run": run, "n_bins": nb, "valid": round(float(valid.mean()), 3), "n_tr": int(n_tr)}


VU26 = ['Fp1', 'Fp2', 'F3', 'F4', 'C3', 'C4', 'P3', 'P4', 'O1', 'O2', 'F7', 'F8', 'T7', 'T8', 'P7', 'P8', 'Fpz', 'Fz', 'Cz',
        'Pz', 'POz', 'Oz', 'FT9', 'FT10', 'TP9', 'TP10']
MEL_BANDS = [(1, 4), (4, 8), (8, 13), (13, 30), (30, 45)]


def vu26(x, chans, sf):
    import mne
    import numpy as np
    names = chans + [c for c in VU26 if c not in chans]
    data = np.vstack([x, np.zeros((len(names) - len(chans), x.shape[1]))])
    info = mne.create_info(names, sf, "eeg")
    raw = mne.io.RawArray(data, info, verbose="ERROR")
    raw.set_montage(mne.channels.make_standard_montage("standard_1005"), verbose="ERROR")
    raw.info["bads"] = [c for c in VU26 if c not in chans]
    raw.interpolate_bads(reset_bads=True, verbose="ERROR")
    return raw.get_data(picks=VU26)


@app.function(image=image, cpu=8.0, memory=32768, timeout=5400, volumes={"/evidence": volume}, max_containers=40)
def feat3(sub: str, run: int) -> str:
    try:
        return json.dumps(_feat3(sub, run))
    except Exception as e:
        import traceback
        return json.dumps({"sub": sub, "run": run, "error": repr(e)[:300], "tb": traceback.format_exc()[-800:]})


def _feat3(sub, run):
    import mne
    import numpy as np
    import pandas as pd
    from scipy.signal import butter, filtfilt, sosfiltfilt
    import b9feat2
    import b9lib
    e = np.load(f"{OUT}/eeg/{sub}_run-{run}.npz"); f = np.load(f"{OUT}/fmri/{sub}_run-{run}.npz")
    x = e["eeg"].astype(np.float64) * 1e6; sf = float(e["sfreq"]); chans = [str(c) for c in e["channels"]]
    n_tr = min(len(f["roi"]), len(e["trig"]))
    nb = int(np.floor(n_tr * 2.1 / 0.8))
    names = [str(n) for n in f["roi_names"]]
    R = f["roi"][:n_tr].astype(float)
    centers = (np.arange(nb) + 0.5) * 0.8
    Yb = np.stack([np.interp(centers, np.arange(n_tr) * 2.1, R[:, j], left=np.nan, right=np.nan) for j in range(R.shape[1])], 1)
    low = [n.lower().replace("'", "’") for n in names]
    Y = b9lib.target_lp(Yb)
    idx7 = [low.index(r) for r in b9lib.ROIS]
    b, a = butter(N=5, Wn=0.15 / (0.5 / 2.1), btype="low")
    T = filtfilt(b, a, R[:, idx7].T, axis=1); T = T - T.mean(1, keepdims=True)
    T = (T / (np.quantile(np.abs(T), 0.95, axis=1, keepdims=True) + 1e-8)).T
    x26 = vu26(x, chans, sf)
    out = {}
    for tag, xx in (("", x), ("v26_", x26)):
        fam = b9feat2.frozen_families(xx, sf, nb)
        out.update({tag + k: v.astype(np.float32) for k, v in fam.items()})
    valid = np.isfinite(out["cf2"]).all(1)
    trig = e["trig"][:n_tr]
    mel = {}
    for tag, xx in (("", x), ("v26_", x26)):
        cube = np.full((n_tr, 8, xx.shape[0], 5), np.nan, np.float32)
        for bi, (lo, hi) in enumerate(MEL_BANDS):
            sq = sosfiltfilt(butter(4, [lo, hi], btype="band", fs=sf, output="sos"), xx, axis=1) ** 2
            cs = np.concatenate([np.zeros((sq.shape[0], 1)), np.cumsum(sq, 1)], 1)
            for k, t in enumerate(trig):
                end = int(round(t * sf))
                for j in range(8):
                    a0, e0 = end - int(round((j + 1) * 2 * sf)), end - int(round(j * 2 * sf))
                    if a0 >= 0:
                        cube[k, j, :, bi] = np.log1p((cs[:, e0] - cs[:, a0]) / (e0 - a0))
        mel[tag + "mel_zp"] = cube
    Path(f"{OUT}/cache3").mkdir(parents=True, exist_ok=True)
    np.savez(f"{OUT}/cache3/{sub}-run{run}.npz", valid=valid, Y7=Y[:, idx7].astype(np.float32), Yall=Y.astype(np.float32),
             Ynb=T.astype(np.float32), roi_names=np.array(names), channels=np.array(chans), **out, **mel)
    stem = f"sub{int(sub.split('-')[1]):02d}-scan{run:02d}"
    root = Path(f"{OUT}/nbfmt"); (root / "EEG").mkdir(parents=True, exist_ok=True); (root / "fMRI_difumo").mkdir(exist_ok=True)
    info = mne.create_info(VU26, sf, "eeg")
    rawx = mne.io.RawArray(x26 * 1e-6, info, verbose="ERROR")
    rawx.set_annotations(mne.Annotations(onset=trig, duration=np.zeros(len(trig)), description=["R149"] * len(trig)))
    mne.export.export_raw(str(root / "EEG" / f"{stem}_eeg.set"), rawx, fmt="eeglab", overwrite=True, verbose="ERROR")
    nb_cols = [n if n != "global signal clean" else "global signal clean" for n in names]
    pd.DataFrame(R, columns=nb_cols).to_pickle(root / "fMRI_difumo" / f"{stem}_difumo64_roi.pkl")
    volume.commit()
    return {"sub": sub, "run": run, "stem": stem, "n_tr": int(n_tr), "nb": nb, "valid": round(float(valid.mean()), 3),
            "dims": {k: int(v.shape[1]) for k, v in out.items() if not k.startswith("v26_")}}


@app.local_entrypoint()
def main(stage: str = "eeg", subs: str = ""):
    S = subs.split(",") if subs else [f"sub-{i:02d}" for i in range(1, 34)]
    fn = {"eeg": eeg, "fmri": fmri, "feat": feat, "feat3": feat3}[stage]
    jobs = [(s, r) for s in S for r in (1, 2)]
    log = HERE / "results" / f"ext_{stage}.jsonl"
    with log.open("a", encoding="utf-8") as fh:
        for r in fn.starmap(jobs, return_exceptions=True):
            line = r if isinstance(r, str) else json.dumps({"error": repr(r)[:300]})
            fh.write(line + "\n"); print(line[:400])
