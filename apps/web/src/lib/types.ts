/** Antwoordvormen van de Hub-API (zie docs/openapi/hub-api.openapi.json). Alleen de velden die de UI gebruikt. */

export type Role = "admin" | "operator" | "viewer" | "kind";

export interface User {
  id: string;
  username: string;
  display_name: string;
  role: Role;
  disabled: boolean;
  /** Noodaccount (contract 1.2 §4.1). */
  break_glass?: boolean;
  /** Herkomst van de gebruiker: lokaal of oidc. */
  auth_bron?: string;
  created_at: string | null;
  updated_at: string | null;
  version: number;
}

export interface SetupStatus {
  setup_vereist: boolean;
  uitleg: string;
}

export interface Me {
  user: User;
  sessie_id: string;
}

export interface LoginResult {
  user: User;
  csrf_token: string;
  sessie_verloopt_op: string;
}

export type DecisionStatus = "Open" | "Ingevuld" | "Getest" | "Geblokkeerd" | "N.v.t.";

export interface EvidenceRecord {
  id: string;
  bron: string;
  soort: string;
  omschrijving: string;
  referentie: string;
  resultaat: "geslaagd" | "mislukt";
  methode?: string | null;
  uitgevoerd_op: string;
  vastgelegd_door: string;
  vastgelegd_op: string;
  hoort_bij_versie: number;
}

export interface Measurement {
  status: "geslaagd" | "afwijking" | "mislukt" | "voorstel";
  reason_code: string | null;
  melding: string;
  advies: string;
  details: Record<string, unknown>;
  run_id: string | null;
  gemeten_op?: string;
  door?: string;
}

export interface Decision {
  id: string;
  titel: string;
  wat_vastleggen: string;
  gate: string;
  status: DecisionStatus;
  waarde: Record<string, unknown> | null;
  waarde_bron: string | null;
  bewijs: EvidenceRecord[];
  reden: string;
  ingevuld_door: string | null;
  ingevuld_op: string | null;
  getest_door: string | null;
  getest_op: string | null;
  laatste_meting: Measurement | null;
  meetbaar: boolean;
  nvt_toegestaan: boolean;
  vast: boolean;
  version: number;
  updated_at: string | null;
  schema?: JsonSchema;
}

export interface DecisionList {
  items: Decision[];
  telling: Partial<Record<DecisionStatus, number>>;
}

export interface GateReason {
  soort: string;
  id: string;
  status: string;
  tekst: string;
}

export interface Gate {
  id: string;
  naam: string;
  status: "toegestaan" | "geblokkeerd" | "unknown";
  toegestaan: boolean;
  redenen: GateReason[];
  afgeleid_op: string;
}

export interface TrueNasStatus {
  nas_url: string | null;
  nas_adres_bron: string | null;
  api_key: { ingesteld: boolean; laatste4: string | null; ingesteld_op: string | null; ingesteld_door: string | null };
  tls: { modus: string; vingerafdruk: string | null; bevestigd_door: string | null; bevestigd_op: string | null };
  laatste_test: {
    op: string | null;
    url: string | null;
    status: string | null;
    reason_code: string | null;
    melding: string;
    advies: string;
  } | null;
  alleen_lezen: boolean;
}

export interface TrueNasTest {
  verbonden: boolean;
  status: "ok" | "unknown";
  reason_code: string | null;
  melding: string;
  advies: string;
  nas_url: string | null;
  nas_versie: string | null;
  key_scope: string | null;
  tls_modus: string | null;
  capabilities: { bron: string; nas_versie: string; lezen: Record<string, string | null> } | null;
  details: Record<string, unknown>;
  getest_op: string;
}

export interface KindState {
  kind: string;
  status: "ok" | "unknown";
  reason_code: string | null;
  melding: string;
  advies: string;
  observed_at: string | null;
  laatste_poging: string | null;
  verouderd: boolean;
  bron: { methode: string | null; nas: string } | null;
}

export interface InventorySummary {
  nas_url: string | null;
  laatste_run: {
    id: string;
    gestart: string | null;
    klaar: string | null;
    status: string;
    reason_code: string | null;
    nas_versie: string | null;
    capability_bron: string | null;
    key_scope: string | null;
    aanleiding: string;
  } | null;
  soorten: (KindState & { aantal: number | null; pad: string })[];
  ttl_seconden: number;
  alleen_lezen: boolean;
}

export interface InventoryKind<T> extends KindState {
  items?: T[];
  data?: T;
  next_cursor?: string | null;
  totaal?: number;
}

export interface Pool {
  naam: string;
  status: string | null;
  gezond: boolean | null;
  gebruik_pct: number | null;
  vrij_bytes: number | null;
  grootte_bytes: number | null;
  gebruikt_bytes: number | null;
  waarschuwing?: boolean;
  scrub: { staat: string | null; fouten: number | string | null; functie: string | null; laatst_beeindigd: string | null };
}

export interface Dataset {
  naam: string;
  pool: string;
  type: string | null;
  mountpoint: string | null;
  versleuteld: boolean | null;
  gebruikt_bytes: number | null;
  beschikbaar_bytes: number | null;
}

export interface AppInfo {
  naam: string;
  staat: string | null;
  images: { image: string; tag: string | null; repository: string | null; digest: string | null }[];
  poorten: { host_ip: string | null; protocol: string; host_poort: number | null; container_poort: number | null }[];
  opslag: { bron: string | null; doel: string | null; type: string | null }[];
  versie: string | null;
  app_versie: string | null;
  custom_app: boolean | null;
  herkend_als: string | null;
  upgrade_beschikbaar: boolean | null;
  status: string;
  gezondheid: string;
  gezondheid_toelichting: string;
}

export interface Gpu {
  vendor: string | null;
  pci_slot: string | null;
  herkend_als: string | null;
  render_node: string | null;
  beschrijving: string | null;
  fout: string | null;
}

export interface Disk {
  naam: string;
  pool: string | null;
  type: string | null;
  model: string | null;
  grootte_bytes: number | null;
  serienummer_laatste4: string | null;
}

export interface SmartResult {
  disk: string;
  aantal_tests: number;
  laatste_test: { status: string | null; omschrijving: string | null; status_tekst: string | null; levensduur_uren: number | null } | null;
}

export interface AlertInfo {
  uuid: string;
  tijd: string | null;
  tekst: string;
  klasse: string | null;
  niveau: string | null;
  genegeerd: boolean | null;
}

export interface SystemInfo {
  versie: string | null;
  info: {
    versie?: string | null;
    hostnaam?: string | null;
    model?: string | null;
    cpu?: string | null;
    cores?: number | null;
    geheugen_bytes?: number | null;
    uptime_seconden?: number | null;
    tijdzone?: string | null;
  } | null;
}

export interface Job {
  id: string;
  soort: string;
  status: "queued" | "running" | "done" | "failed";
  aangevraagd_door: string;
  aangemaakt: string | null;
  gestart: string | null;
  klaar: string | null;
  resultaat: Record<string, unknown>;
}

export interface RegistryItem {
  app: string;
  herkend_als: string | null;
  basis_url: string | null;
  reden_geen_url: string | null;
  hostpoorten: number[];
  verouderd: boolean;
}

export interface CoverageApp {
  app: string;
  herkend_als: string | null;
  datasets: string[];
  lokaal_snapshot: string;
  extern: string;
  extern_herstelgarantie: boolean;
  db_export: { status: string; bron: string; reason_code: string | null; melding?: string; laatste?: string; leeftijd_uren?: number };
  laatste_hersteltest: { resultaat: string; uitgevoerd_op: string; soort: string } | null;
  volledige_appbackup: boolean;
  redenen: string[];
  rpo_rto: {
    bron: string | null;
    rpo_uren: number | null;
    rto_uren: number | null;
    gemeten_leeftijd_herstelpunt_uren: number | null;
    rpo_status: string;
    rpo_reden: string;
    rto_status: string;
  };
}

export interface CoverageDataset {
  dataset: string;
  pool: string | null;
  apps: string[];
  lokaal_snapshot: { status: string; reason_code: string | null; laatste_snapshot?: string | null; leeftijd_uren?: number | null; observed_at?: string | null };
  extern: { status: string; herstelgarantie: boolean; opmerking: string; onedrive_gedetecteerd?: boolean; cloud_sync: { omschrijving: string | null; provider: string | null; laatste_job_staat: string | null; laatste_job_beeindigd: string | null }[] };
  laatste_hersteltest: { resultaat: string; uitgevoerd_op: string } | null;
}

export interface Coverage {
  apps: CoverageApp[];
  datasets: CoverageDataset[];
  bronnen: Record<string, { status: string; reason_code: string | null; observed_at: string | null; verouderd: boolean }>;
  opmerking: string;
  afgeleid_op: string;
}

export interface SelfBackup {
  id: string;
  aanleiding: string;
  status: string;
  reason_code: string | null;
  melding: string | null;
  sha256: string | null;
  inhoudsopgave_items: number | null;
  gestart_op: string | null;
  beeindigd_op: string | null;
}

export interface SelfBackupList {
  items: SelfBackup[];
  laatste_geverifieerd: SelfBackup | null;
}

export interface Session {
  id: string;
  aangemaakt: string | null;
  laatst_gezien: string | null;
  verloopt: string | null;
  user_agent: string;
  ip: string;
  huidige: boolean;
}

export interface AuditItem {
  [key: string]: unknown;
}

// Minimale JSON-schemavorm (zoals pydantic hem exporteert).
export interface JsonSchema {
  type?: string | string[];
  title?: string;
  description?: string;
  properties?: Record<string, JsonSchema>;
  required?: string[];
  items?: JsonSchema;
  anyOf?: JsonSchema[];
  $ref?: string;
  $defs?: Record<string, JsonSchema>;
  enum?: (string | number | boolean)[];
  const?: string | number | boolean;
  default?: unknown;
  format?: string;
  pattern?: string;
  minimum?: number;
  maximum?: number;
  exclusiveMinimum?: number;
  minLength?: number;
  maxLength?: number;
  minItems?: number;
  maxItems?: number;
  additionalProperties?: boolean;
}
