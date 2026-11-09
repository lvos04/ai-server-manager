import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** Klassen samenvoegen (shadcn-conventie): latere Tailwind-klassen winnen van eerdere. */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
