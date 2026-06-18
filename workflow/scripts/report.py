"""Assemble the final study report: enumerate the Run-3 target classes with
physics descriptions, per-scan counts, suggested searches, and representative
benchmark models. Writes results/report.md and results/class_summary.csv.
"""
import os
import pandas as pd

cfg = snakemake.config                                        # noqa: F821
L = float(cfg["target_lumi_fb"])
L0 = float(cfg["baseline_lumi_fb"])

# Human-facing metadata per class: (title, physics, signature, suggested Run-3 search)
CLASS_META = {
    "WZ-onshell-multilepton": (
        "On-shell WZ multilepton",
        "Bino-like LSP with heavier wino/higgsino chi2/chi1+ split by more than m_Z, "
        "so chi2 -> Z chi1 and chi1+ -> W chi1 are on-shell.",
        "2 or 3 leptons + missing energy (WZ topology); the flagship EWKino final state.",
        "Extend the 2L0J / 3L on-shell search to the full Run-3 dataset (higher mass reach)."),
    "Wh-1Lbb": (
        "On-shell Wh (1 lepton + bb)",
        "Bino-like LSP, chi2 -> h chi1 with the Higgs reconstructed via h -> bb, "
        "chi1+ -> W chi1.",
        "1 lepton + bb + missing energy.",
        "Extend the 1Lbb search; statistics-limited, gains directly with luminosity."),
    "WZ-offshell-soft": (
        "Off-shell WZ / moderately compressed",
        "Bino/higgsino mix with a few GeV < dm(chi2,chi1) < m_Z, giving off-shell W*/Z* "
        "and soft leptons.",
        "Soft (low-pT) di/tri-leptons + ISR jet + missing energy.",
        "Extend the 3L-offshell / compressed soft-lepton search; key compressed gap."),
    "compressed-higgsino": (
        "Compressed higgsino",
        "Higgsino-like LSP (small |mu|), nearly degenerate chi1+/chi2/chi3, "
        "dm(chi2,chi1) of order a few-to-tens of GeV. Natural-SUSY / higgsino-DM target.",
        "Soft dileptons + ISR (mono-jet-like) + missing energy.",
        "Dedicated compressed-higgsino soft-lepton + mono-jet search."),
    "compressed-wino": (
        "Compressed wino (prompt)",
        "Wino-like LSP with small splitting but prompt chargino decay.",
        "Soft leptons / mono-X + missing energy.",
        "Compressed soft-lepton + mono-jet search."),
    "compressed-mixed": (
        "Compressed mixed-state",
        "Mixed-composition LSP with a compressed spectrum, dm(chi2,chi1) < threshold.",
        "Soft leptons + ISR + missing energy.",
        "Compressed soft-lepton search."),
    "LLP-disappearing-track": (
        "Long-lived chargino (disappearing track)",
        "Wino/higgsino-like states with a tiny chargino-neutralino splitting, so the "
        "chargino is long-lived and leaves a short, disappearing track.",
        "Disappearing track + ISR + missing energy.",
        "Extend the disappearing-track search; reach grows with luminosity & detector use."),
    "slepton-multilepton": (
        "Slepton-mediated multilepton",
        "A charged slepton lies between the LSP and the produced electroweakino, so "
        "cascades pass through real sleptons, enhancing the lepton yield.",
        "2-3 light leptons (e/mu) + missing energy, often harder spectra.",
        "Slepton-mediated 2L/3L search."),
    "slepton-multilepton-stau": (
        "Stau-enriched (tau-rich) cascades",
        "The lightest slepton in the cascade is a stau, so final states are tau-rich -- "
        "a known coverage gap.",
        "Hadronic/leptonic taus + missing energy.",
        "Dedicated tau-rich electroweakino search (a genuine Run-3 gap)."),
    "heavy-other": (
        "Heavy / just-beyond-reach",
        "Higher-mass electroweakinos not otherwise categorised; current data lacks the "
        "luminosity but the projection says Run-3 expects sensitivity.",
        "Mixed final states depending on the dominant decay.",
        "Full-dataset reinterpretation of the relevant inclusive search."),
}

BENCH_COLS = ["scan", "model_number", "m_n1", "m_n2", "m_c1", "dm_n2n1",
              "lsp_type", "ctau_c1_mm", "proj_driver", "exp_min_now", "exp_min_proj"]


def scan_of(path):
    return os.path.basename(os.path.dirname(path))


# ---- load everything ----
proj = {scan_of(p): pd.read_parquet(p) for p in snakemake.input.projected}   # noqa: F821
tgts = {scan_of(p): pd.read_parquet(p) for p in snakemake.input.targets}     # noqa: F821
holes = {scan_of(p): pd.read_parquet(p) for p in snakemake.input.holes}      # noqa: F821
plots = {scan_of(p): p for p in snakemake.input.plots}                       # noqa: F821

REQ = "+".join(cfg.get("require_constraints", []) or ["none"])

all_t = pd.concat(tgts.values(), ignore_index=True) if tgts else pd.DataFrame()

# ---- class x scan summary table ----
summary = (all_t.groupby(["phys_class", "scan"]).size()
           .unstack(fill_value=0) if len(all_t) else pd.DataFrame())
if len(summary):
    summary["total"] = summary.sum(axis=1)
    summary = summary.sort_values("total", ascending=False)
summary.to_csv(snakemake.output.class_summary)               # noqa: F821

# ---- build markdown ----
md = []
md.append("# Run-3 EWK SUSY search targets from the ATLAS pMSSM scan\n")
md.append(f"_Data: ATLAS pMSSM electroweak scan, arXiv:2402.01392. "
          f"Projection: `{cfg.get('projection', 'sqrtL')}` scaling of expected significance from "
          f"{L0:.0f} fb$^{{-1}}$ to **{L:.0f} fb$^{{-1}}$** (Run 2+3 combined). "
          f"CLs exclusion threshold {cfg['cls_threshold']}. "
          f"External constraints required to pass: **{REQ}** "
          f"(ATLAS flags, 0 = excluded; DM left optional as cosmology-dependent)._\n")

md.append("## Definition of a target\n")
md.append("A model is a **Run-3 target** if it is:\n\n"
          "1. **not excluded now** (observed): min over all channels of `ObsCLs` >= 0.05;\n"
          "2. **not even expected to be excluded now**: min over the 8 recastable searches "
          "of `ExpCLs` >= 0.05;\n"
          "3. **expected to be reached at the target luminosity**: projected min `ExpCLs` < 0.05.\n\n"
          "This isolates parameter space that today's searches genuinely do not reach, "
          "but where Run-3 statistics are expected to gain sensitivity.\n")

md.append("## Headline numbers\n")
md.append("Target counts at three levels of external-constraint stringency. Applying the "
          "external constraints matters a lot — the collider-only count is dominated by models "
          "that other measurements already disfavour.\n")
md.append(f"| Scan | Total | Excluded now | Collider-only targets | + {REQ} (reported) | + DM too |")
md.append("|---|---:|---:|---:|---:|---:|")
for scan, d in proj.items():
    n_coll = int(d.is_target_collider.sum())
    n_req = int(d.is_target.sum())
    n_dm = int((d.is_target_collider & d.pass_required & d.pass_DM).sum())
    md.append(f"| {scan} | {len(d)} | {int(d.obs_excluded_now.sum())} | "
              f"{n_coll} | {n_req} | {n_dm} |")
md.append("\n_\"+ DM too\" additionally requires the dark-matter constraint (relic density + direct "
          "detection) to pass; it is the most model-dependent and shrinks the set the most._\n")

# ---- class x scan table ----
md.append("## Target classes (class x scan)\n")
if len(summary):
    cols = list(summary.columns)
    md.append("| Class | " + " | ".join(cols) + " |")
    md.append("|---" * (len(cols) + 1) + "|")
    for cls, row in summary.iterrows():
        md.append(f"| `{cls}` | " + " | ".join(str(int(row[c])) for c in cols) + " |")
md.append("")

# ---- per-class detail with benchmarks ----
ordered = list(summary.index) if len(summary) else []
md.append(f"## The classes ({len(ordered)} populated)\n")
md.append("Each class below is an interesting target for a (dedicated or extended) "
          "Run-3 search: currently allowed, but projected to be reachable.\n")

for i, cls in enumerate(ordered, 1):
    title, physics, sig, search = CLASS_META.get(
        cls, (cls, "(uncategorised)", "(varies)", "(reinterpretation)"))
    sub = all_t[all_t["phys_class"] == cls].copy()
    md.append(f"### {i}. {title}  &nbsp; `({cls})`\n")
    md.append(f"- **Models flagged:** {len(sub)} "
              f"({', '.join(f'{s}: {int((sub.scan==s).sum())}' for s in proj)})")
    md.append(f"- **Physics:** {physics}")
    md.append(f"- **Signature:** {sig}")
    md.append(f"- **Suggested Run-3 search:** {search}")
    # benchmarks: most decisively reachable (smallest projected ExpCLs)
    bench = sub.sort_values("exp_min_proj").head(2)
    cols = [c for c in BENCH_COLS if c in bench.columns]
    md.append("\n  Representative benchmarks (most decisively reachable):\n")
    md.append("  | " + " | ".join(cols) + " |")
    md.append("  |" + "---|" * len(cols))
    for _, r in bench.iterrows():
        vals = []
        for c in cols:
            v = r[c]
            if isinstance(v, float):
                vals.append(f"{v:.3g}")
            else:
                vals.append(str(v))
        md.append("  | " + " | ".join(vals) + " |")
    md.append("")

# ---- designed-but-empty classes ----
empty = [c for c in CLASS_META if c not in set(ordered)]
if empty:
    md.append("### Designed classes with no targets\n")
    md.append("The taxonomy also defines these classes, which are **unpopulated** in these scans "
              "(e.g. sleptons are decoupled at ~10 TeV, so slepton-mediated cascades cannot occur): "
              + ", ".join(f"`{c}`" for c in empty) + ".\n")

# ---- coverage holes -------------------------------------------------
all_h = pd.concat(holes.values(), ignore_index=True) if holes else pd.DataFrame()
md.append("## Coverage holes — gaps that need fixing ASAP\n")
md.append(f"A **hole** is a model that is _viable_ (passes {REQ}), _light_ "
          f"(min(m_χ₁±, m_χ₂⁰) ≤ {cfg['hole_mass_max_gev']:.0f} GeV, so copiously produced) "
          f"yet _invisible_ to the whole programme (min expected CLs ≥ {cfg['hole_expcls_min']}). "
          "Because there is essentially **no** expected sensitivity, the √L projection does not help "
          "— these need a **new or re-optimised search**, not just more luminosity.\n")
if len(all_h):
    md.append("| Scan | Holes | Lumi-fixable @ target L | also DM-allowed | dominant LSP | dominant class |")
    md.append("|---|---:|---:|---:|---|---|")
    for scan, h in holes.items():
        if not len(h):
            md.append(f"| {scan} | 0 | – | – | – | – |")
            continue
        dom_lsp = h.lsp_type.value_counts().idxmax()
        dom_cls = h.phys_class.value_counts().idxmax()
        md.append(f"| {scan} | {len(h)} | {int(h.lumi_fixable.sum())} | {int(h.pass_DM.sum())} | "
                  f"`{dom_lsp}` | `{dom_cls}` |")
    md.append("")
    md.append(f"**Take-away:** the holes are overwhelmingly **compressed spectra** "
              f"(near-degenerate χ with Δm of order a few GeV → decay products too soft to trigger/select). "
              f"In the EWKino scan they are dominated by **compressed higgsinos**; in Bino-DM by "
              f"**compressed binos** (coannihilation region). None are fixed by Run-3 luminosity.\n")
    bcols = ["scan", "model_number", "m_n1", "m_light_ewk", "dm_n2n1",
             "lsp_type", "phys_class", "exp_min_now", "pass_DM"]
    bcols = [c for c in bcols if c in all_h.columns]
    bench = all_h.sort_values("m_light_ewk").head(8)
    md.append("Lightest holes (most copiously produced, hence most urgent):\n")
    md.append("| " + " | ".join(bcols) + " |")
    md.append("|" + "---|" * len(bcols))
    for _, r in bench.iterrows():
        md.append("| " + " | ".join(f"{r[c]:.3g}" if isinstance(r[c], float) else str(r[c])
                                    for c in bcols) + " |")
    md.append("")
else:
    md.append("_No holes found at the configured thresholds._\n")

md.append("## Figures\n")
for scan, p in plots.items():
    rel = os.path.relpath(p, os.path.dirname(snakemake.output.report))   # noqa: F821
    md.append(f"### {scan}\n![{scan} mass plane]({rel})\n")

md.append("## Caveats\n")
md.append(f"- This run used `projection: {cfg.get('projection', 'sqrtL')}`. `sqrtL` is the "
          "**statistics-limited** (optimistic) bound; set `projection: sqrtL_syst` in "
          "`config.yaml` for the conservative bound where reach saturates as luminosity grows "
          "(`systematics_fraction` controls the saturation).\n"
          "- Projections reuse the **published Run-2 analyses' expected CLs**; a genuinely "
          "new/optimised search could do better than this proxy.\n"
          "- Decay-mode flags (WZ vs Wh vs slepton) use the **dominant** branching ratio "
          "from the SLHA decay tables, not a full final-state simulation.\n"
          "- External constraints use the ATLAS-provided flags (0 = excluded). EW + Flavour are "
          "imposed by default; DM (relic density + direct detection) is reported but not imposed, "
          "as the relic-density requirement is cosmology-dependent.\n")

with open(snakemake.output.report, "w") as fh:                # noqa: F821
    fh.write("\n".join(md) + "\n")
print(f"wrote {snakemake.output.report} with {len(ordered)} classes")        # noqa: F821
