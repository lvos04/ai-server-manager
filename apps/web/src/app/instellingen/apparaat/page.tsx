import type { Metadata } from "next";
import { ApparaatScreen } from "./ApparaatScreen";

export const metadata: Metadata = { title: "Apparaat en app" };

export default function Page() {
  return <ApparaatScreen />;
}
