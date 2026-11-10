import {
  Ban,
  Check,
  CircleCheck,
  CircleDot,
  CircleHelp,
  CirclePause,
  ClockAlert,
  FlaskConical,
  Hourglass,
  Info,
  KeyRound,
  LifeBuoy,
  Link2,
  Link2Off,
  Lock,
  LockOpen,
  Minus,
  OctagonX,
  Power,
  ShieldX,
  SquarePen,
  TriangleAlert,
  UserRound,
  type LucideIcon,
} from "lucide-react";
import type { ReactNode } from "react";
import {
  ERNST_LABEL,
  WORD,
  ZEKERHEID_LABEL,
  type Ernst,
  type IconKey,
  type StatusView,
  type Tone,
  type Zekerheid,
} from "@/lib/status";
import { cn } from "@/lib/utils";

/** Vaste koppeling betekenis → lucide-icoon (ONTWERPTAAL §7, OB-13). */
const TONE_ICON: Record<Tone, LucideIcon> = {
  healthy: CircleCheck,
  degraded: TriangleAlert,
  down: OctagonX,
  unknown: CircleHelp,
  stale: ClockAlert,
  paused: CirclePause,
  unlinked: Link2Off,
  not_yet: Hourglass,
  neutral: Minus,
  info: Info,
  gate: Lock,
};

export const ICON: Record<IconKey, LucideIcon> = {
  draait: Power,
  aan: Power,
  gekoppeld: Link2,
  ingesteld: LifeBuoy,
  geslaagd: Check,
  ingetrokken: ShieldX,
  open: CircleDot,
  ingevuld: SquarePen,
  getest: FlaskConical,
  slot: Lock,
  "slot-open": LockOpen,
  min: Minus,
  rol: UserRound,
  rotatie: KeyRound,
};

const TONE_CLASS: Record<Tone, string> = {
  healthy: "text-healthy-ink [&_svg]:text-healthy",
  degraded: "border-degraded bg-degraded-bg text-degraded-ink [&_svg]:text-degraded",
  down: "border-down bg-down-bg text-down-ink [&_svg]:text-down",
  unknown: "border-dashed border-unknown bg-unknown-bg text-unknown-ink [&_svg]:text-unknown",
  unlinked: "border-dashed border-unknown bg-unknown-bg text-unknown-ink [&_svg]:text-unknown",
  stale: "arcering border-dashed border-stale text-unknown-ink [&_svg]:text-stale",
  paused: "border-paused bg-paused-bg text-paused-ink [&_svg]:text-paused",
  not_yet: "border-border-strong bg-muted text-foreground",
  neutral: "border-border-strong text-foreground [&_svg]:text-foreground",
  info: "border-info bg-info-bg text-info-ink [&_svg]:text-info",
  gate: "rounded-sm border-gate bg-gate-bg text-gate-ink [&_svg]:text-gate",
};

/**
 * StatusBadge (C-03/C-03a): pil met icoon + vast woord. Gezond zonder vlak; onbekend/verouderd gestippeld; toestanden
 * die geen gezondheid zijn (Gekoppeld, Draait, Geslaagd, Aan) als neutrale pil, lopende processen als info-pil.
 */
export function StatusBadge({ view, groot, className, testId }: { view: StatusView; groot?: boolean; className?: string; testId?: string }) {
  const Icon = (view.icon && ICON[view.icon]) || TONE_ICON[view.tone];
  return (
    <span
      className={cn(
        // Peil 1.1.1 (C-03): radius = halve regelhoogte, zodat een omlopende pil niet wordt afgesneden.
        "inline-flex min-h-8 w-fit max-w-full items-center gap-1.5 rounded-2xl border-2 border-transparent px-2.5 py-0.5 text-sm leading-5 font-semibold [&_svg]:size-4.5 [&_svg]:shrink-0",
        TONE_CLASS[view.tone],
        groot && "min-h-10 rounded-[1.25rem] px-3.5 text-base [&_svg]:size-5",
        className,
      )}
      data-status={view.tone}
      data-testid={testId}
    >
      <Icon aria-hidden="true" />
      <span>{view.label || (view.tone in WORD ? WORD[view.tone as keyof typeof WORD] : "")}</span>
    </span>
  );
}

/** ErnstLabel (T-20): rechthoek met dikke linkerbalk, alleen tekst. */
export function ErnstLabel({ ernst }: { ernst: Ernst }) {
  const cls: Record<Ernst, string> = {
    kritiek: "border-l-down-ink bg-destructive text-destructive-foreground",
    hoog: "border-l-down bg-down-bg text-down-ink",
    middel: "border-l-foreground bg-muted text-foreground",
    laag: "border-l-unknown bg-unknown-bg text-unknown-ink",
    info: "border-l-info bg-info-bg text-info-ink",
  };
  return (
    <span className={cn("inline-flex min-h-8 w-fit items-center rounded-sm border-l-[6px] py-0.5 pr-2.5 pl-2 text-sm leading-5 font-semibold", cls[ernst])} data-ernst={ernst}>
      <span className="sr-only">Ernst: </span>
      {ERNST_LABEL[ernst]}
    </span>
  );
}

/** ZekerheidLabel (T-24): drie stippen + woord, geen statuskleur, nooit een percentage. */
export function ZekerheidLabel({ zekerheid }: { zekerheid: Zekerheid }) {
  const vol = { zeker: 3, waarschijnlijk: 2, onzeker: 1, weet_niet: 0 }[zekerheid];
  return (
    <span className="inline-flex min-h-8 w-fit items-center gap-2 rounded-full border-2 border-border-strong px-2.5 text-sm font-semibold text-foreground" data-zekerheid={zekerheid}>
      <span className="inline-flex gap-1" aria-hidden="true">
        {[0, 1, 2].map((i) => (
          <span key={i} className={cn("inline-block size-2.5 rounded-full border-2 border-foreground", i < vol && "bg-foreground")} />
        ))}
      </span>
      <span className="sr-only">Zekerheid: </span>
      {ZEKERHEID_LABEL[zekerheid]}
    </span>
  );
}

/** Validatielabel (C-09): exacte strings, gestippeld en mono; ook "Gereed/Geslaagd" nooit in de stijl van Gezond. */
export function Validatielabel({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex min-h-8 w-fit max-w-full items-center gap-1.5 rounded-sm border-2 border-dashed border-validation bg-validation-bg px-2 font-mono text-sm leading-5 text-validation-ink [&_svg]:size-4 [&_svg]:shrink-0">
      <FlaskConical aria-hidden="true" />
      <span className="sr-only">Validatie: </span>
      {children}
    </span>
  );
}

/** Label "Gate dicht"/beleid: slot, neutraal-sterk. */
export function SlotLabel({ children, beleid }: { children: ReactNode; beleid?: boolean }) {
  const Icon = beleid ? Ban : Lock;
  return (
    <span className="inline-flex min-h-8 w-fit items-center gap-1.5 rounded-sm border-2 border-gate bg-gate-bg px-2 text-sm font-semibold text-gate-ink [&_svg]:size-4 [&_svg]:text-gate">
      <Icon aria-hidden="true" />
      {children}
    </span>
  );
}
