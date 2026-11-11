import type { Metadata } from "next";
import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { Melding } from "@/components/Melding";
import { ExecutorKoppelen } from "./ExecutorKoppelen";

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
          <h2 id="status">Status</h2>
          <p>
            De executor voert alleen door de Hub ondertekende acties uit een vaste lijst uit (apps starten, stoppen, herstarten,
            installeren, verwijderen zonder data, bijwerken en terugzetten, en snapshots maken). Hij controleert elk verzoek zelf
            opnieuw en leest na afloop terug of de wijziging klopt; wijkt er iets af, dan stopt hij en volgt er een melding.
          </p>
          <p>
            Zolang de executor niet is gekoppeld, blijven de gates ‘Apps installeren’ en ‘R2/R3-acties’ dicht. Zie{" "}
            <Link href="/onboarding">Wat mag nu?</Link>
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
          <h2 id="koppelen">2. Koppelen met een koppelcode (30 minuten)</h2>
          <ol className="howto" data-genummerd="">
            <li>Maak hieronder een koppelcode. Hij werkt één keer en verloopt na 30 minuten.</li>
            <li>Open de statuspagina van de executor en vul daar de koppelcode in; controleer dat de vingerafdruk gelijk is.</li>
            <li>
              De TrueNAS-API-key met schrijfrechten vul je <strong>alleen</strong> op de executorpagina in; de Hub ziet hem nooit.
            </li>
          </ol>
          <ExecutorKoppelen />
          <Melding soort="nogniet" titel="Schermen voor voorstellen en goedkeuren volgen later in fase P2">
            <p>
              Het beleid, de goedkeuringen en de uitvoering werken al via de Hub-API. De schermen om een actie voor te stellen, de
              preview te bekijken en goed te keuren zijn nog niet gebouwd.
            </p>
          </Melding>
        </section>
      </div>
    </>
  );
}
