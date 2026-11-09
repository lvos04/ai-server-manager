"use client";

import { ListChecks } from "lucide-react";
import { useState } from "react";
import { Controles, type Controle } from "@/components/Controles";
import { ErrorPanel } from "@/components/ErrorPanel";
import { Loading } from "@/components/Loading";
import { RolMelding } from "@/components/RolMelding";
import { TableWrap } from "@/components/TableWrap";
import { Button } from "@/components/ui/button";
import { apiRequest } from "@/lib/api";
import { formatDateTime, formatTime, orUnknown } from "@/lib/format";
import { auditLabel } from "@/lib/home";
import { hasRole, useRole } from "@/lib/session";
import { useApi } from "@/lib/use-api";
import { InstellingenKop } from "../delen";

interface AuditRow {
  id: number;
  op: string | null;
  actor_type: string;
  actor_id: string;
  actie: string;
  doel_type: string | null;
  doel_id: string | null;
  ketting_nr: number | null;
}

interface Verify {
  status: "intact" | "verbroken";
  gecontroleerd: number;
  kop: { nr: number; hash: string } | null;
  fouten: { soort: string; nr?: number; anker_nr?: number; laatste_nr?: number; aantal?: number }[];
  anker: { status: string; anker_nr?: number; anker_op?: string };
  gecontroleerd_op: string;
}

const FOUT: Record<string, string> = {
  gat_in_nummering: "Nummering",
  koppeling_verbroken: "Koppeling",
  inhoud_gewijzigd: "Inhoud",
  onverzegelde_rijen: "Verzegeling",
  staart_ontbreekt: "Anker",
  anker_afwijkend: "Anker",
};

function verifyControles(v: Verify): Controle[] {
  const has = (...s: string[]) => v.fouten.filter((f) => s.includes(f.soort));
  const staart = has("staart_ontbreekt")[0];
  return [
    { id: "nummering", naam: "Doorlopende nummering", uitkomst: has("gat_in_nummering").length ? "fout" : "ok", detail: `${v.gecontroleerd} rijen gecontroleerd.` },
    { id: "koppeling", naam: "Koppeling (vorige hash)", uitkomst: has("koppeling_verbroken").length ? "fout" : "ok" },
    { id: "inhoud", naam: "Inhoud ongewijzigd", uitkomst: has("inhoud_gewijzigd", "onverzegelde_rijen").length ? "fout" : "ok" },
    staart
      ? {
          id: "anker",
          naam: "Anker in /appdata/audit",
          uitkomst: "onbekend",
          detail: `De staart ontbreekt (anker ${staart.anker_nr}, laatste ${staart.laatste_nr}). Verwacht na een bewuste database-restore (zie docs/INCIDENTEN.md); anders is er een rij verwijderd.`,
        }
      : {
          id: "anker",
          naam: "Anker in /appdata/audit",
          uitkomst: v.anker.status === "ok" ? "ok" : v.anker.status === "geen_anker" ? "onbekend" : "fout",
          detail: v.anker.status === "geen_anker" ? "Nog geen anker geschreven (dagelijkse controle)." : v.anker.status === "ok" ? `Anker tot nr ${v.anker.anker_nr}.` : `Anker: ${v.anker.status}.`,
        },
  ];
}

export function AuditScreen() {
  const role = useRole();
  const admin = hasRole(role, "admin");
  const audit = useApi<{ items: AuditRow[]; next_cursor: string | null }>(admin ? "/api/v1/audit?limit=50" : null);
  const [verify, setVerify] = useState<Verify | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<unknown>(null);
  const check = async () => {
    setBusy(true);
    setErr(null);
    try {
      setVerify((await apiRequest<Verify>("/api/v1/audit/verify")).data);
    } catch (e) {
      setErr(e);
    } finally {
      setBusy(false);
    }
  };
  return (
    <>
      <InstellingenKop titel="Auditspoor" intro="Append-only met een hash-ketting: elke beheerhandeling staat hier, en niemand kan regels wijzigen of verwijderen zonder dat de controle het ziet." />
      {!admin ? (
        <RolMelding>Het auditspoor is alleen voor beheerders.</RolMelding>
      ) : (
        <div className="stack" data-testid="audit">
          <section className="card" aria-labelledby="ketting-titel">
            <h2 id="ketting-titel">Ketting controleren</h2>
            <div>
              <Button onClick={() => void check()} bezig={busy} data-testid="ketting-controleren">
                <ListChecks aria-hidden="true" />
                Ketting controleren
              </Button>
            </div>
            {err ? <ErrorPanel error={err} /> : null}
            {verify ? (
              <div className="flex flex-col gap-2" data-testid="ketting-uitkomst">
                <p role="status">
                  Uitkomst om {formatTime(verify.gecontroleerd_op)}: {verify.status === "intact" ? "ketting intact" : `ketting verbroken (${verify.fouten.map((f) => FOUT[f.soort] ?? f.soort).join(", ")})`}.
                </p>
                <Controles items={verifyControles(verify)} />
              </div>
            ) : null}
          </section>
          <section className="card" aria-labelledby="audit-titel">
            <h2 id="audit-titel">Laatste 50 handelingen</h2>
            {audit.error ? <ErrorPanel error={audit.error} alert={false} /> : null}
            {!audit.data && audit.loading ? <Loading /> : null}
            <TableWrap label="Auditspoor">
              <table>
                <caption className="sr-only">Auditspoor</caption>
                <thead>
                  <tr>
                    <th scope="col">Wanneer</th>
                    <th scope="col">Wie</th>
                    <th scope="col">Handeling</th>
                    <th scope="col">Doel</th>
                    <th scope="col">Nr</th>
                  </tr>
                </thead>
                <tbody>
                  {(audit.data?.items ?? []).map((r) => (
                    <tr key={r.id}>
                      <td>{formatDateTime(r.op)}</td>
                      <td>
                        {r.actor_id}
                        <div className="meta">{r.actor_type}</div>
                      </td>
                      <td>
                        {auditLabel(r.actie)}
                        <div className="meta">
                          <code>{r.actie}</code>
                        </div>
                      </td>
                      <td>{r.doel_type ? `${r.doel_type}: ${orUnknown(r.doel_id)}` : "—"}</td>
                      <td className="font-mono">{r.ketting_nr ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </TableWrap>
          </section>
        </div>
      )}
    </>
  );
}
