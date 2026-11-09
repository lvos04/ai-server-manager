import type { Metadata } from "next";
import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";

export const metadata: Metadata = { title: "Executor" };

export default function Page() {
  return (
    <>
      <PageHeader
        title="Executor installeren en koppelen"
        intro="De executor is de enige app met een TrueNAS-key met schrijfrechten. Hij voert alleen door de Hub ondertekende, goedgekeurde acties uit uit een vaste lijst — nooit shell, sudo of Docker."
      />
      <div className="stack">
        <section className="card stack" aria-labelledby="status" data-testid="executor-status">
          <div className="stat-head">
            <h2 id="status">Status</h2>
            <StatusBadge view={{ tone: "neutral", label: "Koppelen volgt in fase P2" }} />
          </div>
          <p>
            <strong>Eerlijk:</strong> in deze versie (fase P0) kan de Hub de executor nog niet koppelen en weet hij dus ook
            niet of de executor draait: de status is <strong>onbekend</strong>. De executor zelf voert in P0 niets uit; zijn
            lijst met toegestane acties is leeg en weigert alles.
          </p>
          <p>
            Daardoor blijven de gates ‘Apps installeren’ en ‘R2/R3-acties’ dicht. Zie <Link href="/onboarding">Wat mag nu?</Link>
          </p>
        </section>
        <section className="card stack" aria-labelledby="installeren">
          <h2 id="installeren">1. Installeren als tweede Custom App (nu al mogelijk)</h2>
          <p>In de TrueNAS-web-UI: Apps → Discover Apps → Custom App. Geen YAML, geen terminal.</p>
          <dl className="kv">
            <dt>Application Name</dt>
            <dd>
              <code>ai-server-manager-executor</code>
            </dd>
            <dt>Image</dt>
            <dd>
              Repository <code>ghcr.io/lvos04/ai-server-manager-executor</code>, Tag: dezelfde exacte versie als de Hub (nooit{" "}
              <code>latest</code>)
            </dd>
            <dt>Poort</dt>
            <dd>Container Port 30410, Host Port 30410 (of een andere vrije poort), TCP</dd>
            <dt>Opslag</dt>
            <dd>
              Host Path naar een <strong>eigen</strong> dataset (niet die van de Hub), Mount Path <code>/appdata</code>
            </dd>
            <dt>Environment</dt>
            <dd>leeg laten — geen wachtwoorden of keys in het formulier</dd>
            <dt>Security</dt>
            <dd>Privileged uit, geen extra capabilities, Custom User uit, Host Network uit, geen GPU</dd>
          </dl>
          <p className="meta">
            Na installatie toont <code>http://&lt;NAS-adres&gt;:30410</code> de statuspagina ‘nog niet gekoppeld’. Voer daar nu
            nog <strong>geen</strong> TrueNAS-key in.
          </p>
        </section>
        <section className="card stack" aria-labelledby="koppelen">
          <h2 id="koppelen">2. Koppelen (volgt in fase P2)</h2>
          <ol className="howto">
            <li>De Hub toont hier straks een eenmalige koppelcode (30 minuten geldig).</li>
            <li>
              Je opent de statuspagina van de executor en vult daar de koppelcode én een TrueNAS-API-key met schrijfrechten in.
              Die key voer je <strong>alleen</strong> op de executorpagina in; de Hub ziet hem nooit.
            </li>
            <li>Executor en Hub wisselen publieke sleutels uit; daarna toont de executor alleen de laatste 4 tekens van de key.</li>
          </ol>
          <p className="muted">Deze stap is nog niet gebouwd; er staat daarom geen knop of invoerveld.</p>
        </section>
      </div>
    </>
  );
}
