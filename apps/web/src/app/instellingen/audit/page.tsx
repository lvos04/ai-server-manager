import type { Metadata } from "next";
import { AuditScreen } from "./AuditScreen";

export const metadata: Metadata = { title: "Auditspoor" };

export default function Page() {
  return <AuditScreen />;
}
