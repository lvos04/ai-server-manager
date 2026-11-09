"use client";

import { buttonVariants } from "@/components/ui/button";
import Link from "next/link";
import { ErrorPanel } from "@/components/ErrorPanel";
import { Loading } from "@/components/Loading";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { Melding } from "@/components/Melding";
import { formatDateTime } from "@/lib/format";
import { decisionStatus, gateStatus, type StatusView } from "@/lib/status";
import type { DecisionList, Gate, TrueNasStatus } from "@/lib/types";
import { useApi } from "@/lib/use-api";

export function truenasView(t: TrueNasStatus | undefined): StatusView {
  if (!t) return { tone: "unknown", label: "Onbekend" };
  if (!t.nas_url) return { tone: "neutral", label: "NAS-adres ontbreekt", icon: "open" };
  if (!t.api_key.ingesteld) return { tone: "neutral", label: "Key ontbreekt", icon: "open" };
  // Een geslaagde verbindingstest is geen gezondheid: neutraal (OB-03).
  if (t.laatste_test?.status === "ok") return { tone: "neutral", label: "Verbonden (alleen-lezen)", icon: "gekoppeld" };
  if (t.laatste_test) return { tone: "down", label: "Verbinding mislukt" };
  return { tone: "neutral", label: "Nog niet getest", icon: "open" };
}

export function OnboardingScreen() {
  const decisions = useApi<DecisionList>("/api/v1/decisions");
  const truenas = useApi<TrueNasStatus>("/api/v1/truenas");
  const gates = useApi<{ items: Gate[]; toelichting: string }>("/api/v1/gates");
  const items = decisions.data?.items ?? [];
  const tested = items.filter((d) => d.status === "Getest").length;
  const pct = items.length ? Math.round((tested / items.length) * 100) : 0;

  return (
    <>
      <PageHeader
        title="Onboarding"
        intro="Leg de achttien besluiten over je NAS vast (D01–D18). Niets wordt aangenomen: je vult zelf in of laat de Hub alleen-lezen meten. ‘Getest’ ontstaat alleen door een echte meting of een vastgelegd bewijs."
      />
      <div className="stack">
        {decisions.error ? <ErrorPanel error={decisions.error} onRetry={() => void decisions.reload()} /> : null}
        <section className="card stack" aria-labelledby="voortgang">
          <h2 id="voortgang">Voortgang</h2>
          {decisions.data ? (
            <>
              <div
                className="progress"
                role="progressbar"
                aria-label="Besluiten getest"
                aria-valuemin={0}
                aria-valuemax={items.length}
                aria-valuenow={tested}
                aria-valuetext={`${tested} van ${items.length} besluiten getest`}
              >
                <span style={{ width: `${pct}%` }} />
              </div>
              <p data-testid="voortgang-tekst">
                {tested} van {items.length} besluiten getest.{" "}
                {Object.entries(decisions.data.telling)
                  .map(([k, v]) => `${k}: ${v}`)
                  .join(" · ")}
              </p>
            </>
          ) : (
            <Loading />
          )}
        </section>

        <ol className="steps">
          <li>
            <section className="card" aria-labelledby="stap-account">
              <div className="stat-head">
                <h2 id="stap-account" className="step-title">
                  Beheerder aanmaken
                </h2>
                <StatusBadge view={{ tone: "neutral", label: "Klaar", icon: "geslaagd" }} />
              </div>
              <p className="meta">Gedaan met de setupcode uit de app-log. Extra gebruikers beheer je onder Instellingen.</p>
            </section>
          </li>
          <li>
            <section className="card" aria-labelledby="stap-truenas">
              <div className="stat-head">
                <h2 id="stap-truenas" className="step-title">
                  TrueNAS koppelen (alleen-lezen)
                </h2>
                <StatusBadge view={truenasView(truenas.data)} />
              </div>
              <p>NAS-adres (D03), een alleen-lezen-API-key, de verbindingstest en zo nodig de certificaat-vingerafdruk.</p>
              <p>
                <Link className={buttonVariants({ variant: "primair" })} href="/onboarding/truenas">
                  TrueNAS-koppeling
                </Link>
              </p>
            </section>
          </li>
          <li>
            <section className="card" aria-labelledby="stap-besluiten">
              <h2 id="stap-besluiten" className="step-title">
                Besluiten D01–D18
              </h2>
              {items.length ? (
                <ul className="plain-list link-list" data-testid="besluitenlijst">
                  {items.map((d) => (
                    <li key={d.id}>
                      <Link href={`/onboarding/besluit/${d.id}`} data-testid={`besluit-${d.id}`}>
                        <span>
                          {d.id} — {d.titel}
                          <br />
                          <span className="meta" style={{ fontWeight: 400 }}>
                            {d.gate}
                            {d.meetbaar ? " · meetbaar via TrueNAS" : ""}
                          </span>
                        </span>
                        <StatusBadge view={decisionStatus(d.status)} />
                      </Link>
                    </li>
                  ))}
                </ul>
              ) : null}
            </section>
          </li>
          <li>
            <section className="card" aria-labelledby="stap-executor">
              <div className="stat-head">
                <h2 id="stap-executor" className="step-title">
                  Executor installeren en koppelen
                </h2>
                <StatusBadge view={{ tone: "not_yet", label: "Schrijfsleutel: op de executorpagina" }} />
              </div>
              <p>
                Uitleg over de tweede Custom App en de koppelcode. De schrijfsleutel voor TrueNAS vul je alleen op de
                statuspagina van de executor in; de Hub ziet hem nooit.
              </p>
              <p>
                <Link className={buttonVariants({ variant: "secundair" })} href="/onboarding/executor">
                  Uitleg executor
                </Link>
              </p>
            </section>
          </li>
        </ol>

        <section className="card stack" aria-labelledby="gates" data-testid="gates">
          <h2 id="gates">Wat mag nu? (gates)</h2>
          <p className="meta">{gates.data?.toelichting ?? "Onbekend telt nooit als groen; gates kunnen niet worden weggeklikt."}</p>
          {gates.error ? <ErrorPanel error={gates.error} /> : null}
          {gates.data ? (
            <ul className="m-0 flex list-none flex-col gap-3 p-0" aria-label="Gates en hun status">
              {gates.data.items.map((g) => (
                <li key={g.id} data-testid={`gate-${g.id}`}>
                  {g.status === "toegestaan" ? (
                    <div className="flex flex-col gap-1 rounded-lg border border-border p-3">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <strong>{g.naam}</strong>
                        <StatusBadge view={gateStatus(g.status)} />
                      </div>
                      <p className="text-sm">Alle voorwaarden aangetoond.</p>
                    </div>
                  ) : g.status === "geblokkeerd" ? (
                    <Melding soort="gate" titel={`Geblokkeerd door de ${g.naam.toLowerCase()}`}>
                      <p>Nodig: {g.redenen.map((r) => r.tekst).join(" ") || "voorwaarden aantonen."}</p>
                      <p className="text-sm">Dit is geen storing; er wacht een voorwaarde. Doorgaan zonder kan niet.</p>
                    </Melding>
                  ) : (
                    <Melding soort="onbekend" titel={`${g.naam}: onbekend — blijft dicht`}>
                      <p>{g.redenen.map((r) => r.tekst).join(" ") || "Status niet vast te stellen; onbekend opent nooit."}</p>
                    </Melding>
                  )}
                </li>
              ))}
            </ul>
          ) : null}
          {gates.data?.items[0] ? <p className="meta">Afgeleid op {formatDateTime(gates.data.items[0].afgeleid_op)}.</p> : null}
        </section>
      </div>
    </>
  );
}
