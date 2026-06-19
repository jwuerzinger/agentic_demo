# Run-3 EWK SUSY search targets from the ATLAS pMSSM scan

A small, fully reproducible study built on the public data of the ATLAS Run-2
electroweak pMSSM scan ([arXiv:2402.01392](https://arxiv.org/abs/2402.01392),
analysis SUSY-2020-15).

**Goals:**
1. find pMSSM models that are **not excluded today** but where ATLAS is
   **expected to gain sensitivity in LHC Run 3**, grouped into physics classes;
2. flag **coverage holes** — viable models that need a *genuinely different* analysis
   strategy than the searches in the scan (not just more luminosity or a re-optimisation).

The whole study is orchestrated with **Snakemake** and runs inside a **pixi**
environment, so it reproduces exactly on any machine.

---

## How to reproduce (the only commands you need)

You need [pixi](https://pixi.sh) installed (`curl -fsSL https://pixi.sh/install.sh | bash`).
Everything else — Python, Snakemake, the scientific stack, the LaTeX engine
(`tectonic`) for the Feynman diagrams, even `curl` and the input data — is handled
by the pipeline from the pinned `pixi.lock`. (On its first run `tectonic` fetches and
caches its TeX package bundle, so that one render step needs network once.)

From the repository root:

```bash
pixi install        # create the locked environment (one-time, ~1-2 min)
pixi run run        # download inputs (if missing) + run the entire study
```

The first step (`download`) fetches the ATLAS SLHA tarballs and exclusion CSVs
into `data/`, so a fresh checkout needs **no manual data step**. Other commands:

```bash
pixi run plan       # dry-run: print the jobs that would execute
pixi run dag        # render the rule graph to docs/dag.png (+ .svg)
pixi run clean      # delete results/ to force a clean re-run
```

To re-run after changing an assumption (e.g. the target luminosity), edit
`config/config.yaml` and run `pixi run run` again — Snakemake re-executes only
the steps whose inputs or parameters changed.

## The pipeline (DAG)

![Snakemake rule graph](docs/dag.png)

`download → parse_slha → merge_exclusion → project → {classify, plots}`, then
`classify`/`holes` fan into `report` and `validate`. Regenerate this image with
`pixi run dag`.

| Step | What it does |
|---|---|
| **download** | Fetch the SLHA tarballs + exclusion CSVs from the ATLAS page into `data/` (skipped if present). |
| **parse_slha** | Stream every `.slha` spectrum from the tarball; extract masses, gaugino/higgsino composition (neutralino mixing matrix), mass splittings, chargino lifetime, dominant decay modes. |
| **merge_exclusion** | Join with the per-analysis expected/observed CLs from the CSV (keyed by `Model_number`). |
| **project** | Scale each of the 8 recastable searches' *expected* significance from 140 → target fb⁻¹; flag **targets**. |
| **classify** | Assign each target to a physics class (compressed higgsino, on-shell WZ, Wh→1ℓbb, off-shell, disappearing track, …). |
| **holes** | Find **coverage holes**: viable models in the *new-strategy* reach tier (a re-optimised included search can't reach them **and** their dominant signature is one none exploit), produced enough + not a covered class. |
| **plots** | Mass-plane figures (excluded / allowed / target / hole). |
| **report** | Assemble `results/report.md` + `results/class_summary.csv`; render a TikZ Feynman diagram for each populated class and extract a representative target/hole spectrum into `results/representatives/`. |
| **sensitivity** | **Independent**, data-anchored estimate for **hand-selected benchmarks** (config `sensitivity.models`): how much better than the best current search a dedicated analysis must be to exclude each model — `R_req = μ₉₅(target)`, projected in signal-strength space (`μ₉₅ ∝ 1/√L`). Not a simulation. See `docs/search_design.md`. |
| **validate** | Assert pipeline invariants; fails the build on any violation. |

### Target definition

A **target** is currently **not excluded** (observed CLs ≥ 0.05), **not even
expected to be excluded now** (expected CLs ≥ 0.05), **but** projected-excluded
(projected CLs < 0.05) at the target luminosity — *and* it must be **viable**:
pass the required external constraints (**EW + Flavour + DM** by default; see below).

### Luminosity scaling (how `project` works)

Each of the 8 recastable searches reports an **expected CLs** at the baseline
luminosity L₀. It is extrapolated to the target L in three steps (per analysis,
per model):

1. **CLs → significance** (expected CLs as a one-sided Gaussian p-value):
   `Z = Φ⁻¹(1 − ExpCLs)` — the exclusion line `CLs = 0.05` is `Z = 1.645`.
2. **scale with luminosity:** `Z(L) = Z · scale`, with `scale = √(L/L₀)`
   (statistics-limited: S/√B with S, B ∝ L). For 140 → 450 fb⁻¹, `scale ≈ 1.793`.
3. **significance → projected CLs:** `ExpCLs(L) = Φ(−Z(L))`.

A model is *projected-excluded* if the **minimum** projected `ExpCLs` over the 8
analyses drops below 0.05. The *expected* (not observed) CLs is scaled, because it
reflects sensitivity (S, B) rather than the data fluctuation.

Consequently a model newly crosses the line at 450 fb⁻¹ when its **current**
expected CLs sits between **0.05** and **≈0.18** = `1 − Φ(1.645/1.793)`. _Example:_
ExpCLs_now = 0.15 → Z = 1.036 → Z(L) = 1.858 → ExpCLs(L) = 0.032 (< 0.05 ⇒ target).

`√L` is optimistic; set `projection: sqrtL_syst` for a systematics-floor variant
where the gain saturates. The generated `results/report.md` recomputes all of these
numbers for whatever `target_lumi_fb` / `projection` you set.

### Reach tiers and the coverage **holes**

For every viable, currently-allowed model we ask what it would take to exclude it at the
target luminosity, via **`R_req`** — the improvement needed over the *best current search*,
in signal-strength space (`μ₉₅ ∝ 1/√L`, the physically correct scaling). That sorts models
into tiers (`reach_tier`, computed in `project.py`):

- **luminosity** (`R_req ≤ 1`) — the existing searches reach them with Run-3 data alone;
- **re-optimise** (`1 < R_req ≤ reopt_factor`) — a tweak of an included search (lower
  thresholds, multivariate) would reach them;
- **new-strategy** (`R_req > reopt_factor` **and** a dominant signature *no* included search
  exploits — radiative χ̃₂⁰→χ̃₁⁰γ → soft-photon; tau-rich → tau);
- **out-of-reach** (far, with no distinct alternative handle).

A **hole** is a *new-strategy* model that is also produced enough for a dedicated search
(`N = σ·L ≥ hole_min_run3_events`) and not already covered by an included dedicated search
(`hole_exclude_classes`, e.g. disappearing tracks). I.e. it needs a **genuinely different
analysis**, not a re-optimisation of what the scan already includes — each hole carries the
suggested `alt_strategy`. (Holes and targets are disjoint: targets ≈ the `luminosity` tier.)

### What you get

| Output | Meaning |
|---|---|
| `results/report.md` | **Read this first** — headline numbers, target classes, **coverage holes**, benchmarks, caveats. |
| `results/class_summary.csv` | Target counts per class × scan. |
| `results/<scan>/sensitivity.parquet` | Per benchmark: the (lepton-channel-anchored) improvement `R_req` over the best current search, plus a `verdict` — luminosity / lepton re-opt / **needs new channel (photon)** / out-of-reach. |
| `results/validation.txt` | Pass/fail of every invariant check. |
| `results/<scan>/targets.parquet` | Flagged target models with features, projection, class. |
| `results/<scan>/holes.parquet` | Coverage-hole models. |
| `results/<scan>/projected.parquet` | All models with current + projected exclusion status + constraint flags. |
| `results/<scan>/mass_plane.png` | Mass-plane plots. |
| `results/representatives/` | Per-class TikZ Feynman diagrams (`.tex`/`.pdf`/`.png`), a representative target & hole `.slha` spectrum per class, and `MANIFEST.csv`. |

### Key knobs (`config/config.yaml`)

| Setting | Default | Meaning |
|---|---|---|
| `target_lumi_fb` / `baseline_lumi_fb` | `450` / `140` | Run-3 target vs Run-2 baseline luminosity. |
| `projection` | `sqrtL` | `sqrtL` (stat-limited) or `sqrtL_syst` (systematics floor, conservative). |
| `require_constraints` | `[EW, Flavour, DM]` | External constraints a viable target must pass (`0 = excluded`). The report still breaks counts down by tier so each cut's effect is visible. |
| `cls_threshold` | `0.05` | CLs below this ⇒ excluded at 95% CL. |
| `reopt_factor` | `5.0` | `R_req` above this ⇒ re-optimising an included search can't reach it (→ new-strategy / out-of-reach tier). |
| `hole_radiative_min` / `hole_tau_min` | `0.50` / `0.50` | BR thresholds for the "uncovered signature" flag: radiative χ̃₂⁰→χ̃₁⁰γ (→ soft-photon) / tau-rich (→ tau). |
| `hole_min_run3_events` | `5000` | Production floor (σ·L) for a hole to be reachable in principle by a dedicated search. |
| `hole_exclude_classes` | `[LLP-disappearing-track]` | Signatures already covered by an included dedicated search, excluded from holes. |
| `sensitivity:` block | — | Benchmark `models` + `assumed_improvement` (the gain a re-optimised **lepton-channel** search is assumed to achieve, ~2–3×; **decoupled** from `reopt_factor`). The baseline is the real per-model expected CLs — no other free inputs. |
| `compressed_dm_max_gev` / `llp_ctau_min_mm` | `35` / `1.0` | Class cuts: "compressed" Δm; long-lived chargino cτ. |

---

## Headline results (defaults)

Applying the external constraints matters a lot — the collider-only count is
dominated by models other measurements already disfavour. The imposed
requirement is **EW+Flavour+DM** (last column):

| Scan | Total | Excluded now | Collider-only | + EW+Flavour | + EW+Flavour+DM |
|---|---:|---:|---:|---:|---:|
| EWKino | 12 280 | 2 355 | 364 | 251 | **41** |
| Bino-DM | 8 897 | 2 590 | 420 | 313 | **47** |

So **88 viable Run-3 targets** in **6 physics classes** (compressed mixed/higgsino,
disappearing track, on-shell WZ, Wh→1ℓbb, off-shell WZ).

**Coverage holes (new-strategy targets):** 534 (EWKino) + 171 (Bino-DM). Every one points
to the **same different strategy — a soft-photon + ISR-jet search** — because their χ̃₂⁰ is
**radiative-dominated** (χ̃₂⁰→χ̃₁⁰γ), a final state none of the included (lepton/jet/bb)
searches exploit. (The photon is that *decay* photon; the *jet* is the ISR recoil that
supplies the Eᵀmiss trigger — there is no ISR photon.) Re-optimising those searches can't reach them (`R_req` ≫ 5, often
effectively ∞), so they need a genuinely new analysis, not more luminosity. They span
m(χ̃₁±/χ̃₂⁰) ≈ 97–553 GeV and include the worked-example benchmark **EWKino 770**.

---

## Repository layout

```
.
├── pixi.toml / pixi.lock        # reproducible environment (pinned; osx-arm64/osx-64/linux-64)
├── config/config.yaml           # all study parameters
├── workflow/
│   ├── Snakefile                # the DAG
│   └── scripts/                 # download via rule; parse_slha, merge, project, classify,
│                                #   holes, sensitivity, plots, report, validate
├── data/                        # ATLAS inputs, fetched by the `download` rule (git-ignored)
├── docs/dag.png                 # rendered rule graph (tracked)
├── docs/search_design.md        # written compressed-higgsino search strategy
├── figures/                     # bespoke benchmark diagrams (e.g. EWKino770_target.*)
└── results/                     # generated by `pixi run run` (git-ignored)
    └── representatives/          #   per-class Feynman diagrams + representative SLHA + MANIFEST.csv
```

Input data provenance:
[ATLAS SUSY-2020-15 public page](https://atlas.web.cern.ch/Atlas/GROUPS/PHYSICS/PAPERS/SUSY-2020-15/inputs/ATLAS_EW_pMSSM_Run2.html)
and [HEPData ins2755168](https://www.hepdata.net/record/ins2755168).

## Method caveats

- `sqrtL` is the **statistics-limited** (optimistic) projection; set
  `projection: sqrtL_syst` for the conservative bound where reach saturates.
- Projections reuse the **published analyses' expected CLs** as a proxy; a
  genuinely new/optimised search could do better.
- Decay-mode tags use the **dominant** branching ratio from the SLHA tables, not a
  full final-state simulation. Observed-only channels (disappearing track, h→inv,
  mₐ) inform the current-exclusion status but are not projected.
- External constraints use the ATLAS-provided flags (`0 = excluded`); the imposed set
  is `EW+Flavour+DM`. The DM constraint's relic-density part is cosmology-dependent
  (assumes the LSP is all of dark matter), so the headline table also shows the looser
  tiers — relax via `require_constraints` if you prefer.
