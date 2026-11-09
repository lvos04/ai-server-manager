/** Nederlandse weergave van tijden, aantallen en groottes. Tijden komen als ISO-8601 UTC (`…Z`) van de API. */

const dateTimeFmt = new Intl.DateTimeFormat("nl-NL", {
  day: "numeric",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});
const dateFmt = new Intl.DateTimeFormat("nl-NL", { day: "numeric", month: "short", year: "numeric" });
const numFmt = new Intl.NumberFormat("nl-NL", { maximumFractionDigits: 1 });

export function parseIso(iso: string | null | undefined): Date | null {
  if (!iso) return null;
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? null : d;
}

export function formatDateTime(iso: string | null | undefined): string {
  const d = parseIso(iso);
  return d ? dateTimeFmt.format(d) : "onbekend";
}

const timeFmt = new Intl.DateTimeFormat("nl-NL", { hour: "2-digit", minute: "2-digit" });

/** "11:56" als het vandaag is, anders "8 nov 2026, 22:10" (ONTWERPTAAL §11 notatie). */
export function formatTime(iso: string | null | undefined, now: Date = new Date()): string {
  const d = parseIso(iso);
  if (!d) return "onbekend";
  const sameDay = d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth() && d.getDate() === now.getDate();
  return sameDay ? timeFmt.format(d) : dateTimeFmt.format(d);
}

export function formatDate(iso: string | null | undefined): string {
  const d = parseIso(iso);
  return d ? dateFmt.format(d) : "onbekend";
}

export function formatRelative(iso: string | null | undefined, now: Date = new Date()): string {
  const d = parseIso(iso);
  if (!d) return "onbekend";
  const diff = Math.round((now.getTime() - d.getTime()) / 1000);
  const future = diff < 0;
  const s = Math.abs(diff);
  let text: string;
  if (s < 45) return future ? "zo meteen" : "zojuist";
  if (s < 3600) {
    const m = Math.max(1, Math.round(s / 60));
    text = `${m} min`;
  } else if (s < 86400) {
    const h = Math.round(s / 3600);
    text = `${h} uur`;
  } else {
    const days = Math.round(s / 86400);
    text = `${days} ${days === 1 ? "dag" : "dagen"}`;
  }
  return future ? `over ${text}` : `${text} geleden`;
}

export function formatNumber(n: number | null | undefined): string {
  return typeof n === "number" && Number.isFinite(n) ? numFmt.format(n) : "onbekend";
}

const UNITS = ["B", "KiB", "MiB", "GiB", "TiB", "PiB"];

export function formatBytes(n: number | null | undefined): string {
  if (typeof n !== "number" || !Number.isFinite(n) || n < 0) return "onbekend";
  let v = n;
  let i = 0;
  while (v >= 1024 && i < UNITS.length - 1) {
    v /= 1024;
    i++;
  }
  return `${numFmt.format(i === 0 ? v : Math.round(v * 10) / 10)} ${UNITS[i]}`;
}

export function formatPercent(n: number | null | undefined): string {
  return typeof n === "number" && Number.isFinite(n) ? `${numFmt.format(n)}%` : "onbekend";
}

export function formatDuration(seconds: number | null | undefined): string {
  if (typeof seconds !== "number" || !Number.isFinite(seconds) || seconds < 0) return "onbekend";
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (d > 0) return `${d} d ${h} u`;
  if (h > 0) return `${h} u ${m} min`;
  return `${m} min`;
}

/** Leesbare weergave van een onbekende/lege waarde: nooit een verzonnen waarde. */
export function orUnknown(v: string | number | null | undefined): string {
  if (v === null || v === undefined || v === "") return "onbekend";
  return String(v);
}
