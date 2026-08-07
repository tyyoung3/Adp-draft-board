"""
Fetches Sleeper and FantasyPros Average Draft Position (ADP).

IMPORTANT CAVEAT: Sleeper does not publish an official ADP API. Their
documented public API (api.sleeper.app) covers users/leagues/rosters/drafts/
players, but nowhere exposes platform-wide ADP. Real Sleeper ADP only shows
up inside their own app UI (built from real draft data) and is mirrored by
a handful of third-party fantasy sites.

This module scrapes BeatADP (beatadp.com/platform-adp), which renders a
server-side table comparing ADP across platforms (Sleeper, ESPN, Yahoo,
Underdog, FantasyPros) and updates it daily. We pull the Sleeper and
FantasyPros columns from it. Because this is a third-party site rather
than sleeper.com itself, this is the most fragile part of the pipeline —
if BeatADP changes their page layout, this will need updating (it's
isolated to this one file on purpose).
"""

import re
import requests
from bs4 import BeautifulSoup

BEATADP_URL = "https://www.beatadp.com/platform-adp"

NFL_TEAMS = {
    "ATL", "BUF", "CHI", "CIN", "CLE", "DAL", "DEN", "DET", "GB", "TEN",
    "IND", "KC", "LV", "LAR", "MIA", "MIN", "NE", "NO", "NYG", "NYJ",
    "PHI", "ARI", "PIT", "LAC", "SF", "SEA", "TB", "WSH", "CAR", "JAX",
    "BAL", "HOU",
}


def _split_name_team(cell_text: str):
    cell_text = cell_text.strip()
    for team in NFL_TEAMS:
        if cell_text.endswith(team) and len(cell_text) > len(team):
            return cell_text[: -len(team)].strip(), team
    return cell_text, None


def _parse_number(text: str):
    text = text.strip().replace(",", "")
    if text in ("", "—", "-", "–", "N/A"):
        return None
    try:
        return float(text)
    except ValueError:
        return None


def get_sleeper_adp(timeout: int = 20):
    """
    Returns a list of dicts:
        {"name": str, "team": str or None,
         "sleeper_adp": float or None, "fantasypros_adp": float or None}

    A row is included as long as at least one of sleeper_adp /
    fantasypros_adp is present.
    """
    headers = {"User-Agent": "Mozilla/5.0 (draft-board local script)"}
    resp = requests.get(BEATADP_URL, headers=headers, timeout=timeout)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    table = soup.find("table")
    if table is None:
        raise RuntimeError(
            "Couldn't find a <table> on the BeatADP page — the site layout "
            "likely changed. Check scrapers/sleeper.py."
        )

    header_cells = [th.get_text(strip=True).lower() for th in table.find_all("th")]
    if not header_cells:
        first_row = table.find("tr")
        header_cells = [td.get_text(strip=True).lower() for td in first_row.find_all("td")] if first_row else []

    if "sleeper" not in header_cells:
        raise RuntimeError(
            "Couldn't find a 'Sleeper' column on the BeatADP page — the "
            "site layout likely changed. Check scrapers/sleeper.py."
        )
    sleeper_idx = header_cells.index("sleeper")
    fp_idx = header_cells.index("fantasypros") if "fantasypros" in header_cells else None

    max_needed_idx = max(sleeper_idx, fp_idx if fp_idx is not None else 0)

    out = []
    rows = table.find_all("tr")
    for row in rows:
        cells = row.find_all("td")
        if not cells or len(cells) <= max_needed_idx:
            continue

        name_cell = None
        for c in cells:
            if c.find("a") is not None:
                name_cell = c
                break
        if name_cell is None:
            continue

        raw_name_text = name_cell.get_text(" ", strip=True)
        raw_name_text = re.sub(r"\s+", " ", raw_name_text)
        name, team = _split_name_team(raw_name_text.replace(" ", "", 0))
        if team is None and " " in raw_name_text:
            parts = raw_name_text.rsplit(" ", 1)
            if len(parts) == 2 and parts[1] in NFL_TEAMS:
                name, team = parts[0], parts[1]
            else:
                name, team = raw_name_text, None

        sleeper_val = _parse_number(cells[sleeper_idx].get_text(strip=True))
        fp_val = _parse_number(cells[fp_idx].get_text(strip=True)) if fp_idx is not None else None

        if not name or (sleeper_val is None and fp_val is None):
            continue

        out.append({
            "name": name.strip(),
            "team": team,
            "sleeper_adp": round(sleeper_val, 1) if sleeper_val is not None else None,
            "fantasypros_adp": round(fp_val, 1) if fp_val is not None else None,
        })

    if not out:
        raise RuntimeError(
            "Parsed 0 rows from BeatADP. Either the page changed or the "
            "request was blocked. Check scrapers/sleeper.py."
        )

    out.sort(key=lambda x: (x["sleeper_adp"] is None, x["sleeper_adp"] if x["sleeper_adp"] is not None else 9999))
    return out
