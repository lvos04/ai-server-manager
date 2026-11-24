import { toonbareFout, vasteFout } from "@/lib/acties";
import { formatDateTime } from "@/lib/format";
import type { ApiState } from "@/lib/use-api";
import { ErrorPanel } from "./ErrorPanel";
import { Loading } from "./Loading";
import { Melding } from "./Melding";

export function Leesstand({ bron, naam }: { bron: ApiState<unknown> & { bronTijd?: string | null }; naam: string }) {
  return <>
    {bron.error && <ErrorPanel error={toonbareFout(bron.error)} vast={vasteFout} title={`${naam} onbekend`} onRetry={() => void bron.reload()} alert={false} />}
    {bron.stale && bron.data !== undefined && <Melding soort="onbekend" titel={bron.bronTijd === null ? "Tijdstip onbekend" : "Verouderd"} className="arcering border-dashed border-stale" data-testid="bronstand">
      <p>Laatst bekende lezing · {formatDateTime(bron.bronTijd === undefined ? bron.lastOk : bron.bronTijd)}</p>
    </Melding>}
    {!bron.data && bron.loading && <Loading text={`${naam} ophalen…`} />}
  </>;
}
