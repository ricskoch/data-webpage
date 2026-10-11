"""Score normalization, levels A, B, C (spec 12.8). Pure functions; native scores are never changed.

Direction is decided in this order: a person's study-level confirmation (dataset.yaml direction_overrides), the
method's documented convention, the known-biology test (core-essential vs non-essential genes), else unknown with
all effect columns null. Reference genes are split into two fixed halves: half A sets direction and scale, half B
is kept apart for the known-biology check, so the check is not graded on the genes that defined the scale.
"""
import numpy as np
import pandas as pd

MAD_TO_SD = 1.4826
EFFECTS = ["effect_rank", "effect_scaled", "effect_z"]


def classify_scores(score_defs, config):
    """Add method_family, signed, direction and direction_evidence to score_defs from dataset.yaml."""
    fam = config["score_families"]
    get = lambda name, key, default: fam.get(name, {}).get(key, default)
    d = score_defs.copy()
    d["method_family"] = d["native_name"].map(lambda n: get(n, "family", "other"))
    d["signed"] = d["native_name"].map(lambda n: get(n, "signed", True))
    d["nonlinear"] = d["native_name"].map(lambda n: get(n, "nonlinear", False))
    d["direction"] = [get(n, "direction", "unknown") if s else "unsigned" for n, s in zip(d["native_name"], d["signed"])]
    d["direction_evidence"] = np.where(d["direction"].isin(["lower_is_depleted", "higher_is_depleted"]),
                                       "documented", np.where(d["signed"], "unresolved", "not_applicable"))
    return d


def primary_positions(score_defs):
    """Per screen, the first score column with a sign. Screens with only unsigned scores are absent."""
    signed = score_defs[score_defs["signed"]]
    return signed.sort_values("position").groupby("screen_id")["position"].first().to_dict()


def split_reference(genes):
    """Sort Entrez IDs and alternate: half A gets the 1st, 3rd, 5th ..., half B the rest."""
    ordered = sorted(genes)
    return set(ordered[0::2]), set(ordered[1::2])


def effect_rank(aligned):
    """Level A: rank percentile within the screen, 0 = most depleted, 1 = most enriched, ties averaged."""
    n = aligned.notna().sum()
    if n < 2:
        return pd.Series(np.nan, index=aligned.index)
    return (aligned.rank(method="average") - 1) / (n - 1)


def effect_z(aligned):
    """Level C: robust z, (score - median) / (1.4826 x MAD). Null when MAD is 0."""
    med = aligned.median()
    mad = (aligned - med).abs().median()
    if not mad > 0:
        return pd.Series(np.nan, index=aligned.index)
    return (aligned - med) / (MAD_TO_SD * mad)


def effect_scaled(aligned, is_ceg, is_neg):
    """Level B: 0 = median non-essential, -1 = median core-essential. Caller checks the anchors separate."""
    m_neg, m_ceg = aligned[is_neg].median(), aligned[is_ceg].median()
    return (aligned - m_neg) / (m_neg - m_ceg)


def _separation(score, is_ceg, is_neg):
    """(median NEG - median CEG) in robust SDs of the whole screen. Positive = essentials score lower."""
    mad = (score - score.median()).abs().median()
    if not mad > 0:
        return 0.0
    return float((score[is_neg].median() - score[is_ceg].median()) / (MAD_TO_SD * mad))


def normalize_screen(score, gene_id, meta, direction, evidence, nonlinear, ceg_halves, neg_halves, config):
    """One screen's primary score -> (effect columns, screen info). See module docstring for the rules."""
    p = config["normalization"]
    genes = gene_id.astype("float")
    in_set = lambda s: genes.isin(list(s))
    ceg_a, ceg_b, neg_a, neg_b = (in_set(s) for s in (*ceg_halves, *neg_halves))
    n_ceg, n_neg = int((ceg_a | ceg_b).sum()), int((neg_a | neg_b).sum())
    full = meta["result_scope"] == "all_genes"
    negative = meta["selection_type"] == "negative"
    enough = n_ceg >= p["min_reference_genes"] and n_neg >= p["min_reference_genes"]

    override = p.get("direction_overrides", {}).get(meta["study_id"])
    if override:
        direction, evidence = override, "human_confirmed"
    elif direction == "unknown" and full and negative and enough:
        sep = _separation(score, ceg_a, neg_a)
        if abs(sep) >= p["min_separation"]:
            direction = "lower_is_depleted" if sep > 0 else "higher_is_depleted"
            evidence = "known_biology_test"

    info = {"direction": direction, "direction_evidence": evidence, "n_ceg_present": n_ceg,
            "n_neg_present": n_neg, "known_biology_pass": None, "scale_note": None}
    cols = {c: pd.Series(np.nan, index=score.index) for c in EFFECTS}
    if direction not in ("lower_is_depleted", "higher_is_depleted") or not full:
        info["normalization_status"] = "not_comparable"
        return cols, info

    aligned = score if direction == "lower_is_depleted" else -score
    cols["effect_rank"] = effect_rank(aligned)
    cols["effect_z"] = effect_z(aligned)
    if negative and enough:
        info["known_biology_pass"] = bool(aligned[ceg_b].median() < aligned[neg_b].median())
        if aligned[ceg_a].median() < aligned[neg_a].median():
            cols["effect_scaled"] = effect_scaled(aligned, ceg_a, neg_a)
            info["scale_note"] = "nonlinear" if nonlinear else None
    if cols["effect_scaled"].notna().any():
        info["normalization_status"] = "anchored"
    elif cols["effect_z"].notna().any():
        info["normalization_status"] = "robust_z"
    else:
        info["normalization_status"] = "rank_only"
    return cols, info


def read_reference(path):
    """Hart-lab gene list (tab file with an ENTREZ_ID column) -> set of Entrez IDs."""
    d = pd.read_csv(path, sep="\t", dtype=str)
    return {int(g) for g in d["ENTREZ_ID"] if str(g).isdigit()}


def apply_normalization(results, screens, score_defs, ceg, neg, config):
    """Add effect columns to results and direction/normalization fields to screens and score_defs."""
    defs = classify_scores(score_defs, config)
    primary = primary_positions(defs)
    by_pos = defs.set_index(["screen_id", "position"])
    ceg_h, neg_h = split_reference(ceg), split_reference(neg)
    effects = {c: np.full(len(results), np.nan, dtype="float32") for c in EFFECTS}
    meta = screens.set_index("screen_id")
    rows = []
    for sid, idx in results.groupby("screen_id", observed=True).indices.items():
        pos = primary.get(sid)
        if pos is None:
            rows.append({"screen_id": sid, "primary_score_position": None, "direction": "unsigned",
                         "direction_evidence": "not_applicable", "normalization_status": "not_comparable"})
            continue
        d = by_pos.loc[(sid, pos)]
        part = results.iloc[idx]
        cols, info = normalize_screen(part[f"score_{pos}"].reset_index(drop=True),
                                      part["gene_id"].reset_index(drop=True), meta.loc[sid], d["direction"],
                                      d["direction_evidence"], bool(d["nonlinear"]), ceg_h, neg_h, config)
        for c in EFFECTS:
            effects[c][idx] = cols[c].to_numpy(dtype="float32")
        rows.append({"screen_id": sid, "primary_score_position": pos, **info})
    info = pd.DataFrame(rows)
    screens = screens.merge(info, on="screen_id", how="left")
    screens["normalization_status"] = screens["normalization_status"].fillna("not_comparable")
    prim = info.dropna(subset=["primary_score_position"]).astype({"primary_score_position": int})
    key = prim.set_index(["screen_id", "primary_score_position"])
    idx = pd.MultiIndex.from_frame(defs[["screen_id", "position"]])
    hit = idx.isin(key.index)
    defs.loc[hit, "direction"] = key.loc[idx[hit], "direction"].to_numpy()
    defs.loc[hit, "direction_evidence"] = key.loc[idx[hit], "direction_evidence"].to_numpy()
    return results.assign(**effects), screens, defs


def known_biology_summary(results, screens, config):
    """Spec 14.3: share of eligible screens where core essentials (half B) are depleted; controls near zero."""
    eligible = screens[screens["known_biology_pass"].notna()]
    share = float(eligible["known_biology_pass"].astype(bool).mean()) if len(eligible) else None
    ctrl = results[results["gene_id_status"].eq("control") & results["effect_z"].notna()]
    med = ctrl.groupby("screen_id", observed=True)["effect_z"].agg(["median", "size"])
    med = med[med["size"] >= 10]
    return {
        "normalization_status": screens["normalization_status"].value_counts().to_dict(),
        "direction_evidence": screens["direction_evidence"].value_counts().to_dict(),
        "essentials_depleted": {"eligible_screens": int(len(eligible)), "pass_share": share,
                                "required_share": config["normalization"]["known_biology_pass_share"],
                                "outliers": eligible.loc[~eligible["known_biology_pass"].astype(bool),
                                                         "screen_id"].tolist()},
        "controls_near_zero": {"screens_with_10_controls": int(len(med)),
                               "share_abs_median_z_below_1": float((med["median"].abs() < 1).mean()) if len(med)
                               else None},
        "passed": share is not None and share >= config["normalization"]["known_biology_pass_share"],
    }
