import Link from "next/link";
import type { PlannedScreen } from "@/lib/nav";
import { PageHeader } from "./PageHeader";
import { StatusBadge } from "./StatusBadge";

/** Eerlijk scherm voor functies die pas in een latere fase komen: geen nepdata, geen schijnknoppen. */
export function NotYetAvailable({ screen }: { screen: PlannedScreen }) {
  return (
    <>
      <PageHeader title={screen.titel} />
      <section className="card stack" aria-labelledby="nog-niet" data-testid="not-yet-available">
        <div className="row">
          <StatusBadge view={{ tone: "neutral", label: "Nog niet beschikbaar" }} />
        </div>
        <h2 id="nog-niet">Nog niet beschikbaar (volgt in fase {screen.fase})</h2>
        <p>
          <strong>Wat hier komt:</strong> {screen.wat}
        </p>
        <p>
          <strong>Bron:</strong> {screen.bron}
        </p>
        <p className="muted">
          Dit scherm toont pas gegevens als de bron echt gekoppeld is. Tot dan staat hier niets — ook geen voorbeeld- of
          testgegevens.
        </p>
        <p>
          <Link href="/">Terug naar Home</Link>
        </p>
      </section>
    </>
  );
}
