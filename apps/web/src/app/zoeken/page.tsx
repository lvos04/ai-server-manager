import type { Metadata } from "next";
import { KindZoeken } from "../KindScreens";

export const metadata: Metadata = { title: "Zoeken" };

export default function Page() {
  return <KindZoeken />;
}
