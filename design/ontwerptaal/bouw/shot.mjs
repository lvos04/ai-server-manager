// Gebruik: node shot.mjs <html-bestand> <uitvoer-prefix> [breedtes, standaard 360,390,768,1440] [themas, standaard licht,donker]
import { chromium } from 'playwright';
import path from 'node:path';
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
  console.log(out);
  await page.close();
}
await browser.close();
