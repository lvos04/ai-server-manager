import { Subnav } from "@/components/Subnav";

export const BACKUP_LINKS = [
  { href: "/backups", label: "Overzicht" },
  { href: "/backups/herstelpunten", label: "Herstelpunten" },
  { href: "/backups/extern", label: "Externe back-up" },
  { href: "/backups/hersteltests", label: "Hersteltests" },
  { href: "/backups/rampenscenarios", label: "Rampenscenario’s" },
];

export function BackupNav() {
  return <Subnav label="Back-uponderdelen" items={BACKUP_LINKS} />;
}
