"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";
import { ErrorPanel } from "@/components/ErrorPanel";
import { Field } from "@/components/Field";
import { Loading } from "@/components/Loading";
import { PageHeader } from "@/components/PageHeader";
import { RefreshInventory } from "@/components/RefreshInventory";
import { StatusBadge } from "@/components/StatusBadge";
import { apiRequest, HubApiError } from "@/lib/api";
import { formatDateTime, orUnknown } from "@/lib/format";
import { serverErrors, translateValidation } from "@/lib/schema-form";
import { hasRole, useRole } from "@/lib/session";
import { decisionStatus, measurementStatus } from "@/lib/status";
import type { Decision, Measurement, TrueNasStatus, TrueNasTest } from "@/lib/types";
import { useApi } from "@/lib/use-api";
import { truenasView } from "../OnboardingScreen";
import { Button } from "@/components/ui/button";

function asError(e: unknown): HubApiError {
  return e instanceof HubApiError ? e : new HubApiError(0, "onbekend", String(e));
}

const QUICK_MEASURE = [
  { id: "D01", label: "TrueNAS-versie" },
  { id: "D03", label: "NAS-adres en aanmelding" },
  { id: "D06", label: "Pool-gezondheid" },
  { id: "D07", label: "Huidige appversies" },
];

export function TrueNasScreen() {
  const role = useRole();
  const isAdmin = hasRole(role, "admin");
  const isOperator = hasRole(role, "operator");
  const conn = useApi<TrueNasStatus>("/api/v1/truenas");
  const d03 = useApi<Decision>("/api/v1/decisions/D03");
  const [test, setTest] = useState<TrueNasTest | null>(null);
  const [testError, setTestError] = useState<HubApiError | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const reloadAll = async () => {
    await Promise.all([conn.reload(), d03.reload()]);
  };

  const runTest = async () => {
    setBusy("test");
    setTestError(null);
    try {
      const { data } = await apiRequest<TrueNasTest>("/api/v1/truenas/test", { method: "POST" });
      setTest(data);
      await conn.reload();
    } catch (e) {
      setTestError(asError(e));
    } finally {
      setBusy(null);
    }
  };

  if (conn.loading && !conn.data) return <Loading />;
  const c = conn.data;
  const fingerprint = test?.reason_code === "tls_untrusted" ? String(test.details.fingerprint_weergave ?? "") : "";

  return (
    <>
      <PageHeader
        title="TrueNAS koppelen (alleen-lezen)"
        intro="De Hub leest je NAS uit met een aparte alleen-lezen-gebruiker. Hij kan daarmee niets wijzigen; een key met schrijfrechten wordt geweigerd."
        actions={<StatusBadge view={truenasView(c)} testId="koppeling-status" />}
      />
      <p>
        <Link href="/onboarding">← Terug naar de onboarding</Link>
      </p>
      {conn.error ? <ErrorPanel error={conn.error} onRetry={() => void conn.reload()} /> : null}
      <ol className="steps">
        <li>
          <AddressStep decision={d03.data} etag={d03.etag} error={d03.error} canEdit={isAdmin} nasUrl={c?.nas_url ?? null} onSaved={reloadAll} />
        </li>
        <li>
          <KeyStep status={c} canEdit={isAdmin} onSaved={reloadAll} />
        </li>
        <li>
          <section className="card" aria-labelledby="stap-test" data-testid="stap-test">
            <h2 id="stap-test" className="step-title">
              Verbinding testen
            </h2>
            <p>Controleert TLS, aanmelden met de key, de rechten van de key, de TrueNAS-versie en welke API-methoden er zijn.</p>
            {c?.laatste_test ? (
              <p className="meta">
                Laatste test {formatDateTime(c.laatste_test.op)}: {c.laatste_test.status === "ok" ? "geslaagd" : `niet geslaagd (${orUnknown(c.laatste_test.reason_code)})`}
              </p>
            ) : null}
            {isOperator ? (
              <div className="row">
                <Button
                 
                  variant="primair"
                  onClick={() => void runTest()}
                  uit={busy !== null || !c?.nas_url}
                  data-testid="verbinding-testen"
                >
                  {busy === "test" ? "Bezig met testen…" : "Verbinding testen"}
                </Button>
                {!c?.nas_url ? <span className="meta">Vul eerst het NAS-adres in.</span> : null}
              </div>
            ) : (
              <p className="meta">Testen kan vanaf de rol operator.</p>
            )}
            {testError ? <ErrorPanel error={testError} title="Test mislukt" /> : null}
            {test ? <TestResult test={test} /> : null}
          </section>
        </li>
        {fingerprint || c?.tls.vingerafdruk ? (
          <li>
            <TrustStep
              presented={fingerprint || null}
              pinned={c?.tls.vingerafdruk ?? null}
              pinnedBy={c?.tls.bevestigd_door ?? null}
              pinnedAt={c?.tls.bevestigd_op ?? null}
              canEdit={isAdmin}
              onTrusted={async () => {
                await conn.reload();
                await runTest();
              }}
              onUntrusted={async () => {
                setTest(null);
                await conn.reload();
              }}
            />
          </li>
        ) : null}
        <li>
          <section className="card" aria-labelledby="stap-meten" data-testid="stap-meten">
            <h2 id="stap-meten" className="step-title">
              Inventaris ophalen en meten
            </h2>
            {c?.laatste_test?.status === "ok" ? (
              <div className="stack">
                <p>De koppeling werkt. Haal de inventaris op en laat de meetbare besluiten meten (alleen-lezen).</p>
                <RefreshInventory onDone={() => void conn.reload()} />
                {isOperator ? <QuickMeasure /> : null}
                <p>
                  <Link href="/server">Naar de Server-inventaris</Link> ·{" "}
                  <Link href="/onboarding/besluit/D02">D02 (pools en datasets kiezen)</Link>
                </p>
              </div>
            ) : (
              <p className="meta">Beschikbaar zodra de verbindingstest geslaagd is.</p>
            )}
          </section>
        </li>
      </ol>
    </>
  );
}

function AddressStep({
  decision,
  etag,
  error,
  canEdit,
  nasUrl,
  onSaved,
}: {
  decision: Decision | undefined;
  etag: string | null;
  error: HubApiError | undefined;
  canEdit: boolean;
  nasUrl: string | null;
  onSaved: () => Promise<void>;
}) {
  const current = (decision?.waarde ?? {}) as { nas_adres?: string; https_poort?: number | null };
  const [adres, setAdres] = useState<string | null>(null);
  const [poort, setPoort] = useState<string | null>(null);
  const [errs, setErrs] = useState<Record<string, string>>({});
  const [saveError, setSaveError] = useState<HubApiError | null>(null);
  const [busy, setBusy] = useState(false);
  const adresValue = adres ?? current.nas_adres ?? "";
  const poortValue = poort ?? (current.https_poort ? String(current.https_poort) : "");

  const save = async (ev: FormEvent) => {
    ev.preventDefault();
    setSaveError(null);
    const e: Record<string, string> = {};
    const a = adresValue.trim();
    if (!a) e.nas_adres = "Vul het adres in waarmee je de TrueNAS-web-UI opent.";
    else if (/^[a-z]+:\/\//i.test(a) || a.includes("/")) e.nas_adres = "Alleen het adres, zonder https:// en zonder pad.";
    let p: number | null = null;
    if (poortValue.trim()) {
      p = Number(poortValue.trim());
      if (!Number.isInteger(p) || p < 1 || p > 65535) e.https_poort = "Een poort is een getal van 1 tot en met 65535.";
    }
    setErrs(e);
    if (Object.keys(e).length) return;
    setBusy(true);
    try {
      const base = decision?.status === "Ingevuld" || decision?.status === "Getest" ? (decision.waarde ?? {}) : {};
      await apiRequest(`/api/v1/decisions/D03/waarde`, {
        method: "PUT",
        body: { waarde: { ...base, nas_adres: a, https_poort: p } },
        ifMatch: etag,
      });
      setAdres(null);
      setPoort(null);
      await onSaved();
    } catch (err) {
      const he = asError(err);
      const se = serverErrors(he.details);
      setErrs(se);
      setSaveError(he);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="card" aria-labelledby="stap-adres" data-testid="stap-adres">
      <div className="stat-head">
        <h2 id="stap-adres" className="step-title">
          NAS-adres (besluit D03)
        </h2>
        {decision ? <StatusBadge view={decisionStatus(decision.status)} /> : null}
      </div>
      <p>
        Het adres waarmee jij de TrueNAS-web-UI opent. De Hub neemt nooit een adres aan. Overige netwerkgegevens van D03
        (hostnamen, VPN, open poorten) vul je in bij <Link href="/onboarding/besluit/D03">besluit D03</Link>.
      </p>
      {error ? <ErrorPanel error={error} /> : null}
      {nasUrl ? (
        <p className="meta">
          De Hub verbindt met: <code data-testid="nas-url">{nasUrl}</code>
        </p>
      ) : null}
      {canEdit ? (
        <form className="form" onSubmit={(ev) => void save(ev)} noValidate>
          <Field id="nas-adres" label="NAS-adres (LAN-IP of hostnaam)" help="Zonder https://, zonder poort en zonder pad." error={errs.nas_adres ? translateValidation(errs.nas_adres) : undefined}>
            {(a) => (
              <input {...a} type="text" autoComplete="off" autoCapitalize="none" spellCheck={false} value={adresValue} onChange={(e) => setAdres(e.target.value)} />
            )}
          </Field>
          <Field id="https-poort" label="HTTPS-poort (optioneel)" help="Alleen invullen als TrueNAS niet op de standaard-HTTPS-poort draait." error={errs.https_poort}>
            {(a) => <input {...a} type="text" inputMode="numeric" autoComplete="off" value={poortValue} onChange={(e) => setPoort(e.target.value)} />}
          </Field>
          {saveError ? <ErrorPanel error={saveError} title="Opslaan mislukt" /> : null}
          <div className="row">
            <Button type="submit" variant="primair" bezig={busy} data-testid="adres-opslaan">
              {busy ? "Opslaan…" : "Adres opslaan"}
            </Button>
          </div>
        </form>
      ) : (
        <p className="meta">Alleen een beheerder kan het adres instellen.</p>
      )}
    </section>
  );
}

function KeyStep({ status, canEdit, onSaved }: { status: TrueNasStatus | undefined; canEdit: boolean; onSaved: () => Promise<void> }) {
  const [key, setKey] = useState("");
  const [error, setError] = useState<HubApiError | null>(null);
  const [busy, setBusy] = useState(false);
  const save = async (ev: FormEvent) => {
    ev.preventDefault();
    setError(null);
    if (key.trim().length < 16) {
      setError(new HubApiError(422, "invoer_onvolledig", "Een TrueNAS-API-key is langer; plak de volledige key."));
      return;
    }
    setBusy(true);
    try {
      await apiRequest("/api/v1/truenas/api-key", { method: "PUT", body: { api_key: key.trim() } });
      setKey("");
      await onSaved();
    } catch (e) {
      setError(asError(e));
    } finally {
      setBusy(false);
    }
  };
  const k = status?.api_key;
  return (
    <section className="card" aria-labelledby="stap-key" data-testid="stap-key">
      <div className="stat-head">
        <h2 id="stap-key" className="step-title">
          Alleen-lezen-gebruiker en API-key
        </h2>
        <StatusBadge view={k?.ingesteld ? { tone: "neutral", label: `Ingesteld (…${k.laatste4 ?? "????"})`, icon: "ingesteld" } : { tone: "neutral", label: "Niet ingesteld", icon: "open" }} />
      </div>
      <details>
        <summary className="flex min-h-touch cursor-pointer items-center font-semibold">
          Zo maak je in de TrueNAS-web-UI een alleen-lezen-gebruiker en API-key
        </summary>
        <ol className="howto">
          <li>
            Ga naar <strong>Credentials → Users</strong> en kies <strong>Add</strong>. Maak een aparte gebruiker alleen voor de
            Hub: geen wachtwoord-login nodig, geen shell, geen sudo, geen toegang tot shares.
          </li>
          <li>
            Geef deze gebruiker alleen de rol <strong>Read-only Administrator</strong> (<code>READONLY_ADMIN</code>). Afhankelijk
            van je TrueNAS-versie doe je dat bij de gebruiker zelf of via <strong>Credentials → Groups/Privileges</strong>.
          </li>
          <li>
            Ga naar <strong>Credentials → API Keys</strong> (in sommige versies via het gebruikersmenu rechtsboven), kies{" "}
            <strong>Add</strong>, selecteer de nieuwe gebruiker en maak de key aan.
          </li>
          <li>Kopieer de key meteen: TrueNAS toont hem maar één keer. Plak hem hieronder.</li>
        </ol>
        <p className="meta">
          Menunamen verschillen per TrueNAS-versie; deze stappen zijn niet op jouw versie gecontroleerd. De Hub controleert zelf
          na het koppelen of de key alleen leesrechten heeft en weigert een key met schrijfrechten.
        </p>
      </details>
      {k?.ingesteld ? (
        <p className="meta" data-testid="key-status">
          Ingesteld: eindigt op <code>{k.laatste4}</code>, op {formatDateTime(k.ingesteld_op)} door {orUnknown(k.ingesteld_door)}. De
          Hub toont de key nooit terug; hij staat versleuteld in de vault.
        </p>
      ) : null}
      {canEdit ? (
        <form className="form" onSubmit={(ev) => void save(ev)} noValidate>
          <Field id="api-key" label={k?.ingesteld ? "Nieuwe API-key (vervangt de huidige)" : "API-key (alleen-lezen)"}>
            {(a) => (
              <input
                {...a}
                type="password"
                autoComplete="off"
                autoCapitalize="none"
                spellCheck={false}
                value={key}
                onChange={(e) => setKey(e.target.value)}
              />
            )}
          </Field>
          {error ? <ErrorPanel error={error} title="Key opslaan mislukt" /> : null}
          <div className="row">
            <Button type="submit" variant="primair" bezig={busy} data-testid="key-opslaan">
              {busy ? "Opslaan…" : "Key opslaan"}
            </Button>
          </div>
        </form>
      ) : (
        <p className="meta">Alleen een beheerder kan de key instellen.</p>
      )}
    </section>
  );
}

function TestResult({ test }: { test: TrueNasTest }) {
  // TestResultaat (C-58): een geslaagde test is neutraal (geen gezondheid); mislukt = gemeten falen.
  return (
    <div
      className={
        test.verbonden
          ? "flex flex-col gap-2 rounded-lg border-2 border-border-strong bg-card p-4"
          : "flex flex-col gap-2 rounded-lg border-2 border-down bg-down-bg p-4 text-down-ink"
      }
      role="status"
      data-testid="test-resultaat"
      data-reason={test.reason_code ?? "ok"}
    >
      <p className="flex flex-wrap items-center gap-2">
        <StatusBadge view={test.verbonden ? { tone: "neutral", label: "Verbonden", icon: "geslaagd" } : { tone: "down", label: "Niet verbonden" }} /> {test.melding}
      </p>
      {test.advies ? <p>{test.advies}</p> : null}
      <dl className="kv">
        <dt>Adres</dt>
        <dd>{test.nas_url ? <code>{test.nas_url}</code> : "onbekend"}</dd>
        {test.reason_code ? (
          <>
            <dt>Reden</dt>
            <dd>
              <code>{test.reason_code}</code>
            </dd>
          </>
        ) : null}
        <dt>TrueNAS-versie</dt>
        <dd>{orUnknown(test.nas_versie)}</dd>
        <dt>Rechten van de key</dt>
        <dd>{test.key_scope === "alleen_lezen" ? "alleen-lezen" : orUnknown(test.key_scope)}</dd>
        <dt>TLS</dt>
        <dd>{test.tls_modus === "pinned" ? "bevestigde vingerafdruk" : orUnknown(test.tls_modus)}</dd>
        <dt>Getest op</dt>
        <dd>{formatDateTime(test.getest_op)}</dd>
      </dl>
      {test.capabilities ? (
        <details>
          <summary className="flex min-h-touch cursor-pointer items-center">Gevonden leesmethoden ({test.capabilities.bron})</summary>
          <ul>
            {Object.entries(test.capabilities.lezen).map(([k, v]) => (
              <li key={k}>
                {k}: {v ? <code>{v}</code> : "niet beschikbaar"}
              </li>
            ))}
          </ul>
        </details>
      ) : null}
    </div>
  );
}

function TrustStep({
  presented,
  pinned,
  pinnedBy,
  pinnedAt,
  canEdit,
  onTrusted,
  onUntrusted,
}: {
  presented: string | null;
  pinned: string | null;
  pinnedBy: string | null;
  pinnedAt: string | null;
  canEdit: boolean;
  onTrusted: () => Promise<void>;
  onUntrusted: () => Promise<void>;
}) {
  const [checked, setChecked] = useState(false);
  const [error, setError] = useState<HubApiError | null>(null);
  const [busy, setBusy] = useState(false);

  const trust = async () => {
    if (!presented) return;
    setBusy(true);
    setError(null);
    try {
      await apiRequest("/api/v1/truenas/tls/trust", { method: "POST", body: { fingerprint_sha256: presented } });
      setChecked(false);
      await onTrusted();
    } catch (e) {
      setError(asError(e));
    } finally {
      setBusy(false);
    }
  };
  const untrust = async () => {
    setBusy(true);
    setError(null);
    try {
      await apiRequest("/api/v1/truenas/tls/untrust", { method: "POST" });
      await onUntrusted();
    } catch (e) {
      setError(asError(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="card stack" aria-labelledby="stap-tls" data-testid="stap-tls">
      <h2 id="stap-tls" className="step-title">
        Certificaat-vingerafdruk bevestigen
      </h2>
      {presented ? (
        <>
          <p>
            TrueNAS gebruikt een certificaat dat deze Hub niet kent (vaak het standaard zelfondertekende certificaat). De Hub
            stuurt de API-key pas als jij bevestigt dat dit het certificaat van <strong>jouw</strong> NAS is.
          </p>
          <p>
            <strong>SHA-256-vingerafdruk die de NAS nu aanbiedt:</strong>
          </p>
          <p className="fingerprint" data-testid="vingerafdruk">
            {presented}
          </p>
          <ol className="howto">
            <li>Open de TrueNAS-web-UI in je browser op hetzelfde adres.</li>
            <li>
              Klik op het slotje of ‘Niet veilig’ naast het adres → certificaat bekijken → <strong>SHA-256-vingerafdruk</strong>. In
              TrueNAS zelf staat het certificaat onder <strong>Credentials → Certificates</strong>.
            </li>
            <li>Vergelijk teken voor teken. Wijkt er iets af, bevestig dan niet: er zit mogelijk iets tussen jou en de NAS.</li>
          </ol>
          {canEdit ? (
            <>
              <label className="choice">
                <input type="checkbox" checked={checked} onChange={(e) => setChecked(e.target.checked)} data-testid="vingerafdruk-gecontroleerd" />
                <span>Ik heb de vingerafdruk vergeleken en hij is exact gelijk.</span>
              </label>
              <div className="row">
                <Button variant="primair" uit={!checked || busy} onClick={() => void trust()} data-testid="vingerafdruk-vertrouwen">
                  {busy ? "Bezig…" : "Dit certificaat vertrouwen"}
                </Button>
              </div>
            </>
          ) : (
            <p className="meta">Alleen een beheerder kan een certificaat vertrouwen.</p>
          )}
        </>
      ) : null}
      {pinned ? (
        <div className="stack" style={{ gap: 8 }}>
          <p>
            <StatusBadge view={{ tone: "info", label: "Vertrouwd certificaat" }} /> Bevestigd door {orUnknown(pinnedBy)} op {formatDateTime(pinnedAt)}:
          </p>
          <p className="fingerprint">{pinned}</p>
          {canEdit ? (
            <div className="row">
              <Button variant="gevaar" bezig={busy} onClick={() => void untrust()}>
                Vertrouwen intrekken
              </Button>
            </div>
          ) : null}
        </div>
      ) : null}
      {error ? <ErrorPanel error={error} title="Vertrouwen mislukt" /> : null}
    </section>
  );
}

function QuickMeasure() {
  const [results, setResults] = useState<Record<string, Measurement | HubApiError>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const run = async (id: string) => {
    setBusy(id);
    try {
      const { data } = await apiRequest<{ meting: Measurement }>(`/api/v1/decisions/${id}/meting`, { method: "POST" });
      setResults((r) => ({ ...r, [id]: data.meting }));
    } catch (e) {
      setResults((r) => ({ ...r, [id]: asError(e) }));
    } finally {
      setBusy(null);
    }
  };
  return (
    <div className="stack" style={{ gap: 8 }} data-testid="snel-meten">
      <h3>Meetbare besluiten</h3>
      <ul className="plain-list">
        {QUICK_MEASURE.map((q) => {
          const r = results[q.id];
          return (
            <li key={q.id} className="row" style={{ justifyContent: "space-between" }}>
              <span>
                <Link href={`/onboarding/besluit/${q.id}`}>{q.id}</Link> — {q.label}
                {r instanceof HubApiError ? <span className="error"> {r.message}</span> : r ? <span className="meta"> {r.melding}</span> : null}
              </span>
              <span className="row">
                {r && !(r instanceof HubApiError) ? <StatusBadge view={measurementStatus(r.status)} /> : null}
                <Button variant="secundair" onClick={() => void run(q.id)} bezig={busy !== null} data-testid={`meet-${q.id}`}>
                  {busy === q.id ? "Meten…" : `Meet ${q.id}`}
                </Button>
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
