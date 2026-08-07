# Draft Board — ESPN vs Sleeper vs FantasyPros ADP

A Flask app for live fantasy football drafts. Pulls Average Draft Position
(ADP) from ESPN, Sleeper, and FantasyPros, shows them side by side, and
lets you check off players as they're drafted so you can see
best-available at a glance.

There are two ways to run this: **locally on a computer**, or **hosted
online** so you can use it from an iPad (or any device) with no computer
involved at all. Pick whichever applies to you.

---

## Option A: Run locally on a computer

```bash
cd adp-draft-board
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip3 install -r requirements.txt
python3 app.py
```

Open **http://127.0.0.1:5050**. If you want another device on the same
WiFi (like an iPad) to reach it too, find your computer's local IP
(`ipconfig getifaddr en0` on Mac, or check WiFi settings) and open
`http://<that-ip>:5050` on the other device instead.

---

## Option B: Host it online (works from iPad with no computer needed)

This runs the app on a free hosting service instead of your own machine,
giving you a normal `https://...` link you can open from Safari on the
iPad from anywhere — not dependent on being near a specific computer or
on the same WiFi network.

### 1. Get the code onto GitHub

If you have access to any computer with a terminal:
```bash
cd adp-draft-board
git init
git add .
git commit -m "Draft board"
```
Create a new empty repo on github.com, then:
```bash
git remote add origin https://github.com/<you>/adp-draft-board.git
git push -u origin main
```

No terminal/computer at all? You can do this entirely from a browser
(works on iPad too):
1. Go to github.com → **New repository** → name it, create it.
2. Click **"uploading an existing file"** on the empty repo page.
3. Drag in all the files/folders from this project (or use "choose your
   files" and select them from the Files app). Commit.

### 2. Deploy on Render (free tier)

1. Go to [render.com](https://render.com) → sign up (can use your GitHub
   account to sign in).
2. **New +** → **Web Service** → connect the `adp-draft-board` repo.
3. Settings:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app` (already set via the included
     `Procfile`, Render should detect it automatically)
   - **Instance type**: Free
4. Click **Create Web Service**. Render will build and deploy — takes a
   couple minutes. You'll get a URL like
   `https://adp-draft-board-xxxx.onrender.com`.
5. Open that URL on your iPad in Safari, tap **Refresh ADP** once to pull
   live data.

### 3. Make it feel like an app on the iPad (optional)

In Safari, open the Render URL → tap the **Share** icon → **Add to Home
Screen**. It'll show up as an icon you can tap straight into, full-screen,
no address bar.

### Free-tier heads up

Render's free web services "sleep" after ~15 minutes of no traffic and
take ~30-60 seconds to wake back up on the next request. This only
matters if the app sits idle before your draft starts — once you're
actively using it (checking off picks), it stays awake. If you load it
right before your draft and it feels slow/blank for the first few
seconds, that's just the wake-up; give it a moment and reload.

### Why drafted-state lives in the browser, not the server

Free hosting tiers often reset their disk on redeploys/restarts. Rather
than risk losing your draft progress mid-draft to that, which players
you've checked off is stored in the iPad's own browser (`localStorage`),
not a server file. That means:
- It survives server restarts/sleep-wake cycles fine.
- It's tied to that specific browser/device — if you also open the link
  on a phone, it won't show the same checkmarks (each device tracks its
  own). For solo iPad use during a draft this isn't an issue.
- **Reset Draft** only clears it on whichever device you tap it from.

---

## Where the ADP data comes from

**ESPN**: Pulled live from ESPN's own public Fantasy API
(`lm-api-reads.fantasy.espn.com/apis/v3/...`). Undocumented but stable,
used by most community ESPN-fantasy tools. No login/league needed.

**Sleeper & FantasyPros**: Sleeper does not publish an ADP API at all —
their public API covers leagues/rosters/drafts but never ADP. Both the
Sleeper and FantasyPros numbers here are scraped from
[BeatADP](https://www.beatadp.com/platform-adp), a third-party site that
mirrors ADP across platforms and updates daily. This is the most fragile
link in the pipeline — isolated to `scrapers/sleeper.py` so it's a
one-file fix if that site's layout changes (it'll raise a clear error
rather than fail silently).

## Project layout

```
adp-draft-board/
├── app.py                  # Flask server + API routes
├── requirements.txt
├── Procfile                 # for Render/gunicorn
├── scrapers/
│   ├── espn.py              # ESPN ADP (direct API)
│   ├── sleeper.py           # Sleeper + FantasyPros ADP (via BeatADP)
│   └── merge.py             # Combines sources, matches players by name
├── templates/index.html     # Dashboard page
├── static/
│   ├── app.js                # Rendering, sorting, filtering, drafted state
│   └── style.css             # Dark theme, mobile/iPad friendly
└── data/players.json         # Cached last-fetched ADP (server-side)
```

## Troubleshooting

- **"Parsed 0 players..." error on refresh**: One of the sites changed
  their page/API structure. The error message tells you which
  (`espn` or `sleeper`) — that source's file is where to look.
- **ESPN column blank**: If it ever goes blank again, check
  `scrapers/espn.py` — ESPN has moved their API hostname before
  (`fantasy.espn.com` → `lm-api-reads.fantasy.espn.com`).
- **Port already in use (local run)**: change the port in `app.py`'s
  `PORT` handling, or set `PORT=5051 python3 app.py`.
