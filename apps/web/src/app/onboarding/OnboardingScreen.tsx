"use client";

import Link from "next/link";
import { ErrorPanel } from "@/components/ErrorPanel";
import { Loading } from "@/components/Loading";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { TableWrap } from "@/components/TableWrap";
import { formatDateTime } from "@/lib/format";
import { decisionStatus, gateStatus, type StatusView } from "@/lib/status";
import type { DecisionList, Gate, TrueNasStatus } from "@/lib/types";
import { useApi } from "@/lib/use-api";

export function truenasView(t: TrueNasStatus | undefined): StatusView {
  if (!t) return { tone: "unknown", label: "Onbekend" };
  if (!t.nas_url) return { tone: "warn", label: "NAS-adres ontbreekt" };
  if (!t.api_key.ingesteld) return { tone: "warn", label: "Key ontbreekt" };
  if (t.laatste_test?.status === "ok") return { tone: "ok", label: "Verbonden (alleen-lezen)" };
  if (t.laatste_test) return { tone: "bad", label: "Verbinding mislukt" };
  return { tone: "warn", label: "Nog niet getest" };
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
                <StatusBadge view={{ tone: "ok", label: "Klaar" }} />
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
                <Link className="btn btn-primary" href="/onboarding/truenas">
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
                <StatusBadge view={{ tone: "neutral", label: "Koppelen volgt in P2" }} />
              </div>
              <p>Uitleg over de tweede Custom App. Het koppelen zelf is in deze versie nog niet mogelijk.</p>
              <p>
                <Link className="btn" href="/onboarding/executor">
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
            <TableWrap label="Gates en hun status">
              <table>
                <caption className="sr-only">Gates en hun status</caption>
                <thead>
                  <tr>
                    <th scope="col">Gate</th>
                    <th scope="col">Status</th>
                    <th scope="col">Waarom</th>
                  </tr>
                </thead>
                <tbody>
                  {gates.data.items.map((g) => (
                    <tr key={g.id}>
                      <td>{g.naam}</td>
                      <td>
                        <StatusBadge view={gateStatus(g.status)} />
                      </td>
                      <td>{g.redenen.length ? g.redenen.map((r) => r.tekst).join(" ") : "Alle voorwaarden aangetoond."}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </TableWrap>
          ) : null}
          {gates.data?.items[0] ? <p className="meta">Afgeleid op {formatDateTime(gates.data.items[0].afgeleid_op)}.</p> : null}
        </section>
      </div>
    </>
  );
}
