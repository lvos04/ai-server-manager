"use client";

import { Validatielabel } from "@/components/StatusBadge";
import { PWA_LABEL, usePwaState } from "@/lib/pwa";
import { InstellingenKop } from "../delen";

export function ApparaatScreen() {
  const pwa = usePwaState();
  return (
    <>
      <InstellingenKop titel="Apparaat en app" intro="Instellingen die alleen voor dit apparaat gelden." />
      <section className="card" aria-labelledby="pwa-titel">
        <h2 id="pwa-titel">Offline-schil (PWA)</h2>
        <dl className="kv">
          <dt>Status</dt>
          <dd data-testid="pwa-status" data-state={pwa}>
            {PWA_LABEL[pwa]}
          </dd>
          <dt>Gegevens offline</dt>
          <dd>Nooit: offline toont de Hub alleen de schil; gegevens zijn dan niet actueel en wijzigen kan niet.</dd>
          <dt>Installeren als app</dt>
          <dd>Via het menu van je browser (“Toevoegen aan startscherm”), alleen via HTTPS of localhost.</dd>
        </dl>
        <Validatielabel>NIET GEVALIDEERD (hardware)</Validatielabel>
        <p className="meta">Niet getest op een echte Android-telefoon of tv.</p>
      </section>
    </>
  );
}
