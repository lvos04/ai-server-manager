// Peil-ontwerpreview — metingen in de gerenderde pagina (wordt als init-script geladen; plain JS, geen build-stap).
// Afgeleid van design/ontwerptaal/bouw/controle.cjs (gerenderd contrast incl. opacity en arcering, doelgrootte,
// overloop, afkappen, stippel- en veldranden, focusring en bedekte focus) en aangevuld met de Peil-semantiek:
// groen alleen voor "gemeten en goed", onbekend/verouderd nooit groen, status nooit alleen kleur, microcopy.
(() => {
  const cvs = document.createElement("canvas");
  cvs.width = cvs.height = 1;
  let ctx = null;
  const cache = new Map();
  const rgba = (s) => {
    if (cache.has(s)) return cache.get(s);
    if (!ctx) ctx = cvs.getContext("2d", { willReadFrequently: true });
    ctx.clearRect(0, 0, 1, 1);
    ctx.fillStyle = "#000";
    ctx.fillStyle = s;
    ctx.fillRect(0, 0, 1, 1);
    const d = ctx.getImageData(0, 0, 1, 1).data;
    const v = [d[0], d[1], d[2], d[3] / 255];
    cache.set(s, v);
    return v;
  };
  const over = (t, b) => {
    const a = t[3] + b[3] * (1 - t[3]);
    if (a === 0) return [0, 0, 0, 0];
    return [0, 1, 2].map((i) => (t[i] * t[3] + b[i] * b[3] * (1 - t[3])) / a).concat([a]);
  };
  const mix = (a, b, t) => [0, 1, 2].map((i) => a[i] * (1 - t) + b[i] * t).concat([1]);
  const lum = (c) => {
    const f = (v) => {
      v /= 255;
      return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
    };
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]);
  };
  const ratio = (a, b) => {
    const x = lum(a),
      y = lum(b);
    return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05);
  };
  const hex = (c) => "#" + c.slice(0, 3).map((v) => Math.round(v).toString(16).padStart(2, "0")).join("");
  const colorsIn = (img) => img.match(/(rgba?\([^)]*\)|oklch\([^)]*\)|oklab\([^)]*\)|color\([^)]*\)|#[0-9a-f]{3,8})/gi) || [];
  const chain = (el) => {
    const c = [];
    for (let e = el; e && e.nodeType === 1; e = e.parentElement) c.push(e);
    return c;
  };
  function paint(el, fg) {
    const ch = chain(el);
    const alts = [];
    function rec(k, backdrop) {
      const e = ch[k];
      const cs = getComputedStyle(e);
      const inside = over(rgba(cs.backgroundColor), backdrop);
      if (cs.backgroundImage && cs.backgroundImage !== "none")
        for (const s of colorsIn(cs.backgroundImage)) {
          const c = rgba(s);
          if (c[3] > 0.05) alts.push(over(c, inside));
        }
      let Bin, Tin;
      if (k === 0) {
        Bin = inside;
        Tin = over(fg, inside);
      } else [Bin, Tin] = rec(k - 1, inside);
      const o = parseFloat(cs.opacity);
      if (o < 1) return [mix(backdrop, Bin, o), mix(backdrop, Tin, o)];
      return [Bin, Tin];
    }
    const [B, T] = rec(ch.length - 1, [255, 255, 255, 1]);
    return { B, T, alts };
  }
  const cumOpacity = (el) => chain(el).reduce((p, e) => p * parseFloat(getComputedStyle(e).opacity), 1);
  const isSrOnly = (el) => {
    for (const e of chain(el)) {
      const cs = getComputedStyle(e);
      if (
        cs.clip === "rect(0px, 0px, 0px, 0px)" ||
        (cs.position === "absolute" && parseFloat(cs.width) <= 1 && parseFloat(cs.height) <= 1 && cs.overflow === "hidden") ||
        cs.clipPath === "inset(50%)"
      )
        return true;
    }
    return false;
  };
  const visible = (el) => {
    // Inhoud van een dichte <details> wordt niet weergegeven (Chromium slaat daar ook de stijl over).
    const dicht = el.closest("details:not([open])");
    if (dicht && !el.closest("summary")) return false;
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) return false;
    if (getComputedStyle(el).visibility === "hidden") return false;
    return !isSrOnly(el);
  };
  const desc = (el) => {
    const id = el.id ? "#" + el.id : "";
    const tid = el.getAttribute("data-testid") ? `[${el.getAttribute("data-testid")}]` : "";
    const cls = (el.getAttribute("class") || "").split(/\s+/).filter(Boolean).slice(0, 4).join(".");
    return el.tagName.toLowerCase() + id + tid + (cls ? "." + cls : "");
  };
  const txt = (el) =>
    [...el.childNodes]
      .filter((n) => n.nodeType === 3)
      .map((n) => n.textContent)
      .join("")
      .replace(/\s+/g, " ")
      .trim();
  const tekstVan = (el) => (el.innerText || el.textContent || "").replace(/\s+/g, " ").trim();

  function meet() {
    const tekst = [];
    let minFont = 99;
    const kleinFont = [];
    for (const el of document.querySelectorAll("body *")) {
      if (["SCRIPT", "STYLE", "NOSCRIPT", "TEMPLATE"].includes(el.tagName)) continue;
      const t = txt(el);
      if (!t || !visible(el)) continue;
      const cs = getComputedStyle(el);
      const fgS = el instanceof SVGElement ? cs.fill : cs.color;
      if (!fgS || fgS === "none" || fgS.startsWith("url")) continue;
      const fg = rgba(fgS);
      const { B, T, alts } = paint(el, fg);
      const fs = parseFloat(cs.fontSize),
        fw = parseInt(cs.fontWeight);
      const groot = fs >= 24 || (fs >= 18.66 && fw >= 700);
      const eis = groot ? 3 : 4.5;
      const r = ratio(T, B);
      let rAlt = r;
      for (const a of alts) rAlt = Math.min(rAlt, ratio(over(fg, a), a));
      if (fs < minFont) minFont = fs;
      if (fs < 14) kleinFont.push({ el: desc(el), t: t.slice(0, 40), fs });
      tekst.push({
        el: desc(el),
        t: t.slice(0, 60),
        fs,
        fw,
        groot,
        eis,
        r: +r.toFixed(2),
        rAlt: +rAlt.toFixed(2),
        fg: hex(T),
        bg: hex(B),
        op: +cumOpacity(el).toFixed(2),
        dis: !!el.closest(':disabled,[aria-disabled="true"]'),
        stale: !!el.closest(".arcering"),
      });
    }
    for (const el of document.querySelectorAll("input[placeholder],textarea[placeholder]")) {
      if (!visible(el)) continue;
      const fg = rgba(getComputedStyle(el, "::placeholder").color);
      const { B, T } = paint(el, fg);
      tekst.push({ el: desc(el) + "::placeholder", t: el.placeholder.slice(0, 50), fs: parseFloat(getComputedStyle(el).fontSize), eis: 4.5, r: +ratio(T, B).toFixed(2), rAlt: +ratio(T, B).toFixed(2), fg: hex(T), bg: hex(B), op: 1 });
    }
    const velden = [];
    for (const el of document.querySelectorAll("input:not([type=hidden]),select,textarea")) {
      if (!visible(el)) continue;
      const cs = getComputedStyle(el);
      const par = paint(el.parentElement, [0, 0, 0, 0]).B;
      const own = paint(el, [0, 0, 0, 0]).B;
      const bc = over(rgba(cs.borderBottomColor), own);
      velden.push({ el: desc(el), type: el.type, rand: +ratio(bc, par).toFixed(2), vlak: +ratio(own, par).toFixed(2), bw: parseFloat(cs.borderBottomWidth), kleur: hex(bc), h: Math.round(el.getBoundingClientRect().height) });
    }
    const stippel = [];
    for (const el of document.querySelectorAll("body *")) {
      const cs = getComputedStyle(el);
      const sides = ["Top", "Left", "Bottom"].filter((s) => ["dashed", "dotted"].includes(cs["border" + s + "Style"]));
      if (!sides.length || !visible(el)) continue;
      const side = sides[0];
      const par = paint(el.parentElement, [0, 0, 0, 0]).B;
      const bc = over(rgba(cs["border" + side + "Color"]), par);
      stippel.push({ el: desc(el), t: tekstVan(el).slice(0, 40), bw: parseFloat(cs["border" + side + "Width"]), buiten: +ratio(bc, par).toFixed(2), kleur: hex(bc) });
    }
    const doelen = [];
    for (const el of document.querySelectorAll(
      'a[href],button,input:not([type=hidden]),select,textarea,summary,[role=button],[role=tab],[role=link],[role=menuitem],[role=radio],[role=checkbox],[role=switch],[tabindex]:not([tabindex="-1"])',
    )) {
      if (!visible(el)) continue;
      if (el.classList.contains("skip-link")) continue;
      const r = el.getBoundingClientRect();
      const inline = el.tagName === "A" && getComputedStyle(el).display === "inline" && el.parentElement && txt(el.parentElement).length > 0;
      const lab = (el.type === "radio" || el.type === "checkbox") && el.closest("label");
      const lr = lab && lab.getBoundingClientRect();
      if (lr && lr.width >= 44 && lr.height >= 44) continue;
      if (r.width < 43.5 || r.height < 43.5) doelen.push({ el: desc(el), t: (el.innerText || el.getAttribute("aria-label") || "").replace(/\s+/g, " ").trim().slice(0, 40), w: Math.round(r.width), h: Math.round(r.height), inline });
    }
    const se = document.scrollingElement;
    const overloop = se.scrollWidth - se.clientWidth;
    const breed = [];
    if (overloop > 0) {
      const cw = se.clientWidth;
      for (const el of document.querySelectorAll("body *")) {
        const r = el.getBoundingClientRect();
        if (r.width > 0 && r.right > cw + 1 && !el.closest(".table-wrap")) breed.push(`${desc(el)} right=${Math.round(r.right)}`);
        if (breed.length > 6) break;
      }
    }
    const afgekapt = [];
    for (const el of document.querySelectorAll("body *")) {
      const cs = getComputedStyle(el);
      if (cs.textOverflow === "ellipsis" && visible(el) && el.scrollWidth > el.clientWidth + 1) afgekapt.push({ el: desc(el), t: tekstVan(el).slice(0, 60) });
    }
    // Inhoud die buiten zijn eigen kader loopt zonder dat het kader scrollt (afgesneden of over de rand).
    const knip = [];
    for (const el of document.querySelectorAll("main *, header *, nav *")) {
      if (!visible(el)) continue;
      const cs = getComputedStyle(el);
      if ((cs.overflowX === "hidden" || cs.overflowX === "clip") && el.scrollWidth > el.clientWidth + 2 && tekstVan(el).length > 0 && !isSrOnly(el)) knip.push({ el: desc(el), t: tekstVan(el).slice(0, 50), sw: el.scrollWidth, cw: el.clientWidth });
    }
    // Tekstoverlap: tekstvakken van verschillende elementen die elkaar raken (labels over elkaar, badge over tekst).
    const vakken = [];
    const vast = (el) => chain(el).some((e) => ["fixed", "sticky"].includes(getComputedStyle(e).position));
    for (const el of document.querySelectorAll("body *")) {
      if (["SCRIPT", "STYLE", "NOSCRIPT", "TEMPLATE"].includes(el.tagName) || el instanceof SVGElement) continue;
      if (!txt(el) || !visible(el) || vast(el)) continue;
      const range = document.createRange();
      for (const n of el.childNodes) {
        if (n.nodeType !== 3 || !n.textContent.trim()) continue;
        range.selectNodeContents(n);
        for (const r of range.getClientRects()) if (r.width > 1 && r.height > 1) vakken.push({ el, r });
      }
      if (vakken.length > 1500) break;
    }
    const overlap = [];
    for (let i = 0; i < vakken.length && overlap.length < 8; i++)
      for (let j = i + 1; j < vakken.length; j++) {
        const a = vakken[i], b = vakken[j];
        if (a.el === b.el || a.el.contains(b.el) || b.el.contains(a.el)) continue;
        const dx = Math.min(a.r.right, b.r.right) - Math.max(a.r.left, b.r.left);
        const dy = Math.min(a.r.bottom, b.r.bottom) - Math.max(a.r.top, b.r.top);
        if (dx > 2 && dy > 3) {
          // Alleen echt zichtbare overlap (niet onder een overlay of popover die bewust over de pagina ligt).
          const cx = Math.max(a.r.left, b.r.left) + dx / 2, cy = Math.max(a.r.top, b.r.top) + dy / 2;
          const binnen = cx >= 0 && cy >= 0 && cx <= innerWidth && cy <= innerHeight;
          const top = binnen ? document.elementFromPoint(cx, cy) : null;
          if (!binnen || (top && (top === a.el || top === b.el || a.el.contains(top) || b.el.contains(top))))
            overlap.push(`${desc(a.el)} "${tekstVan(a.el).slice(0, 25)}" × ${desc(b.el)} "${tekstVan(b.el).slice(0, 25)}"`);
          if (overlap.length >= 8) break;
        }
      }
    return { tekst, minFont, kleinFont, velden, stippel, doelen, overloop, breed, afgekapt, knip: knip.slice(0, 10), overlap };
  }

  function focus() {
    const el = document.activeElement;
    if (!el || el === document.body) return null;
    const cs = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    const d = el.tagName.toLowerCase() + (el.id ? "#" + el.id : "") + (el.getAttribute("data-testid") ? `[${el.getAttribute("data-testid")}]` : "") + ' "' + (el.innerText || el.getAttribute("aria-label") || "").replace(/\s+/g, " ").trim().slice(0, 30) + '"';
    const pts = [
      [r.left + r.width / 2, r.top + r.height / 2],
      [r.left + 2, r.top + 2],
      [r.right - 2, r.bottom - 2],
      [r.left + 2, r.bottom - 2],
      [r.right - 2, r.top + 2],
    ];
    let zichtbaarPt = 0,
      inViewport = 0;
    for (const [x, y] of pts) {
      if (x < 0 || y < 0 || x > innerWidth || y > innerHeight) continue;
      inViewport++;
      const top = document.elementFromPoint(x, y);
      if (top && (top === el || el.contains(top) || top.contains(el))) zichtbaarPt++;
    }
    const bgOf = (e) => {
      const layers = [];
      for (let p = e; p && p.nodeType === 1; p = p.parentElement) layers.push(rgba(getComputedStyle(p).backgroundColor));
      let c = [255, 255, 255, 1];
      for (const l of layers.reverse()) c = over(l, c);
      return c;
    };
    const parBg = bgOf(el.parentElement || el);
    const ow = parseFloat(cs.outlineWidth);
    const ost = cs.outlineStyle;
    const oc = rgba(cs.outlineColor);
    const has = ost !== "none" && ow > 0;
    // Ring geheel of deels buiten een scrollkader met overflow hidden? (afgesneden focus)
    let geknipt = false;
    for (let p = el.parentElement; p && p !== document.body; p = p.parentElement) {
      const pcs = getComputedStyle(p);
      if (pcs.overflowX !== "visible" || pcs.overflowY !== "visible") {
        const pr = p.getBoundingClientRect();
        const m = ow + parseFloat(cs.outlineOffset || "0");
        if (r.left - m < pr.left - 0.5 || r.right + m > pr.right + 0.5 || r.top - m < pr.top - 0.5 || r.bottom + m > pr.bottom + 0.5) geknipt = true;
        break;
      }
    }
    return {
      desc: d,
      ow,
      ost,
      offset: parseFloat(cs.outlineOffset),
      ringR: has ? +ratio(over(oc, parBg), parBg).toFixed(2) : 0,
      bs: cs.boxShadow !== "none" ? cs.boxShadow.slice(0, 80) : "",
      inViewport,
      zichtbaarPt,
      geknipt,
      rTop: Math.round(r.top),
      rBottom: Math.round(r.bottom),
      w: Math.round(r.width),
      h: Math.round(r.height),
    };
  }

  // Peil-semantiek: groen alleen voor "gemeten en goed"; onbekend/verouderd nooit groen; status nooit alleen kleur.
  function semantiek() {
    const root = getComputedStyle(document.documentElement);
    const tok = (n) => {
      const v = root.getPropertyValue(n).trim();
      if (!v) return null;
      const c = rgba(v);
      return c.slice(0, 3).join(",");
    };
    const key = (s) => {
      if (!s || s === "none" || s.startsWith("url")) return null;
      const c = rgba(s);
      if (c[3] < 0.05) return null;
      return c.slice(0, 3).join(",");
    };
    const groenTok = new Set(["--healthy", "--healthy-ink", "--healthy-bg"].map(tok).filter(Boolean));
    const statusBg = {};
    for (const n of ["healthy", "degraded", "down", "unknown", "info", "approval", "stale"]) {
      const v = tok(`--${n}-bg`);
      if (v) statusBg[v] = n;
    }
    const statusRand = {};
    for (const n of ["healthy", "degraded", "down", "unknown", "stale"]) {
      const v = tok(`--${n}`);
      if (v) statusRand[v] = n;
    }
    const groen = [];
    const kleurAlleen = [];
    const zonderIcoon = [];
    const ctxTekst = (el) => {
      for (let e = el; e && e !== document.body; e = e.parentElement) {
        const t = tekstVan(e);
        if (t) return t.slice(0, 120);
      }
      return "";
    };
    for (const el of document.querySelectorAll("body *")) {
      if (!visible(el) && !(el instanceof SVGElement)) continue;
      if (el instanceof SVGElement && el.getClientRects().length === 0) continue;
      const cs = getComputedStyle(el);
      const keys = [];
      if (el instanceof SVGElement) {
        keys.push(key(cs.stroke), key(cs.fill), key(cs.color));
      } else {
        if (txt(el)) keys.push(key(cs.color));
        keys.push(key(cs.backgroundColor));
        if (parseFloat(cs.borderTopWidth) > 0 && cs.borderTopStyle !== "none") keys.push(key(cs.borderTopColor));
        if (parseFloat(cs.borderLeftWidth) > 0 && cs.borderLeftStyle !== "none") keys.push(key(cs.borderLeftColor));
      }
      if (keys.some((k) => k && groenTok.has(k))) {
        if (el instanceof SVGElement && el.closest("svg") !== el) continue; // alleen het svg-element zelf melden
        groen.push({ el: desc(el), t: ctxTekst(el) });
      }
      if (!(el instanceof SVGElement)) {
        const bgK = key(cs.backgroundColor);
        const randK = parseFloat(cs.borderTopWidth) >= 2 ? key(cs.borderTopColor) : null;
        const soort = (bgK && statusBg[bgK]) || (randK && statusRand[randK]);
        // Alleen kleine statusvormen (pil, tag, label); grote panelen hebben een kop met tekst.
        const r = el.getBoundingClientRect();
        if (soort && r.height <= 64 && r.width <= 480) {
          const t = tekstVan(el);
          const label = el.getAttribute("aria-label") || "";
          if (!t && !label) kleurAlleen.push({ el: desc(el), soort });
          else if (!el.querySelector("svg") && !el.closest("[data-ernst]") && el.getAttribute("data-status")) zonderIcoon.push({ el: desc(el), soort, t: t.slice(0, 40) });
        }
      }
    }
    return { groen, kleurAlleen, zonderIcoon };
  }

  // Zichtbare tekst per tekstknoop (zonder code/mono/kbd, die zijn technische waarden) voor de woordenlijstcontrole.
  function woorden() {
    const uit = [];
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    for (let n = walker.nextNode(); n; n = walker.nextNode()) {
      const el = n.parentElement;
      if (!el || ["SCRIPT", "STYLE", "NOSCRIPT", "TEMPLATE"].includes(el.tagName)) continue;
      if (el.closest("code,kbd,pre,samp,.font-mono,[data-technisch]")) continue;
      const t = (n.textContent || "").replace(/\s+/g, " ").trim();
      if (!t) continue;
      if (!visible(el) && !isSrOnly(el)) continue;
      uit.push(t);
    }
    // Knoppen: woord(en) per knop (ook aria-label).
    const knoppen = [...document.querySelectorAll("button,[role=button],a[data-slot=button]")]
      .filter((b) => visible(b))
      .map((b) => (b.getAttribute("aria-label") || tekstVan(b)).slice(0, 60));
    return { teksten: uit, knoppen, titel: document.title, lang: document.documentElement.lang };
  }

  function structuur() {
    const h = [...document.querySelectorAll("h1,h2,h3,h4,h5,h6")].filter((e) => e.getClientRects().length || e.closest(".sr-only")).map((e) => +e.tagName[1]);
    const sprong = [];
    for (let k = 1; k < h.length; k++) if (h[k] > h[k - 1] + 1) sprong.push(`h${h[k - 1]}→h${h[k]}`);
    const ids = {};
    for (const e of document.querySelectorAll("[id]")) ids[e.id] = (ids[e.id] || 0) + 1;
    const dubbel = Object.keys(ids).filter((k) => ids[k] > 1);
    const kapot = [];
    for (const e of document.querySelectorAll("[aria-controls],[aria-describedby],[aria-labelledby]"))
      for (const a of ["aria-controls", "aria-describedby", "aria-labelledby"])
        for (const id of (e.getAttribute(a) || "").split(/\s+/).filter(Boolean)) if (!document.getElementById(id)) kapot.push(`${a}=${id}`);
    const h1 = [...document.querySelectorAll("h1")].map((e) => tekstVan(e).slice(0, 60));
    return { h1: h1.length, h1Tekst: h1, sprong, dubbel, kapot, main: document.querySelectorAll("main").length, status: document.querySelectorAll("[role=status]").length };
  }

  function beweging() {
    const o = [];
    for (const el of document.querySelectorAll("*")) {
      const cs = getComputedStyle(el);
      if (cs.animationName !== "none" && Math.max(...cs.animationDuration.split(",").map(parseFloat)) > 0.02 && cs.animationPlayState !== "paused") o.push("anim " + cs.animationName + " " + desc(el));
      if (Math.max(...cs.transitionDuration.split(",").map(parseFloat)) > 0.02) o.push("trans " + cs.transitionDuration + " " + desc(el));
    }
    return [...new Set(o)].slice(0, 10);
  }

  // Alle dichte <details> openen (en daarna terugzetten) om ook de uitklapinhoud te meten.
  function openDetails() {
    const dicht = [...document.querySelectorAll("details:not([open])")];
    for (const d of dicht) d.open = true;
    window.__peilDicht = dicht;
    return dicht.length;
  }
  function sluitDetails() {
    for (const d of window.__peilDicht || []) d.open = false;
    window.__peilDicht = [];
  }

  window.__peil = { openDetails, sluitDetails, meet, focus, semantiek, woorden, structuur, beweging };
})();
