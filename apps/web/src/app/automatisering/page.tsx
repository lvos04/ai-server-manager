import type { Metadata } from "next";
import { Automatisering } from "./Automatisering";

export const metadata: Metadata = { title: "Automatisering" };
export default function Page() { return <Automatisering onderdeel="flows" />; }
