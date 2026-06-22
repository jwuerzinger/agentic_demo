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

The radiative photon is **soft**: its rest-frame energy is `E_γ = (m₂²−m₁²)/2m₂ ≈ Δm(χ̃₂⁰,χ̃₁⁰)` — a
*few* GeV. The hard ISR jet that the system recoils against boosts it modestly into the lab frame
(to ~5–20 GeV for an O(100–200 GeV) ISR jet), and the two χ̃₁⁰ plus the neutrino carry the Eᵀmiss.

### Reach floor and the two production channels (the make-or-break)

- **Reach floor.** Because `E_γ ≈ Δm`, the search has a hard *low-Δm* limit: below `Δm ≈ 3 GeV`
  (`config: photon_recon_dm_min_gev`) the photon is too soft to reconstruct or trigger-assist even
  with dedicated low-Eᵀ / converted-photon methods. The *most* compressed holes are therefore likely
  beyond **both** the lepton search and this one — honest "edge of any reach" territory. The sweet
  spot is intermediate Δm (≈ 3–8 GeV): photon hard enough to see, splittings still too small for the
  soft-lepton search. (The report's hole table flags photon-reachable vs ultra-compressed counts.)
- **Two channels.**
  - **0ℓ: χ̃₂⁰χ̃₁⁰ → γ + ISR + Eᵀmiss.** Highest rate, but swamped by Z(→νν)+γ and fake photons at
    low Eᵀ — viable only if low-Eᵀ photon ID and the fake estimate are under tight control.
  - **1ℓ: χ̃₁±χ̃₂⁰ → γ + soft ℓ + ISR + Eᵀmiss.** Lower rate, but the soft-lepton tag suppresses the
    QCD/fake-photon background by orders of magnitude. **For the genuinely compressed holes this is
    likely the *more* sensitive channel**, despite the rate cost — it is where a dedicated search
    most plausibly beats the lepton-only re-optimisation.

## Strategy

| Element | Choice | Why |
|---|---|---|
| **Trigger** | Eᵀmiss trigger, threshold ~200 GeV | the soft photon (and any soft lepton) cannot trigger; the ISR recoil provides the Eᵀmiss |
| **Objects** | photon down to **the lowest Eᵀ reconstruction allows** (~5–10 GeV; **converted** photons extend lower); ISR jet(s); Eᵀmiss; soft e/µ (pT ≳ 3–4 GeV) for the 1ℓ channel | pushing low-Eᵀ photon reco/ID below the standard ~25 GeV threshold is *the* dedicated ingredient and the make-or-break |
| **Preselection** | ≥1 ISR jet (pT ≳ 100 GeV); Eᵀmiss ≳ 200 GeV; ≥1 soft photon; b-jet veto; split by soft-lepton multiplicity (0ℓ / 1ℓ) | isolate the ISR-recoil radiative-compressed topology |

### Discriminating variables
- **Eᵀ(γ)** and **Eᵀ(γ)/Eᵀmiss** — the photon spectrum endpoint tracks Δm, exactly as `m(ℓℓ)` does
  for the soft-dilepton search; the single most powerful variable, scanned in fine bins.
- **Δφ(Eᵀmiss, ISR jet)** (back-to-back), **min Δφ(jet, Eᵀmiss)** (reject mis-measured jets),
  **Eᵀmiss-significance**.
- 1ℓ channel: soft-lepton pT and mᵀ(ℓ, Eᵀmiss).

### Signal regions
Binned in **Eᵀ(γ)** (soft, the endpoint sweeps Δm) × **Eᵀmiss**, in 0ℓ and 1ℓ categories. The lowest
Eᵀ(γ) bins target the hardest (most compressed) points; the reach floor above sets where the binning
stops being meaningful.

### Backgrounds and estimation
| Background | Source | Estimate |
|---|---|---|
| **Fake photons** (dominant at low Eᵀ) | jets / π⁰→γγ misidentified as a photon | **data-driven** from a photon-ID sideband (loose-not-tight / converted-track templates); the limiting systematic |
| Z(→νν)+γ | real soft γ + genuine Eᵀmiss | MC normalised in a dedicated CR; irreducible in 0ℓ |
| W(→ℓν)+γ | real γ + Eᵀmiss + lepton | MC + CR; the main background to the 1ℓ channel (still far smaller than 0ℓ fakes) |
| Drell-Yan / γ+jets | mis-measured Eᵀmiss | min Δφ(jet,Eᵀmiss) + Eᵀmiss-significance |

The **fake-photon rate at low Eᵀ is the analysis-defining challenge** — the photon analogue of the
soft-lepton fake problem. The 1ℓ requirement is the cleanest lever against it.

### Systematics
Fake-photon factor (dominant), low-Eᵀ photon reco/ID/conversion efficiency, jet/Eᵀmiss scale &
resolution, pile-up, MC theory (Vγ). Controlling the fake-photon estimate and the low-Eᵀ photon
efficiency is what a dedicated analysis must do to open this final state.

### Interpretation
CLs limits in the (m(χ̃₁⁰), Δm) plane. 770 (m ≈ 183 GeV, Δm ≈ 4.5 GeV) sits in the sweet spot:
invisible to the current program because its visible energy is a soft *photon*, yet with Δm large
enough that a dedicated soft-photon SR has a genuine handle.

## What the toy in the pipeline does (and does not)

`workflow/scripts/sensitivity.py` is **not** a detector simulation. It is data-anchored: for each
benchmark it reads the **real** per-model expected CLs (best of the 8 recastable searches) from
`merged.parquet`, converts it to an expected limit on signal strength via the asymptotic
`ExpCLs(µ)=2(1−Φ(µ/σ))`, and projects it in signal-strength space (`µ₉₅ ∝ 1/√L`). The output is
**`R_req`** = the improvement needed over the best current search — which, crucially, is the soft-
*lepton* search that uses **none** of the photon. So `R_req` is *lepton-channel-anchored*: a large
value means the lepton search is blind, **not** that a photon search fails. Whether the soft-photon
channel closes that gap is exactly what this metric cannot tell you — it needs the real low-Eᵀ photon
efficiency and fake-photon background above. The verdict (`luminosity` / `lepton re-opt` /
`needs new channel (photon)` / `out of reach`) reports that distinction honestly; the lone tunable
input is `assumed_improvement` (the lepton re-opt gain).
