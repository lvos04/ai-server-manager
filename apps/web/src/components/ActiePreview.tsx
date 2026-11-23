import type { ReactNode } from "react";
import { diffRegels, doelVelden, RISICO_WOORD, risicoKlasse, type ActieVerzoek, type DiffRegel, type RisicoKlasse } from "@/lib/acties";
import { cn } from "@/lib/utils";
import { Aftellen } from "./Aftellen";
import { shortDigest } from "./KopieerVeld";
import { Melding } from "./Melding";

const RISICO_CLS: Record<RisicoKlasse, string> = {
  R0: "border-risk-0 bg-risk-0-bg text-risk-0-ink",
  R1: "border-risk-1 bg-risk-1-bg text-risk-1-ink",
  R2: "border-risk-2 bg-risk-2-bg text-risk-2-ink",
  R3: "border-risk-3 bg-risk-3-bg text-risk-3-ink",
};
const CODE_CLS: Record<RisicoKlasse, string> = {
  R0: "bg-risk-0-solid text-risk-0-on-solid",
  R1: "bg-risk-1-solid text-risk-1-on-solid",
  R2: "bg-risk-2-solid text-risk-2-on-solid",
  R3: "bg-risk-3-solid text-risk-3-on-solid",
};

/** RisicoBadge (C-08): treden-glyph + code + vast woord; nooit statuskleur. Onbekende klasse = "Risico onbekend". */
export function RisicoBadge({ klasse }: { klasse: string | null | undefined }) {
  const k = risicoKlasse(klasse);
  if (!k) {
    return (
      <span className="inline-flex min-h-8 w-fit items-center rounded-sm border-2 border-dashed border-unknown bg-unknown-bg px-2 text-sm font-semibold text-unknown-ink" data-risico="onbekend">
        Risico onbekend
      </span>
    );
  }
  const niveau = Number(k[1]);
  return (
    <span className={cn("inline-flex w-fit max-w-full items-stretch overflow-hidden rounded-sm border-2 text-sm font-semibold", RISICO_CLS[k])} data-risico={k}>
      <span className={cn("inline-flex items-center gap-1 px-1.5 font-mono", CODE_CLS[k])}>
        <svg width="19" height="16" viewBox="0 0 19 16" aria-hidden="true" focusable="false">
          {[5, 8, 11, 14].map((h, i) => (
            <rect key={h} x={i * 5} y={16 - h} width="4" height={h} fill="currentColor" opacity={i <= niveau ? 1 : 0.3} />
          ))}
        </svg>
        {k}
      </span>
      <span className="px-2 py-1">
        <span className="sr-only"> · </span>
        {RISICO_WOORD[k]}
      </span>
    </span>
  );
}

const RAND: Record<RisicoKlasse, string> = { R0: "border-risk-0", R1: "border-risk-1", R2: "border-risk-2", R3: "border-risk-3" };

const TEKEN: Record<DiffRegel["soort"], string> = { gewijzigd: "~", toegevoegd: "+", verwijderd: "−" };

/** DiffWeergave (C-20): Veld/Was/Wordt; teken aria-hidden met de soort als sr-tekst. Smal: Was en Wordt onder elkaar. */
export function DiffWeergave({ regels }: { regels: DiffRegel[] }) {
  if (!regels.length) return <p data-testid="diff-leeg">Geen veldwijzigingen in deze preview.</p>;
  return (
    <div className="flex flex-col gap-2">
      <p className="text-sm text-muted-foreground">
        Legenda: <span aria-hidden="true">~</span> gewijzigd · <span aria-hidden="true">+</span> toegevoegd · <span aria-hidden="true">−</span> verwijderd
      </p>
      <div role="table" aria-label="Wat verandert er" className="flex flex-col divide-y divide-border rounded-lg border border-border" data-testid="diff">
        <div role="row" className="hidden grid-cols-[2rem_minmax(0,1fr)_minmax(0,1fr)_minmax(0,1fr)] gap-2 px-3 py-2 text-sm font-semibold md:grid">
          <span role="columnheader">
            <span className="sr-only">Soort</span>
          </span>
          <span role="columnheader">Veld</span>
          <span role="columnheader">Was</span>
          <span role="columnheader">Wordt</span>
        </div>
        {regels.map((r) => (
          <div role="row" key={`${r.soort}-${r.veld}`} className="grid grid-cols-[2rem_minmax(0,1fr)] gap-x-2 gap-y-1 px-3 py-2 md:grid-cols-[2rem_minmax(0,1fr)_minmax(0,1fr)_minmax(0,1fr)]" data-diff={r.soort}>
            <span role="cell" className="font-mono font-bold">
              <span aria-hidden="true">{TEKEN[r.soort]}</span>
              <span className="sr-only">{r.soort}</span>
            </span>
            <span role="cell" className="font-mono font-bold break-all">
              {r.veld}
            </span>
            <span role="cell" className="col-start-2 break-all md:col-start-auto">
              <span className="text-sm text-muted-foreground md:sr-only">Was: </span>
              <span className={r.was !== undefined ? "bg-diff-old-bg text-diff-old-ink line-through" : ""}>{r.was ?? "(nieuw)"}</span>
            </span>
            <span role="cell" className="col-start-2 break-all md:col-start-auto">
              <span className="text-sm text-muted-foreground md:sr-only">Wordt: </span>
              <span className={r.wordt !== undefined ? "bg-diff-new-bg font-semibold text-diff-new-ink" : ""}>{r.wordt ?? "(verwijderd)"}</span>
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export const ONVEILIGE_DIFF = "Deze wijziging kan nog niet veilig worden weergegeven.";

function Feit({ label, children }: { label: string; children: ReactNode }) {
  return (
    <>
      <dt>{label}</dt>
      <dd>{children}</dd>
    </>
  );
}

const AANVRAGER: Record<string, string> = { user: "gebruiker", ai: "AI", flow: "flow", service: "dienst", system: "systeem" };

/**
 * ActiePreview (C-19): samenvatting, diff, verloop en veiligheid van één voorstel. Toont alleen getypte velden en vaste
 * teksten van het beleid; de vrije reden van het voorstel blijft buiten beeld. `kop` bepaalt het kopniveau.
 */
export function ActiePreview({ v, kop: Kop = "h2", verouderd, kinderen }: { v: ActieVerzoek; kop?: "h2" | "h3"; verouderd?: boolean; kinderen?: ReactNode }) {
  const k = risicoKlasse(v.risk_class);
  const claim = risicoKlasse(v.risk_claim);
  const { regels, onveilig, gevolgen } = diffRegels(v.preview);
  const backup = v.preview?.requires_backup;
  const herstelpunt = v.goedkeuring?.backup_checkpoint_id ?? null;
  return (
    <section
      className={cn("flex min-w-0 flex-col gap-4 rounded-lg border-2 bg-card p-4", k ? RAND[k] : "border-dashed border-unknown", verouderd && "arcering border-dashed")}
      aria-labelledby={`preview-${v.request_id}`}
      data-testid="actie-preview"
    >
      <p className="text-sm text-muted-foreground">
        Voorstel · <code>{v.action_id}</code> · aangevraagd door {AANVRAGER[v.actor.type] ?? "onbekend"}
      </p>
      <Kop id={`preview-${v.request_id}`} className="text-xl font-bold">
        {v.preview?.omschrijving ?? v.action_id}
      </Kop>
      <div className="flex flex-wrap items-center gap-3">
        <RisicoBadge klasse={v.risk_class} />
        {v.geldig_tot ? (
          <span className="text-sm">
            Voorstel geldig tot {new Date(v.geldig_tot).toLocaleTimeString("nl-NL", { hour: "2-digit", minute: "2-digit" })} (nog <Aftellen tot={v.geldig_tot} testId="aftellen-voorstel" />)
          </span>
        ) : null}
      </div>
      <details data-testid="waarom-klasse">
        <summary className="flex min-h-touch cursor-pointer items-center font-semibold">Waarom {k ?? "deze klasse"}?</summary>
        <dl className="kv pt-2">
          <Feit label="Regels">{v.rule_ids.length ? v.rule_ids.map((r) => <code key={r} className="mr-2">{r}</code>) : "geen"}</Feit>
          <Feit label="Beleid">
            <code title={v.policy_hash}>{shortDigest(v.policy_hash)}</code>
          </Feit>
        </dl>
        {claim && claim !== k ? (
          <p data-testid="risk-claim">
            De aanvrager stelde {claim} voor; het beleid bepaalt {k ?? "de klasse"}.
          </p>
        ) : null}
      </details>
      <div className="grid min-w-0 gap-4 xl:grid-cols-[minmax(0,1fr)_20rem]">
        <div className="flex min-w-0 flex-col gap-4">
          <div>
            <h3 className="text-base font-bold">Samenvatting</h3>
            <dl className="kv">
              <Feit label="Doel">
                <code>{doelVelden(v.target).map(([n, w]) => `${n}: ${w}`).join(" · ") || "onbekend"}</code>
              </Feit>
              <Feit label="Uitvoerder">{v.uitvoerder}</Feit>
              <Feit label="Kritiek doel">{v.preview?.kritiek === undefined ? "Onbekend" : v.preview.kritiek ? "ja" : "nee"}</Feit>
              <Feit label="Reikwijdte">Onbekend</Feit>
              <Feit label="Onderbreking">Onbekend</Feit>
            </dl>
          </div>
          <div>
            <h3 className="text-base font-bold">Wat verandert er</h3>
            {onveilig ? (
              <Melding soort="gate" data-testid="diff-onveilig">
                <p>{ONVEILIGE_DIFF}</p>
              </Melding>
            ) : (
              <DiffWeergave regels={regels} />
            )}
            {!onveilig && gevolgen?.length ? (
              <div className="pt-3" data-testid="diff-gevolgen">
                <h4 className="font-semibold">Wat er met de app en de data gebeurt</h4>
                <ul className="list-disc pl-6">
                  {gevolgen.map((g) => (
                    <li key={g}>{g}</li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
          <div>
            <h3 className="text-base font-bold">Zo verloopt het</h3>
            <ol data-genummerd="" className="flex flex-col gap-1 pl-6">
              {backup ? <li>Back-up: herstelpunt binden</li> : null}
              <li>Uitvoeren door {v.uitvoerder}</li>
              <li>Controle na uitvoering (readback)</li>
              <li>Klaar, of een incident bij een afwijking</li>
            </ol>
            <p className="text-sm text-muted-foreground">
              Dit zijn verwachte stappen. Pas na de controle (readback) staat er <em>Uitgevoerd en gecontroleerd</em>.
            </p>
          </div>
        </div>
        <aside aria-label="Veiligheid van dit voorstel" className="flex min-w-0 flex-col gap-2 rounded-lg bg-muted p-4">
          <dl className="kv">
            <Feit label="Back-up vereist">{backup === undefined ? "Onbekend" : backup ? "ja" : "nee"}</Feit>
            <Feit label="Herstelpunt">
              {herstelpunt ? <code className="break-all">{herstelpunt}</code> : backup ? "Nog niet gebonden" : "Niet nodig"}
            </Feit>
            <Feit label="Terugzetten">{v.preview?.terugdraaien ?? "Onbekend"}</Feit>
            <Feit label="Data">{v.preview?.dataretentie ?? "Onbekend"}</Feit>
            <Feit label="Gebonden aan">preview_hash, resource_etag en policy_hash</Feit>
          </dl>
        </aside>
      </div>
      {kinderen}
    </section>
  );
}
