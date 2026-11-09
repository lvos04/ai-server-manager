"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";
import { ErrorPanel } from "@/components/ErrorPanel";
import { Field } from "@/components/Field";
import { Loading } from "@/components/Loading";
import { PageHeader } from "@/components/PageHeader";
import { SchemaForm } from "@/components/SchemaForm";
import { StatusBadge } from "@/components/StatusBadge";
import { ValueView } from "@/components/ValueView";
import { apiRequest, HubApiError } from "@/lib/api";
import { DECISION_HELP, EVIDENCE_KINDS } from "@/lib/decisions";
import { formatDateTime } from "@/lib/format";
import { describe, fromDraft, serverErrors, toDraft, type Draft, type Errors, type FieldNode } from "@/lib/schema-form";
import { hasRole, useRole } from "@/lib/session";
import { decisionStatus, measurementStatus, testResult } from "@/lib/status";
import type { Decision, Measurement } from "@/lib/types";
import { useApi } from "@/lib/use-api";

const BRON: Record<string, string> = { gebruiker: "ingevuld door de gebruiker", meting: "gemeten via TrueNAS", vast: "vast besluit" };

function asError(e: unknown): HubApiError {
  return e instanceof HubApiError ? e : new HubApiError(0, "onbekend", String(e));
}

export function DecisionScreen({ id, prev, next }: { id: string; prev?: string; next?: string }) {
  const role = useRole();
  const isAdmin = hasRole(role, "admin");
  const isOperator = hasRole(role, "operator");
  const { data: d, error, loading, etag, reload } = useApi<Decision>(`/api/v1/decisions/${id}`);
  const node: FieldNode | null = d?.schema ? describe(d.schema, d.schema) : null;
  const help = DECISION_HELP[id];

  const [draft, setDraft] = useState<Draft>(null);
  const [draftFor, setDraftFor] = useState<number | null>(null);
  const [errors, setErrors] = useState<Errors>({});
  const [saveError, setSaveError] = useState<HubApiError | null>(null);
  const [saved, setSaved] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [measure, setMeasure] = useState<Measurement | null>(null);
  const [measureError, setMeasureError] = useState<HubApiError | null>(null);

  // Invoer opnieuw opbouwen zodra er een nieuwe versie van het besluit is (na opslaan, meten of bewijs).
  if (node && d && draftFor !== d.version) {
    setDraftFor(d.version);
    setDraft(toDraft(node, d.waarde));
  }

  if (loading && !d) return <Loading />;
  if (error) return <ErrorPanel error={error} onRetry={() => void reload()} />;
  if (!d || !node) return null;

  const editable = isAdmin && !d.vast;

  const save = async (ev: FormEvent) => {
    ev.preventDefault();
    setSaveError(null);
    setSaved(null);
    const res = fromDraft(node, draft);
    setErrors(res.errors);
    if (Object.keys(res.errors).length) {
      setSaveError(new HubApiError(422, "invoer_onvolledig", "Controleer de gemarkeerde velden."));
      return;
    }
    setBusy("opslaan");
    try {
      await apiRequest<Decision>(`/api/v1/decisions/${id}/waarde`, { method: "PUT", body: { waarde: res.value }, ifMatch: etag });
      setSaved("Opgeslagen. Status: Ingevuld (nog niet getest).");
      setErrors({});
      await reload();
    } catch (e) {
      const err = asError(e);
      setErrors(serverErrors(err.details));
      setSaveError(err);
    } finally {
      setBusy(null);
    }
  };

  const runMeasure = async () => {
    setMeasureError(null);
    setMeasure(null);
    setBusy("meten");
    try {
      const { data } = await apiRequest<{ besluit: Decision; meting: Measurement }>(`/api/v1/decisions/${id}/meting`, { method: "POST" });
      setMeasure(data.meting);
      await reload();
    } catch (e) {
      setMeasureError(asError(e));
    } finally {
      setBusy(null);
    }
  };

  const lastMeasure = measure ?? d.laatste_meting;

  return (
    <>
      <PageHeader
        title={`${d.id} — ${d.titel}`}
        intro={d.wat_vastleggen}
        actions={<StatusBadge view={decisionStatus(d.status)} testId="besluit-status" />}
      />
      <nav className="row" aria-label="Besluiten" style={{ marginBottom: 16 }}>
        <Link className="btn" href="/onboarding">
          ← Overzicht
        </Link>
        {prev ? (
          <Link className="btn" href={`/onboarding/besluit/${prev}`}>
            Vorige ({prev})
          </Link>
        ) : null}
        {next ? (
          <Link className="btn" href={`/onboarding/besluit/${next}`}>
            Volgende ({next})
          </Link>
        ) : null}
      </nav>

      <div className="stack">
        <section className="card stack" aria-labelledby="uitleg">
          <h2 id="uitleg">Uitleg</h2>
          <dl className="kv">
            <dt>Gate</dt>
            <dd>{d.gate}</dd>
            {help ? (
              <>
                <dt>Waarom</dt>
                <dd>{help.waarom}</dd>
                <dt>Waar vind je het</dt>
                <dd>{help.waar}</dd>
                <dt>Wanneer ‘Getest’</dt>
                <dd>{help.hoe_getest}</dd>
              </>
            ) : null}
          </dl>
        </section>

        <section className="card stack" aria-labelledby="waarde" data-testid="huidige-waarde">
          <h2 id="waarde">Huidige waarde</h2>
          {d.waarde ? (
            <>
              <ValueView node={node} value={d.waarde} />
              <p className="meta">
                {d.waarde_bron ? BRON[d.waarde_bron] ?? d.waarde_bron : "bron onbekend"}
                {d.ingevuld_door ? ` · door ${d.ingevuld_door}` : ""}
                {d.ingevuld_op ? ` op ${formatDateTime(d.ingevuld_op)}` : ""}
                {d.getest_op ? ` · getest ${formatDateTime(d.getest_op)}${d.getest_door ? ` (${d.getest_door})` : ""}` : ""}
              </p>
            </>
          ) : (
            <p>Nog niet ingevuld. Er staat bewust geen voorbeeldwaarde.</p>
          )}
          {d.reden ? (
            <p>
              <strong>Reden ({d.status}):</strong> {d.reden}
            </p>
          ) : null}
          {d.vast ? <p className="notice tone-info">Dit is een vast besluit van de gebruiker en kan hier niet worden gewijzigd.</p> : null}
        </section>

        {d.meetbaar ? (
          <section className="card stack" aria-labelledby="meten" data-testid="sectie-meten">
            <h2 id="meten">Meten via TrueNAS (alleen-lezen)</h2>
            <p>De Hub leest dit besluit uit de TrueNAS-API met de alleen-lezen-key. Een geslaagde meting zet het besluit op Getest, met bewijs.</p>
            {isOperator ? (
              <div className="row">
                <button type="button" className="btn btn-primary" onClick={() => void runMeasure()} disabled={busy !== null} data-testid="meten">
                  {busy === "meten" ? "Bezig met meten…" : "Meten via TrueNAS"}
                </button>
                <Link href="/onboarding/truenas">TrueNAS-koppeling</Link>
              </div>
            ) : (
              <p className="meta">Meten kan vanaf de rol operator.</p>
            )}
            {measureError ? <ErrorPanel error={measureError} title="Meten mislukt" /> : null}
            {lastMeasure ? (
              <div className={`notice tone-${measurementStatus(lastMeasure.status).tone}`} role="status" data-testid="meting-resultaat">
                <p>
                  <StatusBadge view={measurementStatus(lastMeasure.status)} /> {lastMeasure.melding}
                </p>
                {lastMeasure.advies ? <p>{lastMeasure.advies}</p> : null}
                {lastMeasure.reason_code ? (
                  <p className="meta">
                    Reden: <code>{lastMeasure.reason_code}</code>
                  </p>
                ) : null}
                <MeasureDetails details={lastMeasure.details} />
                {lastMeasure.gemeten_op ? <p className="meta">Gemeten op {formatDateTime(lastMeasure.gemeten_op)}.</p> : null}
              </div>
            ) : null}
          </section>
        ) : null}

        {!d.vast ? (
          <section className="card stack" aria-labelledby="invullen" data-testid="sectie-invullen">
            <h2 id="invullen">{d.waarde ? "Waarde wijzigen" : "Invullen"}</h2>
            {!editable ? <p className="meta">Invullen kan alleen een beheerder.</p> : null}
            {d.status === "Getest" && editable ? (
              <p className="notice tone-warn">Let op: wijzigen zet het besluit terug op Ingevuld; de test hoorde bij de oude waarde.</p>
            ) : null}
            <form className="form" onSubmit={(ev) => void save(ev)} noValidate>
              <SchemaForm node={node} draft={draft} errors={errors} disabled={!editable || busy !== null} idPrefix={`w-${id}`} onChange={setDraft} />
              {saveError ? <ErrorPanel error={saveError} title="Opslaan mislukt" /> : null}
              <p role="status" aria-live="polite" className="meta" data-testid="opslaan-status">
                {saved ?? ""}
              </p>
              {editable ? (
                <div className="row">
                  <button type="submit" className="btn btn-primary" disabled={busy !== null} data-testid="opslaan">
                    {busy === "opslaan" ? "Opslaan…" : "Opslaan"}
                  </button>
                </div>
              ) : null}
            </form>
          </section>
        ) : null}

        {!d.vast && editable ? <EvidenceForm decision={d} onDone={reload} /> : null}
        {!d.vast && editable ? <StatusForm decision={d} etag={etag} onDone={reload} /> : null}

        <section className="card stack" aria-labelledby="bewijs" data-testid="bewijslijst">
          <h2 id="bewijs">Bewijs</h2>
          {d.bewijs.length ? (
            <ul className="plain-list">
              {[...d.bewijs].reverse().map((b) => (
                <li key={b.id} className="card" style={{ padding: 12 }}>
                  <div className="row" style={{ justifyContent: "space-between" }}>
                    <strong>{b.bron === "meting" ? `Meting${b.methode ? ` (${b.methode})` : ""}` : EVIDENCE_KINDS.find((k) => k.value === b.soort)?.label ?? b.soort}</strong>
                    <StatusBadge view={testResult(b.resultaat)} />
                  </div>
                  <p style={{ margin: "4px 0" }}>{b.omschrijving}</p>
                  <p className="meta" style={{ margin: 0 }}>
                    {b.referentie ? <>Referentie: <code>{b.referentie}</code> · </> : null}
                    uitgevoerd {formatDateTime(b.uitgevoerd_op)} · vastgelegd door {b.vastgelegd_door} op {formatDateTime(b.vastgelegd_op)} · hoort bij versie {b.hoort_bij_versie}
                  </p>
                </li>
              ))}
            </ul>
          ) : (
            <p>Nog geen bewijs.</p>
          )}
        </section>
      </div>
    </>
  );
}

function MeasureDetails({ details }: { details: Record<string, unknown> }) {
  const entries = Object.entries(details ?? {}).filter(([, v]) => v !== null && v !== undefined && !(Array.isArray(v) && v.length === 0));
  if (!entries.length) return null;
  return (
    <dl className="kv">
      {entries.map(([k, v]) => (
        <div key={k} style={{ display: "contents" }}>
          <dt>{k.replace(/_/g, " ")}</dt>
          <dd>{Array.isArray(v) ? v.map(String).join(", ") : typeof v === "object" ? JSON.stringify(v) : String(v)}</dd>
        </div>
      ))}
    </dl>
  );
}

function EvidenceForm({ decision, onDone }: { decision: Decision; onDone: () => Promise<void> }) {
  const [soort, setSoort] = useState("");
  const [omschrijving, setOmschrijving] = useState("");
  const [referentie, setReferentie] = useState("");
  const [resultaat, setResultaat] = useState("");
  const [datum, setDatum] = useState("");
  const [error, setError] = useState<HubApiError | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const allowed = decision.status === "Ingevuld" || decision.status === "Getest";

  const submit = async (ev: FormEvent) => {
    ev.preventDefault();
    setError(null);
    setOk(null);
    if (!soort || !resultaat || !datum || omschrijving.trim().length < 10) {
      setError(new HubApiError(422, "invoer_onvolledig", "Vul soort, resultaat, datum en een omschrijving van minstens 10 tekens in."));
      return;
    }
    setBusy(true);
    try {
      await apiRequest(`/api/v1/decisions/${decision.id}/bewijs`, {
        method: "POST",
        body: { soort, omschrijving: omschrijving.trim(), referentie: referentie.trim(), resultaat, uitgevoerd_op: datum },
      });
      setOk("Bewijs vastgelegd.");
      setOmschrijving("");
      setReferentie("");
      await onDone();
    } catch (e) {
      setError(asError(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="card stack" aria-labelledby="bewijs-vastleggen" data-testid="sectie-bewijs">
      <h2 id="bewijs-vastleggen">Bewijs vastleggen</h2>
      {!allowed ? (
        <p className="meta">Vul het besluit eerst in; bewijs hoort bij een ingevulde waarde.</p>
      ) : (
        <form className="form" onSubmit={(ev) => void submit(ev)} noValidate>
          <Field id={`bw-soort-${decision.id}`} label="Soort bewijs">
            {(a) => (
              <select {...a} value={soort} onChange={(e) => setSoort(e.target.value)}>
                <option value="">— maak een keuze —</option>
                {EVIDENCE_KINDS.map((k) => (
                  <option key={k.value} value={k.value}>
                    {k.label}
                  </option>
                ))}
              </select>
            )}
          </Field>
          <Field id={`bw-oms-${decision.id}`} label="Wat heb je gedaan en gezien?" help="Minstens 10 tekens. Geen geheimen.">
            {(a) => <textarea {...a} value={omschrijving} onChange={(e) => setOmschrijving(e.target.value)} />}
          </Field>
          <Field id={`bw-ref-${decision.id}`} label="Referentie (optioneel)" help="Bijv. bestandsnaam van een schermafbeelding of een ticketnummer.">
            {(a) => <input {...a} type="text" value={referentie} onChange={(e) => setReferentie(e.target.value)} />}
          </Field>
          <fieldset>
            <legend>Resultaat</legend>
            <div className="row" style={{ gap: 16 }}>
              {["geslaagd", "mislukt"].map((r) => (
                <label key={r} className="choice">
                  <input type="radio" name={`bw-res-${decision.id}`} value={r} checked={resultaat === r} onChange={() => setResultaat(r)} />
                  {r === "geslaagd" ? "Geslaagd" : "Mislukt"}
                </label>
              ))}
            </div>
          </fieldset>
          <Field id={`bw-datum-${decision.id}`} label="Uitgevoerd op">
            {(a) => <input {...a} type="date" value={datum} onChange={(e) => setDatum(e.target.value)} />}
          </Field>
          {error ? <ErrorPanel error={error} title="Vastleggen mislukt" /> : null}
          <p role="status" aria-live="polite" className="meta">
            {ok ?? ""}
          </p>
          <div className="row">
            <button type="submit" className="btn" disabled={busy}>
              {busy ? "Bezig…" : "Bewijs vastleggen"}
            </button>
          </div>
        </form>
      )}
    </section>
  );
}

function StatusForm({ decision, etag, onDone }: { decision: Decision; etag: string | null; onDone: () => Promise<void> }) {
  const [status, setStatus] = useState("");
  const [reden, setReden] = useState("");
  const [error, setError] = useState<HubApiError | null>(null);
  const [busy, setBusy] = useState(false);
  const options = [
    { value: "Geblokkeerd", label: "Geblokkeerd (met reden)" },
    ...(decision.nvt_toegestaan ? [{ value: "N.v.t.", label: "N.v.t. (met reden)" }] : []),
    { value: "Open", label: "Terug naar Open (waarde wissen)" },
  ];

  const submit = async (ev: FormEvent) => {
    ev.preventDefault();
    setError(null);
    if (!status) {
      setError(new HubApiError(422, "invoer_onvolledig", "Kies een status."));
      return;
    }
    setBusy(true);
    try {
      await apiRequest(`/api/v1/decisions/${decision.id}/status`, { method: "POST", body: { status, reden: reden.trim() }, ifMatch: etag });
      setStatus("");
      setReden("");
      await onDone();
    } catch (e) {
      setError(asError(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="card stack" aria-labelledby="status-wijzigen">
      <h2 id="status-wijzigen">Status wijzigen</h2>
      <p className="meta">‘Ingevuld’ en ‘Getest’ ontstaan alleen door invullen, meten of bewijs. N.v.t. opent nooit een gate.</p>
      <form className="form" onSubmit={(ev) => void submit(ev)} noValidate>
        <Field id={`st-${decision.id}`} label="Nieuwe status">
          {(a) => (
            <select {...a} value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="">— maak een keuze —</option>
              {options.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          )}
        </Field>
        {status && status !== "Open" ? (
          <Field id={`st-reden-${decision.id}`} label="Reden" help="Minstens 5 tekens.">
            {(a) => <textarea {...a} value={reden} onChange={(e) => setReden(e.target.value)} />}
          </Field>
        ) : null}
        {error ? <ErrorPanel error={error} title="Status wijzigen mislukt" /> : null}
        <div className="row">
          <button type="submit" className="btn" disabled={busy}>
            {busy ? "Bezig…" : "Status wijzigen"}
          </button>
        </div>
      </form>
    </section>
  );
}
