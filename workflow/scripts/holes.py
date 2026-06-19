"""Coverage HOLES = genuinely NEW-search targets: viable, currently-allowed models that
need a *significantly different* analysis strategy than the searches in the pMSSM scan.

A model is a hole if (all of):
  * it is in the `new-strategy` reach tier (set in classify.py): R_req over the best current
    search exceeds `reopt_factor` (so re-optimising an included search will not reach it) AND
    its dominant decay signature is one no included search exploits (radiative chi2->chi1 gamma
    -> soft photon; tau-rich -> tau);
  * it is produced enough at the target luminosity for a dedicated search to have a chance:
    N = sigma(m_light, mode) * target_lumi >= hole_min_run3_events;
  * its class is not already covered by an included dedicated search (`hole_exclude_classes`,
    e.g. the disappearing-track signature).

(Viability and "not currently excluded" are already folded into the reach tier.) Each hole
carries the `alt_strategy` its signature points to. Holes are ranked by how light they are.
"""
import numpy as np
import pandas as pd

df = pd.read_parquet(snakemake.input[0])                      # noqa: F821
cfg = snakemake.config                                        # noqa: F821
scan = snakemake.wildcards.scan                               # noqa: F821

NMIN = float(cfg["hole_min_run3_events"])
L = float(cfg["target_lumi_fb"])
EXCLUDE = set(cfg.get("hole_exclude_classes", []) or [])
XS = cfg["xsec_13tev_fb"]


def xsec_fb(mass, mode):
    pts = XS["wino" if mode == "wino" else "higgsino"]        # bino/mixed -> higgsino (conservative)
    return float(np.exp(np.interp(np.log(max(mass, 1.0)),
                                  np.log([m for m, _ in pts]), np.log([s for _, s in pts]))))


df["xsec_fb"] = [xsec_fb(m, l) for m, l in zip(df["m_light_ewk"], df["lsp_type"])]
df["n_run3"] = df["xsec_fb"] * L

mask = (
    (df["reach_tier"] == "new-strategy")
    & (df["n_run3"] >= NMIN)
    & (~df["phys_class"].isin(EXCLUDE))
)
holes = df[mask].copy().sort_values("m_light_ewk")
holes["scan"] = scan

by_strategy = holes.groupby("alt_strategy").size().rename("n").reset_index()

print(f"[{scan}] HOLES (new-strategy, produced enough, not a covered class): {len(holes)}")
if len(holes):
    print(f"[{scan}]   alt strategies: {holes.alt_strategy.value_counts().to_dict()}")
    print(f"[{scan}]   by phys_class : {holes.phys_class.value_counts().to_dict()}")
    print(f"[{scan}]   m_light range : {holes.m_light_ewk.min():.0f}-{holes.m_light_ewk.max():.0f} GeV; "
          f"R_req {holes.R_req.min():.1f}-{holes.R_req.max():.1f}")

holes.to_parquet(snakemake.output.holes, index=False)         # noqa: F821
by_strategy.assign(scan=scan).to_csv(snakemake.output.summary, index=False)  # noqa: F821
