// Vindt elementen die buiten de viewport steken (oorzaak horizontale overloop)
const { createRequire } = require('module');
const req = createRequire(__filename);
const { chromium } = req('playwright');
const [,, file, w] = process.argv;
(async () => { const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: +w, height: 800 } });
 await p.goto('file://' + file); await p.waitForTimeout(200);
 console.log(JSON.stringify(await p.evaluate(() => { const W = document.documentElement.clientWidth; const o = []; for (const el of document.querySelectorAll('body *')) { const rc = el.getBoundingClientRect(); if (rc.right > W + 1 && rc.width > 0) { let a = el.parentElement, clip = false; while (a) { if (['hidden','auto','scroll','clip'].includes(getComputedStyle(a).overflowX)) { clip = true; break; } a = a.parentElement; } if (!clip) o.push(`${el.tagName.toLowerCase()} ws=${getComputedStyle(el).whiteSpace} right=${Math.round(rc.right)} "${(el.textContent||'').replace(/\s+/g,' ').trim().slice(0,50)}"`); } } return { sw: document.scrollingElement.scrollWidth, W, o: o.slice(0, 6) }; }), null, 1)); await b.close(); })();
