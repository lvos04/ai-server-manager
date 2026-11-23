import type { Metadata } from "next";
import { BeleidScreen } from "./BeleidScreen";

export const metadata: Metadata = { title: "Risicobeleid" };

export default function Page() {
  return <BeleidScreen />;
}
