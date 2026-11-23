import { OctagonX } from "lucide-react";
import { resultaatCode, type ActieVerzoek } from "@/lib/acties";
import { formatDateTime, formatDuration } from "@/lib/format";
import { cn } from "@/lib/utils";
import { shortDigest } from "./KopieerVeld";

type StapToestand = "klaar" | "huidig" | "mislukt" | "gestopt" | "onbekend" | "open";

const BOL: Record<StapToestand, string> = {
  klaar: "bg-foreground",
  huidig: "bg-primary",
  mislukt: "bg-down",
  gestopt: "bg-degraded",
  onbekend: "border-2 border-dashed border-unknown bg-unknown-bg",
  open: "border-2 border-border-strong bg-card",
};
const WOORD: Record<StapToestand, string> = {
  klaar: "klaar",
  huidig: "bezig",
  mislukt: "mislukt",
  gestopt: "gestopt",
  onbekend: "onbekend",
  open: "nog niet",
};

function tekst(v: Record<string, unknown> | null, k: string): string | null {
  const w = v?.[k];
  return typeof w === "string" ? w : null;
}

/** Eindtekst van de uitvoering; een onbekende of lopende uitkomst is nooit een succes. */
export function eindTekst(status: string): string {
  return (
    {
      bezig: "Uitvoering bezig",
      uitgevoerd: "Uitgevoerd en gecontroleerd",
      afwijking: "Gestopt: afwijking na uitvoering",
      mislukt: "Mislukt: er is niets als uitgevoerd gemeld",
      onbekend: "Uitkomst onbekend",
      afgewezen: "Niet uitgevoerd: afgewezen",
      geweigerd: "Niet uitgevoerd: geweigerd door het beleid",
      verlopen: "Niet uitgevoerd: verlopen",
    }[status] ?? "Nog niet uitgevoerd"
  );
}

/** UitvoeringsTijdlijn (C-23): gecontroleerd → uitgevoerd → controle na uitvoering, met tijd, duur en voor/na-hash. */
export function UitvoeringsTijdlijn({ v, verouderd }: { v: ActieVerzoek; verouderd?: boolean }) {
  const s = v.status;
  const gestart = Boolean(v.gestart_op) || ["bezig", "uitgevoerd", "afwijking", "mislukt", "onbekend"].includes(s);
  const uitvoering: StapToestand =
    s === "uitgevoerd" || s === "afwijking" ? "klaar" : s === "bezig" ? "huidig" : s === "mislukt" ? "mislukt" : s === "onbekend" ? "onbekend" : "open";
  const controle: StapToestand = s === "uitgevoerd" ? "klaar" : s === "afwijking" ? "gestopt" : s === "onbekend" ? "onbekend" : "open";
  const r = v.resultaat;
  const voor = tekst(r, "before_hash");
  const na = tekst(r, "after_hash");
  const duur = v.gestart_op && v.uitgevoerd_op ? (Date.parse(v.uitgevoerd_op) - Date.parse(v.gestart_op)) / 1000 : null;
  const stappen: { naam: string; t: StapToestand; tijd?: string | null; extra?: string }[] = [
    { naam: "Gecontroleerd en ondertekend", t: gestart ? "klaar" : "open", tijd: v.gestart_op },
    { naam: "Uitgevoerd", t: uitvoering, tijd: s === "uitgevoerd" || s === "afwijking" ? v.uitgevoerd_op : null, extra: duur !== null && duur >= 0 ? `duur ${formatDuration(duur)}` : undefined },
    { naam: "Controle na uitvoering", t: controle, extra: voor && na && s === "uitgevoerd" ? `voor ${shortDigest(voor)} · na ${shortDigest(na)}` : undefined },
  ];
  const code = resultaatCode(r);
  return (
    <section className="card" aria-labelledby="uitvoering-kop" data-testid="uitvoering">
      <h2 id="uitvoering-kop" className="text-xl font-bold">
        Uitvoering
      </h2>
      <ol className={cn("m-0 flex list-none flex-col gap-3 p-0", verouderd && "arcering rounded-sm border-2 border-dashed border-stale p-2")} aria-live="polite">
        {stappen.map((st) => (
          <li key={st.naam} className="flex items-start gap-3" data-stap={st.t}>
            <span className={cn("mt-1 inline-flex size-4 shrink-0 items-center justify-center rounded-full text-background", BOL[st.t])} aria-hidden="true">
              {st.t === "mislukt" ? <OctagonX className="size-3" /> : null}
            </span>
            <span className="flex flex-col">
              <span className="font-semibold">
                {st.naam} <span className="font-normal text-muted-foreground">· {WOORD[st.t]}</span>
              </span>
              {st.tijd ? <time dateTime={st.tijd} className="text-sm">{formatDateTime(st.tijd)}</time> : null}
              {st.extra ? <span className="text-sm">{st.extra}</span> : null}
            </span>
          </li>
        ))}
      </ol>
      <p className="font-bold" data-testid="uitvoering-eind">
        {verouderd && gestart ? `Laatst bekend: ${eindTekst(s)}` : eindTekst(s)}
      </p>
      {code && s !== "uitgevoerd" && s !== "afgewezen" ? (
        <p className="text-sm">
          Code <code>{code}</code>
        </p>
      ) : null}
    </section>
  );
}
