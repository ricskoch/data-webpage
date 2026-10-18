"""Per-screen score vectors for the drug page (F22): the scatter of a drug screen against its no-drug screen.

The drug page plots each screen's primary score as the paper reports it (not flipped to "low = depleted"),
standardised within the screen as a robust z, (score - median) / (1.4826 x MAD). Richard chose this on 2026-10-11
because the direction of most drug screens cannot be inferred. The page says so next to the plot.
"""
import numpy as np
import pandas as pd

import normalize

Z_DIGITS = 2


def plottable_ids(screens, candidates):
    """Screens that get a vector: drug screens with a control candidate, and those candidates.

    A screen needs a full gene list and a signed primary score (primary_score_position set).
    """
    ok = screens["result_scope"].eq("all_genes") & screens["primary_score_position"].notna()
    usable = set(screens.loc[ok, "screen_id"])
    paired = candidates.dropna(subset=["control_screen_id"])
    drugs = set(paired["screen_id"]) & usable
    controls = set(paired.loc[paired["screen_id"].isin(drugs), "control_screen_id"]) & usable
    return sorted(drugs | controls)


def primary_scores(results, screens, ids):
    """Long table (screen_id, perturbation_id, score): each wanted screen's primary score column."""
    pos = screens.set_index("screen_id")["primary_score_position"]
    parts = []
    wanted = results[results["screen_id"].isin(ids)]
    for sid, part in wanted.groupby("screen_id", observed=True):
        parts.append(pd.DataFrame({"screen_id": str(sid), "perturbation_id": part["perturbation_id"].astype(str).to_numpy(),
                                   "score": part[f"score_{int(pos[sid])}"].to_numpy(dtype="float64")}))
    cols = ["screen_id", "perturbation_id", "score"]
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=cols)


def collapse_duplicates(scores):
    """One score per (screen, perturbation): ORCS can list a gene twice in a screen, so take the median.

    Returns (collapsed table, number of rows folded away) so the loss is reported, not hidden.
    """
    out = scores.dropna(subset=["score"]).groupby(["screen_id", "perturbation_id"], as_index=False, sort=True)["score"].median()
    return out, int(scores["score"].notna().sum() - len(out))


def screen_vector(scores, pert_index):
    """{'i': perturbation indices, 'z': robust z} for one screen, sorted by index; null z (MAD 0) gives no vector."""
    z = normalize.effect_z(scores.set_index("perturbation_id")["score"])
    z = z.dropna()
    if z.empty:
        return None
    pairs = sorted((pert_index[p], round(float(v), Z_DIGITS)) for p, v in z.items())
    return {"i": [i for i, _ in pairs], "z": [v for _, v in pairs]}
