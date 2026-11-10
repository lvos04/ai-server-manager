// Peil — automatische controle van de prototypes (afgeleid van de jury-audit: gerenderde contrasten incl. opacity en
// arcering, doelgrootte, overloop, afkappen, stippelranden, veldranden, focusdoorloop en bedekte focus) + axe-core
// (WCAG 2.0/2.1/2.2 A+AA). Gebruik: node bouw/controle.cjs <pagina.html> [breedtes] [themas]
const { createRequire } = require('module');
const req = createRequire(__filename);
const { chromium } = req('playwright');
const path = require('path'); const fs = require('fs');
const BASE = path.join(__dirname, '..', 'prototypes');
const [,, pagina, wArg, tArg] = process.argv; const richting = 'peil';
// Review 1.1.0: niet meer stilzwijgend afhankelijk van de node_modules van een andere repo. Volgorde: $AXE_CORE →
// axe-core uit de eigen node_modules van bouw/ (npm ci in bouw/).
const AXE = [process.env.AXE_CORE, (() => { try { return req.resolve('axe-core/axe.min.js'); } catch { return null; } })()].find((f) => f && require('fs').existsSync(f));
if (!AXE) throw new Error('axe-core niet gevonden: zet AXE_CORE=<pad naar axe.min.js>');
const widths = (wArg || '320,360,390,768,1024,1440').split(',').map(Number);
const themes = (tArg || 'licht,donker').split(',');
// 1.1.1 (E12): PEIL_LETTER="DejaVu Sans" meet met een ander systeemlettertype (zoals de Ubuntu-runner in CI); uitvoer
// dan in controle/uit-letter/ zodat de standaardmeting niet wordt overschreven. Codes houden hun mono-letter.
const LETTER = process.env.PEIL_LETTER || '';
const LETTER_CSS = LETTER ? `:root:root{--font-sans:${JSON.stringify(LETTER)},sans-serif !important} body, body *:not(code):not(kbd):not(samp):not(pre):not(.font-mono):not(.mono){font-family:${JSON.stringify(LETTER)},sans-serif !important}` : '';
const UIT = path.join(__dirname, '..', 'controle', LETTER ? 'uit-letter' : 'uit'); fs.mkdirSync(UIT, { recursive: true });

const IN_PAGE = () => {
  const cvs = document.createElement('canvas'); cvs.width = cvs.height = 1;
  const ctx = cvs.getContext('2d', { willReadFrequently: true });
  const cache = new Map();
  const rgba = (s) => { if (cache.has(s)) return cache.get(s); ctx.clearRect(0,0,1,1); ctx.fillStyle = '#000'; ctx.fillStyle = s; ctx.fillRect(0,0,1,1); const d = ctx.getImageData(0,0,1,1).data; const v = [d[0],d[1],d[2],d[3]/255]; cache.set(s, v); return v; };
  const over = (t, b) => { const a = t[3] + b[3]*(1-t[3]); if (a === 0) return [0,0,0,0]; return [0,1,2].map(i => (t[i]*t[3] + b[i]*b[3]*(1-t[3]))/a).concat([a]); };
  const mix = (a, b, t) => [0,1,2].map(i => a[i]*(1-t) + b[i]*t).concat([1]);
  const lum = (c) => { const f = (v) => { v /= 255; return v <= 0.04045 ? v/12.92 : Math.pow((v+0.055)/1.055, 2.4); }; return 0.2126*f(c[0])+0.7152*f(c[1])+0.0722*f(c[2]); };
  const ratio = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x,y)+0.05)/(Math.min(x,y)+0.05); };
  const hex = (c) => '#' + c.slice(0,3).map(v => Math.round(v).toString(16).padStart(2,'0')).join('');
  const colorsIn = (img) => (img.match(/(rgba?\([^)]*\)|oklch\([^)]*\)|oklab\([^)]*\)|color\([^)]*\)|#[0-9a-f]{3,8})/gi) || []);
  const chain = (el) => { const c = []; for (let e = el; e && e.nodeType === 1; e = e.parentElement) c.push(e); return c; };
  function paint(el, fg) { // compositie van achtergrondlagen + opacity-groepen, wit canvas onderaan
    const ch = chain(el); const alts = [];
    function rec(k, backdrop) {
      const e = ch[k]; const cs = getComputedStyle(e);
      const inside = over(rgba(cs.backgroundColor), backdrop);
      if (cs.backgroundImage && cs.backgroundImage !== 'none') for (const s of colorsIn(cs.backgroundImage)) { const c = rgba(s); if (c[3] > 0.05) alts.push(over(c, inside)); }
      let Bin, Tin; if (k === 0) { Bin = inside; Tin = over(fg, inside); } else [Bin, Tin] = rec(k - 1, inside);
      const o = parseFloat(cs.opacity); if (o < 1) return [mix(backdrop, Bin, o), mix(backdrop, Tin, o)];
      return [Bin, Tin];
    }
    const [B, T] = rec(ch.length - 1, [255,255,255,1]); return { B, T, alts };
  }
  const cumOpacity = (el) => chain(el).reduce((p, e) => p * parseFloat(getComputedStyle(e).opacity), 1);
  const isSrOnly = (el) => { for (const e of chain(el)) { const cs = getComputedStyle(e); if (cs.clip === 'rect(0px, 0px, 0px, 0px)' || (cs.position === 'absolute' && parseFloat(cs.width) <= 1 && parseFloat(cs.height) <= 1 && cs.overflow === 'hidden') || cs.clipPath === 'inset(50%)') return true; } return false; };
  const visible = (el) => { const r = el.getBoundingClientRect(); if (r.width === 0 || r.height === 0) return false; if (getComputedStyle(el).visibility === 'hidden') return false; return !isSrOnly(el); };
  const desc = (el) => { const id = el.id ? '#' + el.id : ''; const cls = (el.getAttribute('class') || '').split(/\s+/).slice(0, 4).join('.'); return el.tagName.toLowerCase() + id + (cls ? '.' + cls : ''); };
  const txt = (el) => [...el.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent).join('').replace(/\s+/g, ' ').trim();
  const tekst = []; let minFont = 99; const kleinFont = [];
  for (const el of document.querySelectorAll('body *')) {
    if (['SCRIPT','STYLE','NOSCRIPT','TEMPLATE'].includes(el.tagName)) continue;
    const t = txt(el); if (!t || !visible(el)) continue;
    const cs = getComputedStyle(el); const fgS = el instanceof SVGElement ? cs.fill : cs.color;
    if (!fgS || fgS === 'none' || fgS.startsWith('url')) continue;
    const fg = rgba(fgS); const { B, T, alts } = paint(el, fg);
    const fs = parseFloat(cs.fontSize), fw = parseInt(cs.fontWeight);
    const groot = fs >= 24 || (fs >= 18.66 && fw >= 700); const eis = groot ? 3 : 4.5;
    const r = ratio(T, B); let rAlt = r; for (const a of alts) rAlt = Math.min(rAlt, ratio(over(fg, a), a));
    if (fs < minFont) minFont = fs; if (fs < 12) kleinFont.push({ el: desc(el), t: t.slice(0, 40), fs });
    tekst.push({ el: desc(el), t: t.slice(0, 60), fs, fw, groot, eis, r: +r.toFixed(2), rAlt: +rAlt.toFixed(2), fg: hex(T), bg: hex(B), op: +cumOpacity(el).toFixed(2), dis: !!el.closest(':disabled,[aria-disabled="true"]') });
  }
  for (const el of document.querySelectorAll('input[placeholder],textarea[placeholder]')) { if (!visible(el)) continue; const fg = rgba(getComputedStyle(el, '::placeholder').color); const { B, T } = paint(el, fg); tekst.push({ el: desc(el) + '::placeholder', t: el.placeholder.slice(0, 50), fs: parseFloat(getComputedStyle(el).fontSize), eis: 4.5, r: +ratio(T, B).toFixed(2), rAlt: +ratio(T, B).toFixed(2), fg: hex(T), bg: hex(B), op: 1 }); }
  const velden = [];
  for (const el of document.querySelectorAll('input:not([type=hidden]),select,textarea')) { if (!visible(el)) continue; const cs = getComputedStyle(el); const par = paint(el.parentElement, [0,0,0,0]).B; const own = paint(el, [0,0,0,0]).B; const bc = over(rgba(cs.borderBottomColor), own); velden.push({ el: desc(el), type: el.type, rand: +ratio(bc, par).toFixed(2), vlak: +ratio(own, par).toFixed(2), bw: parseFloat(cs.borderBottomWidth), kleur: hex(bc), h: Math.round(el.getBoundingClientRect().height) }); }
  const stippel = [];
  for (const el of document.querySelectorAll('body *')) { const cs = getComputedStyle(el); const sides = ['Top','Left','Bottom'].filter(s => ['dashed','dotted'].includes(cs['border' + s + 'Style'])); if (!sides.length || !visible(el)) continue; const side = sides[0]; const par = paint(el.parentElement, [0,0,0,0]).B; const bc = over(rgba(cs['border' + side + 'Color']), par); stippel.push({ el: desc(el), t: (el.textContent || '').replace(/\s+/g,' ').trim().slice(0, 40), bw: parseFloat(cs['border' + side + 'Width']), buiten: +ratio(bc, par).toFixed(2), kleur: hex(bc) }); }
  const doelen = [];
  for (const el of document.querySelectorAll('a[href],button,input:not([type=hidden]),select,textarea,summary,[role=button],[role=tab],[role=link],[tabindex]:not([tabindex="-1"])')) { if (!visible(el)) continue; const r = el.getBoundingClientRect(); const inline = el.tagName === 'A' && getComputedStyle(el).display === 'inline' && el.parentElement && txt(el.parentElement).length > 0; const lab = (el.type === 'radio' || el.type === 'checkbox') && el.closest('label'); const lr = lab && lab.getBoundingClientRect(); if (lr && lr.width >= 44 && lr.height >= 44) continue; if (r.width < 44 || r.height < 44) doelen.push({ el: desc(el), t: (el.innerText || el.getAttribute('aria-label') || '').replace(/\s+/g,' ').trim().slice(0, 40), w: Math.round(r.width), h: Math.round(r.height), inline }); }
  const se = document.scrollingElement; const overloop = se.scrollWidth - se.clientWidth;
  // 1.1.1: inhoud die buiten zijn eigen knop, pil, navigatie-item of rij steekt (zonder dat de pagina overloopt);
  // vond in my_house en appstore-en-fork fouten die de paginaoverloop niet ziet (E12, E16).
  const uitsteek = [];
  for (const el of document.querySelectorAll('a, button, summary, label, li, dd, td, th, .status, .pil, .onder-item, .zij-item, .kop-item, .melding, .blok, .kaart')) {
    if (!visible(el)) continue; const cs = getComputedStyle(el);
    if (cs.display === 'inline' || cs.display === 'contents' || cs.overflowX !== 'visible') continue;
    const over = el.scrollWidth - el.clientWidth; if (over > 1) uitsteek.push({ el: desc(el), t: (el.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 40), over });
  }
  const afgekapt = [];
  for (const el of document.querySelectorAll('body *')) { const cs = getComputedStyle(el); if (cs.textOverflow === 'ellipsis' && visible(el) && el.scrollWidth > el.clientWidth + 1) afgekapt.push({ el: desc(el), t: (el.textContent||'').replace(/\s+/g,' ').trim().slice(0, 60), title: el.getAttribute('title') || '' }); }
  return { tekst, minFont, kleinFont, velden, stippel, doelen, overloop, afgekapt, uitsteek };
};

const FOCUS = () => {
  const el = document.activeElement; if (!el || el === document.body) return null;
  const cs = getComputedStyle(el); const r = el.getBoundingClientRect();
  const desc = el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') + ' "' + ((el.innerText || el.getAttribute('aria-label') || '').replace(/\s+/g, ' ').trim().slice(0, 30)) + '"';
  const pts = [[r.left + r.width / 2, r.top + r.height / 2], [r.left + 2, r.top + 2], [r.right - 2, r.bottom - 2], [r.left + 2, r.bottom - 2], [r.right - 2, r.top + 2]];
  let zichtbaarPt = 0, inViewport = 0;
  for (const [x, y] of pts) { if (x < 0 || y < 0 || x > innerWidth || y > innerHeight) continue; inViewport++; const top = document.elementFromPoint(x, y); if (top && (top === el || el.contains(top) || top.contains(el))) zichtbaarPt++; }
  const cvs = document.createElement('canvas'); cvs.width = cvs.height = 1; const ctx = cvs.getContext('2d');
  const rgba = (s) => { ctx.clearRect(0,0,1,1); ctx.fillStyle = '#000'; ctx.fillStyle = s; ctx.fillRect(0,0,1,1); const d = ctx.getImageData(0,0,1,1).data; return [d[0],d[1],d[2],d[3]/255]; };
  const over = (t, b) => { const a = t[3] + b[3]*(1-t[3]); return [0,1,2].map(i => (t[i]*t[3] + b[i]*b[3]*(1-t[3]))/(a||1)).concat([a]); };
  const lum = (c) => { const f = (v) => { v /= 255; return v <= 0.04045 ? v/12.92 : Math.pow((v+0.055)/1.055, 2.4); }; return 0.2126*f(c[0])+0.7152*f(c[1])+0.0722*f(c[2]); };
  const ratio = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x,y)+0.05)/(Math.min(x,y)+0.05); };
  const bgOf = (e) => { const layers = []; for (let p = e; p && p.nodeType === 1; p = p.parentElement) layers.push(rgba(getComputedStyle(p).backgroundColor)); let c = [255,255,255,1]; for (const l of layers.reverse()) c = over(l, c); return c; };
  const parBg = bgOf(el.parentElement);
  const ow = parseFloat(cs.outlineWidth); const ost = cs.outlineStyle; const oc = rgba(cs.outlineColor);
  const has = ost !== 'none' && ow > 0;
  return { desc, ow, ost, offset: parseFloat(cs.outlineOffset), ringR: has ? +ratio(over(oc, parBg), parBg).toFixed(2) : 0, bs: cs.boxShadow !== 'none' ? cs.boxShadow.slice(0, 80) : '', inViewport, zichtbaarPt, rTop: Math.round(r.top), rBottom: Math.round(r.bottom) };
};

(async () => {
  const browser = await chromium.launch();
  const file = path.join(BASE, pagina);
  const res = { richting, pagina, letter: LETTER || 'systeem (standaard)', runs: [] };
  for (const theme of themes) for (const w of widths) {
    const page = await browser.newPage({ viewport: { width: w, height: 844 }, colorScheme: theme === 'donker' ? 'dark' : 'light', hasTouch: w < 1024 });
    if (LETTER_CSS) await page.addInitScript((css) => document.addEventListener('DOMContentLoaded', () => { const st = document.createElement('style'); st.textContent = css; document.head.appendChild(st); }), LETTER_CSS);
    await page.goto('file://' + file);
    await page.evaluate((t) => document.documentElement.classList.toggle('dark', t === 'donker'), theme);
    await page.waitForTimeout(250);
    const r = await page.evaluate(IN_PAGE);
    const run = { theme, w, ...r, tekstFout: r.tekst.filter(x => x.r < x.eis || x.rAlt < x.eis), minTekst: r.tekst.filter(x => !x.dis).reduce((m, x) => Math.min(m, x.r, x.rAlt), 99), aantalTekst: r.tekst.length };
    delete run.tekst;
    if (w === 390 || w === 1440) {
      await page.goto('file://' + file + '?f=' + Date.now());
      await page.evaluate((t) => document.documentElement.classList.toggle('dark', t === 'donker'), theme);
      await page.waitForTimeout(150);
      run.scrollPadding = await page.evaluate(() => getComputedStyle(document.documentElement).scrollPaddingBottom);
      const focus = [];
      for (let i = 0; i < 400; i++) {
        await page.keyboard.press('Tab');
        let f = await page.evaluate(FOCUS);
        if (f && (!(f.ost !== 'none' && f.ow > 0) || f.ringR < 3)) { await page.waitForTimeout(450); f = await page.evaluate(FOCUS); } // na transitie opnieuw meten
        if (!f) break; focus.push(f);
        if (focus.length > 3 && f.desc === focus[0].desc) break;
      }
      run.focus = { aantal: focus.length, eerste: focus[0] && focus[0].desc, zonderRing: focus.filter(f => !(f.ost !== 'none' && f.ow > 0) && !f.bs).map(f => f.desc), zwak: focus.filter(f => f.ow > 0 && f.ringR < 3).map(f => `${f.desc} ${f.ringR}`), bedekt: focus.filter(f => f.inViewport > 0 && f.zichtbaarPt === 0).map(f => `${f.desc} top=${f.rTop} bottom=${f.rBottom}`), ringMin: focus.filter(f => f.ow > 0).reduce((m, f) => Math.min(m, f.ringR), 99), breedtes: [...new Set(focus.map(f => f.ow + 'px/' + f.offset))] };
    }
    run.structuur = await page.evaluate(() => {
      const h = [...document.querySelectorAll('h1,h2,h3,h4,h5,h6')].filter(e => e.getClientRects().length || e.closest('.sr-only')).map(e => +e.tagName[1]);
      const sprong = []; for (let k = 1; k < h.length; k++) if (h[k] > h[k - 1] + 1) sprong.push(`h${h[k - 1]}→h${h[k]}`);
      const ids = {}; for (const e of document.querySelectorAll('[id]')) ids[e.id] = (ids[e.id] || 0) + 1;
      const dubbel = Object.keys(ids).filter(k => ids[k] > 1);
      const kapot = []; for (const e of document.querySelectorAll('[aria-controls],[aria-describedby],[aria-labelledby]')) for (const a of ['aria-controls','aria-describedby','aria-labelledby']) for (const id of (e.getAttribute(a) || '').split(/\s+/).filter(Boolean)) if (!document.getElementById(id)) kapot.push(`${a}=${id}`);
      return { h1: document.querySelectorAll('h1').length, sprong, dubbel, kapot, main: document.querySelectorAll('main').length, status: document.querySelectorAll('[role=status]').length };
    });
    if (w === 390 || w === 1440) {
      await page.addScriptTag({ path: AXE });
      run.axe = await page.evaluate(async () => { const r = await axe.run(document, { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'] } }); return r.violations.map(v => ({ id: v.id, impact: v.impact, n: v.nodes.length, voorbeeld: v.nodes.slice(0, 3).map(x => x.target.join(' ') + ' :: ' + (x.failureSummary || '').split('\n').slice(1, 2).join('')) })); });
    }
    res.runs.push(run); await page.close();
  }
  const p = await browser.newPage({ viewport: { width: 390, height: 844 }, reducedMotion: 'reduce' });
  await p.goto('file://' + file); await p.waitForTimeout(200);
  res.bewegingBijReduce = await p.evaluate(() => { const o = []; for (const el of document.querySelectorAll('*')) { const cs = getComputedStyle(el); if (cs.animationName !== 'none' && Math.max(...cs.animationDuration.split(',').map(parseFloat)) > 0.02) o.push('anim ' + cs.animationName); if (Math.max(...cs.transitionDuration.split(',').map(parseFloat)) > 0.02) o.push('trans ' + cs.transitionDuration); } return [...new Set(o)]; });
  try { res.aria = await p.locator('body').ariaSnapshot(); } catch (e) { res.aria = 'fout: ' + e.message; }
  await p.close(); await browser.close();
  fs.writeFileSync(path.join(UIT, `${pagina.replace('.html', '')}.json`), JSON.stringify(res, null, 1));
})().catch(e => { console.error(e); process.exit(1); });
