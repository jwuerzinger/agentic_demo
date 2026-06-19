"""Parse every SLHA spectrum in a scan tarball into a flat feature table.

For each model we extract, directly from the SPheno SLHA output:
  * input parameters   M1, M2, mu, tan(beta), mA      (Block EXTPAR/MINPAR)
  * physical masses    neutralinos, charginos, sleptons, ...  (Block MASS)
  * LSP composition    bino/wino/higgsino fractions    (Block NMIX, row 1)
  * chargino lifetime  ctau from the total width        (DECAY 1000024)
  * dominant decays    of chi2^0 and chi1^+             (DECAY tables)

Derived mass splittings and composition labels are computed downstream
(classify.py) so the raw, auditable numbers live here.

Run as a Snakemake `script:` (reads the injected `snakemake` object).
"""
import tarfile
import pandas as pd

# ħc = 0.1973269804 GeV·fm ; 1 fm = 1e-12 mm  ->  ħc in GeV·mm
HBAR_C_GEV_MM = 0.1973269804e-12

# PDG ids we keep from the MASS block
MASS_PDG = {
    "m_n1": 1000022, "m_n2": 1000023, "m_n3": 1000025, "m_n4": 1000035,
    "m_c1": 1000024, "m_c2": 1000037,
    "m_seL": 1000011, "m_seR": 2000011, "m_smuL": 1000013, "m_smuR": 2000013,
    "m_stau1": 1000015, "m_stau2": 2000015,
    "m_snu_e": 1000012, "m_snu_mu": 1000014, "m_snu_tau": 1000016,
    "m_gluino": 1000021, "m_stop1": 1000006, "m_sbot1": 1000005,
    "m_h": 25, "m_A": 36,
}
# charged-slepton PDGs, used to find the lightest slepton in the cascade
SLEP_CHARGED = [1000011, 2000011, 1000013, 2000013, 1000015, 2000015]


def parse_one(text):
    """Parse a single SLHA file (string) into a dict of features."""
    mass = {}
    extpar = {}
    minpar = {}
    nmix = {}                  # (i,j) -> value
    widths = {}                # pdg -> total width
    decays = {1000023: [], 1000024: []}   # pdg -> list of (BR, (daughters...))

    block = None               # current block tag (lower-case) or "decay"
    decay_pdg = None           # pdg of the DECAY block currently open

    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        low = line.lower()

        if low.lstrip().startswith("block"):
            block = low.split()[1] if len(low.split()) > 1 else None
            decay_pdg = None
            continue
        if low.lstrip().startswith("decay"):
            tok = line.split()
            block = "decay"
            try:
                decay_pdg = int(tok[1])
                widths[decay_pdg] = float(tok[2])
            except (ValueError, IndexError):
                decay_pdg = None
            continue

        tok = line.split()
        try:
            if block == "mass":
                mass[int(tok[0])] = abs(float(tok[1]))
            elif block == "extpar":
                extpar[int(tok[0])] = float(tok[1])
            elif block == "minpar":
                minpar[int(tok[0])] = float(tok[1])
            elif block == "nmix":
                nmix[(int(tok[0]), int(tok[1]))] = float(tok[2])
            elif block == "decay" and decay_pdg in decays:
                br = float(tok[0])
                nda = int(tok[1])
                daughters = tuple(int(x) for x in tok[2:2 + nda])
                decays[decay_pdg].append((br, daughters))
        except (ValueError, IndexError):
            continue

    out = {}
    for name, pdg in MASS_PDG.items():
        out[name] = mass.get(pdg, float("nan"))

    # Input parameters
    out["M1"] = extpar.get(1, float("nan"))
    out["M2"] = extpar.get(2, float("nan"))
    out["mu"] = extpar.get(23, float("nan"))
    out["mA_in"] = extpar.get(26, float("nan"))
    out["tanb"] = minpar.get(3, extpar.get(25, float("nan")))

    # LSP (neutralino 1) composition from NMIX row 1: |B|^2,|W|^2,|Hd|^2+|Hu|^2
    n11, n12 = nmix.get((1, 1), 0.0), nmix.get((1, 2), 0.0)
    n13, n14 = nmix.get((1, 3), 0.0), nmix.get((1, 4), 0.0)
    norm = n11 * n11 + n12 * n12 + n13 * n13 + n14 * n14
    norm = norm if norm > 0 else 1.0
    out["f_bino"] = n11 * n11 / norm
    out["f_wino"] = n12 * n12 / norm
    out["f_higgsino"] = (n13 * n13 + n14 * n14) / norm

    # Chargino lifetime (proxy for disappearing-track signature)
    w = widths.get(1000024, float("nan"))
    if w is not None and w > 0:
        out["ctau_c1_mm"] = HBAR_C_GEV_MM / w
    else:
        out["ctau_c1_mm"] = float("inf")   # width 0 / not computed => effectively stable

    # Dominant decay channel of chi2^0 and chi1^+ (by branching ratio)
    def dominant(pdg):
        chans = decays.get(pdg, [])
        if not chans:
            return float("nan"), ()
        return max(chans, key=lambda c: c[0])

    br_n2, dau_n2 = dominant(1000023)
    br_c1, dau_c1 = dominant(1000024)
    out["n2_br"] = br_n2
    out["n2_daughters"] = "|".join(str(d) for d in dau_n2)
    out["c1_br"] = br_c1
    out["c1_daughters"] = "|".join(str(d) for d in dau_c1)

    # --- summed branching ratios of chi2^0 and chi1^+ by final state ---
    # The LSP (1000022) recoils invisibly; bucket each decay by what accompanies it. On-shell
    # 2-body decays give chi1 + {Z, h, gamma, W}; off-shell (compressed) 3-body decays give
    # chi1 + a fermion pair. These SUMMED BRs (not just the single dominant channel) are what
    # classify.py (WZ/Wh) and project.py (the radiative "uncovered signature" flag) read, so the
    # radiative / WZ / Wh / leptonic determinations all sit on the same footing.
    LEP, TAU, NU, QRK = {11, 13}, {15}, {12, 14, 16}, {1, 2, 3, 4, 5, 6}

    def br_by_final_state(pdg):
        c = dict(Z=0.0, h=0.0, gamma=0.0, W=0.0, pi=0.0, lep=0.0, tau=0.0, qq=0.0, inv=0.0)
        for br, daus in decays.get(pdg, []):
            rest = sorted(abs(d) for d in daus if abs(d) != 1000022)   # strip the invisible LSP
            if rest == [23]:                              c["Z"] += br
            elif rest == [25]:                            c["h"] += br
            elif rest == [22]:                            c["gamma"] += br      # radiative
            elif rest == [24]:                            c["W"] += br
            elif rest == [211]:                           c["pi"] += br         # chi1^+- -> chi1^0 pi^+- (LLP)
            elif any(d in TAU for d in rest):             c["tau"] += br        # tau-containing (test first)
            elif any(d in LEP for d in rest):             c["lep"] += br        # e/mu-containing
            elif rest and all(d in QRK for d in rest):    c["qq"] += br
            elif rest and all(d in NU for d in rest):     c["inv"] += br
        return c

    n2, c1 = br_by_final_state(1000023), br_by_final_state(1000024)
    out["br_n2_Z"], out["br_n2_h"], out["br_n2_gamma"] = n2["Z"], n2["h"], n2["gamma"]
    out["br_n2_ll"], out["br_n2_qq"] = n2["lep"], n2["qq"]   # ll = chi2 -> chi1 ell+ ell- (e/mu)
    out["br_c1_W"], out["br_c1_lep"] = c1["W"], c1["lep"]     # lep = chi1 -> chi1 ell nu (e/mu)
    out["br_c1_tau"], out["br_c1_qq"] = c1["tau"], c1["qq"]

    # lightest charged slepton
    sleps = [mass[p] for p in SLEP_CHARGED if p in mass]
    out["m_slep_light"] = min(sleps) if sleps else float("nan")
    out["light_slep_is_stau"] = bool(sleps) and (
        min(sleps) == min(mass.get(1000015, float("inf")), mass.get(2000015, float("inf")))
    )
    return out


def main():
    tarball = snakemake.input.tarball           # noqa: F821
    scan = snakemake.params.scan                 # noqa: F821
    out_path = snakemake.output[0]               # noqa: F821

    rows, n_fail = [], 0
    with tarfile.open(tarball, "r:gz") as tf:
        for member in tf:
            if not member.name.endswith(".slha"):
                continue
            # filename stem is the Model_number used in the exclusion CSV
            stem = member.name.rsplit("/", 1)[-1][:-len(".slha")]
            try:
                model_number = int(stem)
                fobj = tf.extractfile(member)
                text = fobj.read().decode("utf-8", "replace")
                feat = parse_one(text)
                feat["model_number"] = model_number
                feat["scan"] = scan
                feat["slha_path"] = member.name   # exact tar member, for representative extraction
                rows.append(feat)
            except Exception:
                n_fail += 1

    df = pd.DataFrame(rows).sort_values("model_number").reset_index(drop=True)
    print(f"[{scan}] parsed {len(df)} models, {n_fail} failures")
    df.to_parquet(out_path, index=False)


if __name__ == "__main__":
    main()
