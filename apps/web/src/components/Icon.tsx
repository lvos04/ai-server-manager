import type { IconName } from "@/lib/nav";

// Eenvoudige lijniconen (24×24), zonder externe bibliotheek. Altijd decoratief: de tekst ernaast is het label.
const PATHS: Record<IconName, string> = {
  home: "M3 11.5 12 4l9 7.5M5.5 10v9.5h5v-5h3v5h5V10",
  apps: "M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z",
  alert: "M12 3 2.5 20h19L12 3zm0 6v5m0 3v.5",
  ai: "M12 3l1.8 4.7L18.5 9.5l-4.7 1.8L12 16l-1.8-4.7L5.5 9.5l4.7-1.8L12 3zM18 15l.9 2.1 2.1.9-2.1.9L18 21l-.9-2.1-2.1-.9 2.1-.9L18 15z",
  more: "M5 12h.01M12 12h.01M19 12h.01",
  server: "M4 4h16v6H4zM4 14h16v6H4zM8 7h.01M8 17h.01",
  media: "M4 5h16v14H4zM10 9l5 3-5 3V9z",
  house: "M4 10.5 12 4l8 6.5V20H4v-9.5zM9.5 20v-5h5v5",
  network: "M12 4v6M5 20v-4h14v4M12 10v6M5 16v-2h14v2M9 4h6",
  flow: "M5 6h5v5H5zM14 13h5v5h-5zM10 8.5h3a2 2 0 0 1 2 2V13",
  backup: "M12 3a9 9 0 1 0 9 9M12 7v5l3 2M21 3v5h-5",
  costs: "M15.5 7.5A5 5 0 1 0 15.5 16.5M5 10.5h8M5 13.5h8",
  settings: "M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6zM19.4 13.5l1.6 1.2-2 3.5-1.9-.7a7 7 0 0 1-1.7 1l-.3 2h-4l-.3-2a7 7 0 0 1-1.7-1l-1.9.7-2-3.5 1.6-1.2a7 7 0 0 1 0-3l-1.6-1.2 2-3.5 1.9.7a7 7 0 0 1 1.7-1l.3-2h4l.3 2a7 7 0 0 1 1.7 1l1.9-.7 2 3.5-1.6 1.2a7 7 0 0 1 0 3z",
  wizard: "M4 6h10M4 12h16M4 18h10M17 4l3 3-3 3",
  logout: "M10 5H5v14h5M14 8l4 4-4 4M18 12H9",
};

export function Icon({ name, size = 22 }: { name: IconName; size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={name === "more" ? 3 : 1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      <path d={PATHS[name]} />
    </svg>
  );
}
