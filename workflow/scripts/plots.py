"""Mass-plane diagnostic plots for one scan: where do the Run-3 target models and
the coverage holes sit relative to the excluded / allowed populations?
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

df = pd.read_parquet(snakemake.input[0])                      # noqa: F821
scan = snakemake.wildcards.scan                               # noqa: F821
cfg = snakemake.config                                        # noqa: F821
L = float(cfg["target_lumi_fb"])

df["dm_n2n1"] = df["m_n2"] - df["m_n1"]
df["m_light_ewk"] = df[["m_c1", "m_n2"]].min(axis=1)

# coverage holes (same definition as holes.py), computed inline for the overlay
hole_mask = (
    (~df["obs_excluded_now"]) & df["pass_required"]
    & (df["m_light_ewk"] <= float(cfg["hole_mass_max_gev"]))
    & (df["exp_min_now"] >= float(cfg["hole_expcls_min"]))
)

excluded = df[df["obs_excluded_now"]]
target = df[df["is_target"]]
holes = df[hole_mask]
allowed = df[~df["obs_excluded_now"] & ~df["is_target"] & ~hole_mask]

fig, axes = plt.subplots(1, 2, figsize=(13, 5.3))
for ax, (yx, ylab) in zip(axes, [("m_n2", r"$m_{\chi^0_2}$ [GeV]"),
                                 ("dm_n2n1", r"$\Delta m(\chi^0_2,\chi^0_1)$ [GeV]")]):
    ax.scatter(excluded["m_n1"], excluded[yx], s=6, c="0.78",
               label=f"excluded now ({len(excluded)})", rasterized=True)
    ax.scatter(allowed["m_n1"], allowed[yx], s=6, c="#4C72B0", alpha=0.45,
               label=f"allowed ({len(allowed)})", rasterized=True)
    ax.scatter(target["m_n1"], target[yx], s=14, c="#C44E52",
               label=f"Run-3 target ({len(target)})", rasterized=True)
    ax.scatter(holes["m_n1"], holes[yx], s=20, marker="x", c="#000000", linewidths=0.8,
               label=f"coverage hole ({len(holes)})", rasterized=True)
    ax.set_xlabel(r"$m_{\chi^0_1}$ [GeV]")
    ax.set_ylabel(ylab)

axes[1].set_yscale("symlog", linthresh=10)
axes[0].legend(loc="upper left", fontsize=8, framealpha=0.9)
fig.suptitle(f"{scan} — Run-3 targets & coverage holes (proj. to {L:.0f} fb$^{{-1}}$)", fontsize=12)
fig.tight_layout()
fig.savefig(snakemake.output[0], dpi=130)                     # noqa: F821
print(f"[{scan}] wrote {snakemake.output[0]}: "
      f"{len(target)} targets, {len(holes)} holes")