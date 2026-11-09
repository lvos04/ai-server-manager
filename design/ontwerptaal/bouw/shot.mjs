// Gebruik: node shot.mjs <html-bestand> <uitvoer-prefix> [breedtes, standaard 360,390,768,1440] [themas, standaard licht,donker]
import { chromium } from 'playwright';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
const [,, file, prefix, widthsArg, themesArg] = process.argv;
const widths = (widthsArg || '360,390,768,1440').split(',').map(Number);
const themes = (themesArg || 'licht,donker').split(',');
const browser = await chromium.launch();
for (const theme of themes) for (const w of widths) {
  const page = await browser.newPage({ viewport: { width: w, height: 900 }, deviceScaleFactor: 1, colorScheme: theme === 'donker' ? 'dark' : 'light' });
  await page.goto('file://' + path.resolve(file) + '#thema=' + theme);
  await page.evaluate((t) => document.documentElement.classList.toggle('dark', t === 'donker'), theme);
  await page.waitForTimeout(150);
  const out = `${prefix}-${theme}-${w}.png`;
  await page.screenshot({ path: out, fullPage: true });
  // Optioneel kleiner maken (Hub-ontwerpstap P1): pngquant als het op het systeem staat; anders blijft de PNG ongewijzigd.
  // Kleuren worden nooit op de afdrukken gemeten (dat doet controle.cjs in de DOM), dus kwantiseren is veilig.
  try { execFileSync('pngquant', ['--quality=80-95', '--speed', '1', '--strip', '--force', '--ext', '.png', out], { stdio: 'ignore' }); } catch { /* pngquant ontbreekt of gaf geen winst */ }
  console.log(out);
  await page.close();
}
await browser.close();
