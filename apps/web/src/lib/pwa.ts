"use client";

import { useEffect, useSyncExternalStore } from "react";

function subscribeOnline(cb: () => void) {
  window.addEventListener("online", cb);
  window.addEventListener("offline", cb);
  return () => {
    window.removeEventListener("online", cb);
    window.removeEventListener("offline", cb);
  };
}

/** Online-status van de browser (server-render: online). */
export function useOnline(): boolean {
  return useSyncExternalStore(subscribeOnline, () => navigator.onLine, () => true);
}

export type PwaState =
  | "laden"
  | "actief"
  | "registreren"
  | "niet_ondersteund"
  | "onveilige_verbinding"
  | "ontwikkeling"
  | "fout";

export const PWA_LABEL: Record<PwaState, string> = {
  laden: "Controleren…",
  actief: "Actief: de app-schil werkt ook offline (gegevens niet: die zijn offline onbekend).",
  registreren: "Wordt geactiveerd…",
  niet_ondersteund: "Niet beschikbaar: deze browser ondersteunt geen service worker.",
  onveilige_verbinding:
    "Niet actief: offline gebruik en installeren als app vereisen HTTPS (of localhost). Via http://<NAS-adres> werkt de Hub gewoon, alleen zonder offline-schil. HTTPS volgt met besluit D17.",
  ontwikkeling: "Niet actief in ontwikkelmodus.",
  fout: "Activeren mislukt; de Hub werkt gewoon online.",
};

let current: PwaState = "laden";
let started = false;
const listeners = new Set<() => void>();

function setPwa(next: PwaState) {
  current = next;
  listeners.forEach((l) => l());
}

function subscribePwa(cb: () => void) {
  listeners.add(cb);
  return () => listeners.delete(cb);
}

/** Huidige status van de offline-schil (voor Instellingen). */
export function usePwaState(): PwaState {
  return useSyncExternalStore(subscribePwa, () => current, () => "laden");
}

function startRegistration() {
  if (started) return;
  started = true;
  if (process.env.NODE_ENV !== "production") return setPwa("ontwikkeling");
  if (!("serviceWorker" in navigator)) return setPwa("niet_ondersteund");
  if (!window.isSecureContext) return setPwa("onveilige_verbinding");
  const version = process.env.NEXT_PUBLIC_HUB_VERSION ?? "0";
  setPwa("registreren");
  navigator.serviceWorker
    .register(`/sw.js?v=${encodeURIComponent(version)}`, { scope: "/" })
    .then(() => navigator.serviceWorker.ready)
    .then(() => setPwa("actief"))
    .catch(() => setPwa("fout"));
}

/** Service worker registreren (alleen productie + secure context: HTTPS of localhost). */
export function useServiceWorker(): void {
  useEffect(() => {
    startRegistration();
  }, []);
}
