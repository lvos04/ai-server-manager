import type { Metadata } from "next";
import { BackupsScreen } from "./BackupsScreen";

export const metadata: Metadata = { title: "Backups" };

export default function Page() {
  return <BackupsScreen />;
}
