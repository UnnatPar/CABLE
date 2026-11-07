import json
import random
from pathlib import Path

HERE = Path(__file__).parent
scans = ["sub01-scan01", "sub02-scan01", "sub03-scan02", "sub04-scan01", "sub05-scan01", "sub06-scan01", "sub07-scan01",
         "sub07-scan02", "sub08-scan01", "sub08-scan02", "sub09-scan01", "sub09-scan02", "sub10-scan02", "sub11-scan01",
         "sub12-scan01", "sub12-scan02", "sub13-scan01", "sub13-scan02", "sub14-scan01", "sub14-scan02", "sub15-scan01",
         "sub16-scan01", "sub17-scan02", "sub18-scan01", "sub19-scan02", "sub20-scan01", "sub20-scan02", "sub21-scan01",
         "sub22-scan01"]
subs = sorted({s.split("-scan")[0] for s in scans})
ids = lambda s: [x for x in scans if x.startswith(s + "-")]
old = json.loads((HERE.parent / "bridge008" / "results" / "resample_splits.json").read_text())
oldkeys = {(tuple(sorted(o["val"])), tuple(sorted(o["test"]))) for o in old}
c1a = []
for i, s in enumerate(subs):
    tr = [t for t in subs if t != s]
    val = [tr[j] for j in range(len(tr)) if j % 5 == i % 5][:4]
    c1a.append({"name": f"loso_{s}", "test": ids(s), "val": [x for v in val for x in ids(v)]})
rng = random.Random(909); c1b = []
while len(c1b) < 20:
    p = list(subs); rng.shuffle(p); te, va = [], []
    for s in p:
        if len(te) < 6:
            te += ids(s)
        elif len(va) < 5:
            va += ids(s)
    key = (tuple(sorted(va)), tuple(sorted(te)))
    if 5 <= len(te) <= 7 and 4 <= len(va) <= 6 and key not in oldkeys and key not in {(tuple(sorted(c["val"])), tuple(sorted(c["test"]))) for c in c1b}:
        c1b.append({"name": f"c1b_{len(c1b):02d}", "test": te, "val": va})
out = HERE / "results" / "confirm_splits.json"
assert not out.exists(), "splits already generated"
out.write_text(json.dumps({"C1a": c1a, "C1b": c1b}, indent=1))
print(len(c1a), len(c1b), c1b[0])
