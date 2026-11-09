import type { Metadata } from "next";
import { OnboardingScreen } from "./OnboardingScreen";

export const metadata: Metadata = { title: "Onboarding" };

export default function Page() {
  return <OnboardingScreen />;
}
