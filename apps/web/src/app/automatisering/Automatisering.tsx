"use client";

import Link from "next/link";
import { Freshness } from "@/components/Freshness";
import { Leesstand } from "@/components/Leesstand";
import { Melding } from "@/components/Melding";
import { PageHeader } from "@/components/PageHeader";
import { ResponsiveList } from "@/components/ResponsiveList";
import { StatusBadge } from "@/components/StatusBadge";
import { Subnav } from "@/components/Subnav";
import { Button } from "@/components/ui/button";
import { RisicoBadge } from "@/components/ActiePreview";
import { risicoKlasse, statusView, weigerReden, type ActieVerzoek } from "@/lib/acties";
import { UUID } from "@/lib/backups";
import { FLOWHERSTEL, flowStatus, herstelbewijs, menselijkHerstel } from "@/lib/flowherstel";
import { formatDateTime, parseIso } from "@/lib/format";
import { useRole } from "@/lib/session";
import { useMeting, usePaginaLijst } from "@/lib/use-meting";

const TABS = [
  ["flows", "Flows"], ["detail", "Flowdetail"], ["testmodus", "Testmodus"],
  ["eventtypen", "Eventtypen"], ["historie", "Uitvoeringshistorie"], ["versies", "Versies en herstel"],
] as const;

const links = TABS.map(([id, label]) => ({ label, href: id === "flows" ? "/automatisering" : `/automatisering/${id}` }));
interface EventRij { event_id: string; source_app: string; event_type: string; schema_version: string; timestamp_utc: string }
const eventSleutel = (e: EventRij) => e.event_id;
const verzoekSleutel = (v: ActieVerzoek) => v.request_id;
const TYPEN = new Set(["flow.action.requested", "energy.reading.recorded", "network.device.discovered"]);
const ACTIES = new Set(["app.start", "app.stop", "app.restart", "app.install", "app.update", "app.rollback", "app.uninstall",
  "sso.oidc.hub.register", "zfs.snapshot.create", "zfs.snapshot.clone_to_sandbox", "notification.send", FLOWHERSTEL, "sso.sessions.revoke"]);

function Gebeurtenissen() {
  const bron = usePaginaLijst<EventRij>("/api/v1/events?source_app=home-control-hub&limit=50", eventSleutel);
  const rijen = bron.data?.items.filter(e => e.source_app === "home-control-hub" && UUID.test(e.event_id)) ?? [];
  return <section className="card stack"><h2>Ontvangen gebeurtenissen</h2>
    <p>Catalogus van eventtypen nog niet beschikbaar.</p>
    <Leesstand bron={bron} naam="Gebeurtenissen" />
    {bron.data && !rijen.length && !bron.stale && <p>Geen gebeurtenissen ontvangen voor dit filter{bron.data.next_cursor ? " op deze pagina" : ""}.</p>}
    <ResponsiveList items={rijen} sleutel={eventSleutel} label="Gebeurtenissen van home-control-hub" tabelVanaf={768} kolommen={[
      { kop: "Type", cel: e => TYPEN.has(e.event_type) ? e.event_type : "Onbekend gebeurtenistype" },
      { kop: "Bron", cel: () => "home-control-hub" }, { kop: "Schemaversie", cel: e => e.schema_version === "1.0" ? "1.0" : "Onbekend" },
      { kop: "Tijdstip", cel: e => formatDateTime(e.timestamp_utc) },
    ]} />
    {bron.data?.next_cursor && <Button onClick={bron.meer}>Meer gebeurtenissen laden</Button>}
  </section>;
}

function flowId(v: ActieVerzoek) {
  const id = v.actor?.id?.startsWith("flow:") && v.actor.id.slice(5);
  return v.actor?.type === "flow" && id && UUID.test(id) ? id : null;
}

function Historie({ herstel = false, flow }: { herstel?: boolean; flow?: string }) {
  const pad = herstel ? `/api/v1/actions?action_id=${FLOWHERSTEL}&limit=50` : "/api/v1/actions?limit=50";
  const bron = usePaginaLijst<ActieVerzoek>(pad, verzoekSleutel);
  const rijen = bron.data?.items.filter(v => UUID.test(v.request_id) && (herstel ? v.action_id === FLOWHERSTEL
    : v.actor?.type === "flow" && (!flow || flowId(v) === flow))) ?? [];
  return <section className="card stack"><h2>{herstel ? "Herstelverzoeken" : "Actieverzoeken van flows"}</h2>
    <p>{herstel ? "Momentopnamen en flowversies zijn niet beschikbaar. Flowherstel loopt via een menselijk R2-voorstel met preview en goedkeuring."
      : "Het volledige runlog van Node-RED is niet beschikbaar. De Hub toont de ontvangen actieverzoeken."}</p>
    <Leesstand bron={bron} naam={herstel ? "Herstelstatus" : "Uitvoeringshistorie"} />
    {bron.data && !rijen.length && !bron.stale && <p>{bron.data.next_cursor ? "Op deze pagina geen passende verzoeken." : herstel ? "Geen herstelverzoeken gevonden." : "Geen actieverzoeken van flows."}</p>}
    <ResponsiveList items={rijen} label={herstel ? "Menselijke herstelvoorstellen" : "Actieverzoeken"} sleutel={verzoekSleutel} kolommen={[
      { kop: "Actie", cel: v => <><strong className="break-all">{ACTIES.has(v.action_id) ? v.action_id : "Actie niet beschikbaar"}</strong>
        {flowId(v) && <p><Link className="losse-link break-all" href={`/automatisering/detail?flow=${flowId(v)}`}>Flow {flowId(v)}</Link></p>}</> },
      { kop: "Gevraagd", cel: v => formatDateTime(v.aangemaakt_op) },
      { kop: "Goedkeuring", cel: v => <><RisicoBadge klasse={v.risk_class} /><p>{typeof v.goedkeuring_nodig !== "boolean" || !risicoKlasse(v.risk_class) ? "Vereiste onbekend" : v.goedkeuring_nodig ? "Menselijke goedkeuring vereist" : "Geen aparte goedkeuring vereist"}</p></> },
      { kop: "Stand", cel: v => <><StatusBadge view={statusView(flowStatus(v, bron.stale))} />{v.status === "afgewezen" && <p>{weigerReden(v.resultaat)}</p>}
        {herstel && <p className="break-all">Momentopname · {herstelbewijs(v) ?? "Niet beschikbaar"}</p>}</> },
      { kop: "Verloop", cel: v => (herstel && !menselijkHerstel(v)) || (!herstel && !flowId(v))
        ? "Voorstel niet beschikbaar" : <Link className="losse-link" href={`/goedkeuringen/${v.request_id}`}>Bekijk actie-preview<span className="sr-only"> {v.request_id}</span></Link> },
    ]} />
    {bron.data?.next_cursor && <Button onClick={bron.meer}>Meer verzoeken laden</Button>}
  </section>;
}

function Flowbron({ onderdeel, flow }: { onderdeel: string; flow?: string }) {
  const rol = useRole();
  const register = useMeting<{ observed_at: string | null; status: string }>("/api/v1/registry/services");
  return <>
    <section className="card stack"><h2>{onderdeel === "testmodus" ? "Testuitkomst onbekend" : onderdeel === "detail" ? "Flowdetail onbekend" : "Flowstatus onbekend"}</h2>
      <Melding soort="nogniet" titel="Nog niet beschikbaar"><p>{onderdeel === "testmodus" ? "Testresultaten komen uit Node-RED. Zandbakbewijs is niet beschikbaar."
        : onderdeel === "detail" ? "Flowdetails nog niet beschikbaar. De trigger en de goedkeuringsvereisten per geconfigureerde actie zijn onbekend."
        : "De Hub ontvangt geen flowlijst. Status per flow, trigger, laatste uitvoering en aantal acties zijn onbekend."}</p></Melding>
      <p>Laatste flowstand · tijdstip niet beschikbaar.</p>
      <Leesstand bron={register} naam="Diensteninventaris" />
      <Freshness observedAt={parseIso(register.data?.observed_at)?.toISOString()} bron="Diensteninventaris" label="Laatste inventarisatie" verouderd={register.stale || register.data?.status !== "ok"} />
      <h3>Openen in Node-RED</h3><p>{rol === "admin" ? "Editoradres niet bevestigd." : "Alleen een beheerder kan de editor openen."}</p>
    </section>
    {onderdeel === "detail" && (flow && UUID.test(flow) ? <Historie flow={flow} /> : <p>Geen voorstel geselecteerd.</p>)}
    {onderdeel === "flows" && <Link href="/instellingen/monitoring#monitorplan" className="losse-link">Bekijk het monitorplan per app</Link>}
  </>;
}

export function Automatisering({ onderdeel, flow }: { onderdeel: string; flow?: string }) {
  const titel = TABS.find(([id]) => id === onderdeel)?.[1] ?? "Flows";
  return <><PageHeader title={onderdeel === "flows" ? "Automatisering" : titel} />
    <Subnav items={links} label="Automatisering" />
    <div className="stack">{onderdeel === "eventtypen" ? <Gebeurtenissen /> : onderdeel === "historie" || onderdeel === "versies"
      ? <Historie key={onderdeel} herstel={onderdeel === "versies"} /> : <Flowbron onderdeel={onderdeel} flow={flow} />}</div>
  </>;
}
