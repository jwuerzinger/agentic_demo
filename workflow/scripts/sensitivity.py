"""TOY sensitivity of a *dedicated* soft-dilepton + ISR + MET search (see
docs/search_design.md) for HAND-SELECTED benchmark models.

This is an **independent** study: it depends only on the parsed spectra
(`results/{scan}/features.parquet`) and `config["sensitivity"]["models"]` -- NOT on the
target/hole classification. It is also NOT a detector simulation.

Per benchmark, a parametrised cut-and-count at the target luminosity:
  S = sigma(m_light, mode) * L * eff(dm) * BR_sel
        sigma  : approximate 13 TeV EW-ino xsec (config xsec_13tev_fb)
        eff(dm): soft-lepton turn-on, eff_plateau * sigmoid((dm - dm_half)/width)
        BR_sel : br_c1_lep^2  (both charginos -> chi1^0 ell nu; the OS-dilepton channel)
  B = bkg_ref_events * (L / bkg_ref_lumi_fb)
  Z = Asimov expected significance with background systematic sigma_B = bkg_syst_frac*B
`excludable` = Z >= excl_significance. eff and B are config knobs (orders of magnitude
anchored to arXiv:1911.12606) -- a *relative*, illustrative reach, not a real limit.
"""
import numpy as np
import pandas as pd

df = pd.read_parquet(snakemake.input[0])                      # noqa: F821  (features.parquet)
cfg = snakemake.config                                        # noqa: F821
scan = snakemake.wildcards.scan                               # noqa: F821
S = cfg["sensitivity"]
L = float(cfg["target_lumi_fb"])
XS = cfg["xsec_13tev_fb"]
PUR = float(cfg["mixing_purity"])

# benchmark model_numbers requested for THIS scan
want = sorted(int(m["model"]) for m in S["models"] if m["scan"] == scan)
work = df[df["model_number"].isin(want)].copy()

EFF0 = float(S["eff_plateau"])
DMH = float(S["eff_dm_half_gev"])
DMW = float(S["eff_dm_width_gev"])
B = float(S["bkg_ref_events"]) * (L / float(S["bkg_ref_lumi_fb"]))
FB = float(S["bkg_syst_frac"])
ZEXC = float(S["excl_significance"])


def lsp_type(r):
    fr = {"bino": r["f_bino"], "wino": r["f_wino"], "higgsino": r["f_higgsino"]}
    top = max(fr, key=fr.get)
    return top if fr[top] >= PUR else "mixed"


def xsec_fb(mass, mode):
    pts = XS["wino" if mode == "wino" else "higgsino"]
    return float(np.exp(np.interp(np.log(max(mass, 1.0)),
                                  np.log([m for m, _ in pts]), np.log([s for _, s in pts]))))


def asimov_Z(s, b, db):
    s = np.asarray(s, float)
    if b <= 0:
        return np.where(s > 0, np.inf, 0.0)
    db2 = db * db
    t1 = (s + b) * np.log((s + b) * (b + db2) / (b * b + (s + b) * db2))
    t2 = (b * b / db2) * np.log(1.0 + db2 * s / (b * (b + db2))) if db2 > 0 else s
    return np.sqrt(np.clip(2.0 * (t1 - t2), 0.0, None))


# derived quantities (inline -- do not need classify)
work["dm_n2n1"] = work["m_n2"] - work["m_n1"]
work["m_light_ewk"] = work[["m_c1", "m_n2"]].min(axis=1)
work["lsp_type"] = work.apply(lsp_type, axis=1)
mode = np.where(work["lsp_type"] == "wino", "wino", "higgsino")

work["xsec_fb"] = [xsec_fb(m, md) for m, md in zip(work["m_light_ewk"], mode)]
work["eff"] = EFF0 / (1.0 + np.exp(-(work["dm_n2n1"] - DMH) / DMW))
work["br_sel"] = work["br_c1_lep"].fillna(0.0) ** 2
work["S"] = work["xsec_fb"] * L * work["eff"] * work["br_sel"]
work["B"] = B
work["Z_excl"] = asimov_Z(work["S"].to_numpy(), B, FB * B)
work["excludable"] = work["Z_excl"] >= ZEXC
work["scan"] = scan

missing = sorted(set(want) - set(work["model_number"]))
if missing:
    print(f"[{scan}] WARNING: benchmark models not found in this scan: {missing}")

cols = ["scan", "model_number", "lsp_type", "m_n1", "m_light_ewk", "dm_n2n1",
        "br_c1_lep", "xsec_fb", "eff", "S", "B", "Z_excl", "excludable"]
out = work[[c for c in cols if c in work.columns]].sort_values("model_number")
print(f"[{scan}] sensitivity for {len(out)} benchmark(s) @ {L:.0f} fb-1 (B={B:.0f}):")
for _, r in out.iterrows():
    print(f"   model {int(r.model_number):>5}  m={r.m_n1:.0f}  dm={r.dm_n2n1:.2f}  "
          f"S={r.S:.0f}  Z={r.Z_excl:.2f}  excludable={r.excludable}")

out.to_parquet(snakemake.output.sensitivity, index=False)     # noqa: F821
out.to_csv(snakemake.output.summary, index=False)             # noqa: F821
