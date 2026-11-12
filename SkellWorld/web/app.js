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
  byId("tuning-status").textContent = "Live informational signal · " + tuning.product_id;
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
  if (!restarted && sequence === lastSequence) return;
  lastSequence = sequence;
  renderTuning(data.tuning);
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
  const source = node("p", "muted", selected.product_id + " · connected now");
  const activity = node("p", "muted",
      recent ? "Last event: " + recent.kind + " · " + new Date(recent.at * 1000).toLocaleTimeString() :
      "No activity recorded in the current session.");
  const clear = node("button", "inspector-clear", "CLEAR SELECTION");
  clear.type = "button";
  clear.addEventListener("click", () => { selectedInstance = null; renderPeersAndActivity(lastPeers, lastEvents); });
  holder.replaceChildren(node("span", "eyebrow", "INSTANCE INSPECTOR"), title, id, source, activity, clear);
}
function renderPeersAndActivity(peers, events) {
  const holder = byId("peers");
  if (peers.length === 0) {
    const empty = node("div", "empty");
    empty.append(node("div", "empty-icon", "◎"), node("strong", "", "No plugins joined yet"), node("p", "", "Open a SkellWorld-compatible plugin and click JOIN WORLD."));
    holder.replaceChildren(empty);
  } else {
    holder.replaceChildren(...peers.map(peer => {
      const card = node("button", "peer peer-button" +
        (selectedInstance === peer.instance_id ? " peer-selected" : ""));
      card.type = "button";
      card.setAttribute("aria-pressed", String(selectedInstance === peer.instance_id));
      const info = node("div", "peer-info");
      info.append(node("strong", "", peer.display_name || peer.product_id),
                  node("small", "", peer.product_id + " · " + peer.instance_id));
      card.append(node("div", "peer-icon", "S"), info, node("span", "state", "INSPECT"));
      card.addEventListener("click", () => {
        selectedInstance = selectedInstance === peer.instance_id ? null : peer.instance_id;
        renderPeersAndActivity(lastPeers, lastEvents);
      });
      return card;
    }));
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
function renderCompanions(data) {
  companions = Array.isArray(data.apps) ? data.apps : [];
  const holder = byId("companions");
  if (!companions.length) {
    holder.replaceChildren(node("p", "muted", "No companion workspaces registered."));
    return;
  }
  holder.replaceChildren(...companions.map(app => {
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
setInterval(refresh, 1500);
