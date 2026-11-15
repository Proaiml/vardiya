// BMC Community reader for the Vardiya bench (read only). Paste the whole file into the browser pane's page on
// community.bmc.com with javascript_tool; it installs window.V and resumes whatever was running.
//
// Rules it keeps: one page load per 40 seconds at most, read only (no clicks, posts, likes or follows), stops at
// once on 429, "Too Many Requests" or a check page and never retries around it. Forum text never leaves the
// browser except as the drafts an agent writes in its own words; the reading LIST (ids, titles, read marks) is
// exported to disk with V.exportList() so a reset browser profile can be restored with V.importList().
//
//   V.collect()          build the reading list from search pages (background; ~2 pages per term)
//   V.read()             read the list one page per 40 s (background); questions first, then articles
//   V.status()           counts and the last log lines
//   V.dig(skip, n)       stored bodies of the read items, in read order (for the extraction agent)
//   V.exportList(i, n)   a slice of the list as JSON, to be written to disk
//   V.importList(json)   merge a slice back (after a profile reset)
//   V.backup()           compact JSON of the read marks and read order (small; write it to disk)
//   V.restore(json)      put the read marks back after a profile reset (then V.collect() refills titles)
//   V.markUsed(ids)      mark source ids already in the bench as done
//   V.stop()             stop both background loops after the current page
(() => {
  const PACE = 40000;
  const TERMS = ["agent unavailable", "agent communication", "job ended notok", "job stuck executing", "oscompstat",
    "new day procedure", "user daily", "order job", "cyclic job", "rerun", "condition", "quantitative resource",
    "control resource", "calendar", "rule based calendar", "time zone", "smart folder", "file watcher",
    "managed file transfer", "sftp", "ssl certificate", "keystore", "password", "run as user", "ldap",
    "windows agent", "logon as user", "permission denied", "disk full", "database", "postgresql", "oracle",
    "high availability", "failover", "gateway", "enterprise manager", "ccm", "automation api", "ctmcontb",
    "ctmorder", "ctmpsm", "variable autoedit", "on do action", "shout email", "alert", "sla service",
    "workload policy", "upgrade", "fix pack", "patch", "sap job", "informatica", "remote host agentless",
    "host group", "timeout", "performance slow", "archiving", "reports", "z/os"];
  const ls = {get: (k, d) => { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch (e) { return d; } },
              set: (k, v) => localStorage.setItem(k, JSON.stringify(v))};
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const log = m => { const L = ls.get("vLog", []); L.push(new Date().toTimeString().slice(0, 8) + " " + m); ls.set("vLog", L.slice(-2000)); };
  const fnv = s => { let h = 0x811c9dc5; for (const c of s) { h ^= c.charCodeAt(0); h = Math.imul(h, 0x01000193) >>> 0; } return h; };
  const split = id => (fnv(id) % 10 < 3 ? "test" : "dev");
  const deep = n => { let s = ""; for (const k of (n.shadowRoot ? [...n.shadowRoot.childNodes, ...n.childNodes] : n.childNodes)) {
    if (k.nodeType === 3) s += k.textContent; else if (k.nodeType === 1 && k.tagName !== "SCRIPT" && k.tagName !== "STYLE") s += " " + deep(k) + " "; } return s; };
  const blocked = (win, text) => {
    try { const P = win.performance; const nv = P.getEntriesByType("navigation")[0];
      if ((nv && nv.responseStatus === 429) || P.getEntriesByType("resource").some(r => r.responseStatus === 429)) return true; } catch (e) {}
    return /Too Many Requests|Just a moment|Checking your browser|Bir dakika/i.test(text || "");
  };
  const db = () => new Promise((res, rej) => { const r = indexedDB.open("vardiya2", 1);
    r.onupgradeneeded = () => r.result.createObjectStore("bodies"); r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error); });
  const put = async (k, v) => { const d = await db(); await new Promise((res, rej) => { const t = d.transaction("bodies", "readwrite"); t.objectStore("bodies").put(v, k); t.oncomplete = res; t.onerror = () => rej(t.error); }); };
  const get = async k => { const d = await db(); return new Promise((res, rej) => { const q = d.transaction("bodies").objectStore("bodies").get(k); q.onsuccess = () => res(q.result); q.onerror = () => rej(q.error); }); };

  // ---- list: {id: {t: "a"|"q", ti: title, s: dev|test, q: [terms], st: 0 unread | 1 read | 2 used | 9 failed}}
  const list = () => ls.get("vList", {});
  const add = (id, type, title, term) => { const L = list(); const e = L[id] || {t: type, ti: title.slice(0, 160), s: split(id), q: [], st: 0};
    if (!e.q.includes(term)) e.q.push(term); L[id] = e; ls.set("vList", L); };

  async function collect() {
    if (window.vCollecting) return "zaten calisiyor";
    window.vCollecting = true; log("toplama basladi");
    let state = ls.get("vCollect", {i: 0, first: 0});
    try {
      while (!localStorage.vStop && state.i < TERMS.length) {
        const t0 = Date.now(), term = TERMS[state.i];
        if (!location.pathname.includes("/global-search/")) { log("arama sayfasinda degil, durdu"); break; }
        location.hash = `#q=${encodeURIComponent("control-m " + term)}&t=All&sort=relevancy&numberOfResults=100&first=${state.first}`;
        let ok = false, text = "";
        for (let k = 0; k < 60; k++) { await sleep(500); text = deep(document.body).replace(/\s+/g, " ");
          const m = text.match(/Results\s+([\d,]+)\s*-\s*([\d,]+)\s+of\s+([\d,]+)/i);
          if (m && +m[1].replace(/,/g, "") === state.first + 1) { ok = true; state.total = +m[3].replace(/,/g, ""); break; } }
        if (blocked(window, text)) { log("ENGEL - toplama durdu"); localStorage.vStop = "engel"; break; }
        let found = 0;
        if (ok) {
          const visit = root => { for (const e of root.querySelectorAll("*")) { const h = e.getAttribute("href") || "";
            const m = h.match(/\/(article|question)\/([A-Za-z0-9]{15,18})/); if (m) { add(m[2], m[1] === "article" ? "a" : "q", (e.textContent || "").trim(), term); found++; }
            if (e.shadowRoot) visit(e.shadowRoot); } };
          visit(document);
        }
        log(`toplama ${term} @${state.first}: ${ok ? found : "sonuc gelmedi"}`);
        // two pages (200 results) per term: past that the results stop being about the term
        if (ok && found >= 50 && state.first < 100 && state.total > state.first + 100) state.first += 100; else { state.i++; state.first = 0; }
        ls.set("vCollect", state);
        const w = PACE - (Date.now() - t0); if (w > 0) await sleep(w);
      }
      if (state.i >= TERMS.length) log("toplama bitti");
    } finally { window.vCollecting = false; }
    return "bitti";
  }

  async function read() {
    if (window.vReading) return "zaten calisiyor";
    window.vReading = true; log("okuma basladi");
    const cur = localStorage.vCur; if (cur) { const L = list(); if (L[cur]) { L[cur].st = 9; ls.set("vList", L); } log("takilan sayfa atlandi " + cur); delete localStorage.vCur; }
    let fails = 0;
    try {
      while (!localStorage.vStop) {
        const L = list(), ids = Object.keys(L).filter(k => L[k].s === "dev" && L[k].st === 0);
        const next = ids.find(k => L[k].t === "q") || ids[0];
        if (!next) { log("okunacak kalmadi"); break; }
        const e = L[next], t0 = Date.now(), isQ = e.t === "q";
        localStorage.vCur = next;
        const f = document.createElement("iframe"); f.style.cssText = "width:1200px;height:900px;position:fixed;left:-3000px;top:0";
        f.src = `/s/${isQ ? "question" : "article"}/${next}`; document.body.appendChild(f);
        let t = "", ok = false;
        for (let i = 0; i < 70; i++) { await sleep(500); try { const b = f.contentDocument && f.contentDocument.body; if (b) { t = deep(b).replace(/\s+/g, " ");
          if (isQ ? (/\d[\d,]* views?/.test(t) && /Write an answer|Share This Page|Related Questions/.test(t)) : /URL Name/.test(t)) { ok = true; break; } } } catch (x) {} }
        const stop = blocked(f.contentWindow, t);
        f.remove();
        if (stop) { log("ENGEL " + next + " - okuma durdu"); localStorage.vStop = "engel"; delete localStorage.vCur; break; }
        const L2 = list();
        if (!ok) { fails++; L2[next].st = 9; log("okunamadi " + next); if (fails >= 3) { ls.set("vList", L2); log("3 ardisik hata - durdu"); localStorage.vStop = "hata"; delete localStorage.vCur; break; } }
        else {
          fails = 0; let body;
          if (isQ) {
            const qa = t.indexOf("asked a question"), qe = t.indexOf("Expand Post", qa);
            const q = t.slice(t.indexOf("Actions for this Feed Item", qa) + 26, qe).trim();
            const clean = s => s.replace(/Actions for this Feed Item|Comment|Expand Post|Upvote|Upvoted|Downvoted|Remove Upvote|Reply|\d+ (years?|months?|days?) ago/g, " ").replace(/\s+/g, " ").trim();
            const vi = t.search(/\d[\d,]* views?/);
            const ends = [t.indexOf("Write an answer", vi), t.indexOf("Share This Page", vi), t.indexOf("Related Questions", vi)].filter(x => x > 0);
            const ans = vi > 0 ? t.slice(vi, ends.length ? Math.min(...ends) : vi + 6000) : "";
            const parts = ans.split("Actions for this Feed Item").slice(1).map(p => p.replace(/Selected as Best/g, " [EN IYI] ")).map(clean).filter(x => x.length > 15);
            body = {Question: q, Best: (parts.find(p => p.includes("[EN IYI]")) || "").slice(0, 2500), Answers: parts.join(" || ").slice(0, 4000)};
          } else {
            const sec = {}, re = /(Problem|Cause|Solution|Question|Answer|Workaround|Additional Information|Symptoms?|Resolution) Help \1 /g;
            const marks = [...t.matchAll(re)], end = t.indexOf("URL Name");
            marks.forEach((m, i) => { const s = m.index + m[0].length, en = i + 1 < marks.length ? marks[i + 1].index : end; sec[m[1]] = t.slice(s, en > s ? en : s + 3000).trim(); });
            if (!marks.length) sec.Raw = t.slice(0, 4000);
            body = sec;
          }
          await put(next, body); L2[next].st = 1;
          const order = ls.get("vOrder", []); order.push(next); ls.set("vOrder", order);
          log("ok " + next + " " + (L2[next].ti || "").slice(0, 50));
        }
        ls.set("vList", L2); delete localStorage.vCur;
        const w = PACE - (Date.now() - t0); if (w > 0) await sleep(w);
      }
    } finally { window.vReading = false; log("okuma cikti"); }
    return "bitti";
  }

  async function dig(skip, n) {
    const order = ls.get("vOrder", []), L = list(), out = [];
    for (const [i, id] of order.slice(skip, skip + n).entries()) { const b = (await get(id)) || {}, e = L[id] || {};
      out.push(e.t === "q" ? {i: skip + i, id, q: (b.Question || "").replace(/\s+/g, " ").slice(0, 600), best: (b.Best || "").slice(0, 900), answers: b.Best ? "" : (b.Answers || "").slice(0, 1100)}
        : {i: skip + i, id, title: e.ti, problem: (b.Problem || b.Question || b.Symptoms || b.Raw || "").slice(0, 600), cause: (b.Cause || "").slice(0, 300),
           solution: (b.Solution || b.Answer || b.Resolution || "").slice(0, 1000)}); }
    return JSON.stringify({total: order.length, items: out});
  }
  function status() {
    const L = list(), v = Object.values(L), c = f => v.filter(f).length;
    return JSON.stringify({liste: v.length, dev: c(e => e.s === "dev"), test: c(e => e.s === "test"),
      okunan: c(e => e.st === 1), kullanilmis: c(e => e.st === 2), atlanan: c(e => e.st === 9),
      kalan_soru: c(e => e.s === "dev" && e.st === 0 && e.t === "q"), kalan_makale: c(e => e.s === "dev" && e.st === 0 && e.t === "a"),
      toplama: ls.get("vCollect", {}), toplaniyor: !!window.vCollecting, okunuyor: !!window.vReading, dur: localStorage.vStop || "",
      son: ls.get("vLog", []).slice(-3)});
  }
  const exportList = (i = 0, n = 800) => { const L = list(), keys = Object.keys(L).sort();
    return JSON.stringify({total: keys.length, from: i, items: Object.fromEntries(keys.slice(i, i + n).map(k => [k, L[k]])), order: i === 0 ? ls.get("vOrder", []) : undefined}); };
  const importList = json => { const x = typeof json === "string" ? JSON.parse(json) : json, L = list();
    for (const [k, e] of Object.entries(x.items || {})) { if (!L[k] || (e.st && !L[k].st)) L[k] = e; }
    ls.set("vList", L); if (x.order) ls.set("vOrder", [...new Set([...ls.get("vOrder", []), ...x.order])]); return Object.keys(L).length; };
  // compact backup: only what cannot be re-collected from search, the read marks and the read order ("id:st,...")
  const backup = () => { const L = list(); return JSON.stringify({c: ls.get("vCollect", {}),
    m: Object.entries(L).filter(([, e]) => e.st).map(([k, e]) => k + ":" + e.st).join(","), o: ls.get("vOrder", []).join(",")}); };
  const restore = json => { const x = typeof json === "string" ? JSON.parse(json) : json, L = list(); let n = 0;
    for (const p of (x.m || "").split(",").filter(Boolean)) { const [k, st] = p.split(":");
      L[k] = L[k] || {t: k.startsWith("0D5") ? "q" : "a", ti: "", s: split(k), q: [], st: 0}; L[k].st = +st; n++; }
    ls.set("vList", L); if (x.o) ls.set("vOrder", [...new Set([...ls.get("vOrder", []), ...x.o.split(",").filter(Boolean)])]);
    if (x.c && !localStorage.vCollect) ls.set("vCollect", x.c); return n; };
  const markUsed = ids => { const L = list(); let n = 0; for (const id of ids) if (L[id] && L[id].st === 0) { L[id].st = 2; n++; } ls.set("vList", L); return n; };
  const stop = () => { localStorage.vStop = "elle"; return "duracak"; };
  const go = () => { delete localStorage.vStop; return "devam"; };
  window.V = {collect, read, dig, status, exportList, importList, backup, restore, markUsed, stop, go, TERMS};
  return "V kuruldu: " + status();
})();
