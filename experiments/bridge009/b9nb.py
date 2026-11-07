import json
from pathlib import Path

import modal

HERE = Path(__file__).parent
app = modal.App("cable-b9nb")
volume = modal.Volume.from_name("cable-data")
COMMIT = "b51b966516a9b0c0a87e6ee6a7b997101a443394"
image = (modal.Image.debian_slim(python_version="3.10")
         .apt_install("git")
         .pip_install("torch==2.0.1", "numpy==1.24.3", "timm==0.4.12", "pandas==2.0.3", "matplotlib", "einops",
                      "scipy==1.10.1", "mne==1.4.2", "nilearn==0.10.2", "scikit-learn==1.3.2", "h5py",
                      "huggingface_hub", "openpyxl", "tensorboardX")
         .pip_install("linear-attention-transformer==0.19.1", "axial-positional-embedding==0.2.1",
                      "local-attention==1.8.6", "product-key-memory==0.1.10", "linformer==0.2.1",
                      extra_options="--no-deps")
         .run_commands(f"git clone https://github.com/soupeeli/NeuroBOLT.git /nb && cd /nb && git checkout {COMMIT}",
                       "mkdir -p /nb/checkpoints && python -c \"import urllib.request; urllib.request.urlretrieve("
                       "'https://raw.githubusercontent.com/935963004/LaBraM/main/checkpoints/labram-base.pth', "
                       "'/nb/checkpoints/labram-base.pth')\""))
ROIS = {"cuneus": "Cuneus", "heschl": "Heschl’s gyrus", "mfg_anterior": "Middle frontal gyrus anterior",
        "precuneus_anterior": "Precuneus anterior", "putamen": "Putamen", "thalamus": "Thalamus",
        "global_clean": "global signal clean"}
HF = "https://huggingface.co/datasets/NeurdyLab/NeuroBOLT/resolve/main"

WRAPPER = r'''
import sys, json, numpy as np
sys.path.insert(0, "/nb")
import utils, dataset_maker.preproc as preproc
LOG = {"lengths": [], "full": []}
_ep = preproc.epoching_seq2one
def ep(*a, **k):
    d, info = _ep(*a, **k); LOG["lengths"].append(len(d["fmri"])); return d, info
preproc.epoching_seq2one = ep
_gm = utils.get_metrics
def flat(x):
    if isinstance(x, list):
        return np.concatenate([np.asarray(v).reshape(-1) for v in x])
    return np.asarray(x).reshape(-1)
CUR = []
def gm(pred, true, metrics, is_binary=True, *a, **k):
    CUR.append((flat(pred).copy(), flat(true).copy()))
    return _gm(pred, true, metrics, is_binary, *a, **k)
utils.get_metrics = gm
import engine
_ev = engine.evaluate
def ev(*a, **k):
    # record only the FINAL get_metrics call of each evaluate() (the whole-set call), whatever its container type
    # (NeuroBOLT passes a list when batches >= 200 windows and a concatenated array otherwise, e.g. 1-scan LOSO tests)
    CUR.clear()
    out = _ev(*a, **k)
    if CUR:
        LOG["full"].append(CUR[-1])
    return out
engine.evaluate = ev
sys.argv = ["main.py"] + sys.argv[1:]
import main as M
opts, ds = M.get_args()
M.main(opts, ds)
arrs = {"lengths": np.array(LOG["lengths"]), "n_full": np.array(len(LOG["full"]))}
for i, (p, t) in enumerate(LOG["full"]):
    arrs[f"p{i}"] = p; arrs[f"t{i}"] = t
np.savez("/tmp/nb_out.npz", **arrs)
'''


@app.function(image=image, timeout=3600, volumes={"/evidence": volume})
def prepare():
    import urllib.request
    tree = json.loads(urllib.request.urlopen("https://huggingface.co/api/datasets/NeurdyLab/NeuroBOLT/tree/main/EEG_set").read())
    tree += json.loads(urllib.request.urlopen("https://huggingface.co/api/datasets/NeurdyLab/NeuroBOLT/tree/main/fMRI_difumo64").read())
    base = Path("/evidence/neurobolt_data"); (base / "EEG").mkdir(parents=True, exist_ok=True); (base / "fMRI_difumo").mkdir(exist_ok=True)
    n = 0
    for e in tree:
        p = e["path"]; sub = "EEG" if p.startswith("EEG_set") else "fMRI_difumo"
        dest = base / sub / Path(p).name
        if not dest.exists():
            urllib.request.urlretrieve(f"{HF}/{p}", dest); n += 1
    volume.commit()
    return {"downloaded": n, "files": len(tree)}


@app.function(image=image, gpu=["A100-80GB", "A100-40GB", "A10G"], cpu=8.0, memory=49152, timeout=14400, volumes={"/evidence": volume}, max_containers=150)
def run_one(roi_key: str, k: str, split: dict, epochs: int = 20) -> dict:
    import shutil
    import subprocess
    import numpy as np
    import pandas as pd
    scans = sorted(p.name.replace("_difumo64_roi.pkl", "") for p in Path("/evidence/neurobolt_data/fMRI_difumo").glob("*.pkl"))
    df = pd.DataFrame({"scan_name": scans,
                       "train": [int(s not in split["val"] and s not in split["test"]) for s in scans],
                       "val": [int(s in split["val"]) for s in scans], "test": [int(s in split["test"]) for s in scans]})
    with pd.ExcelWriter("/tmp/split.xlsx") as w:
        df.to_excel(w, sheet_name="fold1", index=False)
    data = Path("/tmp/data"); shutil.copytree("/evidence/neurobolt_data", data, dirs_exist_ok=True)
    Path("/nb/run_wrapped.py").write_text(WRAPPER)
    Path("/tmp/ckpt").mkdir(parents=True, exist_ok=True); Path("/tmp/log").mkdir(parents=True, exist_ok=True)
    cmd = ["python", "/nb/run_wrapped.py", "--batch_size", "64", "--finetune", "/nb/checkpoints/labram-base.pth",
           "--labels_roi", ROIS[roi_key], "--dataset", "VU", "--train_test_mode", "full_test",
           "--split_index_sheet", "/tmp/split.xlsx", "--dataset_root", "/tmp/data/", "--epochs", str(epochs),
           "--output_dir", "/tmp/ckpt/", "--log_dir", "/tmp/log/", "--no_save_ckpt"] + (["--warmup_epochs", "0"] if epochs < 6 else [])
    p = subprocess.run(cmd, cwd="/nb", capture_output=True, text=True)
    if p.returncode != 0 or not Path("/tmp/nb_out.npz").exists():
        return {"roi": roi_key, "k": k, "status": "error", "stderr": p.stderr[-3000:], "stdout": p.stdout[-2000:]}
    import re
    z = np.load("/tmp/nb_out.npz")
    lengths = z["lengths"].tolist()
    full = [(z[f"p{i}"], z[f"t{i}"]) for i in range(int(z["n_full"]))]
    pairs = [(full[i], full[i + 1]) for i in range(0, len(full) - 1, 2)]
    own = re.findall(r"Min mse val: ([\d.]+), max corr test: ([-\d.]+)", p.stdout)
    vmse = [float(np.mean((v[0] - v[1]) ** 2)) for v, _ in pairs]
    best = int(np.argmin(vmse)); tp, tt = pairs[best][1][0], pairs[best][1][1]
    test_rows = [i for i, s in enumerate(scans) if s in split["test"]]
    tl = [lengths[i] for i in test_rows]
    def scan_rs(p_, t_):
        out_, o_ = [], 0
        for n in tl:
            out_.append(float(np.corrcoef(p_[o_:o_ + n], t_[o_:o_ + n])[0, 1])); o_ += n
        return out_
    per_scan = scan_rs(tp, tt)
    per_epoch = [float(np.mean(scan_rs(te_[0], te_[1]))) for _, te_ in pairs]
    o_ = 0; preds = {}
    for i_, n in zip(test_rows, tl):
        preds[scans[i_]] = {"p": tp[o_:o_ + n].astype(float).tolist(), "t": tt[o_:o_ + n].astype(float).tolist()}; o_ += n
    Path("/evidence/bridge009/nb_confirm").mkdir(parents=True, exist_ok=True)
    Path(f"/evidence/bridge009/nb_confirm/{k}__{roi_key}.json").write_text(json.dumps(preds)); volume.commit()
    return {"roi": roi_key, "k": k, "status": "ok", "best_epoch": best, "n_epochs_logged": len(pairs),
            "pooled_r": float(np.corrcoef(tp, tt)[0, 1]), "per_scan_r": per_scan, "mean_per_scan_r": float(np.mean(per_scan)),
            "per_epoch_test_mean_per_scan_r": per_epoch, "oracle_test_mean_per_scan_r": max(per_epoch),
            "test_scans": [scans[i] for i in test_rows], "length_check": int(sum(tl)) == len(tp),
            "neurobolt_printed_val_selected_test_corr": float(own[-1][1]) if own else None,
            "stdout_tail": p.stdout[-600:]}


@app.local_entrypoint()
def main(sets: str = "C1a,C1b", only: str = "", epochs: int = 20, fresh: bool = False, rois: str = ""):
    sp = json.loads((HERE / "results" / "confirm_splits.json").read_text())
    cutoff = 1792208640 if fresh else 0
    done = {e.path.split("/")[-1].replace(".json", "") for e in volume.listdir("/bridge009/nb_confirm") if e.mtime >= cutoff} if not only else set()
    done -= set() if fresh else {f"c1b_00__{r}" for r in ROIS}
    jobs = [(r, s["name"], s, epochs) for st in sets.split(",") for s in sp[st] for r in ROIS
            if (not only or s["name"] in only.split(",")) and (not rois or r in rois.split(",")) and f"{s['name']}__{r}" not in done]
    print(len(jobs), "jobs to run;", len(done), "already complete")
    out = HERE / "results" / "nb_confirm.jsonl"
    with out.open("a", encoding="utf-8") as fh:
        for res in run_one.starmap(jobs, return_exceptions=True, order_outputs=False):
            res = res if isinstance(res, dict) else {"status": "exception", "error": repr(res)[:500]}
            res.pop("stdout_tail", None)
            fh.write(json.dumps(res) + "\n"); fh.flush()
            print({k: v for k, v in res.items() if k in ("roi", "k", "status", "mean_per_scan_r", "length_check")})
