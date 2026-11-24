"use client";

import { Check, Lock } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { vasteFout } from "@/lib/acties";
import { isUuid } from "@/lib/uuid";
import { ErrorPanel } from "@/components/ErrorPanel";
import { useNow } from "@/components/Freshness";
import { KopieerVeld } from "@/components/KopieerVeld";
import { Loading } from "@/components/Loading";
import { Melding } from "@/components/Melding";
import { PageHeader } from "@/components/PageHeader";
import { RolMelding } from "@/components/RolMelding";
import { Button, buttonVariants } from "@/components/ui/button";
import { CATALOGUS_NOG_NIET, planBlokkade, planCatalogus, planDigests, type InstallPlan } from "@/lib/appbeheer";
import { formatTime } from "@/lib/format";
import { hasRole, useRole } from "@/lib/session";
import { useAction } from "@/lib/use-action";
import { useBronlijst } from "@/lib/use-meting";
import { cn } from "@/lib/utils";

export const STAPPEN = ["Kies app", "Parameters", "Controle vooraf", "Preview", "Goedkeuring", "Uitvoering", "Controle na uitvoering"] as const;
type Toestand = "klaar" | "huidig" | "open" | "geblokkeerd";

export const NIET_IN_PLAN = "Niet beschikbaar — het installatieplan levert dit nog niet aan de browser.";


/** Welke stap nu aan de beurt is: zonder plan ‘Kies app’; een blokkade houdt de wizard bij ‘Controle vooraf’. */
export function huidigeStap(plan: InstallPlan | null, blok: string | null): number {
  if (!plan) return 0;
  if (plan.status === "geinstalleerd_controles_open") return 6;
  if (blok) return 2;
  return plan.request_id ? 4 : 3;
}

function Stappen({ huidig, geblokkeerd }: { huidig: number; geblokkeerd: boolean }) {
  return (
    <nav aria-label="Stappen van de installatie" data-testid="wizard-stappen">
      <ol className="m-0 flex list-none flex-wrap gap-2 p-0 xl:flex-nowrap">
        {STAPPEN.map((titel, i) => {
          const t: Toestand = i < huidig ? "klaar" : i === huidig ? (geblokkeerd ? "geblokkeerd" : "huidig") : "open";
          return (
            <li key={titel} className="flex items-center gap-2 xl:flex-1" aria-current={i === huidig ? "step" : undefined} data-toestand={t}>
              <span
                className={cn(
                  "inline-flex size-8 shrink-0 items-center justify-center rounded-full border-2 font-mono text-sm font-bold",
                  t === "klaar" && "border-foreground bg-foreground text-background",
                  t === "huidig" && "border-primary bg-primary text-primary-foreground",
                  t === "geblokkeerd" && "border-dashed border-gate bg-gate-bg text-gate-ink",
                  t === "open" && "border-border-strong bg-card",
                )}
              >
                {/* De stand staat ook als tekst in de vorm: status nooit alleen kleur of icoon. */}
                {t === "klaar" ? <Check className="size-4" aria-hidden="true" /> : t === "geblokkeerd" ? <Lock className="size-4" aria-hidden="true" /> : <span aria-hidden="true">{i + 1}</span>}
                <span className="sr-only">{t === "klaar" ? "Klaar: " : t === "geblokkeerd" ? "Geblokkeerd: " : t === "open" ? "Nog niet: " : "Nu: "}</span>
              </span>
              <span className="sr-only xl:not-sr-only xl:text-sm">{titel}</span>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

/** Installatiepreview (COMPONENTEN.md §15): alleen getypte velden uit het plan; geen geheime waarde, geen vrije tekst. */
function InstallatiePreview({ plan, oud }: { plan: InstallPlan; oud: boolean }) {
  const cat = planCatalogus(plan);
  const digests = planDigests(plan);
  const nb = <span className="text-sm">{NIET_IN_PLAN}</span>;
  return (
    <section className="card flex flex-col gap-3" aria-labelledby="preview-kop" data-testid="installatiepreview">
      <h3 id="preview-kop" className="text-lg font-bold">
        Installatiepreview
      </h3>
      <dl className="kv">
        <dt>App</dt>
        <dd>
          <code>{plan.app_id}</code>
        </dd>
        <dt>Naam op de NAS</dt>
        <dd>
          <code>{plan.app_name}</code>
        </dd>
        <dt>Installatiewijze</dt>
        <dd>Officiële catalogusapp of standaard TrueNAS Custom App. Nooit YAML of compose.</dd>
        <dt>Catalogus</dt>
        <dd>{cat ? <code>{`${cat.train} / ${cat.app} / ${cat.version}`}</code> : "Onbekend"}</dd>
        <dt>Image-digests</dt>
        <dd className="flex flex-col gap-2">{digests.length ? digests.map((d) => <KopieerVeld key={d} label="Digest" waarde={d} />) : "Onbekend"}</dd>
        <dt>Hostpaden en mounts</dt>
        <dd>{nb}</dd>
        <dt>Poorten en netwerk</dt>
        <dd>{nb}</dd>
        <dt>GPU en privileges (met reden)</dt>
        <dd>{nb}</dd>
        <dt>Resources</dt>
        <dd>{nb}</dd>
        <dt>Geheimen (alleen namen)</dt>
        <dd>{nb}</dd>
        <dt>Back-up en dataretentie</dt>
        <dd>{nb}</dd>
      </dl>
      <h4 className="text-base font-bold">Controles na installatie</h4>
      {plan.controles_na_installatie.length ? (
        <ul className="list-disc pl-6" data-testid="controles-na">
          {plan.controles_na_installatie.map((c) => (
            <li key={c.id}>
              <code>{c.id}</code> · {c.beschrijving_nl} · <strong>Open</strong>
            </li>
          ))}
        </ul>
      ) : !oud && (
        <p>Dit manifest noemt geen controles na installatie.</p>
      )}
      <p className="text-sm text-muted-foreground">Zolang een controle open staat, is de app niet ‘gezond’.</p>
    </section>
  );
}

/** S-047 Installatiewizard: zeven stappen; alleen een bestaand plan-ID kan worden hervat. */
export function Installatiewizard({ planId }: { planId: string | null }) {
  const role = useRole();
  const router = useRouter();
  const nu = useNow(1000);
  const p = useBronlijst<InstallPlan>(planId ? `/api/v1/catalog/plans/${planId}` : null, "observed_at", 15_000);
  const propose = useAction<{ request_id?: unknown }>();
  const plan = p.data ?? null;
  const blok = plan ? planBlokkade(plan, nu) : null;
  const huidig = huidigeStap(plan, blok);
  const operator = hasRole(role, "operator");

  let reden: string | null = null;
  if (!planId) reden = "Kies eerst een app.";
  else if (!plan) reden = "Het plan is nog niet gelezen.";
  else if (p.stale) reden = "Een actuele lezing van het plan ontbreekt. Ververs de pagina.";
  else if (blok) reden = blok;
  else if (!operator) reden = "Alleen een operator of beheerder kan een voorstel maken.";
  else if (huidig !== 3) reden = "In deze stap is er niets meer voor te stellen.";

  const maakVoorstel = async () => {
    if (!plan || reden || propose.busy) return;
    const r = await propose.run(`/api/v1/catalog/plans/${plan.plan_id}/steps/${plan.step_id}/propose`);
    if (r && isUuid(r.request_id)) router.push(`/goedkeuringen/${r.request_id}`);
    else void p.reload();
  };

  let inhoud;
  if (!planId) {
    inhoud = (
      <Melding soort="nogniet" titel={CATALOGUS_NOG_NIET} data-testid="kies-app-nog-niet">
        <p>
          <strong>Bron:</strong> een leesroute in de Hub voor goedgekeurde manifests met versie-ID, parameterschema en controle vooraf. Tot
          die er is, kan de wizard geen app aanbieden en ook geen parameters of controle tonen.
        </p>
        <p>Een gestart installatieplan hervat je met zijn plan-ID.</p>
      </Melding>
    );
  } else if (p.error && !plan) {
    inhoud =
      p.error.status === 404 || p.error.code === "validation_error" ? (
        <Melding soort="onbekend" data-testid="plan-niet-gevonden">
          <p>Dit installatieplan is niet gevonden.</p>
        </Melding>
      ) : (
        <ErrorPanel vast={vasteFout} error={p.error} title="Plan ophalen mislukt" onRetry={() => void p.reload()} />
      );
  } else if (!plan) {
    inhoud = <Loading text="Plan ophalen…" />;
  } else {
    inhoud = (
      <>
        {p.stale ? (
          <Melding soort="onbekend" titel={p.bronTijd ? `Verouderd · stand van ${formatTime(p.bronTijd)}` : "Tijdstip van het plan onbekend"} data-testid="plan-verouderd">
            <p>Een actuele lezing van het plan en de controle vooraf ontbreekt.</p>
          </Melding>
        ) : null}
        {huidig === 2 ? (
          <Melding soort="gate" titel="Controle vooraf blokkeert" data-testid="controle-vooraf">
            <p>{blok}</p>
          </Melding>
        ) : null}
        {plan.request_id ? (
          <p>
            <Link href={`/goedkeuringen/${plan.request_id}`} className={buttonVariants({ variant: "secundair" })} data-testid="naar-goedkeuring">
              Naar het voorstel en de goedkeuring
            </Link>
          </p>
        ) : null}
        {huidig === 6 ? (
          <Melding soort="info" titel="Geïnstalleerd · controles na installatie staan open" data-testid="controles-open">
            <p>De installatie is teruggelezen. De app is pas gezond als de controles hieronder zijn afgerond.</p>
          </Melding>
        ) : null}
        <InstallatiePreview plan={plan} oud={p.stale} />
      </>
    );
  }

  return (
    <>
      <PageHeader
        title="App installeren"
        kruimel={[{ label: "Server", href: "/server" }, { label: "Apps", href: "/apps" }, { label: "Appstore", href: "/apps/catalogus" }, { label: "Installeren" }]}
        intro="Installeren gaat altijd via een voorstel met preview en goedkeuring, als standaard TrueNAS Custom App of officiële catalogusapp."
      />
      <div className="flex flex-col gap-4">
        <Stappen huidig={huidig} geblokkeerd={huidig === 2 || (huidig === 0 && !planId)} />
        <h2 className="text-xl" data-testid="wizard-stap">
          Stap {huidig + 1} van {STAPPEN.length}: {STAPPEN[huidig]}
        </h2>
        {!operator ? <RolMelding>Installeren kan pas vanaf de rol operator.</RolMelding> : null}
        {inhoud}
        {propose.error ? <ErrorPanel vast={vasteFout} error={propose.error} title="Voorstel maken mislukt" /> : null}
        <div data-actiebalk="" className="flex flex-col gap-2">
          <div className="flex flex-col-reverse gap-2 sm:flex-row">
            <Link href="/apps/catalogus" className={buttonVariants({ variant: "stil" })}>
              Annuleren
            </Link>
            <Button variant="primair" uit={Boolean(reden)} bezig={propose.busy} aria-describedby={reden ? "volgende-reden" : undefined} onClick={() => void maakVoorstel()} data-testid="wizard-volgende">
              Volgende: voorstel maken
            </Button>
          </div>
          {reden ? (
            <p id="volgende-reden" className="text-sm" data-testid="volgende-reden">
              {reden}
            </p>
          ) : null}
        </div>
      </div>
    </>
  );
}
