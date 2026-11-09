import type { Metadata } from "next";
import { Suspense } from "react";
import { Loading } from "@/components/Loading";
import { LogsScreen } from "./LogsScreen";

export const metadata: Metadata = { title: "Logs" };

export default function Page() {
  return (
    <Suspense fallback={<Loading />}>
      <LogsScreen />
    </Suspense>
  );
}
