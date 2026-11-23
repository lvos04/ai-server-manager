"use client";

import { Lock, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { RisicoBadge } from "@/components/ActiePreview";
import { useNow } from "@/components/Freshness";
import { isUuid } from "@/lib/uuid";
import { ErrorPanel } from "@/components/ErrorPanel";
import { KopieerVeld } from "@/components/KopieerVeld";
import { Loading } from "@/components/Loading";
import { Melding } from "@/components/Melding";
import { ResponsiveList } from "@/components/ResponsiveList";
import { RolMelding } from "@/components/RolMelding";
import { Button, buttonVariants } from "@/components/ui/button";
import { vasteFout, werkwoord, type ActieLijst, type Beleid } from "@/lib/acties";
import { APP_DOEL, appActies, EMBY_ZIN, terugzetPunten, updateDoel, wieBeslist, type AppActie } from "@/lib/appbeheer";
import { gateVoorwaarde, meettijd, puntenReden, type Herstelpunt } from "@/lib/backups";
import { useBackupGate } from "@/lib/use-backup-gate";
import { useMeting } from "@/lib/use-meting";
import type { CatalogDetail } from "@/lib/catalog";
import { formatDateTime } from "@/lib/format";
import { hasRole, ROLE_LABEL, useRole } from "@/lib/session";
import { useAction } from "@/lib/use-action";
import type { ApiState } from "@/lib/use-api";
import { useApi } from "@/lib/use-api";

export const ALLEEN_CONTAINER = "Alleen de container wordt verwijderd. Je gegevens blijven bewaard.";
export const GEEN_TERUGZETPAD =
  "Terugzetten is geblokkeerd: er is geen bevestigd terugzetpad. Alleen een eigen, uitgevoerde bijwerking van deze app via de Hub telt; een eerder gezien image is geen veilig terugzetpad.";

/** Eén voorstel maken (POST /api/v1/actions) en daarna naar de actie-preview en goedkeuring (S-061/S-063). */
function useVoorstel(app: CatalogDetail) {
  const router = useRouter();
  const a = useAction<{ request_id: string }>();
  const stel = async (actionId: string, parameters: Record<string, unknown> = {}) => {
    if (a.busy) return;
    // De reden is een vaste tekst; vrije tekst van de gebruiker gaat nooit mee.
    const r = await a.run("/api/v1/actions", { body: { action_id: actionId, target: APP_DOEL(app.naam), parameters, reason: `Hub appdetail: ${actionId}` } });
    if (isUuid(r?.request_id)) router.push(`/goedkeuringen/${r.request_id}`);
  };
  return { ...a, stel };
}

function Uitleg({ rijen }: { rijen: AppActie[] }) {
  const regels = [...new Map(rijen.flatMap((r) => r.blokkades.map((b) => [b.id, b] as const))).values()];
  if (!regels.length) return null;
  const onbekend = regels.some((b) => b.code === "actiebeleid_onbekend" || b.code === "doel_niet_herkenbaar");
  return (
    <Melding soort={onbekend ? "onbekend" : "info"} icon={ShieldCheck} titel={onbekend ? "Bescherming onbekend" : "Beschermde app"} data-testid="beschermd">
      {regels.some((b) => b.code === "emby_nooit_door_platform") ? <p className="font-semibold">{EMBY_ZIN}</p> : null}
      <ul className="list-disc pl-6">
        {regels.map((r) => <li key={r.id}>{r.reden}</li>)}
      </ul>
    </Melding>
  );
}

function BeleidStand({ beleid }: { beleid: ApiState<Beleid> }) {
  if (beleid.data && !beleid.stale) return null;
  if (beleid.data) {
    return (
      <Melding soort="onbekend" titel="Verouderd" data-testid="beleid-verouderd">
        <p>Het risicobeleid kon niet opnieuw worden gelezen. Er zijn geen knoppen tot een nieuwe, geslaagde lezing.</p>
      </Melding>
    );
  }
  if (beleid.error) return <ErrorPanel vast={vasteFout} error={beleid.error} title="Toegestane acties onbekend" onRetry={() => void beleid.reload()} alert={false} />;
  return <Loading text="Acties ophalen…" />;
}

// ------------------------------------------------------------------ S-044 Versies
export function Versies({ app, beleid }: { app: CatalogDetail; beleid: ApiState<Beleid> }) {
  const role = useRole();
  const operator = hasRole(role, "operator");
  const voorstel = useVoorstel(app);
  const updates = useApi<ActieLijst>(operator ? "/api/v1/actions?action_id=app.update&status=uitgevoerd&limit=50" : null);
  const rijen = beleid.data ? appActies(beleid.data, app) : [];
  const bijwerken = rijen.find((r) => r.actie.action_id === "app.update");
  const terugzetten = rijen.find((r) => r.actie.action_id === "app.rollback");
  const bruikbaar = Boolean(beleid.data && !beleid.stale);
  const nu = useNow(1000).getTime();
  const controleer = operator && bruikbaar && (bijwerken?.blokkades.length === 0 || terugzetten?.blokkades.length === 0);
  const { gate, dekking, stand } = useBackupGate(controleer, nu);
  const herstel = useMeting<{ items: Herstelpunt[] }>(controleer ? `/api/v1/backups/herstelpunten?app=${encodeURIComponent(app.naam)}` : null);
  const rij = Array.isArray(dekking.data?.apps) ? dekking.data.apps.find(a => a.app === app.naam) : undefined;
  const eigenPunten = herstel.data?.items.filter(p => p.app === app.naam);
  const reden = stand === "geblokkeerd" ? (gate.data?.redenen[0] ? gateVoorwaarde(gate.data.redenen[0])[0] : "De back-upgate is dicht.")
    : stand !== "toegestaan" ? "De back-upgate is onbekend."
    : !eigenPunten || herstel.stale ? "De herstelpunten zijn onbekend."
    : eigenPunten.length && !eigenPunten.some(p => puntenReden(p, rij?.herkend_als ?? app.app_id, rij?.rpo_rto.rpo_uren, nu) === null)
      ? "Er is geen bruikbaar geverifieerd herstelpunt binnen de RPO." : null;
  const doel = updateDoel(app);
  const punten = updates.data ? terugzetPunten(updates.data.items, app.naam) : [];
  const c = app.catalogus ?? {};
  return (
    <div className="flex flex-col gap-4" data-testid="app-versies">
      <dl className="kv">
        <dt>Huidige versie</dt>
        <dd>{app.versie ?? app.image.tag ?? "Onbekend"}</dd>
        <dt>Image</dt>
        <dd>
          <code className="break-all">
            {app.image.repository ?? "onbekend"}:{app.image.tag ?? "?"}
          </code>
        </dd>
        <dt>Nieuwste catalogusversie</dt>
        <dd>
          {typeof c.nieuwste_versie === "string" ? c.nieuwste_versie : "Beschikbare versie onbekend"}
          {app.bron?.observed_at ? <span className="text-sm text-muted-foreground"> · TrueNAS, gemeten {formatDateTime(meettijd(app.bron.observed_at, nu))}</span> : null}
        </dd>
      </dl>
      <KopieerVeld label="Image-digest" waarde={app.image.digest ?? "onbekend"} />
      <h2 className="text-lg">Versiehistorie</h2>
      {app.image_historie.length ? (
        <ResponsiveList
          items={app.image_historie}
          label="Gezien op de NAS"
          sleutel={(h) => `${h.op}-${h.digest ?? h.tag}`}
          tabelVanaf={768}
          kolommen={[
            { kop: "Gezien", cel: (h) => formatDateTime(h.op) },
            { kop: "Image", cel: (h) => <code className="break-all">{`${h.repository ?? "?"}:${h.tag ?? "?"}`}</code> },
            { kop: "Digest", cel: (h) => <code className="break-all">{h.digest ?? "digest onbekend"}</code> },
          ]}
        />
      ) : (
        <p>Nog geen versiehistorie.</p>
      )}
      <p className="text-sm text-muted-foreground">Een eerder gezien image bewijst op zichzelf geen veilig terugzetpad.</p>

      <h2 className="text-lg">Bijwerken en terugzetten</h2>
      {bruikbaar ? <Uitleg rijen={rijen} /> : null}
      {!operator ? (
        <RolMelding>Je kijkt als {ROLE_LABEL[role ?? "viewer"]}: bijwerken en terugzetten kan pas vanaf de rol operator.</RolMelding>
      ) : !bruikbaar ? (
        <BeleidStand beleid={beleid} />
      ) : (
        <div className="flex flex-col gap-3">
          {controleer && reden && <p id="versies-backupreden">{reden} <Link href="/backups" className="losse-link">Bekijk de back-upgate</Link></p>}
          {bijwerken?.blokkades.length === 0 && ("parameters" in doel ? (
            <div className="flex flex-col gap-1">
              <p>Bijwerken opent eerst een voorstel met preview, risicoklasse en de vereiste back-up. Er gebeurt nog niets.</p>
              <div>
                <Button variant="primair" uit={!!reden} aria-describedby={reden ? "versies-backupreden" : undefined} bezig={voorstel.busy} onClick={() => void voorstel.stel("app.update", doel.parameters)} data-testid="bijwerken">
                  Bijwerken naar {doel.naar}
                </Button>
              </div>
            </div>
          ) : (
            <Melding soort="nogniet" titel="Bijwerken" data-testid="bijwerken-niet">
              <p>{doel.reden}</p>
            </Melding>
          ))}
          {terugzetten?.blokkades.length === 0 && (updates.error ? (
            <ErrorPanel vast={vasteFout} error={updates.error} title="Terugzetpaden ophalen mislukt" alert={false} />
          ) : !updates.data ? (
            <Loading text="Terugzetpaden ophalen…" regels={1} />
          ) : punten.length ? (
            <ul className="m-0 flex list-none flex-col gap-2 p-0" data-testid="terugzetpunten">
              {punten.map((p) => (
                <li key={p.request_id} className="flex flex-wrap items-center gap-2">
                  <Button uit={!!reden || updates.stale} aria-describedby={reden ? "versies-backupreden" : undefined} bezig={voorstel.busy} onClick={() => void voorstel.stel("app.rollback", { herstel_van: p.request_id })}>
                    Terugzetten naar de stand vóór de bijwerking van {p.uitgevoerd_op ? formatDateTime(p.uitgevoerd_op) : "onbekend tijdstip"}
                  </Button>
                </li>
              ))}
            </ul>
          ) : (
            <Melding soort="gate" icon={Lock} data-testid="terugzetten-geblokkeerd">
              <p>{GEEN_TERUGZETPAD}</p>
              <p>
                <Link href="/backups">Bekijk herstelpunten</Link>
              </p>
            </Melding>
          ))}
          {voorstel.error ? <ErrorPanel vast={vasteFout} error={voorstel.error} title="Voorstel maken mislukt" /> : null}
        </div>
      )}
    </div>
  );
}

// ------------------------------------------------------------------ S-048 Verwijderen, stap 1
function ControleerWatBlijft({ app, sluit, voorstel }: { app: CatalogDetail; sluit: () => void; voorstel: ReturnType<typeof useVoorstel> }) {
  const annuleer = useRef<HTMLButtonElement>(null);
  useEffect(() => annuleer.current?.focus(), []);
  return (
    <section className="card flex flex-col gap-3" aria-labelledby="verwijderen-kop" data-testid="verwijderen-controle">
      <h3 id="verwijderen-kop" className="text-lg font-bold">
        Controleer wat blijft · stap 1 van 2
      </h3>
      <p className="font-semibold" data-testid="data-blijft">
        {ALLEEN_CONTAINER}
      </p>
      <dl className="kv">
        <dt>App</dt>
        <dd>
          {app.titel} (<code>{app.naam}</code>)
        </dd>
        <dt>Datasets die blijven</dt>
        <dd>{app.datasets.length ? app.datasets.map((d) => <code key={d} className="block break-all">{d}</code>) : "Geen dataset gevonden in de inventaris."}</dd>
        <dt>Opslag (hostpad → container)</dt>
        <dd>
          {app.opslag.length
            ? app.opslag.map((o) => (
                <code key={`${o.bron}-${o.doel}`} className="block break-all">
                  {o.bron} → {o.doel}
                </code>
              ))
            : "Geen mounts gevonden in de inventaris."}
        </dd>
        <dt>Herstel</dt>
        <dd>Opnieuw installeren; de datasets hierboven blijven staan.</dd>
      </dl>
      <p className="text-sm">
        Data verwijderen is een aparte R3-procedure met een eigen goedkeuring. Het beleid blokkeert die nu, dus hier staat geen knop of keuze
        voor.
      </p>
      <p className="text-sm">Na deze stap volgt het voorstel. Daar keurt een beheerder de verwijdering apart goed (stap 2 van 2).</p>
      <div className="flex flex-col-reverse gap-2 sm:flex-row">
        <Button ref={annuleer} variant="stil" onClick={sluit} data-testid="verwijderen-annuleren">
          Annuleren
        </Button>
        <Button variant="gevaar" bezig={voorstel.busy} onClick={() => void voorstel.stel("app.uninstall")} data-testid="verwijderen-volgende">
          Volgende: verwijderen goedkeuren
        </Button>
      </div>
    </section>
  );
}

// ------------------------------------------------------------------ S-045 Acties
export function Acties({ app, beleid }: { app: CatalogDetail; beleid: ApiState<Beleid> }) {
  const role = useRole();
  const operator = hasRole(role, "operator");
  const voorstel = useVoorstel(app);
  const [verwijderen, setVerwijderen] = useState(false);
  const bruikbaar = Boolean(beleid.data && !beleid.stale);
  const rijen = beleid.data ? appActies(beleid.data, app) : [];
  const magVerwijderen = rijen.find((r) => r.actie.action_id === "app.uninstall")?.blokkades.length === 0;

  const handeling = (r: AppActie) => {
    const id = r.actie.action_id;
    if (r.blokkades.length) return <span className="text-sm">Niet in de Hub: {r.blokkades[0]!.reden}</span>;
    if (!operator || !bruikbaar) return <span className="text-sm">Geen handeling</span>;
    if (id === "app.update" || id === "app.rollback") {
      return (
        <Link href="?tab=versies" className={buttonVariants({ variant: "secundair", size: "klein" })}>
          Via Versies<span className="sr-only">: {werkwoord(id)}</span>
        </Link>
      );
    }
    if (id === "app.uninstall") {
      return (
        <Button size="klein" variant="secundair" onClick={() => setVerwijderen(true)} data-testid="actie-app.uninstall">
          Verwijderen…<span className="sr-only">: {app.titel}</span>
        </Button>
      );
    }
    return (
      <Button size="klein" variant="secundair" bezig={voorstel.busy} onClick={() => void voorstel.stel(id)} data-testid={`actie-${id}`}>
        Bekijk voorstel<span className="sr-only">: {werkwoord(id)}</span>
      </Button>
    );
  };

  return (
    <div className="flex flex-col gap-3" data-testid="app-acties">
      {!operator ? <RolMelding>Je kijkt als {ROLE_LABEL[role ?? "viewer"]}: acties voorstellen kan pas vanaf de rol operator.</RolMelding> : null}
      <BeleidStand beleid={beleid} />
      <Uitleg rijen={rijen} />
      {beleid.data ? (
        rijen.length ? (
          <ResponsiveList
            items={rijen}
            label="Acties voor deze app"
            sleutel={(r) => r.actie.action_id}
            rijTestId={(r) => `rij-${r.actie.action_id}`}
            tabelVanaf={768}
            kolommen={[
              { kop: "Actie", cel: (r) => <strong>{werkwoord(r.actie.action_id)}</strong> },
              { kop: "Risico", cel: (r) => <RisicoBadge klasse={r.klasse} /> },
              { kop: "Back-up vooraf", cel: (r) => (r.actie.requires_backup ? "Vereist" : "Niet nodig") },
              { kop: "Wie beslist", cel: (r) => wieBeslist(r.klasse) },
              { kop: "Handeling", cel: handeling },
            ]}
          />
        ) : (
          <p>Geen acties voor deze app.</p>
        )
      ) : null}
      <p className="text-sm text-muted-foreground">
        De klasse komt uit het risicobeleid. Het voorstel zelf controleert het doel opnieuw; de server beslist.
      </p>
      {verwijderen && operator && bruikbaar && magVerwijderen ? (
        <ControleerWatBlijft app={app} sluit={() => setVerwijderen(false)} voorstel={voorstel} />
      ) : null}
      {voorstel.error ? <ErrorPanel vast={vasteFout} error={voorstel.error} title="Voorstel maken mislukt" /> : null}
    </div>
  );
}
