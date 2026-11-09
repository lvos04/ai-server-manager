import type { Metadata } from "next";
import { NoodaccountScreen } from "./NoodaccountScreen";

export const metadata: Metadata = { title: "Noodaccount" };

export default function Page() {
  return <NoodaccountScreen />;
}
