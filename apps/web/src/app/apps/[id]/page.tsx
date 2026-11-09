import type { Metadata } from "next";
import { Suspense } from "react";
import { Loading } from "@/components/Loading";
import { AppDetail } from "./AppDetail";

export const metadata: Metadata = { title: "App" };

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <Suspense fallback={<Loading />}>
      <AppDetail id={UUID.test(id) ? id.toLowerCase() : "00000000-0000-0000-0000-000000000000"} />
    </Suspense>
  );
}
