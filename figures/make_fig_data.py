import json
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).parent
B9 = HERE.parent / "experiments" / "bridge009"
sys.path.insert(0, str(B9))
import b9analyze as A

R = B9 / "results"
splits = json.loads((R / "confirm_splits.json").read_text())
c1 = A.load_jsonl(R / "confirm_results.jsonl")
out = {}
for set_name in ("C1b", "C1a"):
    names = [s["name"] for s in splits[set_name]]
    meth = {m: A.method_split_scores(c1, m) for m in ("ours", "mel_mlp", "mel_ridge")}
    meth["neurobolt"] = A.nb_scores(names)
    out[set_name] = {m: {sp: st.fmean(v.values()) for sp, v in sc.items() if sp in names} for m, sc in meth.items()}
summ = json.loads((R / "confirm_summary.json").read_text())["C3"]
out["C3"] = {"ours": summ["oursv26_"]["by_subject"], "neurobolt": summ["neurobolt_v26"]["by_subject"],
             "mel_mlp": summ["mel_mlpv26_"]["by_subject"], "mel_ridge": summ["mel_ridgev26_"]["by_subject"]}
out["C3_scan_means"] = {m: summ[k]["mean_over_scans"] for m, k in (("ours", "oursv26_"), ("neurobolt", "neurobolt_v26"),
                         ("mel_mlp", "mel_mlpv26_"), ("mel_ridge", "mel_ridgev26_"))}
zs = json.loads((R / "zeroshot_summary.json").read_text())
zo = [json.loads(l) for l in open(R / "c3_results.jsonl", encoding="utf-8") if "zeroshot" in l][0]["per_scan"]
zn = A.nb_scores(["zeroshot"], R / "nb_zs_preds")["zeroshot"]
out["zeroshot"] = {"ours": st.fmean(st.fmean(v) for v in zo.values()), "neurobolt": st.fmean(zn.values()),
                   "paired_by_subject": zs["zeroshot_ours_vs_neurobolt"]}
inv = {v: k for k, v in json.loads((R / "nb_zeroshot_mapping.json").read_text()).items()}
by_sub = lambda per: {s: st.fmean(v for k, v in per.items() if k.split("-scan")[0] == s)
                      for s in sorted({k.split("-scan")[0] for k in per})}
out["zeroshot_by_subject"] = {"ours": by_sub({s: st.fmean(v) for s, v in zo.items()}),
                              "neurobolt": by_sub({inv[s]: v for s, v in zn.items()})}
eff = json.loads((R / "data_efficiency.json").read_text())
out["efficiency"] = {m: {n: st.fmean(r[m] for r in eff if r["n"] == n) for n in (4, 8, 12, 16)} for m in ("ours", "mel_ridge")}
out["ablation"] = [["MEL (ridge)", .311], ["MEL (MLP ens.)", .324], ["raw spectra, ridge", .347],
                   ["+ freq. alignment", .375], ["+ re-centring", .386],
                   ["CABLE, 12 members", .4045], ["+ extra feature families", .4091]]
loso = [s["name"] for s in splits["C1a"]]
pr = {}
for m in ("ours", "mel_mlp"):
    rows = [v for r in c1 if r.get("method") == m and r.get("split") in loso for v in r["per_scan"].values()]
    pr[m] = [st.fmean(x[j] for x in rows) for j in range(7)]
nbr = []
for sp in loso:
    d = {roi: json.loads((R / "nb_preds" / f"{sp}__{roi}.json").read_text()) for roi in A.ROIS}
    for scan in d[A.ROIS[0]]:
        nbr.append([A.pearson(d[roi][scan]["p"][4:], d[roi][scan]["t"][4:]) for roi in A.ROIS])
pr["neurobolt"] = [st.fmean(x[j] for x in nbr) for j in range(7)]
out["per_roi_c1a"] = pr
cross = {s: st.fmean(v) for r in c1 if r.get("method") == "ours" and r.get("split") in loso for s, v in r["per_scan"].items()}
c2 = [r for r in A.load_jsonl(R / "c2_results.jsonl") if r["method"] == "ours"][-1]["per_scan"]
out["cross_vs_within"] = {s: [cross[s], st.fmean(c2["pooled"][s])] for s in cross if s in c2["pooled"]}
(HERE / "fig_data.json").write_text(json.dumps(out, indent=1))
print("per-ROI", {m: [round(v, 3) for v in x] for m, x in pr.items()}, "scatter n", len(out["cross_vs_within"]))
for k in ("C1b", "C1a", "C3"):
    print(k, {m: (len(v), round(st.fmean(v.values()), 4)) for m, v in out[k].items()})
print(out["zeroshot"], out["efficiency"])
print("zero-shot by subject", {m: (len(v), round(st.fmean(v.values()), 4)) for m, v in out["zeroshot_by_subject"].items()})
