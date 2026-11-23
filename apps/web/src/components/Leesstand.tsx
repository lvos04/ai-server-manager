import { toonbareFout, vasteFout } from "@/lib/acties";
import { formatDateTime } from "@/lib/format";
import type { ApiState } from "@/lib/use-api";
import { ErrorPanel } from "./ErrorPanel";
import { Loading } from "./Loading";
import { Melding } from "./Melding";

export function Leesstand({ bron, naam }: { bron: ApiState<unknown>; naam: string }) {
  return <>
    {bron.error && <ErrorPanel error={toonbareFout(bron.error)} vast={vasteFout} title={`${naam} onbekend`} onRetry={() => void bron.reload()} alert={false} />}
    {bron.stale && bron.data !== undefined && <Melding soort="onbekend" titel="Verouderd"><p>Laatst bekende lezing · {formatDateTime(bron.lastOk)}</p></Melding>}
    {!bron.data && bron.loading && <Loading text={`${naam} ophalen…`} />}
  </>;
}
