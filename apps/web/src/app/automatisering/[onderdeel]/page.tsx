import { notFound } from "next/navigation";
import { Automatisering } from "../Automatisering";

export default async function Page({ params, searchParams }: {
  params: Promise<{ onderdeel: string }>; searchParams: Promise<{ flow?: string }>;
}) {
  const { onderdeel } = await params;
  if (!["detail", "testmodus", "eventtypen", "historie", "versies"].includes(onderdeel)) notFound();
  const { flow } = await searchParams;
  return <Automatisering onderdeel={onderdeel} flow={typeof flow === "string" ? flow : undefined} />;
}
