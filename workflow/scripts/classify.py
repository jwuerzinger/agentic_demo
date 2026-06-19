"""Assign each model to a physics class describing the topology a Run-3 search
would target. Classes are priority-ordered and mutually exclusive, defined by
interpretable cuts on LSP nature, mass splittings, intermediate sleptons and
the chargino lifetime.

Classes
  LLP-disappearing-track   : (near-)degenerate chargino, long-lived
  slepton-multilepton      : a charged slepton sits in the cascade (tau-rich flagged)
  compressed-higgsino      : higgsino-like LSP, small dm(chi2,chi1)
  compressed-wino          : wino-like LSP, small dm, prompt
  WZ-onshell-multilepton   : dm(chi2,chi1) >= mZ, chi2 -> Z chi1
  Wh-1Lbb                  : dm(chi2,chi1) >= mh, chi2 -> h chi1
  WZ-offshell-soft         : few GeV < dm(chi2,chi1) < mZ
  heavy-other              : everything else (mostly just-beyond-reach high mass)
"""
import numpy as np
import pandas as pd

df = pd.read_parquet(snakemake.input[0])                      # noqa: F821
cfg = snakemake.config                                        # noqa: F821
scan = snakemake.wildcards.scan                               # noqa: F821

DM_C = float(cfg["compressed_dm_max_gev"])
CTAU = float(cfg["llp_ctau_min_mm"])
PUR = float(cfg["mixing_purity"])
MZ = float(cfg["mass_Z"])
MH = float(cfg["mass_h"])

# --- derived quantities -------------------------------------------------
df["dm_n2n1"] = df["m_n2"] - df["m_n1"]
df["dm_c1n1"] = df["m_c1"] - df["m_n1"]
df["dm_n3n1"] = df["m_n3"] - df["m_n1"]
# lighter produced electroweakino above the LSP (proxy for production cross-section)
df["m_light_ewk"] = df[["m_c1", "m_n2"]].min(axis=1)


def lsp_type(r):
    fb, fw, fh = r["f_bino"], r["f_wino"], r["f_higgsino"]
    top = max(fb, fw, fh)
    if top < PUR:
        return "mixed"
    return {fb: "bino", fw: "wino", fh: "higgsino"}[top]


df["lsp_type"] = df.apply(lsp_type, axis=1)

# slepton sitting between the LSP and the produced electroweakino
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

targets = df[df["is_target"]].copy()

# per-class counts among primary targets
counts = (targets.groupby("phys_class")
          .size().rename("n_target").reset_index()
          .sort_values("n_target", ascending=False))
counts["scan"] = scan

print(f"[{scan}] target classes:\n{counts.to_string(index=False)}")

df.to_parquet(snakemake.output.classified, index=False)       # noqa: F821
targets.to_parquet(snakemake.output.targets, index=False)     # noqa: F821
counts.to_csv(snakemake.output.summary, index=False)          # noqa: F821
