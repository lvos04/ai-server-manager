import type { Metadata } from "next";
import { DienstenScreen } from "./DienstenScreen";

export const metadata: Metadata = { title: "Diensten" };

export default function Page() {
  return <DienstenScreen />;
}
