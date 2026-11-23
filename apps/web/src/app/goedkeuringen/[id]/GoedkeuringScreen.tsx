"use client";

import { useState } from "react";
import { ActiePreview } from "@/components/ActiePreview";
import { ErrorPanel } from "@/components/ErrorPanel";
import { Freshness } from "@/components/Freshness";
import { GoedkeuringsPagina } from "@/components/GoedkeuringsPagina";
import { Loading } from "@/components/Loading";
import { Melding } from "@/components/Melding";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { statusView, toonbareFout, type ActieVerzoek, type Hashes, vasteFout } from "@/lib/acties";
import { FLOWHERSTEL, flowStatus, herstelbewijs, menselijkHerstel } from "@/lib/flowherstel";
import Link from "next/link";
import { useMeting } from "@/lib/use-meting";
import { formatTime } from "@/lib/format";
/** S-061/S-063/S-064: één voorstel met preview, goedkeuring en uitvoering. */
export function GoedkeuringScreen({ id }: { id: string }) {
  const s = useMeting<ActieVerzoek>(`/api/v1/actions/${id}`, undefined, 10_000);
  const isHerstel = s.data?.action_id === FLOWHERSTEL;
  const status = s.data && (isHerstel ? flowStatus(s.data, s.stale) : s.data.status);
  // De gebonden velden zoals de gebruiker ze het eerst zag; wijkt de server daarna af, dan vervalt de beslissing.
  const [gezien, setGezien] = useState<Hashes | null>(null);
  if (s.data && gezien === null) {
    setGezien({ preview_hash: s.data.preview_hash, resource_etag: s.data.resource_etag, policy_hash: s.data.policy_hash });
  }
  const kruimel = [{ label: "Goedkeuringen", href: "/goedkeuringen" }, { label: "Verzoek" }];
  let inhoud;
  if (s.data && isHerstel && !menselijkHerstel(s.data)) {
    inhoud = <Melding soort="gate" titel="Flowherstel geblokkeerd"><p>Alleen een menselijk R2-voorstel voor Node-RED kan worden beoordeeld.</p></Melding>;
  } else if (s.data) {
    inhoud = (
      <>
        {s.stale ? (
          <Melding soort="onbekend" titel={`Verouderd · stand van ${formatTime(s.lastOk)}`} data-testid="verouderd">
            <p>De laatste lezing is mislukt. Beslissen en uitvoeren wachten op een nieuwe, geslaagde lezing.</p>
          </Melding>
        ) : null}
        {isHerstel && <p>Momentopname · {herstelbewijs(s.data) ?? "Niet beschikbaar in dit voorstel."}</p>}
        {isHerstel && status !== s.data.status ? <>
          <ActiePreview v={s.data} verouderd={s.stale} />
          <Melding soort="onbekend" titel="Herstelstatus onbekend"><p>Actueel, overeenkomend leesbewijs van de eigenaar ontbreekt.</p></Melding>
        </> : <GoedkeuringsPagina v={s.data} gezien={gezien} verouderd={s.stale} opnieuw={() => void s.reload()} />}
      </>
    );
  } else if (s.error?.status === 404 || s.error?.code === "validation_error") {
    inhoud = (
      <Melding soort="onbekend" data-testid="niet-gevonden">
        <p>Dit verzoek is niet gevonden.</p>
      </Melding>
    );
  } else if (s.error) {
    inhoud = <ErrorPanel vast={vasteFout} error={toonbareFout(s.error)} title="Goedkeuring ophalen mislukt" onRetry={() => void s.reload()} />;
  } else {
    inhoud = <Loading text="Goedkeuring ophalen…" />;
  }
  return (
    <>
      <PageHeader
        title="Goedkeuring beoordelen"
        kruimel={kruimel}
        meta={s.data ? <StatusBadge view={statusView(status!)} testId="verzoek-status" /> : undefined}
      />
      <div className="flex flex-col gap-4">
        {inhoud}
        {s.data?.action_id === "zfs.snapshot.clone_to_sandbox" && <Link className="losse-link" href="/backups/hersteltests">Terug naar hersteltests</Link>}
        {s.data ? <Freshness observedAt={s.lastOk} bron="Hub-acties" verouderd={s.stale} /> : null}
      </div>
    </>
  );
}
