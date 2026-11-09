"use client";

import { useEffect, useRef, useState } from "react";
import { useNow } from "./Freshness";

/** Aftellen (C-22): elke seconde zichtbaar (mm:ss), aankondiging alleen op 5 min, 1 min en verlopen. */
export function Aftellen({ tot, onVerlopen, testId }: { tot: string; onVerlopen?: () => void; testId?: string }) {
  const now = useNow(1000);
  const rest = Math.max(0, Math.floor((Date.parse(tot) - now.getTime()) / 1000));
  const [aankondiging, setAankondiging] = useState("");
  const gemeld = useRef<Set<string>>(new Set());
  useEffect(() => {
    const punt = rest === 0 ? "0" : rest <= 60 ? "60" : rest <= 300 ? "300" : null;
    if (punt && !gemeld.current.has(punt)) {
      gemeld.current.add(punt);
      const tekst = punt === "0" ? "Verlopen." : punt === "60" ? "Nog 1 minuut." : "Nog 5 minuten.";
      const t = setTimeout(() => setAankondiging(tekst), 0);
      if (punt === "0") onVerlopen?.();
      return () => clearTimeout(t);
    }
  }, [rest, onVerlopen]);
  const mm = String(Math.floor(rest / 60)).padStart(2, "0");
  const ss = String(rest % 60).padStart(2, "0");
  return (
    <span data-testid={testId}>
      <span className="font-mono font-semibold tabular-nums" aria-hidden="true">
        {mm}:{ss}
      </span>
      <span className="sr-only">nog {Math.ceil(rest / 60)} minuten</span>
      <span className="sr-only" aria-live="polite">
        {aankondiging}
      </span>
    </span>
  );
}
