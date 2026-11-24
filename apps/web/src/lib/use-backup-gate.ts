"use client";

import { backupGate } from "./backups";
import type { Coverage, Gate, SelfBackupList } from "./types";
import { useBronlijst, useMeting } from "./use-meting";

export function useBackupGate(lezen: boolean, nu: number) {
  const gate = useMeting<Gate>(lezen ? "/api/v1/gates/backup_gate" : null);
  const dekking = useMeting<Coverage>(lezen ? "/api/v1/backups/coverage" : null);
  const eigen = useBronlijst<SelfBackupList>(lezen ? "/api/v1/backups/self" : null);
  const stand = backupGate(gate.data, dekking.stale ? undefined : dekking.data, gate.stale, nu, eigen.stale ? undefined : eigen.data);
  return { gate, dekking, eigen, stand };
}
