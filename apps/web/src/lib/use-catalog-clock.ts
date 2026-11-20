"use client";

import { useEffect, useReducer } from "react";

/** Werk badges en tellingen bij zodra de eerste bronmeting verloopt, ook tijdens een lopende ophaalactie. */
export function useCatalogClock(grenzen: number[]): number {
  const [, ververs] = useReducer((slag: number) => slag + 1, 0);
  const nu = new Date().getTime();
  const volgende = grenzen.reduce((eerste, grens) => grens >= nu ? Math.min(eerste, grens) : eerste, Infinity);
  useEffect(() => {
    if (!Number.isFinite(volgende)) return;
    const timer = setTimeout(ververs, Math.max(0, volgende + 1 - Date.now()));
    return () => clearTimeout(timer);
  }, [volgende]);
  return nu;
}
