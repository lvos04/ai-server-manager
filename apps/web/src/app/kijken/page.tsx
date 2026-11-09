import type { Metadata } from "next";
import { KindKijken } from "../KindScreens";

export const metadata: Metadata = { title: "Kijken" };

export default function Page() {
  return <KindKijken />;
}
