import type { Metadata } from "next";
import { ProblemenScreen } from "../ProblemenScreen";

export const metadata: Metadata = { title: "Incident" };

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  // Alleen een geldig incident-id gaat naar de API; al het andere is gewoon 'niet gevonden' van de API.
  return <ProblemenScreen selectedId={UUID.test(id) ? id.toLowerCase() : "00000000-0000-0000-0000-000000000000"} />;
}
