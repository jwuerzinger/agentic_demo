"""Assemble the final study report: enumerate the Run-3 target classes with
physics descriptions, per-scan counts, suggested searches, and representative
benchmark models. Writes results/report.md and results/class_summary.csv.
"""
import os
import shutil
import subprocess
import tarfile
import numpy as np
import pandas as pd
from scipy.special import ndtri, ndtr

cfg = snakemake.config                                        # noqa: F821
L = float(cfg["target_lumi_fb"])
L0 = float(cfg["baseline_lumi_fb"])
THR = float(cfg["cls_threshold"])

# luminosity scale factor (mirror project.py) for the Method section
_ratio = L / L0
if cfg.get("projection", "sqrtL") == "sqrtL_syst":
    _f = float(cfg.get("systematics_fraction", 0.30))
    SCALE = np.sqrt(_ratio) / np.sqrt(1.0 + _f * (_ratio - 1.0))
else:
    SCALE = np.sqrt(_ratio)
# current expected-CLs band that newly crosses threshold at the target lumi:
#   ExpCLs(L) < THR  <=>  ExpCLs_now < 1 - Phi( Phi^-1(1-THR) / scale )
BAND_HI = float(1.0 - ndtr(ndtri(1.0 - THR) / SCALE))
# worked example: a model with ExpCLs_now = 0.15
EX_NOW = 0.15
EX_PROJ = float(ndtr(-(ndtri(1.0 - EX_NOW) * SCALE)))

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

# ---------------------------------------------------------------------------
# Per-class Feynman diagrams. Plain TikZ + core pgf decorations only (shipped by
# any TeX Live) -- no external tikz-feynman package, so the pixi env is self-
# sufficient. pp -> EW-ino pair (Drell-Yan) on the left; class-specific decays
# on the right.
# ---------------------------------------------------------------------------
TIKZ_HEADER = r"""\documentclass[border=6pt]{standalone}
\usepackage{tikz}\usepackage{amsmath}\usepackage{amssymb}
\usetikzlibrary{decorations.pathmorphing,decorations.markings,arrows.meta}
\tikzset{
  ferm/.style={draw,thick,postaction=decorate,decoration={markings,
    mark=at position 0.56 with {\arrow{Stealth[length=1.7mm]}}}},
  boson/.style={draw,thick,decorate,decoration={snake,amplitude=1.1pt,segment length=5pt}},
  gluon/.style={draw,thick,decorate,decoration={coil,aspect=0.5,amplitude=2.2pt,segment length=4.5pt}},
  scal/.style={draw,thick,dashed},
  llp/.style={draw,thick,double,double distance=1.4pt},
  susy/.style={red!80!black},
  sferm/.style={ferm,susy},
  sscal/.style={scal,susy},
  sllp/.style={llp,susy},
  lab/.style={font=\footnotesize},
  slab/.style={font=\footnotesize,text=red!80!black},
}
\begin{document}
\begin{tikzpicture}[x=1cm,y=1cm,>=Stealth]
"""
TIKZ_FOOTER = "\n\\end{tikzpicture}\n\\end{document}\n"


def _tikz(boson, up, dn, decays, isr=False, note=""):
    """Assemble a diagram: production boson, the two produced inos (up/dn =
    (style, label)), and a class-specific `decays` snippet."""
    p = []
    p.append(r"\coordinate(q1)at(-3.6,1.0);\coordinate(q2)at(-3.6,-1.0);"
             r"\coordinate(va)at(-2.1,0);\coordinate(vb)at(-0.8,0);"
             r"\coordinate(u)at(0.9,1.15);\coordinate(d)at(0.9,-1.15);")
    p.append(r"\draw[ferm](q1)--(va);\draw[ferm](q2)--(va);"
             r"\node[lab,left]at(q1){$q$};\node[lab,left]at(q2){$\bar q$};")
    if isr:
        # emit the ISR gluon from a point that lies ON the q1--va line
        # (q1=(-3.6,1.0), va=(-2.1,0); at x=-3.0 the line is at y=0.6)
        p.append(r"\fill(-3.0,0.6)circle(1.1pt);"
                 r"\draw[gluon](-3.0,0.6)--(-3.55,1.85) node[lab,above]{ISR jet};")
    p.append(r"\draw[boson](va)--(vb) node[lab,midway,above]{%s};" % boson)
    p.append(r"\draw[%s](vb)--(u) node[slab,midway,above left]{%s};" % up)
    p.append(r"\draw[%s](vb)--(d) node[slab,midway,below left]{%s};" % dn)
    p.append(decays)
    if note:
        p.append(r"\node[lab]at(0.1,-3.0){%s};" % note)
    return "\n".join(p)


def _compressed(lsp):
    decays = (r"\draw[boson](u)--(2.5,2.3) node[lab,right]{$Z^{*}\!\to f\bar f$ (soft)};"
              r"\draw[sferm](u)--(3.0,1.25) node[slab,right]{$\tilde\chi^0_1$};"
              r"\draw[boson](d)--(2.5,-2.3) node[lab,right]{$W^{*}\!\to f\bar f'$ (soft)};"
              r"\draw[sferm](d)--(3.0,-1.25) node[slab,right]{$\tilde\chi^0_1$};")
    return _tikz(r"$W^{*}$", ("sferm", r"$\tilde\chi^0_2$"), ("sferm", r"$\tilde\chi^\pm_1$"),
                 decays, isr=True, note=r"compressed %s: $\Delta m\sim$ few GeV" % lsp)


_WZ = _tikz(r"$W^{*}$", ("sferm", r"$\tilde\chi^0_2$"), ("sferm", r"$\tilde\chi^\pm_1$"),
            r"\draw[boson](u)--(2.6,2.4) node[lab,right]{$Z$};"
            r"\draw[sferm](u)--(3.0,1.25) node[slab,right]{$\tilde\chi^0_1$};"
            r"\draw[boson](d)--(2.6,-2.4) node[lab,right]{$W^\pm$};"
            r"\draw[sferm](d)--(3.0,-1.25) node[slab,right]{$\tilde\chi^0_1$};")

_WH = _tikz(r"$W^{*}$", ("sferm", r"$\tilde\chi^0_2$"), ("sferm", r"$\tilde\chi^\pm_1$"),
            r"\draw[scal](u)--(2.35,2.25) node[lab,midway,above]{$h$};"
            r"\draw[ferm](2.35,2.25)--(3.35,2.75) node[lab,right]{$b$};"
            r"\draw[ferm](2.35,2.25)--(3.35,1.85) node[lab,right]{$\bar b$};"
            r"\draw[sferm](u)--(3.0,0.95) node[slab,right]{$\tilde\chi^0_1$};"
            r"\draw[boson](d)--(2.6,-2.4) node[lab,right]{$W^\pm$};"
            r"\draw[sferm](d)--(3.0,-1.25) node[slab,right]{$\tilde\chi^0_1$};")

_LLP = _tikz(r"$W^{*}$", ("sllp", r"$\tilde\chi^\pm_1$"), ("sferm", r"$\tilde\chi^0_1$"),
             r"\draw[ferm](u)--(2.7,1.85) node[lab,right]{$\pi^\pm$ (soft)};"
             r"\draw[sferm](u)--(3.0,0.85) node[slab,right]{$\tilde\chi^0_1$};"
             r"\node[lab]at(0.95,1.62){disappears};",
             isr=True, note=r"long-lived $\tilde\chi^\pm_1$: $\Delta m\lesssim m_\pi$")

_SLEP = _tikz(r"$W^{*}$", ("sferm", r"$\tilde\chi^0_2$"), ("sferm", r"$\tilde\chi^\pm_1$"),
              r"\draw[ferm](u)--(1.9,2.25) node[lab,right]{$\ell$};"
              r"\draw[sscal](u)--(2.25,0.5) node[slab,midway,above right]{$\tilde\ell$};"
              r"\draw[ferm](2.25,0.5)--(3.3,1.05) node[lab,right]{$\ell$};"
              r"\draw[sferm](2.25,0.5)--(3.3,-0.1) node[slab,right]{$\tilde\chi^0_1$};"
              r"\draw[boson](d)--(2.6,-2.4) node[lab,right]{$W^\pm$};"
              r"\draw[sferm](d)--(3.0,-1.25) node[slab,right]{$\tilde\chi^0_1$};")

_STAU = _tikz(r"$W^{*}$", ("sferm", r"$\tilde\chi^0_2$"), ("sferm", r"$\tilde\chi^\pm_1$"),
              r"\draw[ferm](u)--(1.9,2.25) node[lab,right]{$\tau$};"
              r"\draw[sscal](u)--(2.25,0.5) node[slab,midway,above right]{$\tilde\tau$};"
              r"\draw[ferm](2.25,0.5)--(3.3,1.05) node[lab,right]{$\tau$};"
              r"\draw[sferm](2.25,0.5)--(3.3,-0.1) node[slab,right]{$\tilde\chi^0_1$};"
              r"\draw[boson](d)--(2.6,-2.4) node[lab,right]{$W^\pm$};"
              r"\draw[sferm](d)--(3.0,-1.25) node[slab,right]{$\tilde\chi^0_1$};")

_HEAVY = _tikz(r"$\gamma^{*}/Z^{*}$", ("sferm", r"$\tilde\chi_i$"), ("sferm", r"$\tilde\chi_j$"),
               r"\draw[sferm](u)--(3.0,1.5) node[slab,right]{decays};"
               r"\draw[sferm](d)--(3.0,-1.5) node[slab,right]{decays};",
               note=r"heavy EW-inos, just beyond current reach")

CLASS_TIKZ = {
    "WZ-onshell-multilepton": _WZ,
    "Wh-1Lbb": _WH,
    "WZ-offshell-soft": _compressed(r"off-shell $WZ$"),
    "compressed-higgsino": _compressed("higgsino"),
    "compressed-wino": _compressed("wino"),
    "compressed-mixed": _compressed("bino/coann."),
    "LLP-disappearing-track": _LLP,
    "slepton-multilepton": _SLEP,
    "slepton-multilepton-stau": _STAU,
    "heavy-other": _HEAVY,
}


def render_diagram(cls, outdir):
    """Write <cls>.tex, compile to PDF (tectonic) and rasterise to PNG (pdftoppm).
    Returns the PNG basename. Raises on failure -- the toolchain is guaranteed by
    the pixi env, so a failure is a real error, not something to skip.
    (tectonic is self-contained: it fetches tikz/pgf/standalone on first use and
    caches them; it leaves no .aux/.log to clean up.)"""
    if cls not in CLASS_TIKZ:
        return None
    with open(os.path.join(outdir, f"{cls}.tex"), "w") as fh:
        fh.write(TIKZ_HEADER + CLASS_TIKZ[cls] + TIKZ_FOOTER)
    r = subprocess.run(["tectonic", "--chatter", "minimal", f"{cls}.tex"],
                       cwd=outdir, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"tectonic failed for {cls}:\n{r.stderr[-2500:]}")
    subprocess.run(["pdftoppm", "-png", "-r", "150", "-singlefile", f"{cls}.pdf", cls],
                   cwd=outdir, check=True)
    return f"{cls}.png"


def scan_of(path):
    return os.path.basename(os.path.dirname(path))


# ---- load everything ----
proj = {scan_of(p): pd.read_parquet(p) for p in snakemake.input.projected}   # noqa: F821
tgts = {scan_of(p): pd.read_parquet(p) for p in snakemake.input.targets}     # noqa: F821
holes = {scan_of(p): pd.read_parquet(p) for p in snakemake.input.holes}      # noqa: F821
sens = {scan_of(p): pd.read_parquet(p) for p in snakemake.input.sensitivity}  # noqa: F821
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

all_h = pd.concat(holes.values(), ignore_index=True) if holes else pd.DataFrame()
ordered = list(summary.index) if len(summary) else []
hole_classes = (all_h["phys_class"].value_counts().index.tolist() if len(all_h) else [])

# ---- render diagrams + extract representative SLHA for the present classes ----
repdir = snakemake.output.representatives                     # noqa: F821
os.makedirs(repdir, exist_ok=True)
present = list(dict.fromkeys(ordered + hole_classes))         # union, target order first

DIA = {}                                                      # phys_class -> png basename
for cls in present:
    png = render_diagram(cls, repdir)
    if png:
        DIA[cls] = png
print(f"rendered {len(DIA)} diagrams for classes: {sorted(DIA)}")

# representative model per (role, class): target = most reachable; hole = lightest
REP = {}                                                      # (role, cls) -> row (Series)
for cls in ordered:
    sub = all_t[all_t["phys_class"] == cls]
    if len(sub):
        REP[("target", cls)] = sub.sort_values("exp_min_proj").iloc[0]
for cls in hole_classes:
    sub = all_h[all_h["phys_class"] == cls]
    if len(sub):
        REP[("hole", cls)] = sub.sort_values("m_light_ewk").iloc[0]

# extract each representative's spectrum from its tarball (one pass per tarball)
SLHA = {}                                                     # (role, cls) -> slha filename
if "slha_path" in all_t.columns or "slha_path" in all_h.columns:
    wanted = {}                                               # scan -> {member_path: out_name}
    for (role, cls), r in REP.items():
        out = f"{role}__{cls}__{r['scan']}_{int(r['model_number'])}.slha"
        wanted.setdefault(r["scan"], {})[r["slha_path"]] = out
        SLHA[(role, cls)] = out
    for scan, mapping in wanted.items():
        tarpath = cfg["scans"][scan]["slha_tarball"]
        with tarfile.open(tarpath, "r:gz") as tf:
            for m in tf:
                if m.name in mapping:
                    with open(os.path.join(repdir, mapping[m.name]), "wb") as fh:
                        fh.write(tf.extractfile(m).read())

# manifest tying class -> diagram + representative model + spectrum
man = []
for (role, cls), r in REP.items():
    man.append({"role": role, "phys_class": cls, "scan": r["scan"],
                "model_number": int(r["model_number"]),
                "m_chi1": round(float(r["m_n1"]), 1), "m_chi2": round(float(r["m_n2"]), 1),
                "m_char1": round(float(r["m_c1"]), 1), "dm_n2n1": round(float(r["dm_n2n1"]), 2),
                "lsp_type": r["lsp_type"], "diagram": DIA.get(cls, ""),
                "slha_file": SLHA.get((role, cls), "")})
pd.DataFrame(man).to_csv(os.path.join(repdir, "MANIFEST.csv"), index=False)


def reprel(name):
    """path of a representatives/ file, relative to the report's directory"""
    return os.path.join(os.path.relpath(repdir, os.path.dirname(snakemake.output.report)), name)  # noqa: F821


# ---- build markdown ----
md = []
md.append("# Run-3 EWK SUSY search targets from the ATLAS pMSSM scan\n")
md.append(f"_Data: ATLAS pMSSM electroweak scan, arXiv:2402.01392. "
          f"Projection: `{cfg.get('projection', 'sqrtL')}` scaling of expected significance from "
          f"{L0:.0f} fb$^{{-1}}$ to **{L:.0f} fb$^{{-1}}$** (Run 2+3 combined). "
          f"CLs exclusion threshold {cfg['cls_threshold']}. "
          f"A viable target must, on top of the ATLAS collider exclusion, pass the external "
          f"constraints **{REQ}** (ATLAS flags, 0 = excluded)._\n")

md.append("## Definition of a target\n")
md.append("A model is a **Run-3 target** if it is:\n\n"
          "1. **not excluded now** (observed): min over all channels of `ObsCLs` >= 0.05;\n"
          "2. **not even expected to be excluded now**: min over the 8 recastable searches "
          "of `ExpCLs` >= 0.05;\n"
          "3. **expected to be reached at the target luminosity**: projected min `ExpCLs` < 0.05;\n"
          f"4. **viable**: passes the required external constraints (`{REQ}`).\n\n"
          "This isolates viable parameter space that today's searches genuinely do not reach, "
          "but where Run-3 statistics are expected to gain sensitivity.\n")

md.append("## Method: luminosity scaling\n")
md.append(
    f"Each of the 8 recastable searches reports an **expected CLs** at the baseline "
    f"{L0:.0f} fb⁻¹. It is extrapolated to {L:.0f} fb⁻¹ in three steps (per analysis, per model):\n\n"
    "1. **CLs → significance** (treat expected CLs as a one-sided Gaussian p-value):\n"
    "   `Z = Φ⁻¹(1 − ExpCLs)`  — the exclusion line `CLs = 0.05` is `Z = 1.645`.\n"
    "2. **scale the significance with luminosity:**  `Z(L) = Z · scale`.\n"
    f"   For `projection: {cfg.get('projection', 'sqrtL')}`, "
    + (f"`scale = √(L/L₀) = √({L:.0f}/{L0:.0f}) = {SCALE:.3f}`"
       if cfg.get('projection', 'sqrtL') == 'sqrtL'
       else f"`scale = √(L/L₀)/√(1+f(L/L₀−1)) = {SCALE:.3f}` (f = {cfg.get('systematics_fraction', 0.30)})")
    + ".\n"
    "3. **significance → projected CLs:**  `ExpCLs(L) = Φ(−Z(L))`.\n\n"
    "The model's projected sensitivity is the **minimum** projected `ExpCLs` over the 8 analyses; "
    "if it falls below 0.05 the model is *projected-excluded*. The **expected** CLs is scaled (not the "
    "observed) because it reflects sensitivity (S, B) rather than the data fluctuation.\n\n"
    "`√L` is the **statistics-limited** scaling (S/√B with S,B ∝ L). It is optimistic; the "
    "`sqrtL_syst` option saturates the gain to model a systematics floor.\n\n"
    f"**Consequence.** A model newly crosses the threshold at {L:.0f} fb⁻¹ when its *current* expected "
    f"CLs lies between **{THR:.2f}** (already expected-excluded below that, hence filtered out) and "
    f"**{BAND_HI:.2f}** = `1 − Φ(1.645/{SCALE:.3f})`. "
    f"_Worked example:_ ExpCLs_now = {EX_NOW:.2f} → Z = {ndtri(1-EX_NOW):.3f} → "
    f"Z(L) = {ndtri(1-EX_NOW)*SCALE:.3f} → ExpCLs(L) = {EX_PROJ:.3f} (< 0.05 ⇒ target).\n")

md.append("## Headline numbers\n")
md.append("Target counts at increasing external-constraint stringency, to show the effect of each cut. "
          f"**The imposed (reported) requirement is `{REQ}`** — that column is the headline.\n")
md.append("| Scan | Total | Excluded now | Collider-only | + EW+Flavour | + EW+Flavour+DM |")
md.append("|---|---:|---:|---:|---:|---:|")
for scan, d in proj.items():
    n_coll = int(d.is_target_collider.sum())
    n_ewf = int((d.is_target_collider & d.pass_EW & d.pass_Flavour).sum())
    n_all = int((d.is_target_collider & d.pass_EW & d.pass_Flavour & d.pass_DM).sum())
    md.append(f"| {scan} | {len(d)} | {int(d.obs_excluded_now.sum())} | {n_coll} | {n_ewf} | {n_all} |")
md.append("\n_The dark-matter constraint (relic density + direct detection) is the most model-dependent "
          "and removes the most models; the relic-density part assumes the LSP is all of dark matter under "
          "standard cosmology._\n")

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
          "Run-3 search: currently allowed, but projected to be reachable. The production+decay "
          "**Feynman diagram** and a **representative SLHA spectrum** for each class are saved under "
          "[`representatives/`](representatives/) (see `representatives/MANIFEST.csv`).\n")

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
    if cls in DIA:
        md.append(f"\n  **Topology (representative target):**\n\n  ![{cls} Feynman diagram]({reprel(DIA[cls])})\n")
    if ("target", cls) in SLHA:
        md.append(f"  Representative spectrum: [`{SLHA[('target', cls)]}`]({reprel(SLHA[('target', cls)])})\n")
    md.append("")

# ---- designed-but-empty classes ----
empty = [c for c in CLASS_META if c not in set(ordered)]
if empty:
    md.append("### Designed classes with no targets\n")
    md.append("The taxonomy also defines these classes, which are **unpopulated** in these scans "
              "(e.g. sleptons are decoupled at ~10 TeV, so slepton-mediated cascades cannot occur): "
              + ", ".join(f"`{c}`" for c in empty) + ".\n")

# ---- search-strategy reach tiers & coverage holes -------------------
_excl = cfg.get("hole_exclude_classes", []) or []
_rf = cfg["reopt_factor"]
md.append("## What would it take? Reach tiers & coverage holes\n")
md.append(f"For every **viable, currently-allowed** model we ask what it would take to exclude it at "
          f"{L:.0f} fb⁻¹, via **`R_req`** — the improvement needed over the **best current search**, in "
          f"signal-strength space (`μ₉₅ ∝ 1/√L`, the physically correct scaling):\n")
md.append(f"| Scan | luminosity (R≤1) | re-optimise (R≤{_rf:g}) | **new strategy** | out-of-reach |")
md.append("|---|---:|---:|---:|---:|")
for scan, d in proj.items():
    vc = d[(~d["obs_excluded_now"]) & d["pass_required"]]["reach_tier"].value_counts()
    md.append(f"| {scan} | {int(vc.get('lumi', 0))} | {int(vc.get('reoptimise', 0))} | "
              f"**{int(vc.get('new-strategy', 0))}** | {int(vc.get('out-of-reach', 0))} |")
md.append("\n- **luminosity** — the existing searches reach these with Run-3 data alone (≈ the targets above).\n"
          "- **re-optimise** — a tweak of an included search (lower thresholds, multivariate) would reach them.\n"
          "- **new strategy** — re-optimising the included searches is *not* enough **and** the dominant signature "
          "is one none of them exploits (radiative χ̃₂⁰→χ̃₁⁰γ → soft photon; tau-rich → tau). These need a "
          "genuinely different analysis.\n"
          "- **out-of-reach** — far from the included searches, with no distinct alternative handle.\n")
md.append(f"A **hole** = a *new-strategy* model that is also produced enough for a dedicated search "
          f"(N = σ·L ≥ {int(cfg['hole_min_run3_events'])} events) and not already covered by an included "
          f"dedicated search ({', '.join(f'`{c}`' for c in _excl) or 'none'}).\n")

def fmt_R(x):
    """R_req display: huge values mean the included searches are totally blind (R_req->inf)."""
    return "≫10³" if (not np.isfinite(x)) or x > 1e3 else f"{x:.1f}"


md.append(f"### Holes — genuinely new-search targets ({len(all_h)})\n")
if len(all_h):
    md.append("| Scan | Holes | suggested strategy | dominant class | m(χ₁±/χ₂⁰) [GeV] | median R_req |")
    md.append("|---|---:|---|---|---|---|")
    for scan, h in holes.items():
        if not len(h):
            md.append(f"| {scan} | 0 | – | – | – | – |")
            continue
        md.append(f"| {scan} | {len(h)} | {h.alt_strategy.value_counts().idxmax()} | "
                  f"`{h.phys_class.value_counts().idxmax()}` | "
                  f"{h.m_light_ewk.min():.0f}–{h.m_light_ewk.max():.0f} | {fmt_R(h.R_req.median())} |")
    md.append(f"\n**Take-away:** these are models the included searches can't be re-optimised into reach "
              f"(R_req > {_rf:g}×) **and** whose dominant decay is a signature none of them use — so they call "
              f"for a *different* analysis (named per model in `alt_strategy`), chiefly a "
              f"**soft-photon + ISR-jet** search — the photon being the radiative decay χ̃₂⁰→χ̃₁⁰γ (a final "
              f"state none of the lepton/jet/bb searches reconstruct), not initial-state radiation. "
              f"**EWKino 770 is one of these.**\n")
    bcols = ["scan", "model_number", "m_n1", "dm_n2n1", "br_n2_gamma", "alt_strategy", "R_req"]
    bcols = [c for c in bcols if c in all_h.columns]
    bench = all_h.sort_values("m_light_ewk").head(8)
    md.append("Lightest holes (R_req ≫10³ = the included searches are effectively blind):\n")
    md.append("| " + " | ".join(bcols) + " |")
    md.append("|" + "---|" * len(bcols))
    for _, r in bench.iterrows():
        cells = [fmt_R(r[c]) if c == "R_req" else
                 (f"{r[c]:.3g}" if isinstance(r[c], float) else str(r[c])) for c in bcols]
        md.append("| " + " | ".join(cells) + " |")
    md.append("")
    md.append("#### Topologies & representative spectra\n")
    for cls in hole_classes:
        title = CLASS_META.get(cls, (cls,))[0]
        n = int((all_h["phys_class"] == cls).sum())
        md.append(f"**{title}** &nbsp; `({cls})` — {n} holes")
        if cls in DIA:
            md.append(f"\n![{cls} Feynman diagram]({reprel(DIA[cls])})\n")
        if ("hole", cls) in SLHA:
            md.append(f"Representative spectrum: [`{SLHA[('hole', cls)]}`]({reprel(SLHA[('hole', cls)])})\n")
    md.append("")
else:
    md.append("_No new-strategy holes at the configured thresholds._\n")

# ---- toy search-design sensitivity --------------------------------
all_s = pd.concat(sens.values(), ignore_index=True) if sens else pd.DataFrame()
md.append("## Designing a search for the radiative compressed-higgsino holes\n")
md.append("The holes are radiative compressed higgsinos/binos (χ̃₂⁰→χ̃₁⁰γ). A **dedicated soft-photon "
          "+ ISR-jet + Eᵀmiss search** — tagging the radiative photon, with the associated soft lepton "
          "from χ̃₁± as a complementary region — targets them; the full analysis design (trigger, low-pT "
          "photon reconstruction, discriminating variables, backgrounds, control/validation regions, "
          "interpretation) is written up in [`docs/search_design.md`](../docs/search_design.md).\n")
_fig = "figures/EWKino770_target.png"
if os.path.exists(_fig):
    md.append(f"Benchmark topology (EWKino 770):\n\n![EWKino 770 target diagram]({os.path.join('..', _fig)})\n")

if len(all_s):
    rimp = float(cfg["sensitivity"]["assumed_improvement"])
    md.append(f"\n### How much better would a search need to be? (at {L:.0f} fb⁻¹)\n")
    md.append("**Independent**, data-anchored estimate (config `sensitivity.models`). The baseline is the "
              "**real** per-model expected CLs (the best of the 8 current searches), projected in "
              "signal-strength space (`μ₉₅ ∝ 1/√L`, the physically correct scaling — see the √L caveat below). "
              f"**`R_req`** is the improvement needed over that best current search. **Crucially, for these "
              f"compressed models the best current search is the soft-*lepton* one — it uses *none* of the "
              f"radiative χ̃₂⁰→χ̃₁⁰γ photon — so `R_req` is anchored to the lepton channel.** The verdict reads: "
              f"`luminosity` (`R_req ≤ 1`) → `lepton re-opt` (`R_req ≤ {rimp:g}`: re-optimise that lepton search) "
              f"→ **`needs new channel (photon)`** (radiative & beyond that — the soft-photon channel is the "
              f"lever, whose gain this metric does **not** estimate; **not** 'unreachable') → `out of reach` "
              f"(non-radiative & beyond the lepton re-opt gain).\n")
    cols = ["scan", "model_number", "m_n1", "dm_n2n1", "br_n2_gamma", "exp_min_now",
            "R_req", "reach_reopt", "verdict"]
    cols = [c for c in cols if c in all_s.columns]
    order = all_s.assign(_k=(all_s["model_number"] != 770).astype(int)).sort_values(["_k", "R_req"])
    md.append("| " + " | ".join(cols) + " |")
    md.append("|" + "---|" * len(cols))
    for _, r in order.iterrows():
        md.append("| " + " | ".join(f"{r[c]:.3g}" if isinstance(r[c], float) else str(r[c])
                                    for c in cols) + " |")
    n_reopt = int((all_s["verdict"] == "lepton re-opt").sum())
    n_photon = int((all_s["verdict"] == "needs new channel (photon)").sum())
    b770 = all_s[(all_s.scan == "EWKino") & (all_s.model_number == 770)]
    v = (f" **EWKino 770** needs **{float(b770['R_req'].iloc[0]):.1f}×** *from the lepton channel* — beyond a "
         f"lepton re-optimisation, so its 69%-BR radiative photon is the handle a dedicated search would exploit."
         if len(b770) else "")
    md.append(f"\n**Verdict:** `R_req` spans **{all_s['R_req'].min():.1f}–{all_s['R_req'].max():.1f}×**. "
              f"**{n_reopt}/{len(all_s)}** are reachable by re-optimising the existing soft-lepton search "
              f"(`R_req ≤ {rimp:g}`); **{n_photon}/{len(all_s)}** are radiative models whose lepton-channel "
              f"`R_req` is too large — for those the **soft-photon channel** (a final state the current searches "
              f"discard) is the lever, and whether it suffices needs a real simulation, not this metric.{v} "
              f"(The `assumed_improvement` lepton re-opt gain is the one tunable input; everything else is the "
              f"real per-model sensitivity.)\n")

md.append("## Figures\n")
for scan, p in plots.items():
    rel = os.path.relpath(p, os.path.dirname(snakemake.output.report))   # noqa: F821
    md.append(f"### {scan}\n![{scan} mass plane]({rel})\n")

md.append("## Caveats\n")
md.append(f"- This run used `projection: {cfg.get('projection', 'sqrtL')}`. `sqrtL` is the "
          "**statistics-limited** (optimistic) bound; set `projection: sqrtL_syst` in "
          "`config.yaml` for the conservative bound where reach saturates as luminosity grows "
          "(`systematics_fraction` controls the saturation).\n"
          "- The √L *significance* scaling used for targets/holes is only valid near the exclusion "
          "boundary (ExpCLs ≲ 0.5). For far-from-reach models (holes, ExpCLs ≥ 0.90) it is unphysical "
          "(sensitivity appears to degrade with luminosity), so the holes' projected-CLs *values* are not "
          "meaningful — though the qualitative 'not luminosity-fixable' conclusion is robust. The "
          "search-sensitivity section above uses the correct signal-strength scaling (μ₉₅ ∝ 1/√L) instead.\n"
          "- Projections reuse the **published Run-2 analyses' expected CLs**; a genuinely "
          "new/optimised search could do better than this proxy.\n"
          "- Decay-mode flags (WZ vs Wh vs slepton) use the **dominant** branching ratio "
          "from the SLHA decay tables, not a full final-state simulation.\n"
          f"- External constraints use the ATLAS-provided flags (0 = excluded); the imposed set is "
          f"`{REQ}`. The DM constraint's relic-density part is cosmology-dependent (assumes the LSP is "
          "all of dark matter under standard cosmology), so the headline table also shows the looser "
          "tiers.\n")

with open(snakemake.output.report, "w") as fh:                # noqa: F821
    fh.write("\n".join(md) + "\n")
print(f"wrote {snakemake.output.report} with {len(ordered)} classes")        # noqa: F821
