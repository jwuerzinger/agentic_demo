"""Assert the pipeline's invariants so a re-run catches regressions automatically.
Writes results/validation.txt and fails the build (raises) if any check fails.
"""
import pandas as pd

cfg = snakemake.config                                        # noqa: F821
thr = float(cfg["cls_threshold"])
checks, failures = [], []


def check(name, ok, detail=""):
    checks.append((name, bool(ok), detail))
    if not ok:
        failures.append(f"{name}: {detail}")


for clf_path, tgt_path, hole_path in zip(
        snakemake.input.classified, snakemake.input.targets, snakemake.input.holes):  # noqa: F821
    scan = clf_path.split("/")[-2]
    d = pd.read_parquet(clf_path)
    t = pd.read_parquet(tgt_path)
    h = pd.read_parquet(hole_path)

    # the targets file is exactly the is_target subset of the classified table
    check(f"{scan}: targets == is_target subset of classified",
          len(t) == int(d["is_target"].sum()),
          f"targets={len(t)} vs is_target={int(d['is_target'].sum())}")
    # target definition holds exactly
    check(f"{scan}: targets are observed-allowed",
          (~t["obs_excluded_now"]).all(), f"{int(t['obs_excluded_now'].sum())} excluded leaked in")
    check(f"{scan}: targets are expected-allowed-now",
          (~t["exp_excluded_now"]).all(), f"{int(t['exp_excluded_now'].sum())} exp-excluded leaked in")
    check(f"{scan}: targets are projected-excluded",
          (t["exp_min_proj"] < thr).all(),
          f"max proj={t['exp_min_proj'].max() if len(t) else float('nan'):.4f}")
    check(f"{scan}: targets pass required constraints",
          bool(t["pass_required"].all()) if len(t) else True, "constraint leak")
    # physical sanity
    check(f"{scan}: no negative dm(n2,n1)", (d["dm_n2n1"] >= -1e-6).all(),
          f"{int((d['dm_n2n1'] < -1e-6).sum())} negative")
    check(f"{scan}: LSP is the lightest sparticle",
          (d[["m_c1", "m_slep_light"]].min(axis=1) >= d["m_n1"] - 1e-6).all(),
          "found lighter sparticle than chi10")
    frac = d[["f_bino", "f_wino", "f_higgsino"]]
    check(f"{scan}: composition fractions in [0,1]",
          bool(((frac >= -1e-6) & (frac <= 1 + 1e-6)).all().all()), "")
    # holes: by construction must be light and insensitive
    if len(h):
        check(f"{scan}: holes are insensitive", (h["exp_min_now"] >= float(cfg["hole_expcls_min"])).all(), "")
        check(f"{scan}: holes are light", (h["m_light_ewk"] <= float(cfg["hole_mass_max_gev"])).all(), "")

lines = [("PASS" if ok else "FAIL") + f"  {name}" + (f"  -- {d}" if d and not ok else "")
         for name, ok, d in checks]
report = f"{sum(ok for _, ok, _ in checks)}/{len(checks)} checks passed\n\n" + "\n".join(lines) + "\n"
with open(snakemake.output[0], "w") as fh:                    # noqa: F821
    fh.write(report)
print(report)

if failures:
    raise AssertionError(f"{len(failures)} validation check(s) failed:\n" + "\n".join(failures))
