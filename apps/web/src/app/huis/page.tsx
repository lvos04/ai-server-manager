import type { Metadata } from "next";
import { HuisScreen } from "./HuisScreen";

export const metadata: Metadata = { title: "Huis" };

export default function Page() {
  return <HuisScreen />;
}
