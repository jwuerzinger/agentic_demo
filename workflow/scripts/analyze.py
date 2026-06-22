"""Per-scan analysis: project -> classify -> find holes, in one pass over merged.parquet.

This single rule replaces the former project / classify / holes rules (all fast, all
config-triggered, a strict linear chain). It threads one dataframe through three stages and
emits the same artifacts (classified / targets / class_counts / holes / holes_counts), so the
downstream rules and the inspectable parquets are unchanged. (`projected.parquet` is gone:
`classified.parquet` is a superset, so plots/report read that instead.)

  1. PROJECT  -- luminosity scaling + reach taxonomy (targets, R_req, reach_tier).
  2. CLASSIFY -- interpretable physics classes (LSP nature, splittings, sleptons, chargino ctau).
  3. HOLES    -- the new-strategy coverage gaps that need a genuinely different search.

`sensitivity` stays a SEPARATE rule on purpose: it is the independent hand-picked-benchmark
study and branches off merged.parquet, not off this analysis.

--- sqrt-L projection CAVEAT (stage 1) ---
The expected-significance scaling Z(L)=Z*sqrt(L/L0) is only valid near the exclusion boundary
(ExpCLs <~ 0.5). Far from reach (ExpCLs > 0.5) it is unphysical (claims sensitivity degrades
with L); that regime is the holes, whose `exp_min_proj` is therefore not meaningful -- but the
reach tier / R_req use the correct signal-strength scaling (mu95 ~ 1/sqrt(L)), so the
hole/target split is robust. Targets sit near the boundary where the heuristic is fine.
"""
import numpy as np
import pandas as pd
from scipy.special import ndtri, ndtr

df = pd.read_parquet(snakemake.input[0])                      # noqa: F821  (merged.parquet)
cfg = snakemake.config                                        # noqa: F821
scan = snakemake.wildcards.scan                               # noqa: F821

# =====================================================================
# 1. PROJECT -- exclusion now, sqrt-L projection, R_req / reach tier, targets
# =====================================================================
proj = cfg["projectable_analyses"]
obs_only = cfg["obs_only_analyses"]
thr = float(cfg["cls_threshold"])
L0 = float(cfg["baseline_lumi_fb"])
L = float(cfg["target_lumi_fb"])

ratio = L / L0
method = str(cfg.get("projection", "sqrtL"))
if method == "sqrtL":
    scale = np.sqrt(ratio)
elif method == "sqrtL_syst":
    fsyst = float(cfg.get("systematics_fraction", 0.30))
    scale = np.sqrt(ratio) / np.sqrt(1.0 + fsyst * (ratio - 1.0))
else:
    raise ValueError(f"unknown projection method: {method!r}")

EPS = 1e-6


def clip(s):
    return s.clip(lower=EPS, upper=1 - EPS)


# observed exclusion (current)
which = str(cfg.get("obs_exclusion_channels", "all"))
obs_pool = proj + obs_only if which == "all" else proj
obs_cols = [f"{a}__ObsCLs" for a in obs_pool if f"{a}__ObsCLs" in df.columns]
df["obs_min_now"] = df[obs_cols].min(axis=1, skipna=True)

# expected exclusion now & projected (projectable analyses)
exp_now_cols, exp_proj_cols = [], []
for a in proj:
    c = f"{a}__ExpCLs"
    if c not in df.columns:
        continue
    z = ndtri(1.0 - clip(df[c]))
    df[f"{a}__ExpCLs_proj"] = ndtr(-(z * scale))
    exp_now_cols.append(c)
    exp_proj_cols.append(f"{a}__ExpCLs_proj")

df["exp_min_now"] = df[exp_now_cols].min(axis=1, skipna=True)
df["exp_min_proj"] = df[exp_proj_cols].min(axis=1, skipna=True)
df["proj_driver"] = df[exp_proj_cols].idxmin(axis=1).str.replace("__ExpCLs_proj", "", regex=False)

# physically-correct reach: expected limit on signal strength, mu95 ~ 1/sqrt(L)
_e = df["exp_min_now"].to_numpy().clip(1e-6, 1 - 1e-9)
_denom = ndtri(1.0 - _e / 2.0)
df["mu95_baseline"] = np.where(_denom > 0, 1.96 / _denom, np.inf)   # best current search @ L0
df["R_req"] = df["mu95_baseline"] * np.sqrt(L0 / L)                 # improvement needed @ target L

df["obs_excluded_now"] = df["obs_min_now"] < thr
df["exp_excluded_now"] = df["exp_min_now"] < thr
df["proj_excluded"] = df["exp_min_proj"] < thr

# external constraints (ATLAS: 0 = excluded, 1 = not excluded)
for name in ["EW", "Flavour", "DM"]:
    col = f"Constraints__{name}"
    df[f"pass_{name}"] = (df[col] == 1) if col in df.columns else True
required = cfg.get("require_constraints", []) or []
pass_required = np.logical_and.reduce(
    [df[f"pass_{n}"].to_numpy() for n in required]) if required else np.ones(len(df), bool)
df["pass_required"] = pass_required

# targets
df["is_target_collider"] = (~df["obs_excluded_now"]) & (~df["exp_excluded_now"]) & df["proj_excluded"]
df["is_target"] = df["is_target_collider"] & df["pass_required"]
df["is_target_weak"] = (~df["obs_excluded_now"]) & df["proj_excluded"] & df["pass_required"]

# search-strategy reach tier: lumi (R_req<=1) -> reoptimise (<=reopt_factor) -> new-strategy
# (>reopt_factor AND a signature no included search uses: radiative chi2->chi1 gamma / tau-rich)
# -> out-of-reach.
REOPT = float(cfg["reopt_factor"])
rad = df.get("br_n2_gamma", pd.Series(0.0, index=df.index)).fillna(0.0) >= float(cfg["hole_radiative_min"])
tau = df.get("br_c1_tau", pd.Series(0.0, index=df.index)).fillna(0.0) >= float(cfg["hole_tau_min"])
df["signature_uncovered"] = rad | tau
df["alt_strategy"] = np.where(rad, "radiative-γ + ISR-jet", np.where(tau, "soft-τ + ISR-jet", ""))
df["reach_tier"] = np.select(
    [df["obs_excluded_now"] | ~df["pass_required"],
     df["R_req"] <= 1.0,
     df["R_req"] <= REOPT,
     df["signature_uncovered"]],
    ["excluded/non-viable", "lumi", "reoptimise", "new-strategy"],
    default="out-of-reach")

print(f"[{scan}] projection={method} scale={scale:.3f}  total={len(df)}  "
      f"obs_excluded={int(df.obs_excluded_now.sum())}  targets={int(df.is_target.sum())}")

# =====================================================================
# 2. CLASSIFY -- interpretable physics classes (priority-ordered, mutually exclusive)
# =====================================================================
DM_C = float(cfg["compressed_dm_max_gev"])
CTAU = float(cfg["llp_ctau_min_mm"])
PUR = float(cfg["mixing_purity"])
MZ = float(cfg["mass_Z"])
MH = float(cfg["mass_h"])

df["dm_n2n1"] = df["m_n2"] - df["m_n1"]
df["dm_c1n1"] = df["m_c1"] - df["m_n1"]
df["dm_n3n1"] = df["m_n3"] - df["m_n1"]
df["m_light_ewk"] = df[["m_c1", "m_n2"]].min(axis=1)   # lighter produced EW-ino (xsec proxy)


def lsp_type(r):
    fb, fw, fh = r["f_bino"], r["f_wino"], r["f_higgsino"]
    top = max(fb, fw, fh)
    if top < PUR:
        return "mixed"
    return {fb: "bino", fw: "wino", fh: "higgsino"}[top]


df["lsp_type"] = df.apply(lsp_type, axis=1)

prod = np.maximum(df["m_c1"], df["m_n2"])
df["slepton_in_cascade"] = (df["m_slep_light"] > df["m_n1"] + 0.1) & (df["m_slep_light"] < prod)


def assign(r):
    # 1) long-lived chargino -> disappearing track
    if (r["ctau_c1_mm"] >= CTAU) or (0 <= r["dm_c1n1"] < 0.3):
        return "LLP-disappearing-track"
    # 2) slepton in the decay chain
    if r["slepton_in_cascade"]:
        return "slepton-multilepton-stau" if r["light_slep_is_stau"] else "slepton-multilepton"
    dm = r["dm_n2n1"]
    # 3) compressed spectra
    if 0 <= dm < DM_C:
        if r["lsp_type"] == "higgsino":
            return "compressed-higgsino"
        if r["lsp_type"] == "wino":
            return "compressed-wino"
        return "compressed-mixed"
    # 4) on-shell decays of chi2 (summed BRs: Wh when h dominates over Z, else default to WZ)
    if dm >= MH and r.get("br_n2_h", 0.0) > r.get("br_n2_Z", 0.0):
        return "Wh-1Lbb"
    if dm >= MZ:
        return "WZ-onshell-multilepton"
    # 5) off-shell / moderately compressed
    if DM_C <= dm < MZ:
        return "WZ-offshell-soft"
    return "heavy-other"


df["phys_class"] = df.apply(assign, axis=1)

# =====================================================================
# 3. HOLES -- new-strategy gaps, produced enough, not already covered by a dedicated search
# =====================================================================
NMIN = float(cfg["hole_min_run3_events"])
EXCLUDE = set(cfg.get("hole_exclude_classes", []) or [])
XS = cfg["xsec_13tev_fb"]


def xsec_fb(mass, mode):
    pts = XS["wino" if mode == "wino" else "higgsino"]        # bino/mixed -> higgsino (conservative)
    return float(np.exp(np.interp(np.log(max(mass, 1.0)),
                                  np.log([m for m, _ in pts]), np.log([s for _, s in pts]))))


df["xsec_fb"] = [xsec_fb(m, l) for m, l in zip(df["m_light_ewk"], df["lsp_type"])]
df["n_run3"] = df["xsec_fb"] * L

hole_mask = (
    (df["reach_tier"] == "new-strategy")
    & (df["n_run3"] >= NMIN)
    & (~df["phys_class"].isin(EXCLUDE))
)
holes = df[hole_mask].copy().sort_values("m_light_ewk")
holes["scan"] = scan

# =====================================================================
# outputs
# =====================================================================
targets = df[df["is_target"]].copy()
counts = (targets.groupby("phys_class").size().rename("n_target").reset_index()
          .sort_values("n_target", ascending=False))
counts["scan"] = scan
by_strategy = holes.groupby("alt_strategy").size().rename("n").reset_index().assign(scan=scan)

print(f"[{scan}] target classes: {counts.set_index('phys_class')['n_target'].to_dict()}")
print(f"[{scan}] HOLES (new-strategy, produced enough, not a covered class): {len(holes)}")
if len(holes):
    print(f"[{scan}]   alt strategies: {holes.alt_strategy.value_counts().to_dict()}")
    print(f"[{scan}]   m_light range : {holes.m_light_ewk.min():.0f}-{holes.m_light_ewk.max():.0f} GeV; "
          f"R_req {holes.R_req.min():.1f}-{holes.R_req.max():.1f}")

df.to_parquet(snakemake.output.classified, index=False)         # noqa: F821
targets.to_parquet(snakemake.output.targets, index=False)       # noqa: F821
counts.to_csv(snakemake.output.counts, index=False)             # noqa: F821
holes.to_parquet(snakemake.output.holes, index=False)           # noqa: F821
by_strategy.to_csv(snakemake.output.holes_counts, index=False)  # noqa: F821
