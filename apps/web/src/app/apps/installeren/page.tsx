import type { Metadata } from "next";
import { isUuid } from "@/lib/uuid";
import { Installatiewizard } from "./Installatiewizard";

export const metadata: Metadata = { title: "App installeren" };

export default async function Page({ searchParams }: { searchParams: Promise<{ plan?: string | string[] }> }) {
  const { plan } = await searchParams;
  // Hervatten kan alleen met het bestaande plan-ID (ontwerp S-047); al het andere begint bij ‘Kies app’.
  return <Installatiewizard planId={isUuid(plan) ? plan.toLowerCase() : null} />;
}
