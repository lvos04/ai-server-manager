export type ThemeChoice = "systeem" | "licht" | "donker";
export const THEME_KEY = "hub-thema";

/**
 * Inline-script in <head>: zet vóór de eerste weergave ALTIJD het opgeloste thema (Peil §13.1 stap 3), ook bij
 * "Systeem": `data-theme="light|dark"` én de klasse `dark`. Bij Systeem volgt het live `prefers-color-scheme`.
 * Peil kent bewust geen CSS-terugval op `prefers-color-scheme`; zonder dit script is de Hub altijd licht.
 */
export const THEME_SCRIPT = `(function(){try{var d=document.documentElement,k='${THEME_KEY}';function keuze(){try{return localStorage.getItem(k)}catch(e){return null}}function zet(){var t=keuze(),m=window.matchMedia('(prefers-color-scheme: dark)').matches,donker=t==='donker'||(t!=='licht'&&m);d.dataset.theme=donker?'dark':'light';d.classList.toggle('dark',donker);d.style.colorScheme=donker?'dark':'light'}zet();window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change',zet);window.addEventListener('hub-thema-gewijzigd',zet);window.addEventListener('storage',function(e){if(e.key===k)zet()})}catch(e){}})();`;

const EVENT = "hub-thema-gewijzigd";

export function subscribeTheme(cb: () => void): () => void {
  window.addEventListener("storage", cb);
  window.addEventListener(EVENT, cb);
  return () => {
    window.removeEventListener("storage", cb);
    window.removeEventListener(EVENT, cb);
  };
}

export function readTheme(): ThemeChoice {
  try {
    const t = localStorage.getItem(THEME_KEY);
    return t === "licht" || t === "donker" ? t : "systeem";
  } catch {
    return "systeem";
  }
}

/** Opgelost thema (wat er nu echt staat). */
export function resolveTheme(choice: ThemeChoice, systemDark: boolean): "light" | "dark" {
  if (choice === "donker") return "dark";
  if (choice === "licht") return "light";
  return systemDark ? "dark" : "light";
}

export function applyTheme(choice: ThemeChoice): void {
  try {
    if (choice === "systeem") localStorage.removeItem(THEME_KEY);
    else localStorage.setItem(THEME_KEY, choice);
  } catch {
    // alleen een gemak per apparaat; zonder opslag werkt het thema per sessie
  }
  const d = document.documentElement;
  const resolved = resolveTheme(choice, window.matchMedia("(prefers-color-scheme: dark)").matches);
  d.dataset.theme = resolved;
  d.classList.toggle("dark", resolved === "dark");
  d.style.colorScheme = resolved;
  window.dispatchEvent(new Event(EVENT));
}
