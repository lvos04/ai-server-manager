import { CircleHelp, Hourglass, Info, Lock, OctagonX, TriangleAlert, type LucideIcon } from "lucide-react";
import type { ComponentProps, ReactNode } from "react";
import { cn } from "@/lib/utils";

export type MeldingSoort = "fout" | "beperkt" | "onbekend" | "info" | "gate" | "nogniet";

const CLS: Record<MeldingSoort, string> = {
  fout: "border-down bg-down-bg text-down-ink [&>svg]:text-down",
  beperkt: "border-degraded bg-degraded-bg text-degraded-ink [&>svg]:text-degraded",
  onbekend: "border-dashed border-unknown bg-unknown-bg text-unknown-ink [&>svg]:text-unknown",
  info: "border-info bg-info-bg text-info-ink [&>svg]:text-info",
  gate: "border-gate bg-gate-bg text-gate-ink [&>svg]:text-gate",
  nogniet: "border-border-strong bg-muted text-foreground [&>svg]:text-foreground",
};

const ICON: Record<MeldingSoort, LucideIcon> = {
  fout: OctagonX,
  beperkt: TriangleAlert,
  onbekend: CircleHelp,
  info: Info,
  gate: Lock,
  nogniet: Hourglass,
};

/** Melding (shadcn Alert in Peil): fout · beperkt · onbekend · info · gate · nog niet beschikbaar. */
export function Melding({
  soort,
  icon,
  titel,
  children,
  className,
  ...rest
}: { soort: MeldingSoort; icon?: LucideIcon; titel?: ReactNode; children?: ReactNode } & Omit<ComponentProps<"div">, "title">) {
  const Icon = icon ?? ICON[soort];
  return (
    <div
      className={cn(
        "flex gap-3 rounded-lg border-2 p-4 text-base [&>svg]:mt-0.5 [&>svg]:size-5 [&>svg]:shrink-0 [&_a:not([data-slot=button])]:font-semibold [&_a:not([data-slot=button])]:text-current",
        CLS[soort],
        className,
      )}
      data-melding={soort}
      {...rest}
    >
      <Icon aria-hidden="true" />
      <div className="flex min-w-0 flex-1 flex-col gap-1.5">
        {titel ? <p className="font-bold">{titel}</p> : null}
        {children}
      </div>
    </div>
  );
}
