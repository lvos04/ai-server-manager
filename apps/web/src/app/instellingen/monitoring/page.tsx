import type { Metadata } from "next";
import { MonitoringScreen } from "./MonitoringScreen";

export const metadata: Metadata = { title: "Monitoring en meldingen" };

export default function Page() {
  return <MonitoringScreen />;
}
