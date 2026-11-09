import type { Metadata } from "next";
import { FirstStart } from "./FirstStart";

export const metadata: Metadata = { title: "Eerste start" };

export default function Page() {
  return <FirstStart />;
}
