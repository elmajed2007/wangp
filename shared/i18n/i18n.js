/* WanGP live UI translator (text nodes + attributes) and RTL switch.
   Dictionary: window.WANGP_I18N_URL ({strings:{en:ar}, templates:{"en {}":"ar {}"}}). */
(function () {
  "use strict";
  if (window.__wangpI18n) return;
  const LANG = window.WANGP_I18N_LANG || "ar";
  const RTL = /^(ar|fa|he|ur)/.test(LANG);
  const api = (window.__wangpI18n = { lang: LANG, ready: false, tr: (s) => s });

  // Make Gradio's own built-in strings (upload boxes, toasts, footer...) use its bundled locale.
  try {
    Object.defineProperty(navigator, "language", { get: () => LANG, configurable: true });
    Object.defineProperty(navigator, "languages", { get: () => [LANG, "en"], configurable: true });
  } catch (e) {}

  const html = document.documentElement;
  html.setAttribute("lang", LANG);
  if (RTL) html.setAttribute("dir", "rtl");
  html.classList.add("wangp-i18n", "wangp-lang-" + LANG);

  const SKIP_TAGS = new Set(["SCRIPT", "STYLE", "TEXTAREA", "CODE", "PRE", "NOSCRIPT", "SVG", "MATH", "KBD", "SAMP", "CANVAS"]);
  const SKIP_SEL = "[contenteditable=''],[contenteditable='true'],.no-translate,[data-no-translate],.cm-editor,.monaco-editor,[data-testid='textbox'] textarea";
  const ATTRS = ["placeholder", "title", "aria-label", "data-tooltip", "alt"];
  const WS = /\s+/g;

  let STR = new Map();
  let TPL = [];
  const cache = new Map();
  const produced = new Set(); // Arabic strings we wrote, never re-translate them

  function fill(tpl, args) {
    if (/\{\d+\}/.test(tpl)) return tpl.replace(/\{(\d+)\}/g, (m, i) => (args[+i] !== undefined ? args[+i] : m));
    let i = 0;
    return tpl.replace(/\{\}/g, () => (args[i++] !== undefined ? args[i - 1] : ""));
  }

  function core(n) {
    if (cache.has(n)) return cache.get(n);
    let res = STR.get(n);
    if (res === undefined) {
      const s = n.replace(/^[\s\-•·|]+|[\s\-•·|]+$/g, "");
      if (s !== n && STR.has(s)) res = n.replace(s, STR.get(s));
    }
    if (res === undefined && n.length < 800) {
      for (const t of TPL) {
        if (t.anchor && n.indexOf(t.anchor) < 0) continue;
        const m = t.rx.exec(n);
        if (m) { res = fill(t.ar, m.slice(1).map((g) => tr(g))); break; }
      }
    }
    if (res === undefined) res = null;
    if (cache.size > 50000) cache.clear();
    cache.set(n, res);
    return res;
  }

  function tr(text) {
    if (!text || typeof text !== "string") return text;
    const n = text.replace(WS, " ").trim();
    if (!n || produced.has(n) || !/[A-Za-z]/.test(n)) return text;
    const res = core(n);
    if (res == null) return text;
    produced.add(res.replace(WS, " ").trim());
    const lead = text.match(/^\s*/)[0], trail = text.match(/\s*$/)[0];
    return lead + res + trail;
  }
  api.tr = tr;

  function skipped(el) {
    for (let e = el; e && e.nodeType === 1; e = e.parentElement) {
      if (SKIP_TAGS.has(e.tagName.toUpperCase())) return true;
      if (e.matches && e.matches(SKIP_SEL)) return true;
    }
    return false;
  }

  function doText(node) {
    const v = node.nodeValue;
    if (!v || v.length > 2000 || !/[A-Za-z]/.test(v)) return;
    const p = node.parentElement;
    if (!p || skipped(p)) return;
    const t = tr(v);
    if (t !== v) node.nodeValue = t;
  }

  function doAttrs(el) {
    if (el.nodeType !== 1 || skipped(el)) return;
    for (const a of ATTRS) {
      const v = el.getAttribute && el.getAttribute(a);
      if (v && /[A-Za-z]/.test(v)) { const t = tr(v); if (t !== v) el.setAttribute(a, t); }
    }
    if (el.tagName === "INPUT" && (el.type === "button" || el.type === "submit") && el.value) {
      const t = tr(el.value); if (t !== el.value) el.value = t;
    }
    if (RTL && el.tagName === "TEXTAREA" && !el.hasAttribute("dir")) el.setAttribute("dir", "auto");
    if (RTL && el.tagName === "INPUT" && el.type === "text" && !el.hasAttribute("dir")) el.setAttribute("dir", "auto");
  }

  function walk(root) {
    if (!root) return;
    if (root.nodeType === 3) return doText(root);
    if (root.nodeType !== 1 && root.nodeType !== 11) return;
    if (root.nodeType === 1) { if (skipped(root)) return; doAttrs(root); }
    const it = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT, {
      acceptNode(n) {
        if (n.nodeType === 1) return SKIP_TAGS.has(n.tagName.toUpperCase()) || (n.matches && n.matches(SKIP_SEL)) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT;
        return NodeFilter.FILTER_ACCEPT;
      },
    });
    let n;
    while ((n = it.nextNode())) {
      if (n.nodeType === 3) doText(n); else { doAttrs(n); if (n.shadowRoot) observeRoot(n.shadowRoot); }
    }
  }

  const pending = new Set();
  let scheduled = false;
  function flush() {
    scheduled = false;
    const items = Array.from(pending); pending.clear();
    for (const n of items) { if (n.isConnected !== false) walk(n); }
  }
  function queue(n) { pending.add(n); if (!scheduled) { scheduled = true; requestAnimationFrame(flush); } }

  const observed = new WeakSet();
  function observeRoot(root) {
    if (observed.has(root)) return;
    observed.add(root);
    new MutationObserver((muts) => {
      for (const m of muts) {
        if (m.type === "childList") m.addedNodes.forEach(queue);
        else if (m.type === "characterData") queue(m.target);
        else if (m.type === "attributes") queue(m.target);
      }
    }).observe(root, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ATTRS.concat(["value"]) });
    walk(root);
  }

  // translate document title too
  function doTitle() { if (document.title) { const t = tr(document.title); if (t !== document.title) document.title = t; } }

  function start(dict) {
    STR = new Map(Object.entries(dict.strings || {}).filter(([k, v]) => v && v !== k).map(([k, v]) => [k.replace(WS, " ").trim(), v]));
    TPL = Object.entries(dict.templates || {}).filter(([k, v]) => v && v !== k).map(([k, v]) => {
      const parts = k.split("{}");
      const rx = new RegExp("^" + parts.map((p) => p.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("(.+?)") + "$", "s");
      return { rx, ar: v, anchor: parts.reduce((a, b) => (b.length > a.length ? b : a), "") };
    }).sort((a, b) => b.anchor.length - a.anchor.length);
    api.ready = true;
    const boot = () => { observeRoot(document.documentElement); doTitle(); };
    if (document.body) boot(); else document.addEventListener("DOMContentLoaded", boot);
    new MutationObserver(doTitle).observe(document.querySelector("title") || document.head, { childList: true, characterData: true, subtree: true });
    // Gradio renders some components inside shadow roots attached later
    const origAttach = Element.prototype.attachShadow;
    Element.prototype.attachShadow = function (init) { const r = origAttach.call(this, init); setTimeout(() => observeRoot(r), 0); return r; };
  }

  let cached = null;
  try { cached = sessionStorage.getItem("wangp-i18n:" + window.WANGP_I18N_URL); } catch (e) {}
  if (cached) { try { start(JSON.parse(cached)); return; } catch (e) {} }
  fetch(window.WANGP_I18N_URL || "/wangp-i18n/dict.json", { credentials: "same-origin" })
    .then((r) => r.json())
    .then((d) => { try { sessionStorage.setItem("wangp-i18n:" + window.WANGP_I18N_URL, JSON.stringify(d)); } catch (e) {} start(d); })
    .catch((e) => console.warn("[wangp-i18n] dictionary not loaded", e));
})();
