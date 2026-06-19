# Run-3 EWK SUSY search targets from the ATLAS pMSSM scan

A small, fully reproducible study built on the public data of the ATLAS Run-2
electroweak pMSSM scan ([arXiv:2402.01392](https://arxiv.org/abs/2402.01392),
analysis SUSY-2020-15).

**Goals:**
1. find pMSSM models that are **not excluded today** but where ATLAS is
   **expected to gain sensitivity in LHC Run 3**, grouped into physics classes;
2. flag **coverage holes** — viable, light models the programme cannot even
   *expect* to constrain, which more luminosity will **not** fix.

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
| **holes** | Find **coverage holes**: viable, light models with no expected sensitivity (not luminosity-fixable). |
| **plots** | Mass-plane figures (excluded / allowed / target / hole). |
| **report** | Assemble `results/report.md` + `results/class_summary.csv`; render a TikZ Feynman diagram for each populated class and extract a representative target/hole spectrum into `results/representatives/`. |
| **sensitivity** | **Independent** toy cut-and-count reach of a *dedicated* soft-dilepton + ISR search (see `docs/search_design.md`) for **hand-selected benchmark models** (config `sensitivity.models`); depends only on the parsed spectra, not the classification. Illustrative, not a simulation. |
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

### A coverage **hole**

is a model that is _viable_ (passes EW + Flavour + DM), _invisible_ (min expected CLs ≥
`hole_expcls_min` across the 8 recastable searches), and _reachable in principle_ by a
**dedicated** Run-3 search — enough EW-ino signal is produced at the target luminosity,
`N = σ(m,mode)·L ≥ hole_min_run3_events` (approximate 13 TeV cross-sections, so winos
reach higher mass than higgsinos). The √L projection of the existing searches does not
help, so these need a **new or re-optimised search**. Signatures with an existing
dedicated search (`hole_exclude_classes`, e.g. disappearing tracks) are excluded.

### What you get

| Output | Meaning |
|---|---|
| `results/report.md` | **Read this first** — headline numbers, target classes, **coverage holes**, benchmarks, caveats. |
| `results/class_summary.csv` | Target counts per class × scan. |
| `results/<scan>/sensitivity.parquet` | Toy dedicated-search reach for the hand-selected benchmark models (S, B, Z, excludable). |
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
| `hole_expcls_min` / `hole_min_run3_events` | `0.90` / `5000` | Hole = expected CLs above this **and** ≥ this many produced EW-ino events at target lumi (reachability). |
| `hole_exclude_classes` | `[LLP-disappearing-track]` | Signatures already covered by a dedicated search, excluded from holes. |
| `sensitivity:` block | — | Toy dedicated-search parameters (ε plateau, Δm turn-on, background, systematic). All illustrative; see `docs/search_design.md`. |
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

**Coverage holes:** 409 (EWKino) + 140 (Bino-DM), **none** fixable by Run-3
luminosity. They are overwhelmingly **compressed higgsinos** (EWKino) and
**compressed binos** (Bino-DM) — near-degenerate spectra (Δm ~ few GeV) with decay
products too soft for current selections, spanning m(χ₁±/χ₂⁰) ≈ 100–550 GeV (the
reachability ceiling for higgsino-strength production at `hole_min_run3_events=5000`).
The disappearing-track region is excluded — it already has a dedicated ATLAS search.

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
