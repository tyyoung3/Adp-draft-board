let allPlayers = [];
let sortKey = "consensus_adp";
let sortAsc = true;
let posFilter = "ALL";

const boardBody = document.getElementById("boardBody");
const searchEl = document.getElementById("search");
const hideDraftedEl = document.getElementById("hideDrafted");
const statusEl = document.getElementById("status");
const errorBanner = document.getElementById("errorBanner");
const countInfo = document.getElementById("countInfo");
const seasonEl = document.getElementById("season");
const scoringEl = document.getElementById("scoring");

const DRAFT_STATE_KEY = "adpDraftBoard.draftedPlayers";

function guessSeason() {
  const now = new Date();
  return now.getMonth() + 1 >= 3 ? now.getFullYear() : now.getFullYear() - 1;
}
seasonEl.value = guessSeason();

// ---- drafted-state lives in this browser's localStorage, not the server ----
function getDraftedMap() {
  try {
    return JSON.parse(localStorage.getItem(DRAFT_STATE_KEY) || "{}");
  } catch (e) {
    return {};
  }
}

function setDraftedMap(map) {
  localStorage.setItem(DRAFT_STATE_KEY, JSON.stringify(map));
}

function applyDraftState(players) {
  const map = getDraftedMap();
  players.forEach((p) => {
    p.drafted = !!map[p.id];
  });
}

function showError(msg) {
  if (!msg) {
    errorBanner.hidden = true;
    errorBanner.textContent = "";
    return;
  }
  errorBanner.hidden = false;
  errorBanner.textContent = msg;
}

async function loadCached() {
  const res = await fetch("/api/players");
  const data = await res.json();
  allPlayers = data.players || [];
  applyDraftState(allPlayers);
  if (data.fetched_at) {
    statusEl.textContent = `Last updated: ${new Date(data.fetched_at).toLocaleString()}`;
  } else {
    statusEl.textContent = "No data yet — tap Refresh ADP";
  }
  render();
}

async function refresh() {
  statusEl.textContent = "Refreshing...";
  showError(null);
  try {
    const res = await fetch("/api/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ season: parseInt(seasonEl.value, 10), scoring: scoringEl.value }),
    });
    const data = await res.json();
    if (!res.ok) {
      showError("Refresh failed:\n" + JSON.stringify(data.errors || data, null, 2));
      statusEl.textContent = "Refresh failed";
      return;
    }
    if (data.errors && Object.keys(data.errors).length) {
      let msg = "Some sources failed to update (showing what we could get):\n";
      for (const [src, err] of Object.entries(data.errors)) msg += `\n${src}: ${err}`;
      showError(msg);
    }
    allPlayers = data.players || [];
    applyDraftState(allPlayers);
    statusEl.textContent = `Last updated: ${new Date(data.fetched_at).toLocaleString()} ` +
      `(ESPN: ${data.counts.espn}, Sleeper: ${data.counts.sleeper})`;
    render();
  } catch (e) {
    showError("Refresh failed: " + e.message);
    statusEl.textContent = "Refresh failed";
  }
}

function toggleDrafted(id, drafted) {
  const map = getDraftedMap();
  if (drafted) {
    map[id] = true;
  } else {
    delete map[id];
  }
  setDraftedMap(map);
  const p = allPlayers.find((x) => x.id === id);
  if (p) p.drafted = drafted;
  render();
}

function resetDraft() {
  if (!confirm("Clear all drafted checkmarks? This can't be undone.")) return;
  setDraftedMap({});
  allPlayers.forEach((p) => (p.drafted = false));
  render();
}

function fmtAdp(v) {
  return v === null || v === undefined ? '<span class="na">—</span>' : v.toFixed(1);
}

function fmtDiff(v) {
  if (v === null || v === undefined) return '<span class="diff-none">—</span>';
  const cls = v > 0 ? "diff-pos" : v < 0 ? "diff-neg" : "diff-none";
  const sign = v > 0 ? "+" : "";
  return `<span class="${cls}">${sign}${v.toFixed(1)}</span>`;
}

function render() {
  const q = searchEl.value.trim().toLowerCase();
  const hideDrafted = hideDraftedEl.checked;

  let rows = allPlayers.filter((p) => {
    if (posFilter !== "ALL" && p.position !== posFilter) return false;
    if (q && !p.name.toLowerCase().includes(q)) return false;
    if (hideDrafted && p.drafted) return false;
    return true;
  });

  rows.sort((a, b) => {
    const av = a[sortKey], bv = b[sortKey];
    const aMissing = av === null || av === undefined || av === "";
    const bMissing = bv === null || bv === undefined || bv === "";

    // Missing values always sink to the bottom, regardless of sort
    // direction — otherwise reversing the sort flips them to the top.
    if (aMissing && bMissing) return 0;
    if (aMissing) return 1;
    if (bMissing) return -1;

    if (typeof av === "string") {
      return sortAsc ? av.localeCompare(bv) : bv.localeCompare(av);
    }
    return sortAsc ? av - bv : bv - av;
  });

  countInfo.textContent = `${rows.length} shown / ${allPlayers.length} total`;

  boardBody.innerHTML = rows
    .map((p, i) => `
      <tr class="${p.drafted ? "drafted" : ""}">
        <td>${i + 1}</td>
        <td class="name-cell">${p.name}</td>
        <td><span class="pos-badge">${p.position || "—"}</span></td>
        <td>${p.team || "—"}</td>
        <td>${fmtAdp(p.espn_adp)}</td>
        <td>${fmtAdp(p.sleeper_adp)}</td>
        <td>${fmtAdp(p.fantasypros_adp)}</td>
        <td>${fmtDiff(p.diff)}</td>
        <td><input type="checkbox" class="draft-check" data-id="${p.id}" ${p.drafted ? "checked" : ""}></td>
      </tr>
    `)
    .join("");

  boardBody.querySelectorAll(".draft-check").forEach((cb) => {
    cb.addEventListener("change", (e) => toggleDrafted(e.target.dataset.id, e.target.checked));
  });
}

document.getElementById("refreshBtn").addEventListener("click", refresh);
document.getElementById("resetBtn").addEventListener("click", resetDraft);
searchEl.addEventListener("input", render);
hideDraftedEl.addEventListener("change", render);

document.getElementById("posFilters").addEventListener("click", (e) => {
  if (e.target.tagName !== "BUTTON") return;
  document.querySelectorAll("#posFilters button").forEach((b) => b.classList.remove("active"));
  e.target.classList.add("active");
  posFilter = e.target.dataset.pos;
  render();
});

document.querySelectorAll("th.sortable").forEach((th) => {
  th.addEventListener("click", () => {
    const key = th.dataset.sort;
    if (sortKey === key) {
      sortAsc = !sortAsc;
    } else {
      sortKey = key;
      sortAsc = true;
    }
    document.querySelectorAll("th.sortable").forEach((t) => t.classList.remove("active"));
    th.classList.add("active");
    render();
  });
});

loadCached();
