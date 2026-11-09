import type { Metadata } from "next";
import { MetriekenScreen } from "./MetriekenScreen";

export const metadata: Metadata = { title: "Metrieken" };

export default function Page() {
  return <MetriekenScreen />;
}
