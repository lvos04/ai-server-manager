import type { Metadata } from "next";
import { InstellingenIndex } from "./InstellingenIndex";

export const metadata: Metadata = { title: "Instellingen" };

export default function Page() {
  return <InstellingenIndex />;
}
