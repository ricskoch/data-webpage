"""Link each drug screen to the untreated screens that can serve as its "no drug" arm (drug page, F22).

ORCS does not link treated and untreated screens, so candidates are found by rule. A candidate is an untreated,
full gene list, timecourse screen of the same cell line, with a signed primary score when the table says (a
screen without one cannot be plotted). Match levels, best first:
  same_study_library  same study and library (the paper's own control arm)
  same_study          same study, other library
  same_cell_line      another study on the same cell line (lab-to-lab differences included; shown as weaker)
Within a level, a candidate with the same library comes first, then by screen ID so the order is stable.
Drug screens without any candidate are kept with match "none", never dropped.
"""
import re

import pandas as pd

DRUG_SETUP = "Drug Exposure"
CONTROL_SETUP = "Timecourse"
LEVELS = ["same_study_library", "same_study", "same_cell_line"]
COLUMNS = ["screen_id", "control_screen_id", "match", "rank"]


def cell_key(label):
    """Compare cell line labels ignoring case, spaces and punctuation: 'HAP-1' == 'HAP1'. Missing -> None."""
    if label is None or (isinstance(label, float) and pd.isna(label)):
        return None
    key = re.sub(r"[^0-9a-z]", "", str(label).lower())
    return key or None


def control_candidates(screens, max_other_study=3):
    """One row per (drug screen, candidate control), ranked; at most max_other_study same_cell_line rows each."""
    s = screens.assign(cell=screens["cell_line_label"].map(cell_key))
    drugs = s[s["experimental_setup"].eq(DRUG_SETUP)]
    scored = s["primary_score_position"].notna() if "primary_score_position" in s else True
    controls = s[s["treatment"].isna() & s["experimental_setup"].eq(CONTROL_SETUP)
                 & s["result_scope"].eq("all_genes") & s["cell"].notna() & scored]
    by_cell = dict(tuple(controls.groupby("cell")))
    rows = []
    for _, d in drugs.sort_values("screen_id").iterrows():
        pool = by_cell.get(d["cell"], controls.iloc[0:0])
        same_study = pool["study_id"].eq(d["study_id"])
        same_lib = pool["library_name"].eq(d["library_name"])
        level = pd.Series("same_cell_line", index=pool.index)
        level[same_study & same_lib] = "same_study_library"
        level[same_study & ~same_lib] = "same_study"
        ranked = pool.assign(level=level.map(LEVELS.index), other_lib=~same_lib).sort_values(
            ["level", "other_lib", "screen_id"])
        ranked = pd.concat([ranked[ranked["level"] < 2], ranked[ranked["level"] == 2].head(max_other_study)])
        if ranked.empty:
            rows.append({"screen_id": d["screen_id"], "control_screen_id": None, "match": "none", "rank": None})
        for i, (cid, lv) in enumerate(zip(ranked["screen_id"], ranked["level"]), start=1):
            rows.append({"screen_id": d["screen_id"], "control_screen_id": cid, "match": LEVELS[lv], "rank": i})
    out = pd.DataFrame(rows, columns=COLUMNS).astype(object)
    return out.where(out.notna(), None)


def summary(candidates):
    """How many drug screens there are and how good their best candidate is."""
    best = candidates.drop_duplicates("screen_id")["match"].value_counts()
    return {"drug_screens": int(candidates["screen_id"].nunique()), "best_match": {k: int(v) for k, v in best.items()}}
