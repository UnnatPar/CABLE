import json
from pathlib import Path

import modal

HERE = Path(__file__).parent
app = modal.App("cable-b9fm")
volume = modal.Volume.from_name("cable-data")
image = (modal.Image.debian_slim(python_version="3.11").apt_install("git")
         .pip_install("torch==2.4.1", "numpy==1.26.4", "scipy==1.13.1", "mne==1.8.0", "pymatreader==1.0.0",
                      "timm==0.4.12", "einops==0.8.0")
         .run_commands("git clone https://github.com/935963004/LaBraM.git /labram",
                       "python -c \"import urllib.request; urllib.request.urlretrieve("
                       "'https://raw.githubusercontent.com/935963004/LaBraM/main/checkpoints/labram-base.pth', "
                       "'/labram/labram-base.pth')\"")
         .add_local_file(HERE / "b9feat2.py", "/root/b9feat2.py"))


def load_model():
    import sys
    import torch
    sys.path.insert(0, "/labram")
    import modeling_finetune
    from timm.models import create_model
    m = create_model("labram_base_patch200_200", pretrained=False, num_classes=0, drop_rate=0.0, drop_path_rate=0.0,
                     attn_drop_rate=0.0, use_mean_pooling=True, init_scale=0.001, use_rel_pos_bias=False,
                     use_abs_pos_emb=True, init_values=0.1, qkv_bias=False)
    ck = torch.load("/labram/labram-base.pth", map_location="cpu")
    ck = ck.get("model", ck)
    sd = {k[8:]: v for k, v in ck.items() if k.startswith("student.")} or ck
    msg = m.load_state_dict(sd, strict=False)
    return m.eval().cuda(), msg


def embed(model, x, sf, nb, w, input_chans, batch=256):
    import numpy as np
    import torch
    from scipy.signal import resample
    L = int(round(w * sf)); ends = np.round((np.arange(nb) + 1) * 0.8 * sf).astype(int)
    ok = [(k, e) for k, e in enumerate(ends) if e - L >= 0 and e <= x.shape[1]]
    out = np.full((nb, 200), np.nan, np.float32)
    ic = torch.tensor(input_chans).cuda()
    for i in range(0, len(ok), batch):
        chunk = ok[i:i + batch]
        seg = np.stack([resample(x[:, e - L:e], int(200 * w), axis=1) for _, e in chunk])
        t = torch.tensor(seg / 100.0, dtype=torch.float32).cuda().reshape(len(chunk), x.shape[0], int(w), 200)
        with torch.no_grad():
            f = model.forward_features(t, input_chans=ic).float().cpu().numpy()
        out[[k for k, _ in chunk]] = f
    return out


def prep(stem):
    import mne
    import numpy as np
    from scipy.signal import butter, sosfilt
    import b9feat2
    raw = mne.io.read_raw_eeglab(f"/evidence/neurobolt_data/EEG/{stem}_eeg.set", preload=True, verbose="ERROR")
    sf = float(raw.info["sfreq"])
    names = [c.replace("'", "").replace("FPz", "Fpz") for c in raw.ch_names]
    x = raw.get_data(picks=[names.index(c) for c in b9feat2.COMMON]) * 1e6
    n_tr = len([d for d in raw.annotations.description if d.strip() == "R149"])
    nb = int(np.floor(n_tr * 2.1 / 0.8))
    xa = x - x.mean(0, keepdims=True)
    xb = sosfilt(butter(4, [1, 45], btype="band", fs=sf, output="sos"), xa, axis=1)
    return x, xb, sf, nb


def chans():
    import ast
    import re
    import b9feat2
    src = Path("/labram/utils.py").read_text()
    standard_1020 = ast.literal_eval(re.search(r"standard_1020 = (\[.*?\])", src, re.S).group(1).replace("\\\n", ""))
    return [0] + [standard_1020.index(c.upper()) + 1 for c in b9feat2.COMMON]


@app.function(image=image, gpu="A10G", cpu=4.0, memory=32768, timeout=3600, volumes={"/evidence": volume}, max_containers=10)
def feat(stem: str) -> str:
    import numpy as np
    from scipy.signal import butter, sosfilt
    import b9feat2
    model, msg = load_model(); ic = chans()
    x, xb, sf, nb = prep(stem)
    out = {"lab4": embed(model, xb, sf, nb, 4, ic), "lab8": embed(model, xb, sf, nb, 8, ic)}
    ea = b9feat2.euclidean_align(x, sf)
    eab = sosfilt(butter(4, [1, 45], btype="band", fs=sf, output="sos"), ea, axis=1) * 20.0
    out["ea_lab4"] = embed(model, eab, sf, nb, 4, ic)
    Path("/evidence/bridge009/fm").mkdir(parents=True, exist_ok=True)
    np.savez(f"/evidence/bridge009/fm/{stem}.npz", **out); volume.commit()
    return json.dumps({"stem": stem, "nb": nb, "sf": sf, "missing_keys": len(msg.missing_keys),
                       "unexpected": len(msg.unexpected_keys), "nan": {k: round(float(np.isnan(v).any(1).mean()), 3) for k, v in out.items()},
                       "sd": {k: round(float(np.nanstd(v)), 3) for k, v in out.items()}})


@app.function(image=image, gpu="A10G", cpu=4.0, memory=32768, timeout=1800, volumes={"/evidence": volume})
def causal_test() -> str:
    import numpy as np
    model, msg = load_model(); ic = chans()
    x, xb, sf, nb = prep("sub06-scan01")
    xb = xb[:, :int(200 * sf)]; nb = int(200 / 0.8)
    a = embed(model, xb, sf, nb, 4, ic)
    t_s = 120.0; x2 = xb.copy(); x2[:, int(t_s * sf):] += np.random.default_rng(0).normal(0, 20, x2[:, int(t_s * sf):].shape)
    b = embed(model, x2, sf, nb, 4, ic)
    kmax = int(t_s / 0.8) - 1
    return json.dumps({"missing": msg.missing_keys[:5], "unexpected": msg.unexpected_keys[:5],
                       "max_diff_upto_t": float(np.nanmax(np.abs(a[:kmax + 1] - b[:kmax + 1]))),
                       "max_diff_after_t": float(np.nanmax(np.abs(a[kmax + 1:] - b[kmax + 1:])))})


@app.local_entrypoint()
def main(test: bool = False):
    if test:
        print(causal_test.remote()); return
    stems = sorted({e.path.split("/")[-1].replace("_eeg.set", "") for e in volume.listdir("/neurobolt_data/EEG") if e.path.endswith(".set")})
    for r in feat.map(stems, return_exceptions=True):
        print(r if isinstance(r, str) else repr(r)[:400])
