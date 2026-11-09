import type { Metadata } from "next";
import { Noodlogin } from "./Noodlogin";

export const metadata: Metadata = { title: "Noodlogin" };

export default function Page() {
  return <Noodlogin />;
}
