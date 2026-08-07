"""Combines ESPN ADP + Sleeper/FantasyPros ADP lists into one merged
player list, matched by normalized player name."""

import re

SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}


def normalize_name(name: str) -> str:
    name = name.lower()
    name = name.replace(".", "").replace("'", "").replace("-", " ")
    name = re.sub(r"\s+", " ", name).strip()
    parts = [p for p in name.split(" ") if p not in SUFFIXES]
    return " ".join(parts)


def merge_sources(espn_list, sleeper_list):
    """
    espn_list: [{"name","team","position","espn_adp"}, ...]
    sleeper_list: [{"name","team","sleeper_adp","fantasypros_adp"}, ...]

    Returns a list of dicts with id, name, team, position, espn_adp,
    sleeper_adp, fantasypros_adp, diff (sleeper_adp - espn_adp), and
    consensus_adp (average of whichever sources are present).
    """
    sleeper_by_key = {}
    for row in sleeper_list:
        key = normalize_name(row["name"])
        sleeper_by_key.setdefault(key, row)

    merged = {}
    for row in espn_list:
        key = normalize_name(row["name"])
        merged[key] = {
            "id": key.replace(" ", "-"),
            "name": row["name"],
            "team": row["team"],
            "position": row["position"],
            "espn_adp": row["espn_adp"],
            "sleeper_adp": None,
            "fantasypros_adp": None,
        }
        sleeper_row = sleeper_by_key.pop(key, None)
        if sleeper_row:
            merged[key]["sleeper_adp"] = sleeper_row.get("sleeper_adp")
            merged[key]["fantasypros_adp"] = sleeper_row.get("fantasypros_adp")
            if merged[key]["team"] in (None, "FA") and sleeper_row.get("team"):
                merged[key]["team"] = sleeper_row["team"]

    for key, row in sleeper_by_key.items():
        merged[key] = {
            "id": key.replace(" ", "-"),
            "name": row["name"],
            "team": row.get("team"),
            "position": None,
            "espn_adp": None,
            "sleeper_adp": row.get("sleeper_adp"),
            "fantasypros_adp": row.get("fantasypros_adp"),
        }

    out = list(merged.values())
    for row in out:
        if row["espn_adp"] is not None and row["sleeper_adp"] is not None:
            row["diff"] = round(row["sleeper_adp"] - row["espn_adp"], 1)
        else:
            row["diff"] = None
        vals = [v for v in (row["espn_adp"], row["sleeper_adp"], row["fantasypros_adp"]) if v is not None]
        row["consensus_adp"] = round(sum(vals) / len(vals), 1) if vals else 9999.0

    out.sort(key=lambda r: r["consensus_adp"])
    return out
