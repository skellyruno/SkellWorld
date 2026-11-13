"use strict";
const byId = id => document.getElementById(id);
const pitchNames = ["C", "C♯", "D", "D♯", "E", "F", "F♯", "G", "G♯", "A", "A♯", "B"];
let catalogPlugins = [];
let catalogFilter = "all";
let lastSequence = null;
let lastUptime = -1;
let isFetching = false;
let selectedInstance = null;
let lastPeers = [];
let lastEvents = [];
let companions = [];
let activeWorkspace = "creator";
let projectHubBusy = false;


const node = (tag, className, value) => {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (value !== undefined) element.textContent = String(value);
  return element;
};
function uptime(seconds) {
  const s = Number.isFinite(seconds) ? Math.max(0, Math.floor(seconds)) : 0;
  if (s < 60) return s + "s";
  if (s < 3600) return Math.floor(s / 60) + "m " + s % 60 + "s";
  return Math.floor(s / 3600) + "h " + Math.floor(s % 3600 / 60) + "m";
}
function renderTuning(tuning) {
  if (!tuning || !Number.isInteger(tuning.root) || tuning.root < 0 ||
      tuning.root > 11 || ![0, 1].includes(tuning.mode)) {
    byId("tuning-key").textContent = "—";
    byId("tuning-a4").textContent = "—";
    byId("tuning-status").textContent = "Waiting for a connected Skell Key signal";
    byId("tuning-notes").replaceChildren(node("span", "muted", "Awaiting scale data"));
    return;
  }
  byId("tuning-key").textContent = pitchNames[tuning.root] + (tuning.mode === 0 ? " Major" : " Minor");
  const a4 = Number(tuning.a4_hz);
  byId("tuning-a4").textContent = Number.isFinite(a4) && a4 >= 400 && a4 <= 480 ?
    a4.toFixed(2) + " Hz" : "—";
  const secondsOld = Math.max(0, Date.now() / 1000 - Number(tuning.at || 0));
  // This is a state snapshot, NOT a required heartbeat. A perfectly healthy
  // key may stay unchanged for minutes; age alone must not be an error.
  byId("tuning-status").textContent =
    "Shared " + uptime(secondsOld) + " ago · Skell Key sender joined";
  const mask = tuning.scale_mask;
  const notes = Number.isInteger(mask) && mask > 0 && mask <= 4095 ?
    pitchNames.filter((_, i) => (mask & (1 << i)) !== 0) : [];
  byId("tuning-notes").replaceChildren(...(notes.length ?
    notes.map(name => node("span", "note-pill", name)) :
    [node("span", "muted", "Key detected · full scale pending")]));
}

function renderStatus(data) {
  const peers = Array.isArray(data.peers) ? data.peers : [];
  const events = Array.isArray(data.events) ? data.events : [];
  byId("connection").classList.remove("offline");
  byId("connection-label").textContent = "HUB ONLINE";
  byId("instance-count").textContent = String(peers.length);
  byId("live-count").textContent = peers.length + " LIVE";
  byId("uptime").textContent = uptime(data.uptime_seconds);
  const sequence = data.sequence;
  const restarted = data.uptime_seconds < lastUptime;
  lastUptime = data.uptime_seconds;
  renderTuning(data.tuning);
  if (!restarted && sequence === lastSequence) {
    // Display elapsed session time without rebuilding the full event feed.
    if (selectedInstance) renderInspector(peers, events);
    return;
  }
  lastSequence = sequence;
  lastPeers = peers;
  lastEvents = events;
  renderPeersAndActivity(peers, events);
}
function renderInspector(peers, events) {
  const holder = byId("inspector");
  const selected = peers.find(peer => peer.instance_id === selectedInstance);
  if (!selected) {
    selectedInstance = null;
    holder.replaceChildren(node("span", "eyebrow", "INSTANCE INSPECTOR"),
      node("p", "muted", "Select a connected plugin to inspect its session and recent informational activity."));
    return;
  }
  const recent = events.filter(event => event.instance_id === selected.instance_id).slice(-1)[0];
  const title = node("strong", "inspector-name", selected.display_name || selected.product_id);
  const id = node("p", "inspector-id", selected.instance_id);
  const source = node("p", "muted", selected.product_id + " · TCP connection currently joined");
  const duration = node("p", "inspector-metric",
    "Connected " + uptime(selected.connected_seconds) +
    " · " + selected.events_sent + " informational event" +
    (selected.events_sent === 1 ? "" : "s"));
  const last = selected.last_event_seconds_ago;
  const activity = node("p", "muted",
    last === null || last === undefined ?
      "No informational events yet. An idle plugin can still be connected." :
      "Last event " + uptime(last) + " ago" +
      (recent ? " · " + recent.kind : "") +
      ". Inactivity alone does not mean the connection failed.");
  const clear = node("button", "inspector-clear", "CLEAR SELECTION");
  clear.type = "button";
  clear.addEventListener("click", () => { selectedInstance = null; renderPeersAndActivity(lastPeers, lastEvents); });
  holder.replaceChildren(node("span", "eyebrow", "INSTANCE INSPECTOR"), title, id, source, duration, activity, clear);
}
function renderPeersAndActivity(peers, events) {
  const holder = byId("peers");
  if (peers.length === 0) {
    const empty = node("div", "empty");
    empty.append(node("div", "empty-icon", "◎"), node("strong", "", "No plugins joined yet"), node("p", "", "Open a SkellWorld-compatible plugin and click JOIN WORLD."));
    holder.replaceChildren(empty);
  } else {
    // An FL Studio session cannot be inferred from these instances. Group
    // only by declared product ID; no invented DAW session names.
    const groups = new Map();
    peers.forEach(peer => {
      if (!groups.has(peer.product_id)) groups.set(peer.product_id, []);
      groups.get(peer.product_id).push(peer);
    });
    const grouped = [];
    Array.from(groups.entries()).sort((a, b) => a[0].localeCompare(b[0])).forEach(([productId, members]) => {
      const count = members.length;
      grouped.push(node("div", "peer-group-label",
        productId + " · " + count + " joined instance" + (count === 1 ? "" : "s")));
      members.forEach(peer => {
        const card = node("button", "peer peer-button" +
          (selectedInstance === peer.instance_id ? " peer-selected" : ""));
        card.type = "button";
        card.setAttribute("aria-pressed", String(selectedInstance === peer.instance_id));
        const info = node("div", "peer-info");
        info.append(node("strong", "", peer.display_name || peer.product_id),
                    node("small", "", peer.instance_id));
        card.append(node("div", "peer-icon", "S"), info, node("span", "state", "INSPECT"));
        card.addEventListener("click", () => {
          selectedInstance = selectedInstance === peer.instance_id ? null : peer.instance_id;
          renderPeersAndActivity(lastPeers, lastEvents);
        });
        grouped.push(card);
      });
    });
    holder.replaceChildren(...grouped);
  }
  renderInspector(peers, events);
  const activity = byId("events");
  const shown = selectedInstance ? events.filter(event => event.instance_id === selectedInstance) : events;
  byId("show-all-activity").textContent = selectedInstance ? "SHOW ALL" : "ALL ACTIVITY";
  if (!shown.length) {
    activity.replaceChildren(node("p", "muted", "World activity appears here when plugins connect or publish informational events."));
  } else {
    activity.replaceChildren(...shown.slice().reverse().slice(0, 35).map(event => {
      const item = node("article", "event");
      const info = node("div", "detail");
      info.append(node("strong", "", event.product_id), node("div", "", event.detail),
        node("time", "", new Date(event.at * 1000).toLocaleTimeString()));
      item.append(node("span", "type", event.kind), info);
      return item;
    }));
  }
}
function renderCatalog(data) {
  catalogPlugins = Array.isArray(data.plugins) ? data.plugins : [];
  byId("catalog-count").textContent = String(catalogPlugins.length);
  filterCatalog();
}
function filterCatalog() {
  const query = byId("catalog-search").value.trim().toLocaleLowerCase();
  const plugins = catalogPlugins.filter(plugin => {
    if (catalogFilter !== "all" && plugin.integration !== catalogFilter) return false;
    const haystack = (plugin.display_name || "") + " " + (plugin.repository || "") +
      " " + (plugin.product_id || "");
    return haystack.toLocaleLowerCase().includes(query);
  });
  byId("catalog-summary").textContent = plugins.length + " of " + catalogPlugins.length + " products";
  if (!plugins.length) {
    byId("catalog").replaceChildren(node("p", "muted", "No matching products. Try another name or filter."));
    return;
  }
  byId("catalog").replaceChildren(...plugins.map(plugin => {
    const card = node("article", "catalog-card");
    const repository = plugin.repository || "";
    const name = plugin.display_name || repository.split("/").pop() || "Unknown product";
    const flag = plugin.integration === "world-enabled" ? "world integration available" :
      plugin.integration === "world-demo" ? "demo connection available" :
      plugin.integration === "shared-core-only" ? "shared core only" : "planned integration";
    const link = node("a", "catalog-link");
    // Repository names are catalog metadata, never arbitrary URLs.
    if (/^skellyruno\/[A-Za-z0-9_.-]+$/.test(repository)) {
      link.href = "https://github.com/" + repository;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.setAttribute("aria-label", "Open GitHub repository for " + name);
    } else {
      link.removeAttribute("href");
    }
    link.append(node("strong", "", name), node("small", "", repository),
      node("div", "flag" + (["world-demo","world-enabled"].includes(plugin.integration) ? " connected" : ""), flag));
    card.append(link);
    return card;
  }));
}
async function runConnectionCheck() {
  const button = byId("run-connection-check");
  const holder = byId("connection-check-results");
  if (button.disabled) return;
  button.disabled = true;
  button.textContent = "CHECKING";
  try {
    const [statusResult, catalogResult] = await Promise.all([
      fetch("/api/status", {cache:"no-store"}),
      fetch("/api/catalog", {cache:"no-store"})
    ]);
    if (!statusResult.ok || !catalogResult.ok) throw Error("local endpoint unavailable");
    const [status, catalog] = await Promise.all([
      statusResult.json(), catalogResult.json()
    ]);
    if (status.schema !== "skellworld-status/1" ||
        catalog.schema !== "skellworld-catalog/1") {
      throw Error("incompatible SkellWorld schema");
    }
    const peers = Array.isArray(status.peers) ? status.peers : [];
    const products = Array.isArray(catalog.plugins) ? catalog.plugins : [];
    const ready = products.filter(p => p.integration === "world-enabled");
    const observed = new Set(peers.map(p => p.product_id));
    const joined = ready.filter(p => observed.has(p.product_id));
    const lines = [
      ["HUB", "ONLINE", "The localhost hub responded to a read-only status request."],
      ["OPTED-IN INSTANCES", String(peers.length), peers.length ?
        "These are connected plugin sessions, not an installed-plugin scan." :
        "No sessions joined. Open the plugin's existing Settings/World menu and enable Join."],
      ["SOURCE INTEGRATIONS", String(ready.length),
        "Products with source integration and build validation; FL Studio host testing is separate."],
      ["INTEGRATED PRODUCTS JOINED", String(joined.length) + " / " + ready.length,
        "Unjoined products might be closed, disconnected or not installed. No inference is possible."]
    ];
    const grid = node("div", "health-grid");
    grid.append(...lines.map(([label, amount, detail]) => {
      const cell = node("div", "health-tile");
      cell.append(node("span", "health-caption", label),
                  node("strong", "health-value", amount),
                  node("small", "health-explain", detail));
      return cell;
    }));
    holder.replaceChildren(grid, node("p", "muted",
      "Connection checks are informational. No control or network access outside this local hub."));
  } catch (_error) {
    holder.replaceChildren(node("p", "health-error",
      "Unable to reach the local SkellWorld hub. Check that SkellWorld.exe is running and reload the dashboard."));
  } finally {
    button.disabled = false;
    button.textContent = "RUN CHECK";
  }
}
async function refresh() {
  if (document.hidden || isFetching) return;
  isFetching = true;
  try {
    const response = await fetch("/api/status", {cache: "no-store"});
    if (!response.ok) throw Error("status " + response.status);
    const payload = await response.json();
    if (payload.schema !== "skellworld-status/1") throw Error("unsupported schema");
    renderStatus(payload);
  } catch (error) {
    byId("connection").classList.add("offline");
    byId("connection-label").textContent = "HUB OFFLINE";
    byId("instance-count").textContent = "—";
    byId("live-count").textContent = "0 LIVE";
    byId("uptime").textContent = "—";
    byId("peers").replaceChildren(node("p", "muted", "The local hub is unavailable. Start it and refresh this page."));
    byId("events").replaceChildren(node("p", "muted", "Waiting for the hub to reconnect."));
    lastSequence = null;
    lastUptime = -1;
    renderTuning(null);
    lastPeers = [];
    lastEvents = [];
    selectedInstance = null;
    renderInspector([], []);
  } finally {
    isFetching = false;
  }
}
async function loadCatalog() {
  try {
    const response = await fetch("/api/catalog", {cache: "no-store"});
    if (!response.ok) throw Error("catalog " + response.status);
    renderCatalog(await response.json());
  } catch (error) {
    byId("catalog").replaceChildren(node("p", "muted", "Catalog unavailable."));
  }
}
function renderProjectHubPulse(data) {
  const holder = byId("projecthub-pulse");
  if (!data || data.schema !== "skellworld-projecthub-bridge/1" ||
      !data.shared || !data.counts) {
    holder.replaceChildren(node("p", "muted",
      "Project Hub sharing is OFF or no valid summary exists. In the Project Hub Windows app, open SkellWorld and choose Share counts with SkellWorld."));
    return;
  }
  const c = data.counts;
  const tiles = [
    ["PROJECTS", c.projects], ["CI PASSED", c.ci_passed],
    ["CI FAILED", c.ci_failed], ["CI STALE", c.ci_stale],
    ["CI UNKNOWN", c.ci_unknown], ["BLOCKED", c.blocked]
  ];
  const grid = node("div", "projecthub-stats");
  grid.append(...tiles.map(([label, count]) => {
    const tile = node("div", "projecthub-stat");
    tile.append(node("small", "", label), node("strong", "", count));
    return tile;
  }));
  const freshness = node("p", data.stale ? "projecthub-stale" : "muted",
      (data.stale ? "STALE SUMMARY · " : "Shared summary · ") +
      Math.floor(Number(data.age_seconds || 0) / 60) + "m old · Project Hub may be closed");
  holder.replaceChildren(grid, freshness);
}
async function refreshProjectHub() {
  if (projectHubBusy || document.hidden || activeWorkspace !== "developer") return;
  projectHubBusy = true;
  try {
    const response = await fetch("/api/projecthub", {cache: "no-store"});
    if (!response.ok) throw Error("project hub " + response.status);
    renderProjectHubPulse(await response.json());
  } catch (_error) {
    byId("projecthub-pulse").replaceChildren(node("p", "muted", "Project Hub summary unavailable."));
  } finally {
    projectHubBusy = false;
  }
}
function renderIntegrationReadiness(data) {
  const holder = byId("integration-readiness");
  const pilots = Array.isArray(data.pilots) ? data.pilots : [];
  if (!pilots.length) {
    holder.replaceChildren(node("p", "muted", "No source integration profiles."));
    return;
  }
  holder.replaceChildren(...pilots.map(pilot => {
    const card = node("article", "readiness-card");
    const title = node("strong", "readiness-name", pilot.name);
    const role = node("p", "muted", pilot.role);
    const state = node("span", "readiness-state",
      pilot.source_status === "implemented" ? "SOURCE IMPLEMENTED" : "IN REVIEW");
    const evidence = node("p", "muted", pilot.evidence);
    const host = node("p", "readiness-pending", "FL STUDIO HOST TEST: " + pilot.host_test);
    card.append(title, role, state, evidence, host);
    if (typeof pilot.repository === "string" &&
        /^skellyruno\/[A-Za-z0-9_.-]+$/.test(pilot.repository)) {
      const link = node("a", "companion-link", "REPOSITORY");
      link.href = "https://github.com/" + pilot.repository;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      card.append(link);
    }
    return card;
  }));
}
async function loadIntegrationReadiness() {
  try {
    const response = await fetch("/api/integrations", {cache: "no-store"});
    if (!response.ok) throw Error("integrations " + response.status);
    const data = await response.json();
    if (data.schema !== "skellworld-integrations/1") throw Error("unsupported integration profile");
    renderIntegrationReadiness(data);
  } catch (_error) {
    byId("integration-readiness").replaceChildren(node("p", "muted", "Integration evidence unavailable."));
  }
}
function renderCompanions(data) {
  companions = Array.isArray(data.apps) ? data.apps : [];
  const holder = byId("companions");
  const available = companions.filter(app => app.mode === activeWorkspace);
  byId("companions-title").textContent = activeWorkspace === "developer" ?
    "Developer workspace" : "Creator workspace";
  if (!available.length) {
    holder.replaceChildren(node("p", "muted", "No companion workspaces registered."));
    return;
  }
  holder.replaceChildren(...available.map(app => {
    const card = node("article", "companion-card");
    const mode = node("span", "eyebrow green", app.mode === "developer" ? "DEVELOPER MODE" : "CREATOR MODE");
    const heading = node("strong", "companion-name", app.name);
    const detail = node("p", "muted", app.description);
    const state = node("p", "companion-status", app.status + " · no installed-app detection");
    card.append(mode, heading, detail, state);
    // Registry is data, not a license to execute commands or open local apps.
    if (typeof app.repository === "string" && /^skellyruno\/[A-Za-z0-9_.-]+$/.test(app.repository)) {
      const link = node("a", "companion-link", "VIEW GITHUB REPOSITORY");
      link.href = "https://github.com/" + app.repository;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      card.append(link);
    }
    return card;
  }));
}
async function loadCompanions() {
  try {
    const response = await fetch("/api/apps", {cache: "no-store"});
    if (!response.ok) throw Error("apps " + response.status);
    const data = await response.json();
    if (data.schema !== "skellworld-apps/1") throw Error("unsupported companion schema");
    renderCompanions(data);
  } catch (_error) {
    byId("companions").replaceChildren(node("p", "muted", "Companion directory unavailable."));
  }
}

function switchWorkspace(mode) {
  if (mode !== "creator" && mode !== "developer") return;
  activeWorkspace = mode;
  document.querySelectorAll("[data-workspace]").forEach(section => {
    section.hidden = section.dataset.workspace !== mode;
  });
  document.querySelectorAll("[data-mode]").forEach(button => {
    const selected = button.dataset.mode === mode;
    button.classList.toggle("active", selected);
    button.setAttribute("aria-pressed", String(selected));
  });
  byId("mode-caption").textContent = mode === "creator" ?
    "Your connected SKELL plugins and creator tools. No installation scanning." :
    "Independent SKELL development workspaces and read-only ecosystem information.";
  renderCompanions({apps: companions});
  if (mode === "developer") refreshProjectHub();
}
document.querySelectorAll("[data-mode]").forEach(button =>
  button.addEventListener("click", () => switchWorkspace(button.dataset.mode)));
byId("refresh-projecthub").addEventListener("click", refreshProjectHub);
byId("run-connection-check").addEventListener("click", runConnectionCheck);
byId("show-all-activity").addEventListener("click", () => {
  selectedInstance = null;
  renderPeersAndActivity(lastPeers, lastEvents);
});
byId("catalog-search").addEventListener("input", filterCatalog);
document.querySelectorAll("[data-filter]").forEach(button => {
  button.addEventListener("click", () => {
    catalogFilter = button.dataset.filter;
    document.querySelectorAll("[data-filter]").forEach(item => {
      const active = item === button;
      item.classList.toggle("selected", active);
      item.setAttribute("aria-pressed", String(active));
    });
    filterCatalog();
  });
});
document.addEventListener("visibilitychange", () => { if (!document.hidden) refresh(); });
refresh();
loadCatalog();
loadCompanions();
loadIntegrationReadiness();
setInterval(refresh, 1500);
setInterval(refreshProjectHub, 15000);
