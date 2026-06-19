"""How much better than the best CURRENT search a DEDICATED analysis would have to be to
exclude each hand-selected benchmark at the target luminosity.

Data-anchored and independent of the target/hole classification: it reads the real
per-model expected CLs (min over the 8 recastable searches) from `merged.parquet` and
works in SIGNAL-STRENGTH space, where the expected 95% CL upper limit scales as
    mu95(L) = mu95(L0) * sqrt(L0 / L)         (physically correct; monotonic in L)
-- unlike the sqrt-L *significance* heuristic in project.py, which is only valid near the
exclusion boundary (ExpCLs <~ 0.5) and misbehaves for far-from-reach models.

mu95(L0) is recovered from the expected CLs via the asymptotic CLs relation
    ExpCLs(mu) = 2 * (1 - Phi(mu / sigma_mu)),    mu95 = 1.96 * sigma_mu
which makes ExpCLs = 0.05 <-> mu95 = 1 (the exclusion boundary) by construction.

Output per benchmark:
    R_req = mu95(target)  -- improvement needed over the best CURRENT search to exclude the model
                             at L. For these compressed models that current search is the soft-
                             LEPTON one, which uses NONE of the radiative chi2->chi1 gamma photon,
                             so R_req is LEPTON-channel-anchored -- it cannot credit a photon search.
    verdict               -- "luminosity"       (R_req <= 1)
                             "lepton re-opt"     (R_req <= assumed_improvement: re-optimise the lepton search)
                             "needs new channel (photon)" (radiative & R_req above that: the soft-photon
                                                  channel is the lever, whose gain this metric does NOT
                                                  estimate -- that needs simulation; NOT "unreachable")
                             "out of reach"      (non-radiative & beyond the lepton re-opt gain)
This is NOT a detector simulation; the one assumption is `assumed_improvement` (the lepton re-opt gain).
"""
import numpy as np
import pandas as pd
from scipy.special import ndtri

df = pd.read_parquet(snakemake.input[0])                      # noqa: F821  (merged.parquet)
cfg = snakemake.config                                        # noqa: F821
scan = snakemake.wildcards.scan                               # noqa: F821
S = cfg["sensitivity"]
L0 = float(cfg["baseline_lumi_fb"])
L = float(cfg["target_lumi_fb"])
RIMP = float(S["assumed_improvement"])
proj = cfg["projectable_analyses"]

want = sorted(int(m["model"]) for m in S["models"] if m["scan"] == scan)
work = df[df["model_number"].isin(want)].copy()

# baseline = best current search's expected CLs (min over the 8 recastable searches, at L0)
expcls_cols = [f"{a}__ExpCLs" for a in proj if f"{a}__ExpCLs" in work.columns]
work["exp_min_now"] = work[expcls_cols].min(axis=1, skipna=True)


def mu95(e):
    """Expected 95% CL upper limit on signal strength from the expected CLs, via the
    asymptotic ExpCLs(mu)=2(1-Phi(mu/sigma)); mu95=1.96*sigma. ExpCLs=0.05 -> mu95=1."""
    e = float(min(max(e, 1e-6), 1 - 1e-9))
    denom = ndtri(1.0 - e / 2.0)                  # = mu/sigma at the nominal mu=1
    return float("inf") if denom <= 0 else 1.96 / denom


RADMIN = float(cfg["hole_radiative_min"])
work["dm_n2n1"] = work["m_n2"] - work["m_n1"]
work["dm_c1n1"] = work["m_c1"] - work["m_n1"]
work["mu95_baseline"] = work["exp_min_now"].map(mu95)            # best current search @ L0
work["mu95_target"] = work["mu95_baseline"] * np.sqrt(L0 / L)    # projected to target L (1/sqrt(L))
work["R_req"] = work["mu95_target"]                             # improvement needed over best current search
work["radiative"] = (work["br_n2_gamma"].fillna(0.0) >= RADMIN  # has the soft-photon handle?
                     if "br_n2_gamma" in work.columns else False)
work["reach_lumi_only"] = work["R_req"] <= 1.0                  # more luminosity alone suffices?
work["reach_reopt"] = work["R_req"] <= RIMP                    # re-optimising the LEPTON search suffices?


def verdict(r):
    if r["reach_lumi_only"]:
        return "luminosity"
    if r["reach_reopt"]:
        return "lepton re-opt"
    # beyond a lepton re-optimisation: a radiative model still has the (uncredited) photon channel
    return "needs new channel (photon)" if r["radiative"] else "out of reach"


work["verdict"] = work.apply(verdict, axis=1)
work["scan"] = scan

cols = ["scan", "model_number", "m_n1", "dm_n2n1", "dm_c1n1", "br_n2_gamma", "exp_min_now",
        "mu95_baseline", "mu95_target", "R_req", "radiative", "reach_lumi_only", "reach_reopt", "verdict"]
out = work[[c for c in cols if c in work.columns]].sort_values("model_number")

print(f"[{scan}] improvement over the best (lepton-channel) current search to exclude @ {L:.0f} fb-1 "
      f"(lepton re-opt gain assumed x{RIMP}):")
for _, r in out.iterrows():
    print(f"   model {int(r.model_number):>5}: exp_min_now={r.exp_min_now:.3f}  R_req={r.R_req:.1f}x  "
          f"-> {r.verdict}")
miss = sorted(set(want) - set(out["model_number"]))
if miss:
    print(f"[{scan}] WARNING: benchmark models not found in this scan: {miss}")

out.to_parquet(snakemake.output.sensitivity, index=False)     # noqa: F821
out.to_csv(snakemake.output.summary, index=False)             # noqa: F821
