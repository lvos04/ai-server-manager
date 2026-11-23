import type { Metadata } from "next";
import { GoedkeuringScreen } from "./GoedkeuringScreen";

export const metadata: Metadata = { title: "Goedkeuring beoordelen" };

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  // Alleen een geldig verzoek-id gaat naar de API; al het andere wordt gewoon 'niet gevonden'.
  return <GoedkeuringScreen id={UUID.test(id) ? id.toLowerCase() : "00000000-0000-0000-0000-000000000000"} />;
}
