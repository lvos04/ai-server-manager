import type { Metadata } from "next";
import { GoedkeuringenScreen } from "./GoedkeuringenScreen";

export const metadata: Metadata = { title: "Goedkeuringen" };

export default function Page() {
  return <GoedkeuringenScreen />;
}
