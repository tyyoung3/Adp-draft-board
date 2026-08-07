"""
Live Draft ADP Board
=====================
Pulls fantasy football ADP from ESPN (public API) and Sleeper (mirrored via
BeatADP, see scrapers/sleeper.py for why), and serves a dashboard showing
them side by side. Which players are "drafted" is tracked in the browser
(localStorage), not on the server, so it works the same whether you're
running this locally or hosting it on something like Render for iPad-only
access.

Local run:
    pip install -r requirements.txt
    python app.py
Then open http://127.0.0.1:5050

Hosted (e.g. Render): see README.md for deploy steps. Render sets a PORT
env var, which this respects automatically.
"""

import json
import os
import datetime

from flask import Flask, jsonify, request, render_template

from scrapers.espn import get_espn_adp
from scrapers.sleeper import get_sleeper_adp, load_half_ppr_seed
from scrapers.merge import merge_sources

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_DIR, "data")
PLAYERS_FILE = os.path.join(DATA_DIR, "players.json")

os.makedirs(DATA_DIR, exist_ok=True)

app = Flask(__name__)


# ---------------------------------------------------------------- helpers --

def _current_season_guess():
    now = datetime.datetime.now()
    return now.year if now.month >= 3 else now.year - 1


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return default


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


# ------------------------------------------------------------------ routes --

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/players", methods=["GET"])
def api_get_players():
    # Note: "drafted" is NOT applied here anymore — that lives in the
    # browser's localStorage on the client, so the server can be stateless
    # across restarts/redeploys on hosts with ephemeral disks.
    players = load_json(PLAYERS_FILE, {"players": [], "fetched_at": None})
    return jsonify(players)


@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    body = request.get_json(silent=True) or {}
    season = int(body.get("season") or _current_season_guess())
    requested_scoring = body.get("scoring", "PPR").upper()

    notes = []
    errors = {}
    espn_list, sleeper_list = [], []

    # ESPN's draft-rank API only accepts PPR/STANDARD sort values — it 400s
    # on half-PPR, and BeatADP's own half-PPR table shows ESPN as entirely
    # unavailable there too (ESPN just doesn't publish half-PPR ADP at
    # all). Fall back to PPR for the ESPN column rather than erroring.
    espn_scoring = requested_scoring
    if requested_scoring == "HALF":
        espn_scoring = "PPR"
        notes.append(
            "ESPN doesn't publish Half PPR ADP at all — the ESPN column "
            "above is showing full PPR ADP instead."
        )

    try:
        espn_list = get_espn_adp(season=season, scoring=espn_scoring)
    except Exception as e:  # noqa: BLE001 - surface any scrape failure to the UI
        errors["espn"] = str(e)

    if requested_scoring == "HALF":
        # BeatADP's scoring toggle is client-side JS, not reflected in any
        # fetchable URL, so half-PPR Sleeper/FantasyPros numbers come from
        # a manually captured static snapshot instead of a live scrape.
        try:
            sleeper_list, captured_at = load_half_ppr_seed()
            notes.append(
                f"Sleeper/FantasyPros Half PPR ADP is a static snapshot "
                f"captured {captured_at}, not live data — BeatADP's scoring "
                f"toggle can't be scraped directly. Re-paste fresh data "
                f"into data/half_ppr_seed.json before draft day if you "
                f"want current numbers."
            )
        except Exception as e:  # noqa: BLE001
            errors["sleeper"] = str(e)
    else:
        try:
            sleeper_list = get_sleeper_adp()
        except Exception as e:  # noqa: BLE001
            errors["sleeper"] = str(e)

    if not espn_list and not sleeper_list:
        return jsonify({"ok": False, "errors": errors}), 502

    merged = merge_sources(espn_list, sleeper_list)
    payload = {
        "players": merged,
        "fetched_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "season": season,
        "scoring": requested_scoring,
        "counts": {"espn": len(espn_list), "sleeper": len(sleeper_list)},
        "notes": notes,
    }
    save_json(PLAYERS_FILE, payload)

    return jsonify({"ok": True, "errors": errors, **payload})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
