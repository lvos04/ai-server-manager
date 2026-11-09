import type { Metadata } from "next";
import { NotYetAvailable } from "@/components/NotYetAvailable";
import { PLANNED } from "@/lib/nav";

const screen = PLANNED["kosten"]!;

export const metadata: Metadata = { title: screen.titel };

export default function Page() {
  return <NotYetAvailable screen={screen} />;
}
