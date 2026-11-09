import type { Metadata } from "next";
import { AppsScreen } from "./AppsScreen";

export const metadata: Metadata = { title: "Apps" };

export default function Page() {
  return <AppsScreen />;
}
