import type { Metadata } from "next";
import { OverScreen } from "./OverScreen";

export const metadata: Metadata = { title: "Over deze Hub" };

export default function Page() {
  return <OverScreen />;
}
