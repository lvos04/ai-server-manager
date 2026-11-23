import type { Metadata } from "next";
import { Installatiewizard } from "./Installatiewizard";

export const metadata: Metadata = { title: "App installeren" };

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export default async function Page({ searchParams }: { searchParams: Promise<{ plan?: string | string[] }> }) {
  const { plan } = await searchParams;
  // Hervatten kan alleen met het bestaande plan-ID (ontwerp S-047); al het andere begint bij ‘Kies app’.
  return <Installatiewizard planId={typeof plan === "string" && UUID.test(plan) ? plan.toLowerCase() : null} />;
}
