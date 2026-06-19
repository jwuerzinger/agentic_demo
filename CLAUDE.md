# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

Two things:

1. **Input data** — local copies of the SLHA spectrum files + exclusion CSVs from the ATLAS Run 2 search for
   electroweak production of SUSY particles interpreted in the pMSSM (analysis **SUSY-2020-15**,
   [arXiv:2402.01392](https://arxiv.org/abs/2402.01392), JHEP 05 (2024)). Each `.slha` file is one pMSSM model.
2. **A reproducible study** (`workflow/`, `config/`, `pixi.toml`) that finds models which are *not excluded
   today* but where ATLAS is *expected to gain sensitivity in LHC Run 3*, grouped into physics classes. See
   the **Reproducible study** section below — this is the main deliverable, written up in `results/report.md`.

There is no compiled build; "running" this repo means running the Snakemake pipeline (see below).

## Data layout

All inputs live under `data/` and are fetched by the `download` rule (the first pipeline step) from the ATLAS
page; `data/` is **git-ignored** and reused if already present. Two gzipped tarballs, one per scan:

- `data/EWKino_SLHA.tar.gz` → `EWKino/<0-12>/<id>.slha` — ~12,280 models (electroweak-ino scan).
- `data/Bino-DM_SLHA.tar.gz` → `Bino-DM/<0-8>/<id>.slha` — ~8,900 models (bino dark-matter scan).

Files are split across numbered bucket subdirectories only to keep directory sizes manageable; `<id>` is the
model identifier and is not contiguous within a bucket. There is no index/manifest inside the tarballs.

**Exclusion data:** `data/EWKino.csv` and `data/Bino-DM.csv` (one row per `Model_number`) give, for each of 11
analysis channels, `<Analysis>__ExpCLs` / `<Analysis>__ObsCLs` (expected/observed CLs) plus `Final__*` and
`Constraints__*`. The 8 channels with an `ExpCLs` (`FullHad`, `1Lbb`, `2L0J`, `2L2J`, `Compressed`,
`3LOffshell`, `3LOnshell`, `4L`) are the recastable searches; `DisappearingTrack`, `h_to_inv`, `mA` are
observed-only. A model is excluded at 95% CL when its CLs `< 0.05`.

**External-constraint flags** (`Constraints__Flavour/EW/DM`) use the convention **`0 = excluded, 1 = not
excluded`** (Flavour: b→sγ, Bs→μμ, B→τν; EW: Δρ, m_W, Z→inv; DM: relic density + direct detection). These are
*not* CLs — they are binary decisions. A model is "viable" only if **EW+Flavour+DM** all pass
(`require_constraints` in config); the report still breaks counts down per tier (the DM relic-density part is
cosmology-dependent, so the looser tiers stay visible).

## SLHA file format

Each file is an SLHA2 "MSSM spectrum + Decays" file produced by **SPheno v4.0.5be**. Blocks that define the
model:

- `EXTPAR` — pMSSM input parameters: `1`=M_1 (bino), `2`=M_2 (wino), `3`=M_3 (gluino), `23`=mu, `26`=m_A,
  `11/12/13`=trilinears A_t/A_b/A_tau, `31-36`=slepton soft masses, `41-49`=squark soft masses.
- `MINPAR` — tanβ and sign(mu).
- `MASS` — physical pole masses; the phenomenology hinges on neutralinos (1000022/1000023/1000025/1000035)
  and charginos (1000024/1000037).
- `DECAY` blocks — branching ratios, after the spectrum.

The electroweak-ino sector (M_1, M_2, mu, tanβ) varies across the scan; the colored sector is largely
decoupled (soft masses ~10 TeV).

## Working with the data (read-only recipes)

Avoid extracting full tarballs (174 MB compressed, ~21k files). Stream what you need:

```bash
# Count models in a scan
tar tzf data/EWKino_SLHA.tar.gz | grep -c '\.slha$'

# Read one spectrum without unpacking
tar xzfO data/EWKino_SLHA.tar.gz EWKino/0/1.slha

# Pull a parameter from a file, e.g. M_1 from EXTPAR
tar xzfO data/EWKino_SLHA.tar.gz EWKino/0/1.slha | awk '/Block EXTPAR/{f=1} f&&$1==1{print $2; exit}'

# Extract a single bucket only
tar xzf data/EWKino_SLHA.tar.gz EWKino/3/
```

## Reproducible study (pixi + Snakemake)

**Convention — non-negotiable for this repo:** every analysis step is a Snakemake rule and runs inside the
pixi environment. Do **not** add ad-hoc analysis scripts you run by hand, and do not `pip install` or use any
other Python — reproducibility depends on it. If you add a step, add a rule in `workflow/Snakefile` and a
script in `workflow/scripts/`, declare its inputs/outputs, and run it through `pixi run`. Tunable numbers live
in `config/config.yaml`, never hard-coded in scripts.

### How a human reproduces the results

Requires [pixi](https://pixi.sh) only. From the repo root:

```bash
pixi install        # build the locked env (pixi.lock pins exact versions)
pixi run run        # download inputs (if missing) + run the whole study -> results/
pixi run plan       # dry-run: show the DAG without executing
pixi run dag        # render the rule graph -> docs/dag.png (+ .svg)
pixi run clean      # rm -rf results/  (force a clean re-run)
```

The same instructions, expanded for end users, are in `README.md` — **keep README.md and this section in sync**
whenever the workflow or its commands change (the README also embeds `docs/dag.png`).

### Structure

```
config/config.yaml      # ALL parameters (lumi, CLs threshold, projection, constraints, class & hole cuts)
workflow/Snakefile      # the DAG (rule `download` is first; `rule all` must stay the top rule)
workflow/scripts/        parse_slha -> merge -> project -> classify ; holes ; plots ; report ; validate
                         #   sensitivity branches off merge_exclusion (independent benchmark study)
docs/search_design.md   # written radiative-compressed-higgsino soft-photon + ISR-jet search strategy
figures/                # bespoke benchmark diagrams (e.g. EWKino770_target.*), not pipeline-generated
data/                   # ATLAS inputs (fetched by `download`, git-ignored)
docs/dag.png            # rendered rule graph (tracked, embedded in README)
results/                # generated (per-scan parquet, plots, report.md, holes, validation.txt)
results/representatives/ #   per-class TikZ Feynman diagrams + representative target/hole .slha + MANIFEST.csv
```

Pipeline per scan: `download → parse_slha → merge_exclusion → project → classify` (+ `plots`, `holes`); a
separate `sensitivity` branch hangs off `merge_exclusion` (independent benchmark study); then `report` + `validate`
fan in all scans. Scripts use the Snakemake `script:` directive — they read the injected
`snakemake` object (`snakemake.input/output/params/config/wildcards`), not argparse. (The `download` rule uses
`shell:` with `curl`; its output is `data/{fname}` with a `wildcard_constraints` on the known filenames.)

### Method

- **`project.py`** — (i) √L scaling of expected significance to `target_lumi_fb` for the **targets**
  (`Z = Φ⁻¹(1−ExpCLs)`, `Z(L)=Z·scale`; `sqrtL` or `sqrtL_syst`); a target is not-excluded-now,
  projected-excluded, and passes `require_constraints`. (ii) Also computes the **`reach_tier`** (the search-
  strategy axis) in *signal-strength* space: `R_req = μ₉₅(target)` with `μ₉₅(L)=μ₉₅(L0)·√(L0/L)` and
  `μ₉₅` from `exp_min_now` (best of the 8) via the asymptotic `ExpCLs(μ)=2(1−Φ(μ/σ))`. Tiers: `lumi`
  (R_req≤1), `reoptimise` (≤`reopt_factor`), `new-strategy` (>`reopt_factor` AND `signature_uncovered`:
  radiative χ̃₂⁰→χ̃₁⁰γ ≥ `hole_radiative_min` or tau-rich), `out-of-reach`. The √L *significance* heuristic is
  only valid near the boundary (see the project.py docstring); the tier/R_req use the correct μ-space scaling.
- **`classify.py`** — bins targets into physics classes via interpretable cuts (LSP composition from `NMIX`,
  mass splittings, intermediate sleptons, chargino cτ); also writes the full `classified.parquet`.
- **`holes.py`** — coverage holes = the **`new-strategy`** reach tier (a re-optimised included search can't
  reach them AND a dominant signature none of them exploits → a genuinely *different* analysis, named in
  `alt_strategy`), additionally requiring production `N = σ·target_lumi ≥ hole_min_run3_events` and
  exclusion of classes with an existing dedicated search (`hole_exclude_classes`, e.g. disappearing tracks).
  Holes and targets are **disjoint** (targets ≈ the `lumi` tier). In these scans every hole is a radiative
  compressed higgsino/bino → a **soft-photon + ISR-jet** search (the photon is the χ̃₂⁰→χ̃₁⁰γ *decay* photon,
  the jet is ISR recoil for the Eᵀmiss trigger — not an ISR photon). The decay-based logic (`classify` WZ/Wh,
  the `project` signature flag) reads `parse_slha`'s summed BR set: `br_n2_{Z,h,gamma,ll,qq}`,
  `br_c1_{W,lep,tau,qq}` — full branching fractions per final state, not single-dominant-channel flags.
- **`report.py`** — besides the markdown report, for each class present among targets ∪ holes it renders a
  **plain-TikZ Feynman diagram** (compiled with `tectonic`, rasterised with `pdftoppm`) and extracts a
  representative target/hole **SLHA spectrum** (via the `slha_path` column recorded by `parse_slha`) into
  `results/representatives/` with a `MANIFEST.csv`. Diagrams use core pgf only (no `tikz-feynman`); `tectonic`
  is self-contained (fetches its TeX bundle once, then caches), so a render failure is a real error.
- **`sensitivity.py`** — for **hand-selected benchmarks** (`config["sensitivity"]["models"]`; EWKino 770/9030/9025,
  Bino-DM 3115), *how much better than the best current search a dedicated analysis must be* to exclude the model.
  **Independent study**: reads `merged.parquet` (the real per-model expected CLs), branches off `merge_exclusion`
  — *not* classify/project/holes. Baseline = `exp_min_now` (min ExpCLs over the 8); mapped to an expected limit on
  signal strength via the asymptotic `ExpCLs(μ)=2(1−Φ(μ/σ))`, then projected in μ-space `μ₉₅(L)=μ₉₅(L0)·√(L0/L)`
  (the physically correct, monotonic scaling — see the √L caveat in `project.py`). Output `R_req = μ₉₅(target)`.
  **Key subtlety:** the best current search for these compressed models is the soft-*lepton* one, which uses
  *none* of the radiative χ̃₂⁰→χ̃₁⁰γ photon, so **`R_req` is lepton-channel-anchored** and cannot credit a photon
  search. Hence the `verdict`: `luminosity` (R_req≤1) → `lepton re-opt` (R_req≤`assumed_improvement`) →
  `needs new channel (photon)` (radiative & beyond that — the soft-photon channel is the *unmodelled* lever, **not**
  "unreachable") → `out of reach` (non-radiative & beyond). `assumed_improvement` (the lepton re-opt gain, ~2–3×) is
  **decoupled** from `reopt_factor` (the population-tiering ceiling, 5.0). **Not a simulation.** Current result:
  9025 ~1.8× (lepton re-opt), 770/3115 ~8.7/7.5× and 9030 ~12.8× (needs the photon channel).
- **`validate.py`** — asserts pipeline invariants and fails the build on any violation.

Current result (require_constraints = EW+Flavour+DM): 88 viable targets (41 EWKino + 47 Bino-DM) in 6 populated
classes; reach tiers (viable, not-excluded) ≈ lumi / reoptimise / new-strategy / out-of-reach; **705 holes**
(534 EWKino + 171 Bino-DM), all radiative compressed higgsinos/binos → a **soft-photon + ISR-jet** search, m ≈
97–553 GeV, incl. benchmark 770 (see `results/report.md`). Relaxing `require_constraints` to `[EW, Flavour]`
raises the targets to 251 + 313.

### Gotchas

- `results/` **and** `data/` are git-ignored and regenerable; `docs/dag.png` is tracked. `results/report.md`
  is **generated** — edit the scripts, never the outputs.
- `rule all` must remain the first rule in the Snakefile (the `download` rule has wildcard output, so it cannot
  be the default target).
- Editing `config/config.yaml` triggers re-runs **only** because the config-dependent rules declare
  `params: cfg=config` (scripts read `snakemake.config`, which Snakemake does not otherwise track). If you add
  a config-driven rule, give it `params: cfg=config` too — otherwise config edits silently won't re-run it.
  `parse_slha` is intentionally exempt so config tweaks don't force the slow ~21k-file re-parse.
- The `script:` paths in the Snakefile are relative to `workflow/`; `configfile`/`data/` paths are relative to
  the repo root (where you invoke `pixi run`).
- `Constraints__*` are binary `0=excluded/1=not-excluded` flags, **not** CLs — never threshold them at 0.05.
- SLHA neutralino masses can be negative (sign of the mass eigenvalue) — take `abs()` for physical masses
  (the parser already does).

## Provenance

Source: ATLAS public results page for SUSY-2020-15 —
https://atlas.web.cern.ch/Atlas/GROUPS/PHYSICS/PAPERS/SUSY-2020-15/inputs/ATLAS_EW_pMSSM_Run2.html
and HEPData record [ins2755168](https://www.hepdata.net/record/ins2755168). Download exclusion CSVs from
there when cross-referencing which models are excluded.

## Git note

`.gitignore` covers `data/` (the 174 MB of fetched inputs), `results/`, `.pixi/`, and `.snakemake/`. The repo
has no Git LFS — don't `git add` the tarballs. Inputs are reproduced by `pixi run run` (the `download` rule),
so they need not be tracked.
