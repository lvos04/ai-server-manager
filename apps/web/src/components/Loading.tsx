"use client";

import { useEffect, useState } from "react";

/** Laden (C-18): skelet in de vorm van de inhoud, sr-only "Laden…"; na 10 s "dit duurt langer dan verwacht". */
export function Loading({ text = "Laden…", regels = 3 }: { text?: string; regels?: number }) {
  const [lang, setLang] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setLang(true), 10_000);
    return () => clearTimeout(t);
  }, []);
  return (
    <div className="flex flex-col gap-3" role="status" aria-busy="true" data-testid="loading">
      <span className="sr-only">{text}</span>
      {Array.from({ length: regels }, (_, i) => (
        <div key={i} className="h-6 rounded-md bg-muted motion-safe:animate-pulse" style={{ width: `${90 - i * 18}%` }} aria-hidden="true" />
      ))}
      {lang ? <p className="text-sm text-muted-foreground">{text.replace(/…$/, "")}… dit duurt langer dan verwacht.</p> : null}
    </div>
  );
}
