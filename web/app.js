// Registry site: draws the list/search/filters from a single index.json, and module pages render docs/index.md at that version's commit.
// Addresses: #/ (list, ?q=&tag=&engine=), #/<name> (latest), #/<name>@<version>. Hosted on GitHub Pages without a server.
"use strict";

const app = document.getElementById("app");
let index = null;

function el(tag, attrs, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (k === "onclick" || k === "oninput" || k === "onchange") e[k] = v;
    else if (v !== undefined && v !== null && v !== false) e.setAttribute(k, v);
  }
  for (const k of kids.flat()) if (k !== null && k !== undefined) e.append(k);
  return e;
}

function engineKey(v) { return v.split(".").map(Number); }
function cmpEngine(a, b) { const x = engineKey(a), y = engineKey(b); return x[0] - y[0] || x[1] - y[1]; }
function engines(m) { return [...new Set(m.versions.map(v => v.engine))]; }

// "owner/repo" → file URL at that commit (raw) and the human-facing URL (blob)
function rawUrl(m, commit, path) { return m.repo.replace("https://github.com/", "https://raw.githubusercontent.com/") + `/${commit}/${path}`; }
function blobUrl(m, commit, path) { return `${m.repo}/blob/${commit}/${path}`; }

function route() {
  const h = decodeURIComponent(location.hash.replace(/^#\/?/, ""));
  const [path, query] = h.split("?");
  const params = new URLSearchParams(query || "");
  if (!path) return renderList(params);
  const [name, version] = path.split("@");
  const m = index.modules.find(x => x.name === name);
  if (!m) return show(el("p", {}, `No module named "${name}". `, el("a", { href: "#/" }, "All modules")));
  renderModule(m, version);
}

function show(...nodes) { app.replaceChildren(...nodes); window.scrollTo(0, 0); }

function renderList(params) {
  const q = params.get("q") || "", tag = params.get("tag") || "", engine = params.get("engine") || "";
  const allTags = [...new Set(index.modules.flatMap(m => m.tags))].sort();
  const allEngines = [...new Set(index.modules.flatMap(engines))].sort(cmpEngine).reverse();

  const setParam = (k, v) => {
    const p = new URLSearchParams({ q, tag, engine, [k]: v });
    for (const key of [...p.keys()]) if (!p.get(key)) p.delete(key);
    history.replaceState(null, "", "#/" + (p.toString() ? "?" + p : ""));
    route();
    if (k === "q") { const i = app.querySelector("input"); i.focus(); i.setSelectionRange(v.length, v.length); }
  };

  const words = q.toLowerCase().split(/\s+/).filter(Boolean);
  const hits = index.modules.filter(m => {
    const text = [m.name, m.title, m.summary, m.author, ...m.tags].join(" ").toLowerCase();
    return words.every(w => text.includes(w)) && (!tag || m.tags.includes(tag)) && (!engine || engines(m).includes(engine));
  });

  show(
    el("div", { class: "filters" },
      el("input", { type: "search", placeholder: "Search modules", value: q, "aria-label": "Search", oninput: e => setParam("q", e.target.value) }),
      el("select", { "aria-label": "Tag", onchange: e => setParam("tag", e.target.value) },
        el("option", { value: "" }, "All tags"), allTags.map(t => el("option", { value: t, selected: t === tag }, t))),
      el("select", { "aria-label": "Engine version", onchange: e => setParam("engine", e.target.value) },
        el("option", { value: "" }, "Any engine"), allEngines.map(v => el("option", { value: v, selected: v === engine }, `Engine ${v}`)))),
    el("p", { class: "muted" }, `${hits.length} of ${index.modules.length} modules`),
    el("div", { class: "list" }, hits.map(m =>
      el("a", { class: "card", href: `#/${m.name}` },
        el("h3", {}, m.title, " ", el("span", { class: "name" }, m.name)),
        el("p", {}, m.summary),
        el("div", { class: "meta" },
          el("span", {}, `v${m.latest}`), el("span", {}, `engine ${engines(m).join(", ")}`),
          el("span", {}, m.author), el("span", {}, m.license),
          m.tags.map(t => el("button", { class: "tag", onclick: e => { e.preventDefault(); setParam("tag", t); } }, t)))))));
}

function checksLine(v) {
  const c = Object.entries(v.checks || {});
  if (!c.length) return null;
  return el("div", { class: "meta" }, c.map(([k, r]) =>
    el("span", { class: r === "pass" || r === "ok" ? "ok" : "bad" }, `${k}: ${r}`)));
}

function renderModule(m, version) {
  const v = version ? m.versions.find(x => x.version === version) : m.versions[0];
  if (!v) return show(el("p", {}, `${m.name} has no version ${version}. `, el("a", { href: `#/${m.name}` }, "Latest")));
  const langs = Object.keys(v.docs || {});
  let lang = langs.includes(preferredLang()) ? preferredLang() : langs[0];
  const add = `tools\\module.ps1 add ${m.name}` + (v === m.versions[0] ? "" : `@${v.version}`);
  const doc = el("article", { class: "doc" }, el("p", { class: "muted" }, "Loading docs…"));
  const langBar = langs.length > 1 ? el("div", { class: "lang" }, langs.map(l =>
    el("button", { "aria-pressed": String(l === lang), onclick: () => { lang = l; savedLang(l); loadDoc(); langBar.querySelectorAll("button").forEach(b => b.setAttribute("aria-pressed", String(b.textContent === l))); } }, l))) : null;

  async function loadDoc() {
    const path = v.docs[lang];
    if (!path) { doc.replaceChildren(el("p", { class: "muted" }, "No docs.")); return; }
    try {
      const r = await fetch(rawUrl(m, v.commit, path));
      if (!r.ok) throw new Error(r.status);
      doc.innerHTML = DOMPurify.sanitize(marked.parse(await r.text()));
      fixLinks(doc, m, v.commit, path);
    } catch (e) {
      doc.replaceChildren(el("p", { class: "bad" }, "Could not load the docs. "), el("a", { href: blobUrl(m, v.commit, path) }, "Open on GitHub"));
    }
  }

  show(el("a", { class: "back", href: "#/" }, "← All modules"),
    el("div", { class: "page" },
      el("div", {}, langBar, doc),
      el("aside", {},
        el("h4", {}, "Add"),
        el("div", { class: "cmd" }, el("code", {}, add),
          el("button", { onclick: e => navigator.clipboard?.writeText(add).then(() => { e.target.textContent = "Copied"; }) }, "Copy")),
        el("p", { class: "muted" }, "Or the editor: File > Modules…, or MealKit Manager's Modules tab."),
        el("h4", {}, "Module"),
        el("div", {}, el("strong", {}, m.title), " ", el("span", { class: "muted" }, m.name)),
        el("p", {}, m.summary),
        el("div", { class: "meta" }, m.tags.map(t => el("a", { class: "tag", href: `#/?tag=${encodeURIComponent(t)}` }, t))),
        el("h4", {}, "This version"),
        el("div", {}, `v${v.version} · engine ${v.engine} · ${m.license}`),
        v.requires.length ? el("div", {}, "Requires ", v.requires.map((q, i) => [i ? ", " : "", el("a", { href: `#/${q.name}` }, q.name + (q.version ? `@${q.version}` : ""))])) : null,
        checksLine(v),
        el("div", { class: "meta" }, el("a", { href: `${m.repo}/tree/${v.tag}` }, "Source"), el("span", {}, `commit ${v.commit.slice(0, 10)}`)),
        el("h4", {}, "Versions"),
        el("ul", { class: "versions" }, m.versions.map(x =>
          el("li", {}, x === v ? el("strong", {}, x.version) : el("a", { href: `#/${m.name}@${x.version}` }, x.version), el("span", { class: "muted" }, ` engine ${x.engine}`)))),
        el("h4", {}, "Author"),
        el("div", {}, m.author),
        el("a", { href: m.repo }, m.repo.replace("https://github.com/", "")))));
  loadDoc();
}

// Relative paths inside docs are rewritten relative to the module repo (images raw, links blob, # as is)
function fixLinks(root, m, commit, docPath) {
  const dir = docPath.includes("/") ? docPath.slice(0, docPath.lastIndexOf("/") + 1) : "";
  const resolve = p => new URL(p, "https://x/" + dir).pathname.slice(1);
  const relative = p => p && !/^([a-z]+:|\/\/|#)/i.test(p);
  root.querySelectorAll("img[src]").forEach(i => { if (relative(i.getAttribute("src"))) i.src = rawUrl(m, commit, resolve(i.getAttribute("src"))); });
  root.querySelectorAll("a[href]").forEach(a => {
    const h = a.getAttribute("href");
    if (relative(h)) a.href = blobUrl(m, commit, resolve(h));
    else if (h.startsWith("#")) a.removeAttribute("href");  // hashes are used as site addresses
  });
}

function savedLang(l) { try { if (l) localStorage.setItem("lang", l); return localStorage.getItem("lang"); } catch { return null; } }
function preferredLang() { return savedLang() || (navigator.language || "en").slice(0, 2); }

fetch("index.json", { cache: "no-cache" })
  .then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })
  .then(j => { index = j; addEventListener("hashchange", route); route(); })
  .catch(() => show(el("p", { class: "bad" }, "Could not load index.json.")));
