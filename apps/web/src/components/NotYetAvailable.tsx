import { Hourglass } from "lucide-react";
import type { ReactNode } from "react";
import Link from "next/link";
import type { PlannedScreen } from "@/lib/nav";
import { Melding } from "./Melding";
import { PageHeader } from "./PageHeader";

/** NogNietBeschikbaar (C-12, T-08a) als pagina: rustig paneel, fase + wat er komt + bron. Geen nepdata. */
export function NotYetAvailable({ screen }: { screen: PlannedScreen }) {
  return (
    <>
      <PageHeader title={screen.titel} />
      <section
        className="flex flex-col gap-3 rounded-lg border-2 border-border-strong bg-muted p-4"
        aria-labelledby="nog-niet"
        data-testid="not-yet-available"
      >
        <h2 id="nog-niet" className="flex items-start gap-2">
          <Hourglass aria-hidden="true" className="mt-1 size-5 shrink-0" />
          Nog niet beschikbaar — volgt in fase {screen.fase}
        </h2>
        <p>
          <strong>Wat hier komt:</strong> {screen.wat}
        </p>
        <p>
          <strong>Bron:</strong> {screen.bron}
        </p>
        <p className="text-muted-foreground">
          Dit scherm toont pas gegevens als de bron echt gekoppeld is. Tot dan staat hier niets — ook geen voorbeeld- of
          testgegevens.
        </p>
        <p>
          <Link href="/" className="losse-link">
            Terug naar Home
          </Link>
        </p>
      </section>
    </>
  );
}

/** C-12a inline: één zin met fase en reden, voor secties en acties die pas later werken. */
export function NogNiet({ fase, children, testId }: { fase: string; children?: ReactNode; testId?: string }) {
  return (
    <Melding soort="nogniet" titel={`Nog niet beschikbaar — volgt in fase ${fase}`} data-testid={testId ?? "not-yet-available"}>
      {children}
    </Melding>
  );
}
