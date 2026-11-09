"use client";

import { Copy } from "lucide-react";
import { useId, useRef, useState } from "react";
import { Button } from "./ui/button";

/**
 * KopieerVeld (C-15): label → selecteerbaar mono-blok + knop "Kopiëren" → live-regel. Zonder secure context (Hub via
 * http tot D17) wordt de tekst geselecteerd: "Tekst geselecteerd. Kopieer via het menu van je browser."
 * Toont nooit een geheim; een ingekorte weergave kopieert toch de volledige waarde.
 */
export function KopieerVeld({ label, waarde, ingekort, testId, groot }: { label: string; waarde: string; ingekort?: string; testId?: string; groot?: boolean }) {
  const id = useId();
  const ref = useRef<HTMLElement>(null);
  const [msg, setMsg] = useState("");
  const copy = async () => {
    if (typeof window !== "undefined" && window.isSecureContext && navigator.clipboard) {
      try {
        await navigator.clipboard.writeText(waarde);
        setMsg("Gekopieerd.");
        return;
      } catch {
        // val terug op selecteren
      }
    }
    const el = ref.current;
    if (el) {
      const range = document.createRange();
      range.selectNodeContents(el);
      const sel = window.getSelection();
      sel?.removeAllRanges();
      sel?.addRange(range);
    }
    setMsg("Tekst geselecteerd. Kopieer via het menu van je browser.");
  };
  return (
    <div className="flex min-w-0 flex-col gap-1.5" data-testid={testId}>
      <span className="text-sm font-semibold" id={`${id}-label`}>
        {label}
      </span>
      {/* Smal (< ± 22 rem): de knop springt onder het veld, zodat een digest niet in een kolom van 12 tekens breekt. */}
      <div className="flex min-w-0 flex-wrap items-start gap-2">
        <code
          ref={ref}
          aria-labelledby={`${id}-label`}
          className={
            groot
              ? "block min-w-0 flex-[1_1_12rem] rounded-sm border-2 border-dashed border-border-strong bg-card px-2.5 py-2 font-mono text-2xl leading-9 font-semibold tracking-wider break-words select-all"
              : "block min-w-0 flex-[1_1_12rem] rounded-sm border-2 border-dashed border-border-strong bg-card px-2.5 py-2 font-mono text-sm break-all text-foreground select-all"
          }
          title={ingekort ? waarde : undefined}
          data-waarde={testId ? waarde : undefined}
        >
          {ingekort ?? waarde}
        </code>
        <Button size="klein" onClick={() => void copy()}>
          <Copy aria-hidden="true" />
          Kopiëren<span className="sr-only">: {label}</span>
        </Button>
      </div>
      <p className="min-h-5 text-sm text-muted-foreground" aria-live="polite">
        {msg}
      </p>
    </div>
  );
}

/** "sha256:91c4…7d02" — korte weergave van een digest (de volledige waarde blijft kopieerbaar). */
export function shortDigest(d: string | null | undefined): string {
  if (!d) return "onbekend";
  const [algo, hex] = d.includes(":") ? d.split(":", 2) : ["", d];
  if (!hex || hex.length <= 12) return d;
  return `${algo ? `${algo}:` : ""}${hex.slice(0, 4)}…${hex.slice(-4)}`;
}
