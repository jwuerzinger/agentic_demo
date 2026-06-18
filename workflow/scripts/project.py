"""Project each analysis's expected exclusion to the Run-3 target luminosity and
flag the "currently-allowed-but-newly-reachable" target models.

Projection of the expected significance (per analysis a, per model):
    Z_exp     = Phi^-1(1 - ExpCLs)
    Z_exp(L)  = Z_exp * scale
    ExpCLs(L) = Phi(-Z_exp(L))
where `scale` depends on `config["projection"]`:
    sqrtL      : scale = sqrt(L/L0)                                  (statistics-limited)
    sqrtL_syst : scale = sqrt(L/L0) / sqrt(1 + f*(L/L0 - 1))         (saturates; conservative)

Status flags:
    obs_excluded_now : min observed CLs (channels per `obs_exclusion_channels`) < threshold
    exp_excluded_now : min expected CLs over projectable channels             < threshold
    proj_excluded    : min projected expected CLs over projectable channels   < threshold

External-constraint flags (ATLAS: 0 = excluded, 1 = not excluded) are turned into
pass_<name> booleans; pass_required = AND over config["require_constraints"].

Targets:
    is_target_collider = not obs-excl & not exp-excl & proj-excl     (collider only)
    is_target          = is_target_collider & pass_required          (default deliverable)
"""
import numpy as np
import pandas as pd
from scipy.special import ndtri, ndtr

df = pd.read_parquet(snakemake.input[0])                      # noqa: F821
cfg = snakemake.config                                        # noqa: F821
proj = cfg["projectable_analyses"]
obs_only = cfg["obs_only_analyses"]
thr = float(cfg["cls_threshold"])
L0 = float(cfg["baseline_lumi_fb"])
L = float(cfg["target_lumi_fb"])

# --- luminosity scale factor for the expected significance ---
ratio = L / L0
method = str(cfg.get("projection", "sqrtL"))
if method == "sqrtL":
    scale = np.sqrt(ratio)
elif method == "sqrtL_syst":
    f = float(cfg.get("systematics_fraction", 0.30))
    scale = np.sqrt(ratio) / np.sqrt(1.0 + f * (ratio - 1.0))
else:
    raise ValueError(f"unknown projection method: {method!r}")

EPS = 1e-6


def clip(s):
    return s.clip(lower=EPS, upper=1 - EPS)


# ---- observed exclusion (current) ----
which = str(cfg.get("obs_exclusion_channels", "all"))
obs_pool = proj + obs_only if which == "all" else proj
obs_cols = [f"{a}__ObsCLs" for a in obs_pool if f"{a}__ObsCLs" in df.columns]
df["obs_min_now"] = df[obs_cols].min(axis=1, skipna=True)

# ---- expected exclusion now & projected (projectable analyses) ----
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
df["proj_driver"] = df[exp_proj_cols].idxmin(axis=1).str.replace(
    "__ExpCLs_proj", "", regex=False)

# ---- status flags ----
df["obs_excluded_now"] = df["obs_min_now"] < thr
df["exp_excluded_now"] = df["exp_min_now"] < thr
df["proj_excluded"] = df["exp_min_proj"] < thr

# ---- external constraints (0 = excluded, 1 = not excluded) ----
for name in ["EW", "Flavour", "DM"]:
    col = f"Constraints__{name}"
    df[f"pass_{name}"] = (df[col] == 1) if col in df.columns else True
required = cfg.get("require_constraints", []) or []
pass_required = np.logical_and.reduce(
    [df[f"pass_{n}"].to_numpy() for n in required]) if required else np.ones(len(df), bool)
df["pass_required"] = pass_required

# ---- targets ----
df["is_target_collider"] = (~df["obs_excluded_now"]) & (~df["exp_excluded_now"]) & df["proj_excluded"]
df["is_target"] = df["is_target_collider"] & df["pass_required"]
df["is_target_weak"] = (~df["obs_excluded_now"]) & df["proj_excluded"] & df["pass_required"]

scan = snakemake.wildcards.scan                               # noqa: F821
print(f"[{scan}] projection={method} scale={scale:.3f}  total={len(df)}  "
      f"obs_excluded={int(df.obs_excluded_now.sum())}")
print(f"[{scan}] targets: collider-only={int(df.is_target_collider.sum())}  "
      f"+{'+'.join(required) or 'none'}={int(df.is_target.sum())}  "
      f"+DM={int((df.is_target_collider & df.pass_required & df.pass_DM).sum())}")

df.to_parquet(snakemake.output[0], index=False)               # noqa: F821
