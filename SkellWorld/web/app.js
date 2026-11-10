"use strict";
const byId = id => document.getElementById(id);
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
function renderStatus(data) {
  const peers = Array.isArray(data.peers) ? data.peers : [];
  const events = Array.isArray(data.events) ? data.events : [];
  byId("connection").classList.remove("offline");
  byId("connection-label").textContent = "HUB ONLINE";
  byId("instance-count").textContent = String(peers.length);
  byId("live-count").textContent = peers.length + " LIVE";
  byId("uptime").textContent = uptime(data.uptime_seconds);
  const holder = byId("peers");
  if (peers.length === 0) {
    const empty = node("div", "empty");
    empty.append(node("div", "empty-icon", "◎"), node("strong", "", "No plugins joined yet"), node("p", "", "Open a SkellWorld-compatible plugin and click JOIN WORLD."));
    holder.replaceChildren(empty);
  } else {
    holder.replaceChildren(...peers.map(peer => {
      const card = node("article", "peer");
      const info = node("div", "peer-info");
      info.append(node("strong", "", peer.display_name || peer.product_id), node("small", "", peer.product_id + " · " + peer.instance_id));
      card.append(node("div", "peer-icon", "S"), info, node("span", "state", "ONLINE"));
      return card;
    }));
  }
  const activity = byId("events");
  if (!events.length) {
    activity.replaceChildren(node("p", "muted", "World activity appears here when plugins connect or publish informational events."));
  } else {
    activity.replaceChildren(...events.slice().reverse().slice(0, 35).map(event => {
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
  const plugins = Array.isArray(data.plugins) ? data.plugins : [];
  byId("catalog-count").textContent = String(plugins.length);
  byId("catalog").replaceChildren(...plugins.map(plugin => {
    const card = node("article", "catalog-card");
    const name = plugin.display_name || plugin.repository.split("/").pop();
    const flag = plugin.integration === "world-demo" ? "demo connection available" :
      plugin.integration === "shared-core-only" ? "shared core only" : "planned integration";
    card.append(node("strong", "", name), node("small", "", plugin.repository),
      node("div", "flag" + (plugin.integration === "world-demo" ? " connected" : ""), flag));
    return card;
  }));
}
async function refresh() {
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
refresh();
loadCatalog();
setInterval(refresh, 1500);
