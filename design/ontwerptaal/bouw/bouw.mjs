// Bouwt alle prototypes naar ../prototypes/*.html en compileert Tailwind 4 naar ../prototypes/css/peil.css.
// Gebruik: node bouw/bouw.mjs [pagina,...]
import fs from 'node:fs';
import { execFileSync } from 'node:child_process';
const B = new URL('./', import.meta.url).pathname, P = new URL('../prototypes/', import.meta.url).pathname;
const paginas = {
  'home': async () => (await import('./pagina-home.mjs')).home(),
  'offline': async () => (await import('./pagina-home.mjs')).home({ offline: true }),
  'problemen': async () => (await import('./pagina-problemen.mjs')).problemen(),
  'appdetail': async () => (await import('./pagina-appdetail.mjs')).appdetail('acties'),
  'appdetail-metrieken': async () => (await import('./pagina-appdetail.mjs')).appdetail('metrieken'),
  'goedkeuring-r3': async () => (await import('./pagina-goedkeuring.mjs')).goedkeuring(),
  'wizardstap': async () => (await import('./pagina-wizard.mjs')).wizard(),
  'huis': async () => (await import('./pagina-huis.mjs')).huis(),
  'kind': async () => (await import('./pagina-kind.mjs')).kind(),
  'statuspagina': async () => (await import('./pagina-statuspagina.mjs')).statuspagina(),
  'statuspagina-gekoppeld': async () => (await import('./pagina-statuspagina.mjs')).statuspaginaGekoppeld(),
  // Peil 1.1.1: twee toestanden die het sjabloon in 1.1.0 niet kon tonen (E01, E02)
  'statuspagina-onleesbaar': async () => (await import('./pagina-statuspagina.mjs')).statuspaginaOnleesbaar(),
  'statuspagina-bezig': async () => (await import('./pagina-statuspagina.mjs')).statuspaginaBezig(),
  // Hub-ontwerpstap P1 + contract 1.2 (docs/ontwerp/HUB_PEIL_ONTWERP.md)
  'apps': async () => (await import('./pagina-apps.mjs')).apps(),
  'appdetail-p1': async () => (await import('./pagina-apps.mjs')).appdetailP1(),
  'server-metrieken': async () => (await import('./pagina-server.mjs')).serverMetrieken(),
  'diensten': async () => (await import('./pagina-diensten.mjs')).diensten(),
  'noodaccount': async () => (await import('./pagina-noodaccount.mjs')).noodaccount(),
  'instellingen-toegang': async () => (await import('./pagina-instellingen.mjs')).instellingenToegang(),
  'instellingen-bronnen': async () => (await import('./pagina-instellingen.mjs')).instellingenBronnen(),
};
const kies = (process.argv[2] || '').split(',').filter(Boolean);
for (const [naam, f] of Object.entries(paginas)) {
  if (kies.length && !kies.includes(naam)) continue;
  try { fs.writeFileSync(P + naam + '.html', (await f()).replace(/>([^<]*)</g, (m, t) => '>' + t.replace(/voorbeeldpool\/(apps|media)\//g, 'voorbeeldpool/<wbr>$1/<wbr>') + '<')); console.log('✓', naam); }
  catch (e) { if (e.code === 'ERR_MODULE_NOT_FOUND') console.log('– overgeslagen', naam); else throw e; }
}
execFileSync('npx', ['@tailwindcss/cli', '-i', B + 'in.css', '-o', P + 'css/peil.css', '--minify'], { stdio: 'inherit', cwd: B });
console.log('peil.css', fs.statSync(P + 'css/peil.css').size, 'B');
