import type { Metadata } from "next";
import { TrueNasScreen } from "./TrueNasScreen";

export const metadata: Metadata = { title: "TrueNAS koppelen" };

export default function Page() {
  return <TrueNasScreen />;
}
