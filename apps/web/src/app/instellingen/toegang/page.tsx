import type { Metadata } from "next";
import { ToegangScreen } from "./ToegangScreen";

export const metadata: Metadata = { title: "Gebruikers en toegang" };

export default function Page() {
  return <ToegangScreen />;
}
