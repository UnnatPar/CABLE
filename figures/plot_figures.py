import json
from pathlib import Path

HERE = Path(__file__).parent

BLUE, GREY, ORANGE, LIGHT = "#2b6cb0", "#8a8a8a", "#d97b29", "#c9c9c9"
METHODS = [("ours", "CABLE", BLUE), ("mel_mlp", "MEL", ORANGE), ("neurobolt", "NeuroBOLT", GREY)]


def _style(plt):
    plt.rcParams.update({"font.size": 8, "axes.spines.top": False, "axes.spines.right": False, "font.family": "DejaVu Sans"})


def schematic(fig, x0, x1, y0, y1):
    import numpy as np
    from matplotlib.patches import ConnectionPatch, Ellipse, FancyBboxPatch
    rng = np.random.default_rng(3)
    P1, P2 = "#c0504d", "#7f6aa8"
    widths = [1.0, 1.0, 0.62, 0.62, 1.0, 1.1]; gap, inner = 0.55, 0.22
    unit = (x1 - x0) / (sum(widths) + 4 * gap + inner)
    H = y1 - y0
    py0, ph = y0 + 0.36 * H, 0.52 * H
    xs, x = [], x0
    for i, w in enumerate(widths):
        xs.append(x); x += w * unit + (inner if i == 2 else gap) * unit
    axs = [fig.add_axes([xs[i], py0, widths[i] * unit, ph]) for i in range(6)]
    for a in axs:
        a.set_xticks([]); a.set_yticks([]); a.patch.set_alpha(0)
        for s in a.spines.values():
            s.set_visible(False)
    a = axs[0]; t = np.linspace(0, 1, 500)
    for k in range(5):
        sig = np.convolve(rng.standard_normal(500), np.ones(5) / 5, "same") * 0.7 + 0.55 * np.sin(2 * np.pi * 20 * t + k)
        past = t <= 0.84
        a.plot(t[past], sig[past] * 0.17 + k, color="#3a3a3a", lw=0.45)
        a.plot(t[~past], sig[~past] * 0.17 + k, color="#c4c4c4", lw=0.45)
    a.axvspan(0.0, 0.84, color="#ececec", zorder=0, lw=0)
    a.axvline(0.84, color="k", lw=0.8, ls=(0, (2, 1.5)))
    a.text(0.84, 4.65, "volume onset", fontsize=6.5, ha="center", va="bottom")
    a.text(0.42, -0.95, "past EEG only", fontsize=6.5, ha="center", va="top", color="#555")
    a.set_xlim(0, 1); a.set_ylim(-1.0, 5.2)
    a = axs[1]; f = np.arange(1, 46, 2.0); tt = np.arange(36)
    S = (1 / f[:, None] ** 0.8) * np.exp(0.18 * rng.standard_normal((len(f), len(tt))))
    S[4:6] *= 2.6 + 1.0 * np.sin(tt / 4.5)[None, :]
    a.imshow(np.log(S), aspect="auto", origin="lower", cmap="Blues", extent=[0, 1, 0, 46])
    a.set_yticks([10, 40]); a.set_yticklabels(["10", "40 Hz"])
    a.tick_params(labelsize=6.5, length=1.5, pad=1)
    a.text(0.5, -3, "time", fontsize=6.5, ha="center", va="top", color="#555")
    def cloud(a, cx, cy, sx, sy, ang, col, n=60):
        z = rng.standard_normal((n, 2)) * [sx, sy]; c, s_ = np.cos(ang), np.sin(ang)
        z = z @ np.array([[c, s_], [-s_, c]]) + [cx, cy]
        a.scatter(z[:, 0], z[:, 1], s=2.0, color=col, lw=0, alpha=0.8)
        a.add_patch(Ellipse((cx, cy), 4 * sx, 4 * sy, angle=np.degrees(ang), fill=False, ec=col, lw=1.0))
    a = axs[2]; cloud(a, -0.9, 0.55, 1.05, 0.33, 0.6, P1); cloud(a, 0.95, -0.7, 0.28, 0.7, -0.35, P2)
    a.text(0, 3.0, "before", fontsize=7, ha="center", va="bottom")
    a = axs[3]; cloud(a, 0, 0, 0.5, 0.5, 0, P1); cloud(a, 0, 0, 0.5, 0.5, 0, P2)
    a.text(0, 3.0, "after", fontsize=7, ha="center", va="bottom")
    for a in axs[2:4]:
        a.set_xlim(-2.9, 2.9); a.set_ylim(-2.9, 2.9); a.set_aspect("equal", adjustable="box")
        a.axhline(0, color="#9db6d3", lw=0.5, zorder=0); a.axvline(0, color="#9db6d3", lw=0.5, zorder=0)
    axs[2].text(1.0, -3.15, "person 1", fontsize=6.5, color=P1, va="top", ha="right", clip_on=False)
    axs[3].text(-1.0, -3.15, "person 2", fontsize=6.5, color=P2, va="top", ha="left", clip_on=False)
    a = axs[4]; lag = np.arange(0.8, 24.1, 0.8)
    wgt = (lag / 5.0) ** 2.2 * np.exp(-(lag - 5.0) / 2.2) - 0.16 * (lag / 12.0) ** 4 * np.exp(-(lag - 12.0) / 3.5)
    a.bar(lag, wgt, width=0.6, color=[BLUE if v > 0 else "#9bb5d6" for v in wgt])
    a.axhline(0, color="k", lw=0.5); a.set_xlim(0, 25)
    a.set_xticks([0.8, 12, 24]); a.set_xticklabels(["0.8", "12", "24 s"]); a.tick_params(labelsize=6.5, length=1.5, pad=1)
    a.text(12.5, 1.02 * wgt.max(), "weight per lag", fontsize=6.5, ha="center", va="bottom", color="#555")
    a.set_ylim(wgt.min() * 1.6, wgt.max() * 1.25)
    a = axs[5]; tb = np.linspace(0, 1, 300); win = np.hanning(70); win /= win.sum()
    for k, name in enumerate(["thalamus", "putamen", "cuneus"]):
        base = np.convolve(rng.standard_normal(300 + 140), win, "valid")[:300]; base = base / base.std() * 0.42
        pred = 0.8 * base + np.convolve(rng.standard_normal(300 + 140), win, "valid")[:300] / 0.05 * 0.012
        a.plot(tb, base + 1.8 * k, color="#a0a0a0", lw=1.0)
        a.plot(tb, pred + 1.8 * k, color=BLUE, lw=1.0)
        a.text(0.0, 1.8 * k + 0.62, name, fontsize=6.5, va="bottom")
    a.set_xlim(0, 1); a.set_ylim(-1.0, 5.2)
    a.text(1.0, -0.95, "measured", fontsize=6.5, color="#888", ha="right", va="top")
    a.text(0.0, -0.95, "predicted", fontsize=6.5, color=BLUE, ha="left", va="top")
    hx0, hx1 = xs[2] - 0.4 * gap * unit, xs[3] + widths[3] * unit + 0.4 * gap * unit
    fig.patches.append(FancyBboxPatch((hx0, y0 + 0.01 * H), hx1 - hx0, 0.97 * H,
                                      boxstyle="round,pad=0.0,rounding_size=0.01", transform=fig.transFigure,
                                      fc="#e8f0f9", ec=BLUE, lw=1.1, zorder=-1))
    for i, j in [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)]:
        fig.add_artist(ConnectionPatch(xyA=(1.0, 0.5), coordsA=axs[i].transAxes, xyB=(-0.2 if j == 1 else 0.0, 0.5),
                                       coordsB=axs[j].transAxes,
                                       arrowstyle="-|>", mutation_scale=9, lw=1.1,
                                       color=BLUE if (i, j) == (2, 3) else "#4d4d4d", shrinkA=4, shrinkB=4))
    labels = [(0, "1  Scalp EEG", "26 channels"), (1, "2  Band power", "2 Hz bins and\n7-band covariances"),
              (None, "3  Per-person alignment", "past-only whitening of each band\nby the person's own covariance"),
              (4, "4  Shared linear readout", "PCA, lags, ridge;\n12 members averaged"),
              (5, "5  Regional BOLD", "7 regions, cortical\nand subcortical")]
    for i, head, sub in labels:
        cx = (hx0 + hx1) / 2 if i is None else xs[i] + widths[i] * unit / 2
        col = BLUE if i is None else "k"
        fig.text(cx, y0 + 0.215 * H, head, ha="center", va="center", fontsize=7.3, fontweight="bold", color=col)
        fig.text(cx, y0 + 0.085 * H, sub, ha="center", va="center", fontsize=6.8, linespacing=1.05)
    fig.text(0.005, y1 + 0.004, "A  CABLE", ha="left", va="bottom", fontsize=8.5, fontweight="bold")


def figure(d) -> bytes:
    import io
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    _style(plt)
    fig = plt.figure(figsize=(7.3, 3.75))
    schematic(fig, 0.045, 0.99, 0.585, 0.945)
    a = fig.add_axes([0.075, 0.105, 0.37, 0.37])
    sets = [("Fresh\nsplits", "C1b", None), ("Leave one\nperson out", "C1a", None),
            ("External\nsite", "C3", "C3_scan_means"), ("Zero-shot,\nnew site", None, None)]
    w = 0.26; rng = np.random.default_rng(0)
    for i, (lab, key, meanskey) in enumerate(sets):
        for j, (m, name, c) in enumerate(METHODS):
            x = i + (j - 1) * w
            if key is None:
                if m == "mel_mlp":
                    continue
                vals = list(d["zeroshot_by_subject"][m].values())
                a.bar(x, d["zeroshot"][m], w * 0.92, color=c)
                a.scatter(x + rng.uniform(-w * 0.28, w * 0.28, len(vals)), vals, s=2.2, color="k", alpha=0.35, lw=0, zorder=3)
                continue
            vals = list(d[key][m].values())
            mean = d[meanskey][m] if meanskey else float(np.mean(vals))
            a.bar(x, mean, w * 0.92, color=c, label=name if i == 0 else None)
            a.scatter(x + rng.uniform(-w * 0.28, w * 0.28, len(vals)), vals, s=2.2, color="k", alpha=0.35, lw=0, zorder=3)
    a.set_xticks(range(4)); a.set_xticklabels([s[0] for s in sets], fontsize=7)
    a.set_ylabel("BOLD prediction r"); a.set_ylim(0, 0.92)
    a.legend(frameon=False, fontsize=7, loc="upper left", ncol=3, handlelength=1, columnspacing=0.8, bbox_to_anchor=(-0.02, 1.04))
    a.set_title("B  New people and a new site", loc="left", fontsize=8.5, fontweight="bold")
    c_ = fig.add_axes([0.555, 0.105, 0.435, 0.37])
    rois = ["Cuneus", "Heschl's", "Mid.\nfrontal", "Precun.", "Putamen", "Thalam.", "Global"]
    x = np.arange(7)
    for j, (m, name, col) in enumerate(METHODS):
        c_.bar(x + (j - 1) * w, d["per_roi_c1a"][m], w * 0.92, color=col, label=name)
    c_.set_xticks(x); c_.set_xticklabels(rois, fontsize=7); c_.set_ylabel("r (leave one person out)")
    c_.set_ylim(0, 0.62)
    c_.set_title("C  Every region, cortical and subcortical", loc="left", fontsize=8.5, fontweight="bold")
    buf = io.BytesIO(); fig.savefig(buf, format="png", dpi=300); plt.close(fig); return buf.getvalue()


def figure2(d) -> bytes:
    import io
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    _style(plt)
    fig = plt.figure(figsize=(7.3, 1.8))
    axA = fig.add_axes([0.01, 0.225, 0.33, 0.635])
    axB = fig.add_axes([0.43, 0.225, 0.24, 0.635])
    axC = fig.add_axes([0.765, 0.225, 0.225, 0.635])
    ab = d["ablation"]; y = np.arange(len(ab))[::-1]
    cols = [ORANGE, ORANGE, LIGHT, BLUE, BLUE, BLUE, LIGHT]
    axA.barh(y, [v for _, v in ab], color=cols, height=0.7, alpha=0.45)
    for yi, (lab, v) in zip(y, ab):
        axA.text(0.005, yi, lab, va="center", fontsize=7, color="k")
        axA.text(0.475, yi, f"{v:.3f}", va="center", fontsize=7)
    axA.set_yticks([]); axA.set_xlim(0, 0.54); axA.set_xticks([0, 0.2, 0.4]); axA.set_xlabel("r (17 people, nested CV)")
    axA.set_title("A  Ablation", loc="left", fontsize=8.5, fontweight="bold")
    n = [4, 8, 12, 16]
    axB.plot(n, [d["efficiency"]["ours"][str(k)] for k in n], "o-", color=BLUE, ms=3, label="CABLE")
    axB.plot(n, [d["efficiency"]["mel_ridge"][str(k)] for k in n], "o-", color=ORANGE, ms=3, label="MEL (ridge)")
    axB.set_xticks(n); axB.set_xlabel("training people"); axB.set_ylabel("r (nested CV)"); axB.set_ylim(0.2, 0.42)
    axB.legend(frameon=False, fontsize=7, loc="lower right")
    axB.set_title("B  Data efficiency", loc="left", fontsize=8.5, fontweight="bold")
    cv = np.array(list(d["cross_vs_within"].values()))
    axC.plot([0, 0.8], [0, 0.8], color=LIGHT, lw=0.8, zorder=0)
    axC.scatter(cv[:, 1], cv[:, 0], s=8, color=BLUE, alpha=0.8, lw=0)
    axC.set_xlabel("within-person r"); axC.set_ylabel("cross-person r")
    axC.set_xlim(-0.05, 0.85); axC.set_ylim(-0.05, 0.85); axC.set_xticks([0, 0.4, 0.8]); axC.set_yticks([0, 0.4, 0.8])
    axC.set_title("C  Person-specific error", loc="left", fontsize=8.5, fontweight="bold")
    buf = io.BytesIO(); fig.savefig(buf, format="png", dpi=300); plt.close(fig); return buf.getvalue()


if __name__ == "__main__":
    d = json.loads((HERE / "fig_data.json").read_text())
    (HERE / "figure1.png").write_bytes(figure(d))
    (HERE / "figure2.png").write_bytes(figure2(d))
    print("wrote", HERE / "figure1.png", HERE / "figure2.png")
