/**
 * Nederlandse uitleg per besluit (D01–D18) en veldlabels voor de wizard. Bewust GEEN voorbeeldwaarden (geen IP's,
 * poolnamen of versies): die komen van de gebruiker of uit een TrueNAS-meting (contract §1, ADR-0007).
 */

export interface DecisionHelp {
  waarom: string;
  waar: string;
  hoe_getest: string;
}

export const DECISION_HELP: Record<string, DecisionHelp> = {
  D01: {
    waarom: "Methodenamen en antwoorden van de TrueNAS-API verschillen per versie. Connectors worden pas tegen de echte NAS gebouwd als de versie vaststaat.",
    waar: "TrueNAS-web-UI → System → General (of het dashboard). Makkelijker: koppel TrueNAS alleen-lezen en kies ‘Meten via TrueNAS’.",
    hoe_getest: "Getest door een meting (system.version) of een vastgelegd bewijsrecord.",
  },
  D02: {
    waarom: "Mounts en back-ups mogen alleen naar datasets die echt bestaan en waarvan bekend is waarvoor ze dienen.",
    waar: "TrueNAS-web-UI → Datasets. ‘Meten via TrueNAS’ toont de gemeten pools en datasets als voorstel; jij kiest welke appdata en welke media zijn.",
    hoe_getest: "Getest als een meting bevestigt dat alle opgegeven pools en datasets op de NAS bestaan.",
  },
  D03: {
    waarom: "Apps bereiken elkaar via het NAS-adres en de hostpoort. De Hub neemt dat adres nooit aan: jij vult het in, daarna wordt het gemeten.",
    waar: "Het adres waarmee je de TrueNAS-web-UI opent (zonder https:// en zonder pad); zie ook TrueNAS → Network.",
    hoe_getest: "Getest als de Hub op dit adres verbinding maakt en zich met de alleen-lezen-key aanmeldt.",
  },
  D04: {
    waarom: "De back-upgate blijft dicht zolang niet bekend is hoe de externe kopie naar OneDrive gemaakt wordt.",
    waar: "TrueNAS-web-UI → Data Protection → Cloud Sync Tasks (of de tool die je gebruikt). Leg vast wáár de herstelgegevens liggen, nooit de sleutel of het wachtwoord zelf.",
    hoe_getest: "Getest alleen met een vastgelegd bewijsrecord.",
  },
  D05: {
    waarom: "Een geslaagde synchronisatie is geen herstelgarantie. Pas een echte terugzet-test van een foto én een database-export bewijst dat herstel werkt.",
    waar: "Zet een foto en een database-export uit OneDrive terug in een geïsoleerde omgeving (nooit over productie heen) en leg de tests vast onder Backups.",
    hoe_getest: "Getest pas als er geslaagde hersteltests van een foto én een database zijn vastgelegd en een bewijsrecord is toegevoegd.",
  },
  D06: {
    waarom: "Bij een pool die niet gezond is of een onbekende status worden geen opslag- of datamutaties toegestaan.",
    waar: "TrueNAS-web-UI → Storage (poolstatus, scrubs, schijven). ‘Meten via TrueNAS’ leest dit alleen-lezen uit.",
    hoe_getest: "Getest door een meting (pool.query, SMART-resultaten waar beschikbaar).",
  },
  D07: {
    waarom: "Updates en upgrades kunnen pas veilig als de huidige versies en image-tags vaststaan.",
    waar: "TrueNAS-web-UI → Apps. ‘Meten via TrueNAS’ leest de geïnstalleerde apps en image-tags uit (app.query).",
    hoe_getest: "Getest door een meting.",
  },
  D08: {
    waarom: "Transcoden moet de juiste GPU gebruiken: de Arc A310 en de UHD 770 mogen niet verwisseld worden.",
    waar: "Server → GPU's toont de gevonden GPU's (PCI-slot). De koppeling met /dev/dri/renderD… is in deze versie nog niet automatisch meetbaar: vul hem alleen in als je hem zeker weet, anders laat je D08 Open.",
    hoe_getest: "Getest alleen met een vastgelegd bewijsrecord.",
  },
  D09: {
    waarom: "Een AI-agent met cloudmodel mag alleen binnen het inbegrepen tegoed werken: harde stop en nooit betaalde overage. AI staat standaard uit.",
    waar: "De officiële console van de aanbieder (organisatie en inbegrepen maandbudget). Wil je geen cloud-AI, zet dit besluit dan op N.v.t.",
    hoe_getest: "Getest alleen met een vastgelegd bewijsrecord.",
  },
  D10: {
    waarom: "Vast besluit van de gebruiker: de bestaande mini-pc blijft voor de videoapp en andere projecten en draait geen Home Hub-diensten.",
    waar: "—",
    hoe_getest: "Vast besluit; niet wijzigbaar in de wizard.",
  },
  D11: {
    waarom: "Een DNS-overstap (AdGuard) kan het hele netwerk platleggen. Eerst moet vaststaan hoe je terugkomt bij een storing.",
    waar: "De beheerpagina van je router: model, huidige DNS-servers en wie poort 53 gebruikt. Leg ook vast hoe je bij een storing weer bij de router komt.",
    hoe_getest: "Getest alleen met een vastgelegd bewijsrecord. N.v.t. als je geen DNS-filter wilt.",
  },
  D12: {
    waarom: "De Gree-airco wordt pas aangestuurd als lokale besturing met een echte readback is aangetoond.",
    waar: "Typeplaatje en app van de airco (type en firmware).",
    hoe_getest: "Getest alleen met een vastgelegd bewijsrecord (echte bind/readback).",
  },
  D13: {
    waarom: "Zigbee installeren vraagt het vaste seriële pad van de dongle, zodat een herstart het apparaat niet verwisselt.",
    waar: "Dongle en adapter (typeplaatje); het pad /dev/serial/by-id/… zoals TrueNAS het toont bij apparaten.",
    hoe_getest: "Getest alleen met een vastgelegd bewijsrecord.",
  },
  D14: {
    waarom: "Een exact energiedashboard vraagt bekende meters. De boiler-Energy Socket wordt alleen gemeten en nooit geschakeld.",
    waar: "De HomeWizard-app (P1-meter, Energy Sockets).",
    hoe_getest: "Getest alleen met een vastgelegd bewijsrecord.",
  },
  D15: {
    waarom: "Een overstap van mediaserver mag geen bestaande tv's, telefoons of spelers breken.",
    waar: "Een lijst van de apparaten waarop je kijkt en hoe ze zich offline moeten gedragen.",
    hoe_getest: "Getest alleen met een vastgelegd bewijsrecord.",
  },
  D16: {
    waarom: "Herstelbeleid per app: hoeveel uur data je maximaal kwijt mag raken (RPO) en hoe lang een app maximaal plat mag liggen (RTO).",
    waar: "Jouw eigen keuze per app. De dekking onder Backups vergelijkt de gemeten herstelpunten met deze doelen.",
    hoe_getest: "Voor de herstelbeleid-gate is Ingevuld genoeg; Getest met een bewijsrecord.",
  },
  D17: {
    waarom: "Inloggen via Authentik/OIDC kan pas als het domein, HTTPS en een recovery-account vaststaan.",
    waar: "Je domeinnaam en certificaat; de rollen die je wilt gebruiken.",
    hoe_getest: "Getest alleen met een vastgelegd bewijsrecord. N.v.t. als je bij lokale accounts blijft.",
  },
  D18: {
    waarom: "Navidrome komt er alleen bij als het na een gebruikerstest echt meerwaarde heeft boven Jellyfin.",
    waar: "Jouw eigen test en afweging.",
    hoe_getest: "Ingevuld is genoeg voor deze optionele gate.",
  },
};

export const FIELD_LABELS: Record<string, string> = {
  versie: "TrueNAS-versie (exact, zoals de NAS hem meldt)",
  api_versie: "API-versie (optioneel)",
  pools: "Pools",
  appdata_datasets: "Datasets voor appdata",
  media_datasets: "Datasets voor media",
  nas_adres: "NAS-adres (LAN-IP of hostnaam)",
  https_poort: "HTTPS-poort",
  hostnamen: "Hostnamen",
  vpn: "VPN",
  tunnel: "Tunnel",
  open_poorten_firewall: "Open poorten in de firewall",
  methode: "Methode",
  taken: "Taken",
  versleuteld: "Versleuteld",
  scope: "Scope (datasets of paden)",
  retentie: "Retentie",
  herstel_credentials_locatie: "Waar liggen de herstelgegevens",
  foto_hersteld: "Foto hersteld",
  db_export_hersteld: "Database-export hersteld",
  omgeving: "Geïsoleerde omgeving",
  uitgevoerd_op: "Uitgevoerd op",
  referentie: "Referentie",
  naam: "Naam",
  status: "Status",
  gezond: "Gezond",
  gebruik_pct: "Gebruik (%)",
  laatste_scrub: "Laatste scrub",
  scrub_fouten: "Scrubfouten",
  smart_ok: "SMART in orde",
  snapshot_capaciteit_ok: "Ruimte voor snapshots in orde",
  apps: "Apps",
  image: "Image",
  staat: "Staat",
  gpus: "GPU's",
  rol: "Rol",
  pci_slot: "PCI-slot",
  render_node: "Render-node",
  qsv_apps: "Apps met Quick Sync (QSV)",
  account_gekoppeld: "Account gekoppeld",
  inbegrepen_maandbudget: "Inbegrepen maandbudget",
  harde_stop: "Harde stop bij 0 resterend tegoed",
  overage_toegestaan: "Betaalde overage toegestaan",
  mini_pc_uitgesloten: "Mini-pc uitgesloten van Home Hub-diensten",
  doel: "Doel",
  routermodel: "Routermodel",
  huidige_dns: "Huidige DNS-servers",
  poort53_eigenaar: "Wie gebruikt poort 53",
  rollback_toegang: "Hoe kom je terug bij een storing",
  gree_type: "Gree-type",
  firmware: "Firmware",
  lokaal_udp: "Lokale UDP-besturing",
  dongle: "Dongle",
  adapter: "Adapter",
  serial_by_id: "Serieel pad (/dev/serial/by-id/…)",
  sensortypes: "Sensortypes",
  p1_meter: "P1-meter aanwezig",
  energy_socket_boiler_alleen_meten: "Boiler-Energy Socket alleen meten (nooit schakelen)",
  airco_1fase_meter: "Aparte 1-fase-meter voor de airco",
  tvs: "Tv's",
  telefoons: "Telefoons",
  spelers: "Spelers (Android TV, Apple TV, …)",
  offline_gedrag: "Gewenst offline gedrag",
  per_app: "Per app",
  app_id: "App-ID",
  rpo_uren: "RPO (uren)",
  rto_uren: "RTO (uren)",
  domeinnaam: "Domeinnaam",
  https: "HTTPS",
  recovery_account: "Recovery-account aanwezig",
  rollen: "Rollen",
  navidrome_gewenst: "Navidrome gewenst",
  toelichting: "Toelichting",
};

export const ENUM_LABELS: Record<string, string> = {
  truenas_cloud_sync: "TrueNAS Cloud Sync",
  rclone: "rclone",
  restic: "restic",
  onedrive_client: "OneDrive-client",
  anders: "Anders",
  a310: "Intel Arc A310",
  uhd770: "Intel UHD 770",
  ondersteund: "Ondersteund",
  niet_ondersteund: "Niet ondersteund",
  onbekend: "Onbekend",
};

/** Extra hulptekst per veld (aanvullend op de beschrijving uit het schema). Nooit een voorbeeldwaarde. */
export const FIELD_HELP: Record<string, string> = {
  nas_adres: "Precies het adres waarmee jij de TrueNAS-web-UI opent, zonder https:// en zonder poort of pad.",
  https_poort: "Alleen invullen als TrueNAS niet op de standaard-HTTPS-poort draait.",
  herstel_credentials_locatie: "Alleen de plek (bijv. welke kluis of map), nooit de sleutel of het wachtwoord zelf.",
  render_node: "Formaat /dev/dri/renderD gevolgd door drie cijfers.",
  serial_by_id: "Het volledige pad zoals TrueNAS het toont.",
  rpo_uren: "Maximaal aantal uren data dat verloren mag gaan.",
  rto_uren: "Maximaal aantal uren dat de app plat mag liggen.",
};

export function fieldLabel(key: string, fallback?: string): string {
  return FIELD_LABELS[key] ?? fallback ?? key;
}

export function enumLabel(value: string): string {
  return ENUM_LABELS[value] ?? value;
}

export const EVIDENCE_KINDS: { value: string; label: string }[] = [
  { value: "handmatige_test", label: "Handmatige test" },
  { value: "meting_extern", label: "Meting met een ander hulpmiddel" },
  { value: "document", label: "Document" },
  { value: "hersteltest", label: "Hersteltest" },
  { value: "screenshot", label: "Schermafbeelding" },
];

/** Volgorde van de wizardstappen (de besluiten zelf volgen de nummering). */
export const MEASURABLE_IDS = ["D01", "D02", "D03", "D06", "D07"];
