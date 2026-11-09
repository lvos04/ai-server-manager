import { UserRound } from "lucide-react";
import type { ReactNode } from "react";
import { Melding } from "./Melding";

/** RolMelding (C-49): één per pagina; de API is de poortwachter, de UI verbergt alleen wat niet mag. */
export function RolMelding({ children }: { children: ReactNode }) {
  return (
    <Melding soort="info" icon={UserRound} data-testid="rolmelding">
      <p>{children}</p>
    </Melding>
  );
}
