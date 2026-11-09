import type { Metadata } from "next";
import { ProblemenScreen } from "./ProblemenScreen";

export const metadata: Metadata = { title: "Problemen" };

export default function Page() {
  return <ProblemenScreen />;
}
