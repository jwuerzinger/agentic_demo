# Search design: radiative compressed higgsinos via a soft photon + ISR jet

Target: the **coverage holes** — viable, copiously-produced compressed higgsinos/binos whose χ̃₂⁰
decays **radiatively**, χ̃₂⁰ → χ̃₁⁰ γ, a final state *none* of the searches in the pMSSM scan
exploit. Benchmark **EWKino 770**: a ~183 GeV higgsino, Δm(χ̃₂⁰,χ̃₁⁰) ≈ 4.5 GeV with
**BR(χ̃₂⁰→χ̃₁⁰γ) ≈ 69%**, Δm(χ̃₁±,χ̃₁⁰) ≈ 2.4 GeV. This is the analysis a dedicated Run-3 search
would run; the `sensitivity` step in the pipeline quantifies its (illustrative) reach.

> **Why a *new* strategy, not a re-optimisation.** The included lepton/jet/bb searches key on
> charged leptons or jets. In these models the χ̃₂⁰ energy comes out as a **soft photon**, which
> those selections neither trigger on nor reconstruct — so no amount of lowering *their* thresholds
> reaches it (`R_req` ≫ `reopt_factor`). The photon is the distinct handle, and it requires a
> different object and trigger. The soft **opposite-sign dilepton** route (χ̃₁⁺χ̃₁⁻ → soft ℓℓ) is the
> *re-optimisation* of the existing `Compressed` search, included here only as a complementary
> cross-check region — it is **not** what makes these models holes.

## Signal process

```
pp → χ̃₁±χ̃₂⁰   via Drell-Yan (W*),  recoiling against a hard ISR jet
   χ̃₂⁰ → χ̃₁⁰ γ        (soft photon; BR ≈ 69% for 770)         <- the distinctive handle
   χ̃₁± → χ̃₁⁰ ℓ±ν      (soft lepton; BR ≈ 35% to e/µ, prompt)   <- complementary tag
```

The photon energy is set by the χ̃₂⁰–χ̃₁⁰ splitting (a few GeV, hence *soft*); the two χ̃₁⁰ plus the
neutrino carry the missing transverse momentum. The associated χ̃₂⁰χ̃₁⁰ channel gives the cleanest
**single-soft-photon + ISR + Eᵀmiss** topology; χ̃₁±χ̃₂⁰ adds a soft lepton for a lower-background tag.

## Strategy

| Element | Choice | Why |
|---|---|---|
| **Trigger** | Eᵀmiss trigger, threshold ~200 GeV | the soft photon (and any soft lepton) cannot trigger; the ISR recoil provides the Eᵀmiss |
| **Objects** | **low-pT photon** (pT ≳ 10 GeV, including converted γ); ISR jet(s); Eᵀmiss; optional soft e/µ (pT ≳ 3–4 GeV) | low-pT photon reconstruction/ID against π⁰ and fakes is *the* dedicated ingredient |
| **Preselection** | ≥1 ISR jet (pT ≳ 100 GeV); Eᵀmiss ≳ 200 GeV; ≥1 soft photon; b-jet veto; (optional) ≤1 soft lepton | isolate the ISR-recoil radiative-compressed topology |

### Discriminating variables
- **Eᵀ(γ)** and **Eᵀ(γ)/Eᵀmiss ≈ Δm/m** — both track the compression; the soft-photon spectrum peaks at ~Δm/2.
- **Δφ(Eᵀmiss, ISR jet)** (back-to-back), **min Δφ(jet, Eᵀmiss)** (reject mis-measured jets).
- **Eᵀmiss-significance**; in the χ̃₁±χ̃₂⁰ region, the soft lepton's pT and mᵀ(ℓ, Eᵀmiss).

### Signal regions
Binned in **Eᵀ(γ)** (soft, ≈ 1–15 GeV — the spectrum sweeps Δm) × **Eᵀmiss**, split by soft-lepton
multiplicity (0ℓ: χ̃₂⁰χ̃₁⁰; 1ℓ: χ̃₁±χ̃₂⁰). The hardest (most compressed) points like 770 populate the
lowest Eᵀ(γ) bins, exactly where no existing search has an object to select.

### Backgrounds and estimation
| Background | Source | Estimate |
|---|---|---|
| Fake photons | jets / π⁰ → "photon" | **data-driven** from a photon-ID sideband (loose-not-tight) |
| Z(→νν)+γ, W(→ℓν)+γ | real soft γ + genuine Eᵀmiss | MC normalised in a dedicated CR |
| Z(→νν)+jets, W+jets | jet faking γ, real Eᵀmiss | folded into the fake-photon estimate + CR |
| Drell-Yan / γ+jets | mis-measured Eᵀmiss | min Δφ(jet,Eᵀmiss) + Eᵀmiss-significance |

Each gets a control region (normalisation) and a validation region (closure) adjacent to the SRs.

### Systematics
Fake-photon factor (dominant), low-pT photon reco/ID/isolation efficiency, jet/Eᵀmiss scale &
resolution, pile-up, and MC theory (Vγ). The fake-photon estimate and the soft-photon efficiency
are what a dedicated analysis must control to open this final state.

### Interpretation
CLs limits in the (m(χ̃₁⁰), Δm) plane. 770 sits at m ≈ 183 GeV, Δm ≈ 4.5 GeV — invisible to the
current programme because its visible energy is a soft *photon*, not a lepton or jet. A dedicated
soft-photon SR is what gives any handle at all.

## What the toy in the pipeline does (and does not)

`workflow/scripts/sensitivity.py` is **not** a detector simulation. It is data-anchored: for each
benchmark it reads the **real** per-model expected CLs (best of the 8 recastable searches) from
`merged.parquet`, converts it to an expected limit on signal strength via the asymptotic
`ExpCLs(µ)=2(1−Φ(µ/σ))`, and projects it in signal-strength space (`µ₉₅ ∝ 1/√L`, the physically
correct monotonic scaling — unlike the √L *significance* heuristic used elsewhere, see the caveat
in `project.py`). The output is **`R_req`** = the factor by which a dedicated search must beat the
best current search to exclude the model at the target luminosity: `R_req ≤ 1` ⇒ luminosity alone
suffices; `R_req ≤ assumed_improvement` ⇒ a realistic dedicated search could. The single tunable
input is `assumed_improvement` (`sensitivity:` block in `config/config.yaml`); everything else is
the measured per-model sensitivity. It gives the **required improvement**, not a simulated limit —
a real result needs full signal+background simulation and the data-driven fake-photon estimate above.
