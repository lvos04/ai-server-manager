// Volledige bouw in de juiste volgorde. Gebruik: node bouw/alles.mjs [--shots] [--controle]
import { execFileSync } from 'node:child_process';
const D = new URL('../', import.meta.url).pathname;
const run = (...a) => execFileSync('node', a, { stdio: 'inherit', cwd: D });
run('bouw/genereer.mjs');            // tokens.json, ontwerptaal.css, statuspagina.css, statuspagina.html
run('bouw/test-sjabloon.mjs');       // 1.1.1: renderer in één doorgang (JS = Python), tonen, formulieren, grootte
run('bouw/contrast.mjs');            // contrast.json (stopt bij een harde fout)
run('bouw/aliaslagen.mjs');          // aliaslagen/*.css + my_house-paren in contrast.json
run('bouw/contrast-breed.mjs');      // brede matrix (367 paren per thema) in contrast.json — review 1.1.0
run('bouw/docs.mjs');                // tokentabellen en contrast-/paletsamenvatting in ONTWERPTAAL.md
run('bouw/bouw.mjs');                // prototypes/*.html + prototypes/css/peil.css
const P = ['home', 'offline', 'problemen', 'appdetail', 'appdetail-metrieken', 'goedkeuring-r3', 'wizardstap', 'huis', 'kind', 'statuspagina', 'statuspagina-gekoppeld', 'statuspagina-onleesbaar', 'statuspagina-bezig',
  'apps', 'appdetail-p1', 'server-metrieken', 'diensten', 'noodaccount', 'instellingen-toegang', 'instellingen-bronnen'];
if (process.argv.includes('--shots')) for (const p of P) run('bouw/shot.mjs', `prototypes/${p}.html`, `shots/${p}`);
if (process.argv.includes('--controle')) { for (const p of P) run('bouw/controle.cjs', `${p}.html`); execFileSync('sh', ['-c', 'node bouw/samenvat.cjs > controle/samenvatting.txt'], { stdio: 'inherit', cwd: D }); run('bouw/gedrag.cjs'); }
