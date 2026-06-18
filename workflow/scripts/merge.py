"""Join the parsed SLHA features with the per-analysis exclusion CLs values.

The exclusion CSV has, for each analysis channel, columns
  <Analysis>__ExpCLs, <Analysis>__ObsCLs, <Analysis>__level
(observed-only channels have just __ObsCLs / __level). We keep the Exp/Obs
CLs columns for every analysis and merge on Model_number.
"""
import pandas as pd

feat = pd.read_parquet(snakemake.input.features)              # noqa: F821
csv = pd.read_csv(snakemake.input.csv)                        # noqa: F821

proj = snakemake.config["projectable_analyses"]               # noqa: F821
obs_only = snakemake.config["obs_only_analyses"]              # noqa: F821

keep = ["Model_number"]
for a in proj:
    keep += [f"{a}__ExpCLs", f"{a}__ObsCLs"]
for a in obs_only:
    keep += [f"{a}__ObsCLs"]
keep += ["Final__CLs", "Final__analysis",
         "Constraints__DM", "Constraints__EW", "Constraints__Flavour"]
keep = [c for c in keep if c in csv.columns]

merged = feat.merge(csv[keep], left_on="model_number",
                    right_on="Model_number", how="inner")
print(f"[{snakemake.wildcards.scan}] merged rows: {len(merged)} "      # noqa: F821
      f"(features {len(feat)}, csv {len(csv)})")
merged.to_parquet(snakemake.output[0], index=False)           # noqa: F821
