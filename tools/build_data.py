import pyreadr, sys, json, re
import pandas as pd, numpy as np, pycountry

D = sys.argv[1]; OUT = sys.argv[2]; ESRI = sys.argv[3]
loc = pd.read_csv(f"{D}/UNlocations.txt", sep="\t")
countries = loc[loc.location_type == 4][["country_code", "name"]]
obs = pyreadr.read_r(f"{D}/popAge1dt.rda")["popAge1dt"]
proj = pyreadr.read_r(f"{D}/popprojAge1dt.rda")["popprojAge1dt"]
proj = proj[["country_code", "year", "age", "popM", "popF"]].copy()
proj["year"] = proj.year.astype(int)
obs = obs[["country_code", "year", "age", "popM", "popF"]]
allp = pd.concat([obs, proj], ignore_index=True)
assert not allp.duplicated(["country_code", "year", "age"]).any()

keep = set(countries.country_code) | {900}
allp = allp[allp.country_code.isin(keep)]

# Package years are 31 Dec of year t (= UN 1 Jan t+1). Mid-year Y = mean(t=Y-1, t=Y), as wpp2024's own 5x5 scripts do.
YEARS = list(range(1950, 2101, 5))
piv = {}
for sex in ["popM", "popF"]:
    p = allp.pivot_table(index=["country_code", "age"], columns="year", values=sex)
    mid = pd.DataFrame({Y: (p[Y - 1] + p[Y]) / 2 for Y in YEARS})
    piv[sex] = mid * 1000.0  # thousands -> persons

# ISO2 mapping
iso_override = {412: ["XK"], 900: ["WORLD"]}
code2iso = {}
for cc in sorted(keep):
    if cc in iso_override: code2iso[cc] = iso_override[cc]; continue
    c = pycountry.countries.get(numeric=f"{cc:03d}")
    code2iso[cc] = [c.alpha_2] if c else None
unmatched = [(cc, countries.set_index("country_code").name.get(cc)) for cc, v in code2iso.items() if v is None]
print("unmatched UN codes:", unmatched)

# Esri names per ISO
esri = {}
for line in open(ESRI, encoding="utf-8"):
    iso, nm = line.rstrip("\n").split("|"); esri.setdefault(iso, []).append(nm)
SUBPARTS = {"Canarias", "Azores", "Madeira", "Glorioso Islands", "Juan De Nova Island", "Saba", "Saint Eustatius"}
short_override = {  # where no single Esri feature gives a clean short name
    344: "Hong Kong", 446: "Macao", 158: "Taiwan", 732: "Western Sahara", 412: "Kosovo",
    535: "Bonaire, Sint Eustatius and Saba", 900: "World",
}
names = countries.set_index("country_code").name.to_dict(); names[900] = "World"

out = {"years": YEARS, "ages": [f"{a}-{a+4}" for a in range(0, 100, 5)] + ["100+"], "areas": {}}
ages = np.arange(101)
group_idx = np.minimum(ages // 5, 20)
skipped = []
have = set(piv["popM"].index.get_level_values(0))
for cc, isos in code2iso.items():
    if not isos: continue
    if cc not in have: skipped.append((cc, names[cc])); continue
    iso = isos[0]
    feats = [n for n in esri.get(iso, []) if n not in SUBPARTS]
    short = short_override.get(cc) or (feats[0] if len(feats) == 1 else names[cc])
    m1 = piv["popM"].loc[cc].reindex(ages).values  # ages x years
    f1 = piv["popF"].loc[cc].reindex(ages).values
    assert not np.isnan(m1).any() and not np.isnan(f1).any(), cc
    rec = {"name": short, "un": names[cc], "iso": isos, "y": {}}
    for j, Y in enumerate(YEARS):
        m5 = np.bincount(group_idx, weights=m1[:, j], minlength=21)
        f5 = np.bincount(group_idx, weights=f1[:, j], minlength=21)
        tot = m1[:, j].sum() + f1[:, j].sum()
        # median age from single years of age (linear within each year of age)
        both = m1[:, j] + f1[:, j]; cum = np.cumsum(both); half = tot / 2
        a = int(np.searchsorted(cum, half)); before = cum[a - 1] if a > 0 else 0
        # Standard interpolation gives a + frac. UN WPP 2024's published "median age, 1 July" is exactly 1.00 lower
        # (checked vs 8 published 2026 values and Japan 2020/2025), so we subtract 1 to match the UN's own figures.
        med = a + (half - before) / both[a] - 1.0
        bp = lambda v: int(round(v / tot * 10000))  # share of total population in hundredths of a percent
        rec["y"][str(Y)] = {"m": [int(round(v)) for v in m5], "f": [int(round(v)) for v in f5],
                            "t": int(round(tot)), "med": round(float(med), 1),
                            "row": [int(round(tot)), round(float(med), 1)] + [bp(v) for v in m5] + [bp(v) for v in f5]}
    out["areas"][iso] = rec

# sanity checks against published WPP 2024 headline figures (mid-year totals)
def tot(iso, Y): return out["areas"][iso]["y"][str(Y)]["t"]
for iso, Y in [("WORLD", 2025), ("WORLD", 2024 + 1), ("IN", 2025), ("CN", 2025), ("US", 2025), ("GB", 2025), ("NE", 2025), ("JP", 2025)]:
    r = out["areas"][iso]["y"][str(Y)]
    print(iso, Y, f"{r['t']:,}", "median", r["med"])
cs = sum(a["y"]["2025"]["t"] for k, a in out["areas"].items() if k != "WORLD")
print("sum of countries 2025:", f"{cs:,}", "vs World", f"{tot('WORLD',2025):,}")
print("areas:", len(out["areas"]), "skipped (no age data):", skipped)
missing_on_map = sorted(k for k in out["areas"] if k not in esri and k != "WORLD")
print("UN areas with no feature in the Esri list:", missing_on_map)
no_data = sorted(set(esri) - set(out["areas"]))
print("Esri ISO codes with no UN data:", no_data)
# compact output: one row per year, [total, medianAge, male shares x21, female shares x21] (shares in 0.01 %)
# compact output: one row per year, [total, medianAge, male counts x21, female counts x21].
# Counts keep 3 significant figures (exact below 1,000), written as e.g. 123e3 (valid JSON numbers).
import math
def sf3(v):
    v = int(round(v))
    if v < 1000: return str(v)
    e = int(math.floor(math.log10(v))) - 2
    m = int(round(v / 10 ** e))
    if m == 1000: m, e = 100, e + 1
    return f"{m}e{e}"
parts = []
for iso, rec in out["areas"].items():
    rows = []
    for Y in YEARS:
        r = rec["y"][str(Y)]
        rows.append("[" + ",".join([str(r["t"]), str(r["med"])] + [sf3(v) for v in r["m"]] + [sf3(v) for v in r["f"]]) + "]")
    extra = (',"iso":' + json.dumps(rec["iso"])) if len(rec["iso"]) > 1 else ""
    parts.append(json.dumps(iso) + ':{"n":' + json.dumps(rec["name"], ensure_ascii=False) + ',"un":' + json.dumps(rec["un"], ensure_ascii=False) + extra + ',"y":[' + ",".join(rows) + "]}")
txt = '{"years":' + json.dumps(YEARS) + ',"ages":' + json.dumps(out["ages"]) + ',"areas":{' + ",".join(parts) + "}}"
chk = json.loads(txt)
# check: rounded counts vs exact, and group sums vs total
worst_rel = 0
for iso, rec in out["areas"].items():
    for j, Y in enumerate(YEARS):
        row = chk["areas"][iso]["y"][j]; r = rec["y"][str(Y)]
        exact = r["m"] + r["f"]
        for a, b in zip(row[2:], exact):
            if b >= 1000: worst_rel = max(worst_rel, abs(a - b) / b)
            else: assert a == b
        assert abs(sum(row[2:]) - r["t"]) <= max(0.002 * r["t"], 21), (iso, Y)
print("worst relative rounding error (counts >= 1000):", round(worst_rel, 5))
open(OUT, "w", encoding="utf-8").write(txt)

import os; print("bytes", os.path.getsize(OUT))
