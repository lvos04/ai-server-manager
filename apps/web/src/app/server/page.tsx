import type { Metadata } from "next";
import { ServerScreen } from "./ServerScreen";

export const metadata: Metadata = { title: "Server" };

export default function Page() {
  return <ServerScreen />;
}
