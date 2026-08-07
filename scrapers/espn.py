"""
Scrapes fantasy football Average Draft Position (ADP) from ESPN's public
(undocumented) Fantasy API. No API key or league required.
"""

import requests

ESPN_PRO_TEAM_MAP = {
    0: "FA", 1: "ATL", 2: "BUF", 3: "CHI", 4: "CIN", 5: "CLE", 6: "DAL",
    7: "DEN", 8: "DET", 9: "GB", 10: "TEN", 11: "IND", 12: "KC", 13: "LV",
    14: "LAR", 15: "MIA", 16: "MIN", 17: "NE", 18: "NO", 19: "NYG",
    20: "NYJ", 21: "PHI", 22: "ARI", 23: "PIT", 24: "LAC", 25: "SF",
    26: "SEA", 27: "TB", 28: "WSH", 29: "CAR", 30: "JAX", 33: "BAL",
    34: "HOU",
}

ESPN_POSITION_MAP = {
    1: "QB", 2: "RB", 3: "WR", 4: "TE", 5: "K", 16: "DST",
}

SCORING_MAP = {
    "PPR": "PPR",
    "HALF": "HALF_PPR",
    "STANDARD": "STANDARD",
}


def get_espn_adp(season: int, scoring: str = "PPR", limit: int = 600, timeout: int = 20):
    """
    Fetch ADP for `season` (e.g. 2026) from ESPN.

    Returns a list of dicts:
        {"name": str, "team": str, "position": str, "espn_adp": float}
    """
    scoring_value = SCORING_MAP.get(scoring.upper(), "PPR")

    # NOTE: ESPN's fantasy API moved off fantasy.espn.com to this
    # subdomain — fantasy.espn.com/apis/... now just returns the regular
    # website HTML instead of JSON. If ESPN moves it again, this is the
    # line to fix.
    url = f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{season}/segments/0/leaguedefaults/3"
    params = {"view": "kona_player_info"}
    headers = {
        "x-fantasy-filter": (
            '{"players":{"limit":%d,'
            '"sortDraftRanks":{"sortPriority":100,"sortAsc":true,"value":"%s"},'
            '"filterStatsForTopScoringPeriodId":{"value":1}}}' % (limit, scoring_value)
        ),
        "User-Agent": "Mozilla/5.0 (draft-board local script)",
    }

    resp = requests.get(url, params=params, headers=headers, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()

    players_raw = data.get("players")
    if not players_raw:
        raise ValueError(
            "ESPN response didn't contain a 'players' list. ESPN may have "
            "changed their API shape — check espn.py."
        )

    out = []
    for entry in players_raw:
        p = entry.get("player", {})
        ownership = p.get("ownership", {}) or {}
        adp = ownership.get("averageDraftPosition")
        if adp is None or adp <= 0:
            continue

        name = p.get("fullName") or f"{p.get('firstName', '')} {p.get('lastName', '')}".strip()
        team = ESPN_PRO_TEAM_MAP.get(p.get("proTeamId"), "FA")
        position = ESPN_POSITION_MAP.get(p.get("defaultPositionId"), "?")

        out.append({
            "name": name,
            "team": team,
            "position": position,
            "espn_adp": round(float(adp), 1),
        })

    if not out:
        raise ValueError(
            "Parsed 0 players with an ADP from ESPN's response. Either it's "
            "very early in the offseason (ESPN hasn't got draft data yet) "
            "or the response shape changed."
        )

    out.sort(key=lambda x: x["espn_adp"])
    return out
