import type { Metadata } from "next";
import { MeetdekkingScreen } from "./MeetdekkingScreen";

export const metadata: Metadata = { title: "Meetdekking" };

export default function Page() {
  return <MeetdekkingScreen />;
}
