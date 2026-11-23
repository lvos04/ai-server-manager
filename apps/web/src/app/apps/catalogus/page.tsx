import type { Metadata } from "next";
import { CatalogusScreen } from "./CatalogusScreen";

export const metadata: Metadata = { title: "Appstore" };

export default function Page() {
  return <CatalogusScreen />;
}
