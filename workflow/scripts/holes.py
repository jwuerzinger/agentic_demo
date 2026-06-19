"""Find coverage HOLES: viable, currently-invisible models that a *dedicated* Run-3
search COULD reach, but for which no existing search even expects sensitivity.

A model is a hole if, simultaneously:
  * not excluded now (observed);
  * viable: passes the required external constraints (EW, Flavour, DM);
  * invisible to the programme: min expected CLs over the 8 recastable searches
    >= hole_expcls_min (even the most sensitive expects ~no power);
  * reachable in principle: enough EW-ino signal is produced at the target
    luminosity that a dedicated search could plausibly exploit it,
    N = sigma(m, mode) * target_lumi  >=  hole_min_run3_events;
  * not in `hole_exclude_classes` -- e.g. the disappearing-track signature, which
    already has a dedicated (observed-only) ATLAS search, so it is not a gap that
    needs a *new* search.

The reachability gate replaces a flat mass cap: because winos have a ~3x larger
production cross-section than higgsinos, they count as reachable out to higher
mass at the same event threshold.

`lumi_fixable` records whether the plain sqrt-L projection of the *existing* searches
would reach it (essentially never, by construction -- that is the point of a hole).
"""
import numpy as np
import pandas as pd

df = pd.read_parquet(snakemake.input[0])                      # noqa: F821
cfg = snakemake.config                                        # noqa: F821
scan = snakemake.wildcards.scan                               # noqa: F821

ECUT = float(cfg["hole_expcls_min"])
NMIN = float(cfg["hole_min_run3_events"])
LUMI = float(cfg["target_lumi_fb"])
EXCLUDE = set(cfg.get("hole_exclude_classes", []) or [])

# Approximate 13 TeV EW-ino cross-sections live in config (shared with sensitivity.py).
# Used here ONLY as a reachability gate -- not for limit setting. mass [GeV] -> sigma [fb].
_XS = cfg["xsec_13tev_fb"]


def xsec_fb(mass, mode):
    pts = _XS["wino" if mode == "wino" else "higgsino"]   # bino/mixed -> higgsino (conservative)
    xm = np.log([m for m, _ in pts])
    ys = np.log([s for _, s in pts])
    return float(np.exp(np.interp(np.log(max(mass, 1.0)), xm, ys)))


df["xsec_fb"] = [xsec_fb(m, l) for m, l in zip(df["m_light_ewk"], df["lsp_type"])]
df["n_run3"] = df["xsec_fb"] * LUMI

mask = (
    (~df["obs_excluded_now"])
    & df["pass_required"]
    & (df["exp_min_now"] >= ECUT)
    & (df["n_run3"] >= NMIN)
    & (~df["phys_class"].isin(EXCLUDE))
)
holes = df[mask].copy()
holes["lumi_fixable"] = holes["proj_excluded"]
holes["scan"] = scan
holes = holes.sort_values("m_light_ewk")

by_class = holes.groupby("phys_class").size().rename("n").reset_index()
by_lsp = holes.groupby("lsp_type").size().rename("n").reset_index()

print(f"[{scan}] HOLES: {len(holes)} (ExpCLs>= {ECUT}, N_run3>= {NMIN:.0f} @ {LUMI:.0f} fb-1, "
      f"viable, excl {sorted(EXCLUDE)})")
print(f"[{scan}]   lumi-fixable: {int(holes.lumi_fixable.sum())}/{len(holes)}   "
      f"DM-allowed: {int(holes.pass_DM.sum())}/{len(holes)}")
if len(holes):
    print(f"[{scan}]   m_light range: {holes.m_light_ewk.min():.0f}-{holes.m_light_ewk.max():.0f} GeV")
    print(f"[{scan}]   by LSP: {by_lsp.set_index('lsp_type')['n'].to_dict()}")
    print(f"[{scan}]   by class: {by_class.set_index('phys_class')['n'].to_dict()}")

holes.to_parquet(snakemake.output.holes, index=False)         # noqa: F821
by_class.assign(scan=scan).to_csv(snakemake.output.summary, index=False)  # noqa: F821
