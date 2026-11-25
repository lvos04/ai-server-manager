"use client";

import Link from "next/link";
import { useCallback, useId, useRef, useState } from "react";
import {
  diffRegels,
  doelNaam,
  naamKlopt,
  risicoKlasse,
  toonbareFout,
  vasteFout,
  vervallen,
  vervallenTekst,
  VOORSTEL_VERLOPEN,
  WEIGER_REDENEN,
  weigerReden,
  werkwoord,
  type ActieVerzoek,
  type Hashes,
} from "@/lib/acties";
import type { HubApiError } from "@/lib/api";
import { hasRole, useRole } from "@/lib/session";
import { KLOON } from "@/lib/backups";
import { useAction } from "@/lib/use-action";
import { ActiePreview, ONVEILIGE_DIFF } from "./ActiePreview";
import { Aftellen } from "./Aftellen";
import { ErrorPanel } from "./ErrorPanel";
import { useNow } from "./Freshness";
import { KopieerVeld } from "./KopieerVeld";
import { Melding } from "./Melding";
import { RolMelding } from "./RolMelding";
import { Button } from "./ui/button";
import { BevestigDialoog } from "./ui/alert-dialog";
import { UitvoeringsTijdlijn } from "./UitvoeringsTijdlijn";

export const ALLEEN_BEHEERDER = "Alleen een beheerder kan dit goedkeuren.";
export const HERSTELPUNT_ONTBREEKT =
  "Er is nog geen aantoonbaar gebonden herstelpunt. Deze actie vraagt een back-up; de Hub toont het herstelpunt nog niet bij de preview, dus goedkeuren kan hier nog niet.";
export const NAAM_EERST = "Typ eerst de exacte naam van het doel";

/** Waarom beslissen (goedkeuren of uitvoeren) nu niet kan, of null. Volgorde: vervallen, verouderd, blokkade, diff, back-up. */
export function beslisBlokkade(v: ActieVerzoek, verval: string | null, verouderd: boolean, metBackup = true): string | null {
  if (verval) return verval;
  if (verouderd) return "Verouderde gegevens. Een actuele stand van het verzoek is nodig.";
  if (v.action_id === "sso.oidc.hub.register" || v.action_id === "sso.sessions.revoke") {
    return "Registratie van de Hub en het intrekken van Authentik-sessies zijn uitgesteld tot versie 2.";
  }
  if (v.action_id === "automation.flows.restore") {
    if (typeof v.preview?.requires_backup !== "boolean") return "De back-upvereiste van de eigenaar is onbekend.";
    if (v.blokkades.length) return "Het beleid blokkeert dit herstelvoorstel.";
  }
  if (v.blokkades.length) return `Geblokkeerd: ${v.blokkades.map((b) => b.reden).join(" ")}`;
  if (!v.preview_hash || !v.resource_etag || diffRegels(v.preview, v.action_id).onveilig) return ONVEILIGE_DIFF;
  if (metBackup && v.preview?.requires_backup && !v.goedkeuring?.backup_checkpoint_id) return HERSTELPUNT_ONTBREEKT;
  return null;
}

/** Vertaal een weigering van de server bij goedkeuren naar de vervaltekst, of null. */
export function foutVerval(e: HubApiError | null): string | null {
  if (e?.code === "voorstel_verlopen") return VOORSTEL_VERLOPEN;
  if (e?.code !== "preview_gewijzigd") return null;
  const g = e.details.gewijzigd;
  return vervallenTekst(Array.isArray(g) ? g.filter((x): x is string => typeof x === "string") : []);
}

function Gebonden({ v }: { v: Hashes }) {
  return (
    <details data-testid="gebonden-velden">
      <summary className="flex min-h-touch cursor-pointer items-center font-semibold">Gebonden velden</summary>
      <div className="flex flex-col gap-2 pt-2">
        <KopieerVeld label="preview_hash" waarde={v.preview_hash ?? "onbekend"} />
        <KopieerVeld label="resource_etag" waarde={v.resource_etag ?? "onbekend"} />
        <KopieerVeld label="policy_hash" waarde={v.policy_hash ?? "onbekend"} />
      </div>
    </details>
  );
}

/** Eén klik = één verzoek: een tweede klik tijdens een lopend verzoek doet niets (naast de idempotency-key). */
function useEenmalig() {
  const bezig = useRef(false);
  return useCallback(async (werk: () => Promise<unknown>) => {
    if (bezig.current) return;
    bezig.current = true;
    try {
      await werk();
    } finally {
      bezig.current = false;
    }
  }, []);
}

/**
 * GoedkeuringsPagina (C-21) met uitvoering (C-23). De server beslist; zonder beheerdersrol staan er geen knoppen maar de
 * rolmelding. R2: één beslisstap. R3: tweede stap met de getypte naam van het doel.
 */
export function GoedkeuringsPagina({ v, gezien, verouderd, opnieuw }: { v: ActieVerzoek; gezien: Hashes | null; verouderd: boolean; opnieuw: () => void }) {
  const role = useRole();
  const admin = hasRole(role, "admin");
  const operator = hasRole(role, "operator");
  const nu = useNow(1000);
  const eenmalig = useEenmalig();
  const redenId = useId();
  const [stap, setStap] = useState<1 | 2>(1);
  const [naam, setNaam] = useState("");
  const [naamStatus, setNaamStatus] = useState("");
  const [weigeren, setWeigeren] = useState(false);
  const [reden, setReden] = useState<string>("");
  const [bevestig, setBevestig] = useState(false);
  const invoer = useRef<HTMLInputElement>(null);
  const approve = useAction<ActieVerzoek>();
  const reject = useAction<ActieVerzoek>();
  const execute = useAction<unknown>();
  const reconcile = useAction<unknown>();

  const fout = approve.error ?? reject.error ?? execute.error ?? reconcile.error;
  // Weigert de server omdat de binding niet meer klopt of het voorstel verlopen is, dan vervallen beide beslisknoppen.
  const verval = foutVerval(fout) ?? vervallen(v, gezien, nu);
  const geenRecht = fout?.status === 403;
  const k = risicoKlasse(v.risk_class);
  const doel = doelNaam(v.target);
  const binding = gezien ?? v;

  const keurGoed = () =>
    eenmalig(async () => {
      const res = await approve.run(`/api/v1/actions/${v.request_id}/approve`, {
        body: { preview_hash: binding.preview_hash, resource_etag: binding.resource_etag, policy_hash: binding.policy_hash },
      });
      if (res) opnieuw();
    });

  const wijsAf = () =>
    eenmalig(async () => {
      const res = await reject.run(`/api/v1/actions/${v.request_id}/reject`, { body: { reden } });
      if (res) opnieuw();
    });

  const voerUit = () =>
    eenmalig(async () => {
      await execute.run(`/api/v1/actions/${v.request_id}/execute`);
      // Ook na een fout of time-out eerst de stand teruglezen; nooit zelf "uitgevoerd" aannemen.
      opnieuw();
    });

  const helderOp = () =>
    eenmalig(async () => {
      await reconcile.run(`/api/v1/actions/${v.request_id}/reconcile`);
      opnieuw();
    });

  const blok = beslisBlokkade(v, verval, verouderd);
  // Ook een door de server verlopen voorstel toont de beslisknoppen, uitgeschakeld met de reden.
  const wacht = v.status === "wacht_op_goedkeuring" || v.status === "verlopen";

  let beslissing = null;
  if (wacht && (!admin || geenRecht)) {
    beslissing = <RolMelding>{ALLEEN_BEHEERDER}</RolMelding>;
  } else if (wacht) {
    const redenRegel = blok ? (
      <Melding soort={verval ? "beperkt" : "gate"} id={redenId} data-testid="beslis-blokkade">
        <p>{blok}</p>
      </Melding>
    ) : null;
    const gevaarUit = !naamKlopt(naam, doel);
    beslissing = (
      <section className="card" aria-labelledby="beslissen-kop" data-testid="beslissen">
        <h2 id="beslissen-kop" className="text-xl font-bold">
          {k === "R3" ? `Goedkeuren · stap ${stap} van 2` : "Goedkeuren"}
        </h2>
        {redenRegel}
        {k === "R3" && stap === 2 && !blok ? (
          <div className="flex flex-col gap-3" data-testid="r3-stap-2">
            <h3 className="text-base font-bold">Wat er gebeurt</h3>
            <ul className="list-disc pl-6">
              <li>
                {werkwoord(v.action_id)}: <code>{doel ?? "onbekend doel"}</code> via {v.uitvoerder}.
              </li>
              {v.preview?.dataretentie ? <li>{v.preview.dataretentie}</li> : null}
              {v.preview?.terugdraaien ? <li>Terugzetten: {v.preview.terugdraaien}</li> : null}
            </ul>
            {v.goedkeuring?.backup_checkpoint_id ? <KopieerVeld label="Herstelpunt" waarde={v.goedkeuring.backup_checkpoint_id} /> : null}
            <Gebonden v={binding} />
            <label htmlFor="r3-naam" className="font-semibold">
              Typ <code>{doel ?? "(doel zonder naam)"}</code> om te bevestigen
            </label>
            <input
              id="r3-naam"
              ref={invoer}
              className="min-h-touch rounded-lg border-2 border-border-strong bg-card px-3 font-mono"
              autoComplete="off"
              spellCheck={false}
              value={naam}
              onChange={(e) => {
                setNaam(e.target.value);
                setNaamStatus("");
              }}
              aria-describedby="r3-naam-status"
              data-testid="r3-naam"
            />
            <p id="r3-naam-status" aria-live="polite" className="min-h-5 text-sm">
              {naamStatus || (gevaarUit ? NAAM_EERST : "De naam klopt.")}
            </p>
            <div className="flex flex-col-reverse gap-2 sm:flex-row">
              <Button variant="stil" onClick={() => setStap(1)}>
                Annuleren
              </Button>
              <Button
                variant="gevaar"
                uit={gevaarUit}
                bezig={approve.busy}
                aria-describedby="r3-naam-status"
                data-testid="r3-definitief"
                onClick={() => void keurGoed()}
                onClickCapture={() => {
                  if (gevaarUit) {
                    setNaamStatus(NAAM_EERST);
                    invoer.current?.focus();
                  }
                }}
              >
                {werkwoord(v.action_id)} definitief
              </Button>
            </div>
          </div>
        ) : (
          <>
            <Gebonden v={binding} />
            {weigeren ? (
              <fieldset className="flex flex-col gap-2" data-testid="weigeren">
                <legend className="font-semibold">Kies een reden om te weigeren</legend>
                {WEIGER_REDENEN.map((r) => (
                  <label key={r} className="keuze flex min-h-touch items-center gap-2">
                    <input type="radio" name="weigerreden" value={r} checked={reden === r} onChange={() => setReden(r)} />
                    {r}
                  </label>
                ))}
                <div className="flex flex-col-reverse gap-2 sm:flex-row">
                  <Button variant="stil" onClick={() => setWeigeren(false)}>
                    Annuleren
                  </Button>
                  <Button uit={!reden} bezig={reject.busy} onClick={() => void wijsAf()} data-testid="weigeren-bevestigen">
                    Weigeren bevestigen
                  </Button>
                </div>
              </fieldset>
            ) : (
              <div className="flex flex-col-reverse gap-2 sm:flex-row">
                <Button variant="stil" asChild>
                  <Link href="/goedkeuringen">Annuleren</Link>
                </Button>
                <Button onClick={() => setWeigeren(true)} data-testid="weigeren-openen">
                  Weigeren…
                </Button>
                {k === "R3" ? (
                  <Button variant="primair" uit={Boolean(blok)} aria-describedby={blok ? redenId : undefined} onClick={() => setStap(2)} data-testid="r3-volgende">
                    Volgende: bevestigen
                  </Button>
                ) : (
                  <Button variant="primair" uit={Boolean(blok)} bezig={approve.busy} aria-describedby={blok ? redenId : undefined} onClick={() => void keurGoed()} data-testid="goedkeuren">
                    Goedkeuren
                  </Button>
                )}
              </div>
            )}
          </>
        )}
      </section>
    );
  }

  // Een zandbakkloon vereist ook bij R1 een beheerder.
  const klaar = v.status === "klaar" && !v.goedkeuring_nodig;
  const goedgekeurd = v.status === "goedgekeurd";
  const goedkeuringVerlopen = goedgekeurd && v.goedkeuring?.expires_at ? Date.parse(v.goedkeuring.expires_at) <= nu.getTime() : false;
  let uitvoeren = null;
  const beheerderNodig = v.action_id === KLOON || (k !== "R0" && k !== "R1");
  if ((klaar || goedgekeurd) && (geenRecht || !operator || (beheerderNodig && !admin))) {
    uitvoeren = <RolMelding>{beheerderNodig ? "Alleen een beheerder kan dit uitvoeren." : "Uitvoeren kan vanaf de rol operator."}</RolMelding>;
  } else if (klaar || goedgekeurd) {
    const uitBlok = goedkeuringVerlopen ? "Goedkeuring verlopen. Keur het voorstel opnieuw goed." : beslisBlokkade(v, verval, verouderd, false);
    uitvoeren = (
      <section className="card" aria-labelledby="uitvoeren-kop" data-testid="uitvoeren-sectie">
        <h2 id="uitvoeren-kop" className="text-xl font-bold">
          Uitvoeren
        </h2>
        {goedgekeurd && v.goedkeuring?.expires_at ? (
          <p>
            Goedkeuring geldig tot {new Date(v.goedkeuring.expires_at).toLocaleTimeString("nl-NL", { hour: "2-digit", minute: "2-digit" })} (nog{" "}
            <Aftellen tot={v.goedkeuring.expires_at} testId="aftellen-goedkeuring" />)
          </p>
        ) : null}
        {uitBlok ? (
          <Melding soort="gate" id={`${redenId}-uit`} data-testid="uitvoer-blokkade">
            <p>{uitBlok}</p>
          </Melding>
        ) : null}
        <div className="flex flex-col-reverse gap-2 sm:flex-row">
          <Button variant="stil" asChild>
            <Link href="/goedkeuringen">Annuleren</Link>
          </Button>
          <Button
            variant="primair"
            uit={Boolean(uitBlok)}
            bezig={execute.busy}
            aria-describedby={uitBlok ? `${redenId}-uit` : undefined}
            onClick={() => setBevestig(true)}
            data-testid="uitvoeren"
          >
            Uitvoeren
          </Button>
        </div>
        <BevestigDialoog open={bevestig} onOpenChange={setBevestig} titel="Actie uitvoeren?" bevestig="Uitvoeren" onBevestig={() => void voerUit()}>
          <p>
            {werkwoord(v.action_id)}: <code>{doel ?? v.action_id}</code>. De Hub controleert alles opnieuw en leest daarna de uitkomst terug.
          </p>
        </BevestigDialoog>
      </section>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {v.status === "afgewezen" ? (
        <Melding soort="info" data-testid="weigerreden">
          <p>{weigerReden(v.resultaat)}</p>
        </Melding>
      ) : null}
      <ActiePreview v={v} verouderd={verouderd} />
      {fout && fout.code !== "preview_gewijzigd" && fout.code !== "voorstel_verlopen" && fout.status !== 403 ? <ErrorPanel vast={vasteFout} error={toonbareFout(fout)} title="De handeling is niet gelukt" /> : null}
      {beslissing}
      {uitvoeren}
      {v.status !== "wacht_op_goedkeuring" ? <UitvoeringsTijdlijn v={v} verouderd={verouderd} /> : null}
      {v.status === "onbekend" && operator ? (
        <section className="card" aria-labelledby="ophelderen-kop">
          <h2 id="ophelderen-kop" className="text-xl font-bold">
            Uitkomst ophelderen
          </h2>
          <p>De Hub leest het journaal van de uitvoerder. Er wordt niets opnieuw uitgevoerd.</p>
          <div>
            <Button bezig={reconcile.busy} uit={verouderd} onClick={() => void helderOp()} data-testid="ophelderen">
              Journaal lezen
            </Button>
          </div>
        </section>
      ) : null}
      {v.status === "bezig" ? (
        <Melding soort="nogniet" titel="Afbreken is nog niet beschikbaar">
          <p>De Hub heeft geen route om één verzoek af te breken. De algemene noodstop heeft een ander bereik.</p>
        </Melding>
      ) : null}
    </div>
  );
}
