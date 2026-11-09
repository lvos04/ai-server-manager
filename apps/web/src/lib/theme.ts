export type ThemeChoice = "systeem" | "licht" | "donker";
export const THEME_KEY = "hub-thema";

/** Inline-script in <head>: thema vóór de eerste weergave zetten (geen flits). Leest alleen localStorage. */
export const THEME_SCRIPT = `(function(){try{var t=localStorage.getItem('${THEME_KEY}');var d=document.documentElement;if(t==='licht')d.dataset.theme='light';else if(t==='donker')d.dataset.theme='dark';}catch(e){}})();`;

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

export function applyTheme(choice: ThemeChoice): void {
  const d = document.documentElement;
  if (choice === "licht") d.dataset.theme = "light";
  else if (choice === "donker") d.dataset.theme = "dark";
  else delete d.dataset.theme;
  try {
    if (choice === "systeem") localStorage.removeItem(THEME_KEY);
    else localStorage.setItem(THEME_KEY, choice);
  } catch {
    // alleen een gemak per apparaat; zonder opslag werkt het thema per sessie
  }
  window.dispatchEvent(new Event(EVENT));
}
