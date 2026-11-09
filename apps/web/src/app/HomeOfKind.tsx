"use client";

import { useRole } from "@/lib/session";
import { HomeScreen } from "./HomeScreen";
import { KindHome } from "./KindScreens";

/** Home: de kindschil krijgt een eigen Home zonder systeemstatus (en zonder API-aanroepen die kind toch weigert). */
export function HomeOfKind() {
  const role = useRole();
  if (role === "kind") return <KindHome />;
  return <HomeScreen />;
}
