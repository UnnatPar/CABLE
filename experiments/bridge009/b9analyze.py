import itertools
import json
import random
import statistics as st
from pathlib import Path

HERE = Path(__file__).parent
R = HERE / "results"
ROIS = ["cuneus", "heschl", "mfg_anterior", "precuneus_anterior", "putamen", "thalamus", "global_clean"]


def pearson(a, b):
    ma, mb = st.fmean(a), st.fmean(b)
    sa = sum((x - ma) ** 2 for x in a) ** .5; sb = sum((y - mb) ** 2 for y in b) ** .5
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (sa * sb + 1e-12)


def load_jsonl(p):
    return [json.loads(l) for l in open(p, encoding="utf-8")] if p.exists() else []


def method_split_scores(rows, method, key="split"):
    out = {}
    for r in rows:
        if r.get("method") == method and "per_scan" in r:
            out[r[key]] = {s: st.fmean(v) for s, v in r["per_scan"].items()}
    return out


def nb_scores(split_names, pred_dir=R / "nb_preds", first=4):
    out = {}
    for sp in split_names:
        per = {}
        files = [pred_dir / f"{sp}__{roi}.json" for roi in ROIS]
        if not all(f.exists() for f in files):
            continue
        d = [json.loads(f.read_text()) for f in files]
        for scan in d[0]:
            per[scan] = st.fmean(pearson(x[scan]["p"][first:], x[scan]["t"][first:]) for x in d)
        out[sp] = per
    return out


def paired(a, b, units):
    d = [a[u] - b[u] for u in units]
    n = len(d); m = st.fmean(d)
    if n <= 20:
        cnt = sum(1 for s in itertools.product((1, -1), repeat=n) if st.fmean(x * y for x, y in zip(d, s)) >= m)
        p = cnt / 2 ** n
    else:
        rng = random.Random(0); cnt = 0; B = 200000
        for _ in range(B):
            if st.fmean(x * (1 if rng.random() < .5 else -1) for x in d) >= m:
                cnt += 1
        p = (cnt + 1) / (B + 1)
    rng = random.Random(1)
    boots = sorted(st.fmean(rng.choice(d) for _ in range(n)) for _ in range(20000))
    return {"n": n, "mean_a": st.fmean(a[u] for u in units), "mean_b": st.fmean(b[u] for u in units), "gain": m,
            "rel_gain": m / st.fmean(b[u] for u in units), "p_signflip": p, "ci95": [boots[500], boots[19499]],
            "wins": sum(x > 0 for x in d)}


def main():
    summary = {}
    c1 = load_jsonl(R / "confirm_results.jsonl")
    splits = json.loads((R / "confirm_splits.json").read_text())
    for set_name, key in (("C1b", "c1b"), ("C1a", "loso")):
        names = [s["name"] for s in splits[set_name]]
        meth = {m: method_split_scores(c1, m) for m in ("ours", "mel_ridge", "mel_mlp")}
        meth["neurobolt"] = nb_scores(names)
        unit = {m: {sp: st.fmean(v.values()) for sp, v in sc.items() if sp in names} for m, sc in meth.items()}
        res = {"n_units": {m: len(v) for m, v in unit.items()}, "means": {m: (st.fmean(v.values()) if v else None) for m, v in unit.items()}}
        for base in ("neurobolt", "mel_mlp", "mel_ridge"):
            common = sorted(set(unit["ours"]) & set(unit[base]))
            if len(common) >= 5:
                res[f"ours_vs_{base}"] = paired(unit["ours"], unit[base], common)
        summary[set_name] = res
    c3 = load_jsonl(R / "c3_results.jsonl")
    if c3:
        res = {}
        for m in sorted({r["method"] for r in c3 if "per_scan" in r}):
            per = {s: st.fmean(v) for r in c3 if r.get("method") == m and "per_scan" in r for s, v in r["per_scan"].items()}
            subj = {}
            for s, v in per.items():
                subj.setdefault(s.split("-scan")[0], []).append(v)
            res[m] = {"mean_over_scans": st.fmean(per.values()), "n_scans": len(per), "by_subject": {k: st.fmean(v) for k, v in subj.items()}}
        nbc3 = nb_scores([f"c3_{j:02d}" for j in range(11)], R / "nb_c3_preds")
        if nbc3:
            per = {s: v for sp in nbc3.values() for s, v in sp.items()}
            subj = {}
            for s, v in per.items():
                subj.setdefault(s.split("-scan")[0], []).append(v)
            res["neurobolt_v26"] = {"mean_over_scans": st.fmean(per.values()), "n_scans": len(per), "by_subject": {k: st.fmean(v) for k, v in subj.items()}}
        for a, b in (("ours_native", "mel_mlp_native"), ("oursv26_", "mel_mlpv26_"), ("oursv26_", "neurobolt_v26"),
                     ("ours_native", "neurobolt_v26"), ("ours_native", "mel_ridge_native")):
            if a in res and b in res:
                common = sorted(set(res[a]["by_subject"]) & set(res[b]["by_subject"]))
                res[f"{a}_vs_{b}"] = paired(res[a]["by_subject"], res[b]["by_subject"], common)
        summary["C3"] = res
    (R / "confirm_summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1)[:6000])


if __name__ == "__main__":
    main()
