import { Check, CircleHelp, Lock, OctagonX, type LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export type ControleUitkomst = "ok" | "fout" | "onbekend" | "beleid";

const ICON: Record<ControleUitkomst, LucideIcon> = { ok: Check, fout: OctagonX, onbekend: CircleHelp, beleid: Lock };
const ICON_CLS: Record<ControleUitkomst, string> = { ok: "text-foreground", fout: "text-down", onbekend: "text-unknown", beleid: "text-gate" };
const WOORD: Record<ControleUitkomst, string> = { ok: "Geslaagd", fout: "Mislukt", onbekend: "Onbekend", beleid: "Beleid" };

export interface Controle {
  id: string;
  naam: ReactNode;
  uitkomst: ControleUitkomst;
  detail?: ReactNode;
}

/**
 * TestResultaat / Controlelijst (C-58): uitkomst van een eenmalige test of zelftest. Geslaagd = neutraal vinkje (geen
 * gezondheid), mislukt = gemeten falen, onbekend = vraagteken, beleid = slot.
 */
export function Controles({ items, testId }: { items: Controle[]; testId?: string }) {
  return (
    <ul className="m-0 flex list-none flex-col divide-y divide-border border-y border-border p-0" data-testid={testId}>
      {items.map((c) => {
        const Icon = ICON[c.uitkomst];
        return (
          <li key={c.id} className="flex flex-wrap items-start gap-x-3 gap-y-1 py-2.5" data-controle={c.id} data-uitkomst={c.uitkomst}>
            <Icon aria-hidden="true" className={cn("mt-0.5 size-5 shrink-0", ICON_CLS[c.uitkomst])} />
            <span className={cn("font-semibold", c.uitkomst === "fout" && "text-down-ink")}>
              <span className="sr-only">{WOORD[c.uitkomst]}: </span>
              {c.naam}
            </span>
            {c.detail ? <span className="basis-full text-sm text-foreground sm:flex-1 sm:basis-auto">{c.detail}</span> : null}
          </li>
        );
      })}
    </ul>
  );
}
