import type { Metadata } from "next";
import { SettingsScreen } from "./SettingsScreen";

export const metadata: Metadata = { title: "Instellingen" };

export default function Page() {
  return <SettingsScreen />;
}
