import { apiRequest, HubApiError, type ApiOptions } from "@/lib/api";
import type { CatalogApp } from "@/lib/catalog";
import type { StatusView } from "@/lib/status";

export const ADAPTERS = "/api/v1/adapterkoppelingen";
export const APPS = {
  mediaguard: {
    naam: "MediaGuard",
    uitleg: "Open in MediaGuard als beheerder Instellingen → API-sleutels. Maak een sleutel met de rol Kijker en laat alle extra rechten uit.",
  },
  "media-source-optimizer": {
    naam: "Media Source Optimizer (MSO)",
    uitleg: "Machinesleutels maak je als beheerder in MSO onder Instellingen → Gebruikers. Voor de Hub is alleen het leesrecht (read) bedoeld. De Hub kan dit recht nog niet controleren en gebruikt alleen de openbare verbindingstest.",
  },
  my_house: {
    naam: "my_house",
    uitleg: "Open als beheerder de API-documentatie in my_house (/api/v1/docs). Maak bij de koppelcodes een eenmalige code met rol viewer (kijker) en doel hub. Neem de code en de server-ID uit hetzelfde antwoord over.",
  },
};
export type AppId = keyof typeof APPS;
export type Installatie = Pick<CatalogApp, "id" | "app_id" | "naam" | "aanwezig" | "deep_link" | "soort">;
export interface Koppeling {
  id: string;
  app_id: AppId;
  catalog_app_id: string;
  basis_url: string;
  laatste4: string;
  ingevoerd_op: string | null;
  version: number;
  verbinding: { status: string; observed_at: string | null; reason_code: string | null; laatste_status?: string | null };
}
export function veiligAdres(waarde: string) {
  try {
    const url = new URL(waarde);
    return url.protocol === "https:" && !url.username && !url.password && !/[?#\s]/.test(waarde);
  } catch {
    return false;
  }
}

export interface Pagina<T> { items: T[]; next_cursor: string | null }
export interface Installaties extends Pagina<Installatie> { inventaris: { status: string } }

export async function allePaginas<T extends Pagina<unknown>>(pad: string, opties?: ApiOptions) {
  const eerste = await apiRequest<T>(pad, opties);
  const items = [...eerste.data.items];
  let cursor = eerste.data.next_cursor;
  const gezien = new Set<string>();
  while (cursor) {
    if (gezien.has(cursor)) throw new HubApiError(502, "cursor_herhaald", "De lijst kon niet volledig worden gelezen.");
    gezien.add(cursor);
    const volgende = await apiRequest<T>(pad + "&cursor=" + encodeURIComponent(cursor), opties);
    items.push(...volgende.data.items);
    cursor = volgende.data.next_cursor;
  }
  return { ...eerste, data: { ...eerste.data, items, next_cursor: null } };
}

export type Veld = "adres" | "invoer" | "server" | "bevestiging";
export interface Probleem { tekst: string; veld?: Veld }

export function oorzaak(reden: string, app: AppId): Probleem {
  const huis = app === "my_house";
  switch (reden) {
    case "bron_koppelcode_ongeldig":
    case "bron_token_verlopen":
    case "bron_token_ingetrokken":
    case "bron_vernieuwing_mislukt":
      return { veld: "invoer", tekst: "De code of de toegang is ongeldig of verlopen. Maak in my_house een nieuwe koppelcode voor de Hub." };
    case "bron_credential_geweigerd":
    case "ongeldige_invoer":
      if (app === "media-source-optimizer") return { tekst: "MSO weigert de openbare test. Controleer in MSO of de statuspagina bereikbaar is." };
      return { veld: "invoer", tekst: huis ? "Controleer de code of maak in my_house een nieuwe koppelcode voor de Hub." : "De sleutel is ongeldig. Kopieer opnieuw de volledige kijker-sleutel uit MediaGuard." };
    case "bron_recht_ongeldig":
    case "bron_recht_geweigerd":
    case "key_too_privileged":
      return { veld: "invoer", tekst: "De rechten passen niet bij leestoegang. Kies in de app de rol kijker zonder extra rechten en maak nieuwe toegang voor de Hub." };
    case "adres_ongeldig":
    case "adres_niet_toegestaan":
    case "https_verplicht":
    case "doelbinding":
    case "doelbinding_ontbreekt":
    case "doelbinding_gewijzigd":
    case "redirect_niet_gevolgd":
      return { veld: "adres", tekst: "Het adres is geweigerd. Controleer het HTTPS-adres en de poort van deze installatie in de appcatalogus." };
    case "bron_identiteit_onbewezen":
    case "bron_identiteit_gewijzigd":
    case "bron_identiteit_onbekend":
      return { veld: "server", tekst: "De server is niet bevestigd. Vergelijk de server-ID met die bij de nieuwe koppelcode in my_house." };
    case "bron_onbereikbaar":
    case "niet_bereikbaar":
    case "tijdslimiet":
      return { tekst: "De app is niet bereikbaar. Controleer of de app draait en probeer de verbinding opnieuw te testen." };
    case "tls_fout":
      return { veld: "adres", tekst: "Het certificaat is geweigerd. Controleer de hostnaam en het certificaat van de app." };
    case "geen_alleen_lezen_bron":
      return { tekst: "MediaGuard biedt nog geen veilige leescontrole. Bekijk de status in MediaGuard zelf." };
    case "al_gekoppeld":
    case "precondition_failed":
    case "not_found":
      return { tekst: "De koppeling is intussen gewijzigd. Vernieuw de lijst en controleer de installatie opnieuw." };
    case "network_error":
      return { tekst: "De Hub is niet bereikbaar. Controleer je verbinding en probeer het opnieuw." };
    default:
      return { tekst: "De Hub kan de verbinding niet bevestigen. Controleer de instellingen in de app en probeer het opnieuw." };
  }
}

export function koppelstatus(koppeling: Koppeling | undefined, nu: number): { pil: StatusView; uitleg?: string } {
  if (!koppeling) return { pil: { tone: "unlinked", label: "Niet gekoppeld" } };
  const m = koppeling.verbinding;
  const tijd = m.observed_at ? Date.parse(m.observed_at) : NaN;
  const bekend = Number.isFinite(tijd) && tijd <= nu;
  if (m.reason_code && !["meting_verouderd", "meettijd_onbekend"].includes(m.reason_code)) {
    return { pil: { tone: "unknown", label: "Contact onbekend" }, uitleg: oorzaak(m.reason_code, koppeling.app_id).tekst };
  }
  // De adaptercontactproef bewaart een meting maximaal vijftien minuten. De bron kan al eerder verval melden.
  if (m.reason_code === "meting_verouderd" || (bekend && nu - tijd >= 900_000)) {
    return { pil: { tone: "stale", label: "Verouderd" }, uitleg: "De laatste contactmeting is verlopen. Test de verbinding opnieuw." };
  }
  if (m.status === "healthy" && bekend && !m.reason_code) {
    return { pil: { tone: "neutral", label: "Gekoppeld", icon: "gekoppeld" } };
  }
  if (m.status === "unknown" && !m.observed_at && (!m.reason_code || m.reason_code === "meettijd_onbekend")) {
    return { pil: { tone: "neutral", label: "Ingesteld" }, uitleg: "De bestemming is opgeslagen. Er is nog geen bevestigde contactmeting." };
  }
  return { pil: { tone: "unknown", label: "Onbekend" }, uitleg: "Er is geen bevestigde verbinding. Test de verbinding opnieuw." };
}
