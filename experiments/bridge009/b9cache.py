from pathlib import Path

import modal

HERE = Path(__file__).parent
app = modal.App("cable-b9cache")
volume = modal.Volume.from_name("cable-data")
image = (modal.Image.debian_slim(python_version="3.12")
         .pip_install("numpy==2.2.6", "scipy==1.18.1")
         .add_local_file(HERE.parent / "bridge003" / "b3lib.py", "/root/b3lib.py")
         .add_local_file(HERE / "b9lib.py", "/root/b9lib.py"))


@app.function(image=image, cpu=2.0, memory=8192, timeout=1800, volumes={"/evidence": volume}, max_containers=30)
def build(stem: str, common: list) -> dict:
    import numpy as np
    import b9lib
    z = np.load(f"/evidence/bridge005/nb/{stem}.npz", allow_pickle=True)
    ch = [str(c) for c in z["channels"]]
    names = [str(n).lower().replace("'", "’") for n in z["roi_names"]]
    Yall = z["roi_all"].astype(float)
    b5 = z["eeg_logpow"][:, [ch.index(c) for c in common], :].astype(float)
    g = np.load(f"/evidence/bridge008/nb_fine/{stem}.npz", allow_pickle=True)
    gch = [str(c) for c in g["channels"]]
    fine = g["eeg_fine"][:, [gch.index(c) for c in common], :].astype(float)
    fams = {"b5": b5.reshape(len(b5), -1), "fine": fine.reshape(len(fine), -1)}
    for fam, d in (("cov4", "nb_cov"), ("cov7", "nb_cov7")):
        cv = np.load(f"/evidence/bridge008/{d}/{stem}.npz", allow_pickle=True)
        cch = [str(c).replace("'", "").replace("FPz", "Fpz") for c in cv["channels"]]
        iu = np.triu_indices(len(cch)); pos = {(int(a), int(b)): k for k, (a, b) in enumerate(zip(*iu))}
        ci = sorted(cch.index(c) for c in common)
        sel = [pos[(a, b)] for ai, a in enumerate(ci) for b in ci[ai:]]
        C = cv["cov_tangent"][:, sel, :].astype(float)
        fams[fam] = C.reshape(len(C), -1)
    n = min([len(Yall)] + [len(v) for v in fams.values()])
    valid = np.isfinite(fams["fine"][:n]).all(1) & np.isfinite(fams["b5"][:n]).all(1)
    Y = b9lib.target_lp(Yall[:n])
    out = Path("/evidence/bridge009/cache"); out.mkdir(parents=True, exist_ok=True)
    np.savez(out / f"{stem}.npz", valid=valid, Y7=Y[:, [names.index(r) for r in b9lib.ROIS]].astype(np.float32),
             Yall=Y.astype(np.float32), roi_names=np.array(names), channels=np.array(common),
             **{k: v[:n].astype(np.float32) for k, v in fams.items()})
    volume.commit()
    return {"stem": stem, "n": int(n), "valid": float(valid.mean()), "n_rois": len(names),
            "dims": {k: int(v.shape[1]) for k, v in fams.items()}, "len_mismatch": {k: int(len(v) - n) for k, v in fams.items()}}


@app.function(image=image, cpu=1.0, memory=4096, timeout=600, volumes={"/evidence": volume})
def common_channels() -> tuple:
    import numpy as np
    base = sorted(Path("/evidence/bridge005/nb").glob("*.npz"))
    chs = None
    for f in base:
        c = set(str(x) for x in np.load(f, allow_pickle=True)["channels"]); chs = c if chs is None else chs & c
    common = [c for c in [str(x) for x in np.load(base[0], allow_pickle=True)["channels"]] if c in chs]
    return [f.stem for f in base], common


@app.local_entrypoint()
def main():
    import json
    stems, common = common_channels.remote()
    print(len(stems), "scans;", len(common), "common channels:", common)
    res = [r for r in build.starmap([(s, common) for s in stems], return_exceptions=True)]
    for r in res:
        print(json.dumps(r) if isinstance(r, dict) else repr(r)[:300])
