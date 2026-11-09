// Haalt lucide-paden (lucide-react 1.66, ISC-licentie) uit de eigen node_modules van bouw/ naar iconen.json,
// zodat prototypes en statuspagina's inline SVG gebruiken met exact dezelfde paden als lucide-react in de Hub.
import fs from 'node:fs';
import { createRequire } from 'node:module';
import path from 'node:path';
const DIR = path.join(path.dirname(createRequire(import.meta.url).resolve('lucide-react/package.json')), 'dist/esm/icons/');
const namen = `microchip file-lock mic shower-head lightbulb-off lightbulb droplets flame snowflake monitor-play smile radio wifi wifi-off
keyboard chevron-up arrow-right list-ordered timer hand power calendar chart-line table-2 trash-2 rotate-ccw archive-restore history
scroll-text file-search user-check users key-round folder hard-drive gauge activity thermometer zap plug-zap sun moon monitor ban
circle-slash lock lock-open file-diff eye undo-2 clipboard-check flask-conical link-2-off loader-circle info circle-pause clock-alert
circle-help octagon-x triangle-alert circle-check check x copy refresh-cw square-arrow-out-up-right chevron-right chevron-left
chevron-down arrow-left plus minus search menu bot inbox layout-grid house server clapperboard sofa network workflow database-backup
wallet settings circle-user bell log-out user sparkles filter hourglass database siren messages-square file-text play pause circle-x
download film tv cpu memory-stick list-checks book-open tag fan ellipsis circle-dot shield-check package hash calendar-clock link-2`.split(/\s+/).filter(Boolean);
const uit = {};
for (const n of namen) {
  let mod = await import(DIR + n + '.mjs');
  let data = mod.__iconData;
  if (!data) { const doel = fs.readFileSync(DIR + n + '.mjs', 'utf8').match(/from '\.\/(.+?)\.mjs'/); if (doel) data = (await import(DIR + doel[1] + '.mjs')).__iconData; }
  if (!data) { console.error('geen data', n); continue; }
  uit[n] = data.node.map(([tag, attrs]) => '<' + tag + ' ' + Object.entries(attrs).filter(([k]) => k !== 'key').map(([k, v]) => `${k}="${v}"`).join(' ') + '/>').join('');
}
fs.writeFileSync(new URL('./iconen.json', import.meta.url), JSON.stringify(uit, null, 1));
console.log(Object.keys(uit).length, 'iconen');
