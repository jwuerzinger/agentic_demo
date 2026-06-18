"""Find coverage HOLES in the ATLAS programme: viable, light models that no search
even *expects* to constrain -- gaps that more luminosity cannot fix.

A model is a hole if it is, simultaneously:
  * not excluded now (observed),
  * viable: passes the required external constraints (EW, Flavour, ...),
  * copiously produced: min(m_chargino1, m_chi2) <= hole_mass_max_gev,
  * invisible to the programme: min expected CLs >= hole_expcls_min
    (so even the most sensitive search expects essentially no power).

For these the √L projection does NOT help (a CLs ~ 1 stays ~ 1), so we also report
`lumi_fixable` = whether the target-luminosity projection would reach it (almost
never, by construction). Holes are ranked by how light they are (severity).
"""
import pandas as pd

df = pd.read_parquet(snakemake.input[0])                      # noqa: F821
cfg = snakemake.config                                        # noqa: F821
scan = snakemake.wildcards.scan                               # noqa: F821

MMAX = float(cfg["hole_mass_max_gev"])
ECUT = float(cfg["hole_expcls_min"])

mask = (
    (~df["obs_excluded_now"])
    & df["pass_required"]
    & (df["m_light_ewk"] <= MMAX)
    & (df["exp_min_now"] >= ECUT)
)
holes = df[mask].copy()
holes["lumi_fixable"] = holes["proj_excluded"]      # would the target lumi reach it?
holes["scan"] = scan
holes = holes.sort_values("m_light_ewk")            # lightest = most egregious

# summary by physics class and LSP type
by_class = holes.groupby("phys_class").size().rename("n").reset_index()
by_lsp = holes.groupby("lsp_type").size().rename("n").reset_index()

print(f"[{scan}] HOLES: {len(holes)} "
      f"(m_light<= {MMAX:.0f} GeV, ExpCLs>= {ECUT}, constraint-passing)")
print(f"[{scan}]   lumi-fixable at target L: {int(holes.lumi_fixable.sum())} / {len(holes)}")
print(f"[{scan}]   also DM-allowed: {int((holes.pass_DM).sum())}")
if len(holes):
    print(f"[{scan}]   by LSP: {by_lsp.set_index('lsp_type')['n'].to_dict()}")
    print(f"[{scan}]   by class: {by_class.set_index('phys_class')['n'].to_dict()}")

holes.to_parquet(snakemake.output.holes, index=False)         # noqa: F821
by_class.assign(scan=scan).to_csv(snakemake.output.summary, index=False)  # noqa: F821
