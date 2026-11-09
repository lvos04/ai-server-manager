import type { Metadata } from "next";
import { DecisionScreen } from "./DecisionScreen";

const IDS = Array.from({ length: 18 }, (_, i) => `D${String(i + 1).padStart(2, "0")}`);

export const dynamicParams = false;

export function generateStaticParams() {
  return IDS.map((id) => ({ id }));
}

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }): Promise<Metadata> {
  const { id } = await params;
  return { title: `Besluit ${id}` };
}

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const i = IDS.indexOf(id);
  return <DecisionScreen id={id} prev={i > 0 ? IDS[i - 1] : undefined} next={i < IDS.length - 1 ? IDS[i + 1] : undefined} />;
}
