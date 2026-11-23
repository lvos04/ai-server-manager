import { notFound } from "next/navigation";
import { PageHeader } from "@/components/PageHeader";
import { BackupNav, BACKUP_LINKS } from "../BackupNav";
import { Extern, Herstelpunten, Rampenscenarios } from "../BackupDetails";
import { Hersteltests } from "../Hersteltests";

export default async function Page({ params, searchParams }: { params: Promise<{ onderdeel: string }>; searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const { onderdeel } = await params;
  const { app, scenario, punt } = await searchParams;
  const titel = BACKUP_LINKS.find(l => l.href === `/backups/${onderdeel}`)?.label;
  if (!titel) notFound();
  return <>
    <PageHeader title={titel} kruimel={[{ label: "Backups", href: "/backups" }, { label: titel }]} />
    <BackupNav />
    {onderdeel === "extern" && <Extern />}
    {onderdeel === "herstelpunten" && <Herstelpunten initApp={typeof app === "string" ? app : undefined} />}
    {onderdeel === "hersteltests" && <Hersteltests initPunt={typeof punt === "string" ? punt : undefined} />}
    {onderdeel === "rampenscenarios" && <Rampenscenarios scenario={typeof scenario === "string" ? scenario : undefined} />}
  </>;
}
