"use client";

import Link from "next/link";
import { useRef, useState, type FormEvent } from "react";
import { Field } from "@/components/Field";
import { Freshness, useNow } from "@/components/Freshness";
import { Loading } from "@/components/Loading";
import { Melding } from "@/components/Melding";
import { StatusBadge } from "@/components/StatusBadge";
import { BevestigDialoog } from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { apiRequest, HubApiError, type ApiOptions } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { useApi } from "@/lib/use-api";
import { uuidv4 } from "@/lib/uuid";
import {
  ADAPTERS, APPS, allePaginas, koppelstatus, oorzaak, type AppId, type Installatie, type Installaties,
  type Koppeling, type Pagina, type Probleem, type Veld, veiligAdres,
} from "./adapterweergave";

type Actie = "Opslaan" | "Testen" | "Ontkoppelen";
const CONTACTWOORDEN: Record<string, string> = { healthy: "Bereikbaar", degraded: "Beperkt", down: "Niet bereikbaar" };

function verbindingsuitval(error: HubApiError) {
  return error.status === 0 || [502, 503, 504].includes(error.status);
}

function AppKaart({ app, doel, koppeling, beheer, inventarisActueel, laatstBekend, nu, vernieuw }: {
  app: AppId; doel?: Installatie; koppeling?: Koppeling; beheer: boolean;
  inventarisActueel: boolean; laatstBekend: boolean; nu: number; vernieuw: () => Promise<void>;
}) {
  const { naam, uitleg } = APPS[app];
  const openbaar = app === "media-source-optimizer";
  const huis = app === "my_house";
  const id = `adapter-${doel?.id ?? koppeling?.catalog_app_id ?? app}`;
  const bewaardAdres = koppeling && veiligAdres(koppeling.basis_url) ? koppeling.basis_url : "";
  const basisadres = bewaardAdres || (doel?.deep_link && veiligAdres(doel.deep_link) ? doel.deep_link : "");
  const [ontkoppel, zetOntkoppel] = useState<Pick<Koppeling, "id" | "version"> | null>(null);
  const ontkoppelKnop = useRef<HTMLButtonElement>(null);
  const formulier = useRef<HTMLFormElement>(null);
  const bevestiging = useRef<HTMLInputElement>(null);
  const [bezig, zetBezig] = useState<Actie | null>(null);
  const [fout, zetFout] = useState<Probleem | null>(null);
  const [melding, zetMelding] = useState("");
  const [mislukteProef, zetMislukteProef] = useState<string | null>(null);
  const invoer = useRef<HTMLInputElement>(null);
  const bezigRef = useRef(false);
  const poging = useRef<{ bedoeling: string; sleutel: string } | null>(null);
  const kanOpslaan = Boolean(doel && inventarisActueel);
  const pad = koppeling ? ADAPTERS + "/" + encodeURIComponent(koppeling.id) : ADAPTERS;
  const stand = koppelstatus(koppeling, nu);
  const versie = koppeling ? koppeling.id + "/" + koppeling.version : null;
  const proefOnzeker = versie !== null && mislukteProef === versie;
  const gemeten = koppeling?.verbinding.observed_at;
  const heeftMeettijd = gemeten && Number.isFinite(Date.parse(gemeten)) && Date.parse(gemeten) <= nu;
  const historisch = koppeling && heeftMeettijd && (laatstBekend || proefOnzeker || stand.pil.tone !== "neutral")
    ? CONTACTWOORDEN[koppeling.verbinding.laatste_status ?? koppeling.verbinding.status] : undefined;
  const veldfout = (veld: Veld) => fout?.veld === veld ? fout.tekst : undefined;

  function gewijzigdeInvoer() {
    poging.current = null;
    zetFout(null);
    zetMelding("");
  }

  function bevestigingWissen() {
    if (bevestiging.current) bevestiging.current.checked = false;
  }

  async function verstuur(actie: Actie, opties: ApiOptions) {
    if (!beheer || bezigRef.current) return;
    bezigRef.current = true;
    zetBezig(actie);
    zetMelding("");
    zetFout(null);
    const bedoeling = [actie, pad, koppeling?.version].join("/");
    if (poging.current?.bedoeling !== bedoeling) poging.current = { bedoeling, sleutel: uuidv4() };
    try {
      const { data } = await apiRequest<{ id?: string; version?: number; verwijderd?: boolean }>(actie === "Testen" ? pad + "/test" : pad, {
        ...opties, idempotencyKey: poging.current.sleutel,
      });
      if (actie === "Ontkoppelen" ? data?.verwijderd !== true : !data?.id || !Number.isInteger(data.version)) {
        throw new Error("Bevestiging ontbreekt.");
      }
      poging.current = null;
      zetMislukteProef(null);
      if (actie !== "Testen") formulier.current?.reset();
      await vernieuw();
      zetMelding(actie === "Opslaan" ? "Koppeling opgeslagen." : actie === "Ontkoppelen" ? "Koppeling verwijderd uit de Hub." : "Contactproef uitgevoerd.");
    } catch (error) {
      if (actie === "Testen") zetMislukteProef(versie);
      if (error instanceof HubApiError && error.status >= 400 && error.status < 500) poging.current = null;
      const reden = error instanceof HubApiError ? error.details.reason ?? error.code : null;
      const probleem = oorzaak(typeof reden === "string" ? reden : "", app);
      zetFout(actie === "Opslaan" && kanOpslaan ? probleem : { tekst: probleem.tekst });
      if (error instanceof HubApiError && [404, 409, 412].includes(error.status)) {
        bevestigingWissen();
        await vernieuw();
      }
    } finally {
      bezigRef.current = false;
      zetBezig(null);
    }
  }

  function opslaan(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!doel || !kanOpslaan || bezigRef.current) return;
    const velden = new FormData(e.currentTarget);
    const adres = String(velden.get("adres") ?? "");
    const server = String(velden.get("server") ?? "").trim();
    const waarde = invoer.current?.value;
    if (!veiligAdres(adres) || (waarde && adres.toLowerCase().includes(waarde.toLowerCase()))) {
      zetFout(oorzaak("adres_ongeldig", app));
    } else if (!openbaar && (!waarde || !/^[!-~]{8,512}$/.test(waarde))) {
      zetFout(oorzaak("ongeldige_invoer", app));
    } else if (huis && !/^[a-f\d]{8}(?:-[a-f\d]{4}){3}-[a-f\d]{12}$/i.test(server)) {
      zetFout({ veld: "server", tekst: "Neem de volledige server-ID over uit my_house." });
    } else if (!bevestiging.current?.checked) {
      zetFout({ veld: "bevestiging", tekst: "Bevestig eerst dat het adres bij deze installatie hoort." });
    } else {
      void verstuur("Opslaan", {
        method: koppeling ? "PATCH" : "POST",
        ifMatch: koppeling ? `"${koppeling.version}"` : null,
        body: { ...(!koppeling && { app_id: app }), catalog_app_id: doel.id, basis_url: adres, doel_bevestigd: true, ...(huis && { server_id: server }) },
        adapterCredential: openbaar ? undefined : waarde,
      });
    }
  }

  return (
    <article className="card" aria-labelledby={id + "-titel"} aria-describedby={doel || bewaardAdres ? id + "-installatie" : undefined}>
      <h3 id={id + "-titel"}>{naam}</h3>
      {doel || bewaardAdres ? (
        <p id={id + "-installatie"} className="text-sm break-all text-muted-foreground">
          Installatie · {doel?.naam ?? bewaardAdres}
        </p>
      ) : null}
      <StatusBadge view={laatstBekend || proefOnzeker ? { tone: "unknown", label: "Onbekend" } : stand.pil} />
      {laatstBekend ? <p>Laatst bekend · de Hub kon deze kaart niet vernieuwen.</p> : proefOnzeker ? <p>De laatste contactproef is mislukt. Test de verbinding opnieuw.</p> : stand.uitleg ? <p>{stand.uitleg}</p> : null}
      {historisch ? <p>Laatst bekend · {historisch}</p> : null}
      <Freshness bron={naam} label="Laatste contactmeting" observedAt={heeftMeettijd ? gemeten : null}
        onbekendeTijd={gemeten ? "Meettijd onbekend" : "Nog geen bevestigde meting"} />
      {koppeling?.laatste4.length === 4 ? <p>Laatste 4 tekens · <code>{koppeling.laatste4}</code> · ingevoerd op {formatDate(koppeling.ingevoerd_op)}</p> : null}
      {beheer ? (
        <>
          <p>{uitleg}</p>
          {app === "mediaguard" && !koppeling ? <p>De Hub kan de sleutel bewaren. Contact en sleutelrechten blijven onbekend totdat MediaGuard een veilige leescontrole biedt.</p> : null}
          {kanOpslaan ? (
            <form key={JSON.stringify([koppeling?.id, koppeling?.version, basisadres, doel?.deep_link])}
              ref={formulier} noValidate className="flex flex-col gap-3" onSubmit={opslaan} onChange={gewijzigdeInvoer}>
              <Field id={id + "-adres"} label="HTTPS-adres" help="Neem het adres met de poort over van deze installatie." error={veldfout("adres")}>
                {(a) => <input {...a} type="url" name="adres" required readOnly={Boolean(bezig)} defaultValue={basisadres} onChange={bevestigingWissen} />}
              </Field>
              <Field id={id + "-invoer"} label={huis ? "Koppelcode" : openbaar ? "Machinesleutel" : "API-sleutel"}
                help={openbaar ? "Sleutelinvoer is voor deze openbare verbinding niet beschikbaar." : koppeling ? "Nieuwe invoer vervangt de opgeslagen toegang." : undefined}
                error={veldfout("invoer")}>
                {(a) => <input {...a} ref={invoer} type="password" disabled={openbaar} readOnly={Boolean(bezig)} required={!openbaar}
                  autoComplete="new-password" autoCapitalize="none" spellCheck={false} maxLength={512} />}
              </Field>
              {huis ? (
                <Field id={id + "-server"} label="Server-ID" help="Deze ID staat bij de koppelcode in my_house." error={veldfout("server")}>
                  {(a) => <input {...a} name="server" required readOnly={Boolean(bezig)} autoCapitalize="none" spellCheck={false} onChange={bevestigingWissen} />}
                </Field>
              ) : null}
              <label className="keuze">
                <input ref={bevestiging} id={id + "-bevestiging"} type="checkbox" disabled={Boolean(bezig)}
                  aria-invalid={fout?.veld === "bevestiging" || undefined}
                  aria-describedby={fout?.veld === "bevestiging" ? id + "-fout" : undefined} />
                Ik heb gecontroleerd dat het adres bij deze installatie hoort.
              </label>
              <div><Button type="submit" variant="primair" uit={Boolean(bezig)} bezig={bezig === "Opslaan"}>Opslaan</Button></div>
            </form>
          ) : (
            <p>Voor het instellen is een actuele installatie nodig. <Link href="/apps">Controleer de appcatalogus</Link> en vernieuw de inventaris.</p>
          )}
          {fout ? (
            <Melding soort="fout" role="alert" titel="Handeling mislukt" id={id + "-fout"}>
              {fout.veld && kanOpslaan ? <a className="losse-link" href={"#" + id + "-" + fout.veld}>{fout.tekst}</a> : <p>{fout.tekst}</p>}
            </Melding>
          ) : null}
          <div className="flex flex-wrap gap-2">
            <Button uit={!koppeling || Boolean(bezig)} bezig={bezig === "Testen"} aria-describedby={!koppeling ? id + "-reden" : undefined}
              onClick={() => void verstuur("Testen", { method: "POST" })}>Testen</Button>
            <Button ref={ontkoppelKnop} uit={!koppeling || Boolean(bezig)} aria-describedby={!koppeling ? id + "-reden" : undefined}
              onClick={() => { if (koppeling) zetOntkoppel({ id: koppeling.id, version: koppeling.version }); }}>Ontkoppelen</Button>
          </div>
          {!koppeling ? <p id={id + "-reden"} className="help">Testen en ontkoppelen kan zodra de koppeling is opgeslagen.</p> : null}
          <p role="status">{bezig ? bezig + "…" : melding}</p>
          <BevestigDialoog open={ontkoppel !== null && ontkoppel.id === koppeling?.id} onOpenChange={(open) => { if (!open) zetOntkoppel(null); }}
            terugNaar={ontkoppelKnop} titel={naam + " ontkoppelen?"} bevestig="Ontkoppelen" gevaar
            onBevestig={() => { if (ontkoppel?.id === koppeling?.id && ontkoppel) void verstuur("Ontkoppelen", { method: "DELETE", ifMatch: `"${ontkoppel.version}"` }); }}>
            <p>{openbaar ? "De Hub vergeet deze openbare koppeling en de contactmeting." :
              huis ? "De Hub vergeet de opgeslagen sleutel en de contactmeting. Trek de toegang van deze Hub ook in my_house zelf in." :
                "De Hub vergeet de opgeslagen sleutel en de contactmeting. Trek de sleutel ook in MediaGuard zelf in."}</p>
            {bewaardAdres ? <p className="break-all">Bestemming · {bewaardAdres}</p> : null}
          </BevestigDialoog>
        </>
      ) : null}
    </article>
  );
}

export function BestaandeApps({ beheer }: { beheer: boolean }) {
  const links = useApi<Pagina<Koppeling>>(ADAPTERS + "?limit=200", 60_000, verbindingsuitval, allePaginas);
  const catalogus = useApi<Installaties>("/api/v1/apps?soort=bestaand&limit=200", 60_000, verbindingsuitval, allePaginas);
  const nu = useNow(1000).getTime();
  const fout = links.error ?? catalogus.error;
  const toonKaarten = links.data && catalogus.data && [links.error, catalogus.error].every(
    (e) => !e || verbindingsuitval(e),
  );
  async function vernieuw() {
    await Promise.all([links.reload(), catalogus.reload()]);
  }
  return (
    <section id="bestaande-apps" aria-labelledby="bestaande-apps-titel" className="flex flex-col gap-3">
      <h2 id="bestaande-apps-titel">Bestaande apps</h2>
      {fout ? (
        <Melding soort="onbekend" titel="Koppelingen onbekend" role="alert">
          <p>De Hub kon de lijst met koppelingen of installaties niet ophalen. Controleer je toegang en probeer het opnieuw.</p>
          <div><Button onClick={() => void vernieuw()}>Opnieuw proberen</Button></div>
        </Melding>
      ) : !toonKaarten ? <Loading text="Koppelingen ophalen…" /> : null}
      {toonKaarten ? (
        <div className="grid items-start gap-4 xl:grid-cols-2">
          {(Object.keys(APPS) as AppId[]).map((app) => {
            const installaties = catalogus.data!.items.filter((d) => d.app_id === app && d.soort === "bestaand" && d.aanwezig);
            const gekoppeld = links.data!.items.filter((k) => k.app_id === app);
            const doelen = new Map(installaties.map((d) => [d.id, d]));
            const perDoel = new Map(gekoppeld.map((k) => [k.catalog_app_id, k]));
            const ids = new Set([...doelen.keys(), ...perDoel.keys()]);
            if (!ids.size) ids.add(app);
            return Array.from(ids, (id) => <AppKaart key={id} app={app} doel={doelen.get(id)} koppeling={perDoel.get(id)}
              inventarisActueel={catalogus.data!.inventaris.status === "ok"} beheer={beheer && !fout} laatstBekend={Boolean(fout)} nu={nu} vernieuw={vernieuw} />);
          })}
        </div>
      ) : null}
    </section>
  );
}
