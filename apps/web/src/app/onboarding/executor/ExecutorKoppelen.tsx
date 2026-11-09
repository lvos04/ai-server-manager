"use client";

import { Link2 } from "lucide-react";
import { ErrorPanel } from "@/components/ErrorPanel";
import { RolMelding } from "@/components/RolMelding";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { formatDateTime } from "@/lib/format";
import { hasRole, useRole } from "@/lib/session";
import { useAction } from "@/lib/use-action";
import { useApi } from "@/lib/use-api";
import { KoppelcodeKaart, type Dienst, type Koppelcode, type RegistryItem } from "../../instellingen/diensten/DienstenScreen";

const EXECUTOR = "ai-server-manager-executor";

/** Stap 2 van de executor: koppelcode (30 min) + vingerafdruk; de schrijfsleutel komt alleen op de executorpagina. */
export function ExecutorKoppelen() {
  const role = useRole();
  const admin = hasRole(role, "admin");
  const services = useApi<{ items: Dienst[] }>(hasRole(role, "operator") ? "/api/v1/services" : null, 10_000);
  const registry = useApi<{ items: RegistryItem[] }>("/api/v1/registry/services");
  const maak = useAction<Koppelcode>();
  const exec = services.data?.items.find((d) => d.app_id === EXECUTOR && d.status === "active");
  return (
    <div className="flex flex-col gap-3" data-testid="executor-koppelen">
      {exec ? (
        <p className="flex flex-wrap items-center gap-2">
          <StatusBadge view={{ tone: "neutral", label: "Gekoppeld", icon: "gekoppeld" }} /> sinds {formatDateTime(exec.enrolled_at)}. ‘Gekoppeld’ zegt niets over
          gezondheid; die zie je bij Apps.
        </p>
      ) : (
        <p>
          <StatusBadge view={{ tone: "unknown", label: "Niet gekoppeld" }} />
        </p>
      )}
      {!admin ? (
        <RolMelding>Een koppelcode maken kan alleen een beheerder.</RolMelding>
      ) : (
        <>
          <div>
            <Button variant={exec ? "secundair" : "primair"} bezig={maak.busy} onClick={() => void maak.run("/api/v1/services/pairing-codes", { body: { app_id: EXECUTOR } })} data-testid="executor-koppelcode-maken">
              <Link2 aria-hidden="true" />
              Koppelcode voor de executor maken
            </Button>
          </div>
          {maak.error ? <ErrorPanel error={maak.error} /> : null}
          {maak.result ? (
            <KoppelcodeKaart code={maak.result} adres={registry.data?.items.find((r) => r.app === EXECUTOR)} onVerlopen={() => undefined} gekoppeld={Boolean(exec && Date.parse(exec.enrolled_at) > Date.parse(maak.result.verloopt_op) - 30 * 60_000)} />
          ) : null}
        </>
      )}
    </div>
  );
}
