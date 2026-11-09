// Peil — gedragscontrole (toetsenbord, live-regio's, R3-bevestiging, kopiëren, forced colors, reduced motion).
// Gebruik: node bouw/gedrag.cjs   → schrijft controle/gedrag.json en een forced-colors-afdruk
const { createRequire } = require('module');
const req = createRequire(__filename);
const { chromium } = req('playwright'); const path = require('path'); const fs = require('fs');
const P = (f) => 'file://' + path.join(__dirname, '..', 'prototypes', f);
(async () => {
  const b = await chromium.launch(); const uit = {};
  let p = await b.newPage({ viewport: { width: 1440, height: 900 } });
  await p.goto(P('appdetail.html'));
  await p.focus('#app-tab-acties'); await p.keyboard.press('ArrowLeft');
  uit.tabs_pijl_links = await p.evaluate(() => ({ focus: document.activeElement.id, versiesZichtbaar: !document.getElementById('app-paneel-versies').hidden, actiesVerborgen: document.getElementById('app-paneel-acties').hidden }));
  await p.keyboard.press('Home'); uit.tabs_home = await p.evaluate(() => document.activeElement.id);
  await p.keyboard.press('End'); uit.tabs_end = await p.evaluate(() => document.activeElement.id);
  await p.click('[data-kopieer]'); await p.waitForTimeout(100);
  uit.kopieer_melding = await p.evaluate(() => document.querySelector('[data-kopieer-melding]').textContent);
  await p.goto(P('appdetail-metrieken.html'));
  await p.focus('#g-geheugen'); await p.keyboard.press('ArrowLeft'); await p.keyboard.press('ArrowLeft'); await p.keyboard.press('ArrowLeft');
  uit.grafiek_voorlees = await p.evaluate(() => document.querySelector('[data-voorlees]').textContent);
  for (let k = 0; k < 6; k++) await p.keyboard.press('ArrowLeft');
  uit.grafiek_gat = await p.evaluate(() => document.querySelector('[data-voorlees]').textContent);
  await p.goto(P('goedkeuring-r3.html'));
  uit.r3_start = await p.getAttribute('#bevestig-knop', 'aria-disabled');
  await p.fill('#bevestig', 'voorbeeld-ap'); await p.dispatchEvent('#bevestig', 'input');
  uit.r3_fout = await p.getAttribute('#bevestig-knop', 'aria-disabled');
  await p.fill('#bevestig', 'voorbeeld-app'); await p.dispatchEvent('#bevestig', 'input');
  uit.r3_goed = await p.getAttribute('#bevestig-knop', 'aria-disabled');
  uit.r3_reden = await p.textContent('#bevestig-reden');
  await p.close();
  // forced colors + 200%-zoom (640 px breed = 1280 px scherm op 200%)
  p = await b.newPage({ viewport: { width: 640, height: 800 }, forcedColors: 'active' });
  await p.goto(P('home.html') + '#thema=licht'); await p.waitForTimeout(150);
  fs.mkdirSync(path.join(__dirname, '..', 'controle'), { recursive: true });
  await p.screenshot({ path: path.join(__dirname, '..', 'controle', 'forced-colors-home-640.png'), fullPage: false });
  uit.forced_colors_stippel = await p.evaluate(() => { const e = document.querySelector('.status-onbekend'); const cs = getComputedStyle(e); return cs.borderTopStyle + ' ' + cs.borderTopWidth + ' ' + cs.borderTopColor; });
  uit.zoom200_overloop = await p.evaluate(() => document.scrollingElement.scrollWidth - document.scrollingElement.clientWidth);
  await p.close();
  fs.writeFileSync(path.join(__dirname, '..', 'controle', 'gedrag.json'), JSON.stringify(uit, null, 1));
  console.log(JSON.stringify(uit, null, 1)); await b.close();
})();
