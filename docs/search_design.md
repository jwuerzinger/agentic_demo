# Search design: compressed higgsinos via soft dileptons + ISR

Target: the compressed-higgsino / compressed-bino **coverage holes** (e.g. benchmark
**EWKino 770** — a ~183 GeV higgsino, Δm(χ̃₂⁰,χ̃₁⁰) ≈ 4.5 GeV, Δm(χ̃₁±,χ̃₁⁰) ≈ 2.4 GeV).
These are viable, copiously produced, yet invisible to the current programme because the
decay products are too soft. This is the analysis a dedicated Run-3 search would run.
The toy `sensitivity` step in the pipeline quantifies its (illustrative) reach.

## Signal process

```
pp → χ̃₁⁺χ̃₁⁻  (and χ̃₁±χ̃₂⁰)   via Drell-Yan (γ*/Z*/W*),  recoiling against a hard ISR jet
   χ̃₁± → χ̃₁⁰ ℓ±ν   (soft; BR ≈ 35% to e/µ for 770, prompt)
```

For 770 the χ̃₂⁰ is radiative-dominated (χ̃₂⁰→χ̃₁⁰γ, 69%), so the **chargino-pair → soft
opposite-sign dilepton** channel is the cleanest handle; the χ̃₁±χ̃₂⁰ single-soft-lepton
channel is a complementary region. The leptons are O(1 GeV) (set by the χ̃₁±–χ̃₁⁰ splitting),
and the two χ̃₁⁰ + neutrinos give the missing transverse momentum.

## Strategy

| Element | Choice | Why |
|---|---|---|
| **Trigger** | Eᵀmiss trigger, threshold ~200 GeV | the soft leptons cannot trigger; the ISR recoil provides the Eᵀmiss |
| **Objects** | "soft" e (pT ≳ 4 GeV) / µ (pT ≳ 3 GeV); ISR jet(s); Eᵀmiss | low-pT lepton reconstruction is the key dedicated ingredient |
| **Preselection** | ≥1 ISR jet (pT ≳ 100 GeV); Eᵀmiss ≳ 200 GeV; exactly 2 OS same-flavour leptons; b-jet and τ veto | isolate the ISR-recoil compressed topology, suppress top/heavy-flavour |

### Discriminating variables
- **m(ℓℓ)** — kinematic endpoint ≈ Δm(χ̃₂⁰,χ̃₁⁰); the single most powerful variable, scanned in fine bins.
- **lepton pT** and **pT(ℓℓ)/Eᵀmiss ≈ Δm/m** — both track the compression.
- **mᵀ2(ℓℓ)**, **Δφ(Eᵀmiss, ISR jet)** (back-to-back), **min Δφ(jet, Eᵀmiss)** (reject mis-measured jets).

### Signal regions
Binned in **m(ℓℓ)** (≈ 1–15 GeV, so the endpoint sweeps Δm) × **Eᵀmiss**. Low-m(ℓℓ) bins
target the most compressed (hardest) points like 770; higher bins overlap the existing
`Compressed` search and provide a cross-check.

### Backgrounds and estimation
| Background | Source | Estimate |
|---|---|---|
| Fake / non-prompt leptons | heavy-flavour, π/K → soft "leptons" | **data-driven** fake-factor from a same-sign / anti-id CR |
| WW, Wγ*, Wt | real soft leptons + Eᵀmiss | MC normalised in a dedicated CR |
| Z(→ττ)+jets | τ → soft ℓ | MC + CR, suppressed by mᵀ2 / m(ℓℓ) |
| Drell-Yan (Z/γ*→ℓℓ) | mis-measured Eᵀmiss | min Δφ(jet,Eᵀmiss) + Eᵀmiss-significance |

Each gets a control region (normalisation) and a validation region (closure) adjacent to the SRs.

### Systematics
Fake-factor (dominant), low-pT lepton reco/ID/isolation efficiency, jet/Eᵀmiss scale &
resolution, pile-up, and MC theory (WW). The fake estimate and the soft-lepton efficiency
are what a dedicated analysis must control to beat the current search.

### Interpretation
CLs limits in the (m(χ̃₁⁰), Δm) plane; 770 sits at m ≈ 183 GeV, Δm ≈ 4.5 GeV — just past
the current `Compressed` search's expected reach (expected CLs ≈ 0.90), i.e. in a low-m(ℓℓ)
SR bin that a lower lepton-pT threshold + the Run-3 dataset is designed to open.

## What the toy in the pipeline does (and does not)

`workflow/scripts/sensitivity.py` turns this design into a parametrised cut-and-count
(`S = σ·L·ε(Δm)·BR²`, `B` scaled from a reference SR yield, Asimov `Z` with a background
systematic) to project the **relative** Run-3 reach across the compressed holes and flag 770.
It is **not** a detector simulation — the efficiency turn-on `ε(Δm)` and the background are
config knobs (`sensitivity:` block in `config/config.yaml`), anchored only at the
order-of-magnitude level to the Run-2 compressed-higgsino search
([arXiv:1911.12606](https://arxiv.org/abs/1911.12606)). A real result needs full signal+background
simulation and the data-driven fake estimate above.
