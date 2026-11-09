import type { Metadata } from "next";
import { HomeOfKind } from "./HomeOfKind";

// De titelsjabloon uit layout.tsx geldt niet voor hetzelfde segment: daarom hier de volledige titel.
export const metadata: Metadata = { title: { absolute: "Home — TrueNAS Home Platform" } };

export default function Page() {
  return <HomeOfKind />;
}
