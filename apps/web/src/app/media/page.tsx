import type { Metadata } from "next";
import { MediaScreen } from "./MediaScreen";

export const metadata: Metadata = { title: "Media" };

export default function Page() {
  return <MediaScreen />;
}
