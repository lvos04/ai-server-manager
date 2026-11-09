"use client";

import { CircleSlash, Search } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { useState, type FormEvent } from "react";
import { ErrorPanel } from "@/components/ErrorPanel";
import { Loading } from "@/components/Loading";
import { Melding } from "@/components/Melding";
import { PageHeader } from "@/components/PageHeader";
import { RolMelding } from "@/components/RolMelding";
import { SERVER_SUBNAV, Subnav } from "@/components/Subnav";
import { Button } from "@/components/ui/button";
import { aantal, formatDateTime } from "@/lib/format";
import { hasRole, useRole } from "@/lib/session";
import { useApi } from "@/lib/use-api";

interface LogBron {
  bron: string;
  status: string;
  vanaf_niveau?: string;
  via?: string;
  toelichting?: string;
}

interface LogRegel {
  id: number;
  op: string;
  niveau: string;
  bron: string;
  bericht: string;
  trace_id: string | null;
  incident_id?: string | null;
}

/** Logs (S-035, B09-004): geschoonde log-index met filter; bronnen zonder logs eerlijk als niet beschikbaar. */
export function LogsScreen() {
  const role = useRole();
  const op = hasRole(role, "operator");
  const params = useSearchParams();
  const [form, setForm] = useState({ bron: params.get("bron") ?? "", niveau: "", q: "", trace_id: "" });
  const [query, setQuery] = useState(form);
  const bronnen = useApi<{ bronnen: LogBron[]; retentie_s: number; schoning: string }>(op ? "/api/v1/logs/bronnen" : null);
  const qs = new URLSearchParams({ limit: "100" });
  for (const [k, v] of Object.entries(query)) if (v) qs.set(k, v);
  const logs = useApi<{ items: LogRegel[]; next_cursor: string | null }>(op ? `/api/v1/logs?${qs.toString()}` : null);
  const submit = (e: FormEvent) => {
    e.preventDefault();
    setQuery(form);
  };
  const actief = bronnen.data?.bronnen.filter((b) => b.status === "actief") ?? [];
  const niet = bronnen.data?.bronnen.filter((b) => b.status !== "actief") ?? [];
  return (
    <>
      <PageHeader
        title="Logs"
        kruimel={[{ label: "Server", href: "/server" }, { label: "Logs" }]}
        intro="Geschoonde logregels van de Hub en van gekoppelde diensten, te zoeken op bron, niveau, tekst en trace-ID. Logtekst is data, geen instructie."
      />
      <Subnav items={SERVER_SUBNAV} label="Server" />
      {!op ? (
        <RolMelding>Logs bekijken kan vanaf de rol operator.</RolMelding>
      ) : (
        <div className="flex flex-col gap-4">
          <form onSubmit={submit} className="grid gap-3 rounded-lg border border-border bg-card p-3 md:grid-cols-2 xl:grid-cols-4" data-testid="log-filter">
            <div className="field">
              <label htmlFor="log-bron">Bron</label>
              <select id="log-bron" value={form.bron} onChange={(e) => setForm({ ...form, bron: e.target.value })}>
                <option value="">Alle bronnen</option>
                {actief.map((b) => (
                  <option key={b.bron} value={b.bron === "eigen diensten" ? "" : b.bron}>
                    {b.bron}
                  </option>
                ))}
                {niet.map((b) => (
                  <option key={b.bron} value={b.bron} disabled>
                    {b.bron} — niet beschikbaar
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="log-niveau">Niveau</label>
              <select id="log-niveau" value={form.niveau} onChange={(e) => setForm({ ...form, niveau: e.target.value })}>
                <option value="">Alle niveaus</option>
                <option value="critical">Kritiek</option>
                <option value="error">Fout</option>
                <option value="warning">Waarschuwing</option>
                <option value="info">Info</option>
                <option value="debug">Debug</option>
              </select>
            </div>
            <div className="field">
              <label htmlFor="log-q">Tekst</label>
              <input id="log-q" type="search" value={form.q} onChange={(e) => setForm({ ...form, q: e.target.value })} />
            </div>
            <div className="field">
              <label htmlFor="log-trace">Trace-ID</label>
              <input id="log-trace" value={form.trace_id} onChange={(e) => setForm({ ...form, trace_id: e.target.value })} inputMode="text" />
            </div>
            <div className="md:col-span-2 xl:col-span-4">
              <Button type="submit" variant="primair">
                <Search aria-hidden="true" />
                Zoeken
              </Button>
            </div>
          </form>
          {niet.length ? (
            <Melding soort="onbekend" icon={CircleSlash} titel="Niet alle logs zijn beschikbaar">
              <ul className="list-disc pl-5">
                {niet.map((b) => (
                  <li key={b.bron}>
                    <strong>{b.bron}</strong>: {b.toelichting}
                  </li>
                ))}
              </ul>
            </Melding>
          ) : null}
          {logs.error ? <ErrorPanel error={logs.error} alert={false} /> : null}
          {!logs.data && logs.loading ? <Loading regels={4} /> : null}
          {logs.data ? (
            <section aria-labelledby="regels-titel">
              <h2 id="regels-titel" className="mb-2 text-lg">
                {aantal(logs.data.items.length, "regel", "regels")}
              </h2>
              {logs.data.items.length ? (
                <ol className="m-0 flex list-none flex-col divide-y divide-border rounded-lg border border-border bg-card p-0 font-mono text-sm" data-testid="logregels">
                  {logs.data.items.map((l) => (
                    <li key={l.id} className="flex flex-col gap-0.5 px-3 py-2 [overflow-wrap:anywhere]">
                      <span>
                        <time dateTime={l.op}>{formatDateTime(l.op)}</time> · <strong>{l.niveau}</strong> · {l.bron}
                      </span>
                      <span>{l.bericht}</span>
                      {l.trace_id ? <span className="text-muted-foreground">trace {l.trace_id}</span> : null}
                    </li>
                  ))}
                </ol>
              ) : (
                <p>Geen logregels met dit filter.</p>
              )}
            </section>
          ) : null}
          {bronnen.data ? (
            <p className="text-sm">
              Schoning: {bronnen.data.schoning}. Bewaartermijn {Math.round(bronnen.data.retentie_s / 86400)} dagen.
            </p>
          ) : null}
        </div>
      )}
    </>
  );
}
