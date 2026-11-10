"use client";

import { KeyRound, LifeBuoy, ListChecks, Network } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { Controles, type Controle } from "@/components/Controles";
import { ErrorPanel } from "@/components/ErrorPanel";
import { Field } from "@/components/Field";
import { KopieerVeld } from "@/components/KopieerVeld";
import { Loading } from "@/components/Loading";
import { Melding } from "@/components/Melding";
import { RolMelding } from "@/components/RolMelding";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { formatDate, formatDateTime, formatTime } from "@/lib/format";
import { hasRole, useRole } from "@/lib/session";
import { useAction } from "@/lib/use-action";
import { useApi } from "@/lib/use-api";
import { InstellingenKop } from "../delen";

interface Nood {
  noodaccount: {
    id: string;
    username: string;
    uitgeschakeld: boolean;
    totp_ingesteld: boolean;
    totp_wacht_op_bevestiging: boolean;
    sessieduur_minuten: number;
    rotatie_vereist: boolean;
    laatst_gebruikt: string | null;
    laatst_bevestigd: string | null;
    herbevestiging_nodig: boolean;
  } | null;
  werkend: boolean;
  oidc_verplicht_mogelijk: boolean;
  /** Contract 1.3 §4.1: 100.64.0.0/10 (CGNAT, ook Tailscale) telt standaard niet als privé. */
  cgnat?: { toegestaan: boolean; gewijzigd_door: string | null; gewijzigd_op: string | null; waarschuwing: string };
  toelichting: string;
}

interface Totp {
  geheim: string;
  otpauth_uri: string;
}

interface Selftest {
  resultaat: "ok" | "niet_ok";
  controles: {
    naam: string;
    status: "ok" | "fout" | "waarschuwing";
    detail?: string;
    adres?: string;
    prive?: boolean;
    lijkt_docker_gateway?: boolean;
    toegestaan_door_beheerder?: boolean;
  }[];
  gemeten_op: string;
}

const NAAM: Record<string, string> = {
  noodaccount: "Noodaccount",
  totp: "TOTP",
  bereik_binnen: "Privé-adres wordt toegelaten",
  bereik_buiten: "Internetadres wordt geweigerd",
  bereik_cgnat: "Adres in 100.64.0.0/10 (CGNAT, ook Tailscale)",
  bron_ip: "Jouw adres zoals de Hub het ziet",
};

function groepen(s: string): string {
  return s.replace(/(.{4})/g, "$1 ").trim();
}

function reden(n: Nood): string | null {
  const a = n.noodaccount;
  if (!a) return "er is nog geen noodaccount ingesteld.";
  if (a.uitgeschakeld) return "het noodaccount is uitgeschakeld.";
  if (a.totp_wacht_op_bevestiging) return "de nieuwe TOTP is nog niet bevestigd.";
  if (!a.totp_ingesteld) return "TOTP is niet ingesteld.";
  return null;
}

function selftestControles(s: Selftest): Controle[] {
  return s.controles.map((c) => {
    if (c.naam === "bron_ip") {
      const uitkomst = c.lijkt_docker_gateway ? "onbekend" : c.prive ? "ok" : "beleid";
      const detail = c.lijkt_docker_gateway
        ? "Onbekend: dit lijkt het gateway-adres van het Docker-netwerk. Dan ziet de Hub niet het echte adres van je apparaat en is de controle op privé-adressen zwakker. Niet gevalideerd op de NAS."
        : c.prive
          ? "Dit adres telt als privé."
          : "Vanaf dit adres wordt noodlogin geweigerd (alleen privé-adressen).";
      return { id: c.naam, naam: <>{NAAM[c.naam]}: <code>{c.adres}</code></>, uitkomst, detail };
    }
    if (c.naam === "bereik_cgnat") {
      return {
        id: c.naam,
        naam: <>{NAAM[c.naam]}: <code>{c.adres}</code></>,
        // Beleid, geen storing: standaard geweigerd; alleen een beheerder kan het toestaan.
        uitkomst: c.status !== "ok" ? "fout" : c.prive ? "ok" : "beleid",
        detail: c.prive ? "Telt als privé: toegestaan door een beheerder." : "Telt niet als privé (standaard).",
      };
    }
    return {
      id: c.naam,
      naam: (
        <>
          {NAAM[c.naam] ?? c.naam}
          {c.adres ? (
            <>
              {" "}
              (<code>{c.adres}</code>)
            </>
          ) : null}
        </>
      ),
      uitkomst: c.status === "ok" ? "ok" : "fout",
      detail: c.detail,
    };
  });
}

/** TotpInstellen (C-59): geheim één keer tonen, bevestigen met een code. Geen QR (OB-07). */
function TotpStap({ totp, onKlaar }: { totp: Totp; onKlaar: () => void }) {
  const [code, setCode] = useState("");
  const confirm = useAction();
  useEffect(() => {
    const warn = (e: BeforeUnloadEvent) => {
      e.preventDefault();
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, []);
  // Contract 1.3 §5: een foute code binnen een geldige sessie is 422 (nooit 401); de UI kijkt naar de status.
  const fout = confirm.error?.status === 422 ? "Deze code klopt niet. Wacht op de volgende code en probeer opnieuw." : undefined;
  return (
    <div className="flex flex-col gap-3" data-testid="totp-stap">
      <h3>Stap 2 van 2 · Authenticator-app en code</h3>
      <Melding soort="info">
        <p>
          Dit geheim zie je maar één keer. Zet het nu in je authenticator-app en bewaar een kopie offline, bijvoorbeeld op papier bij je
          herstelkit. De Hub toont het hierna nooit meer.
        </p>
      </Melding>
      <KopieerVeld label="Geheim (handmatig invoeren)" waarde={totp.geheim} ingekort={groepen(totp.geheim)} testId="totp-geheim" />
      <KopieerVeld label="Koppeling voor de app (otpauth)" waarde={totp.otpauth_uri} testId="totp-uri" />
      <form
        className="form"
        onSubmit={async (e: FormEvent) => {
          e.preventDefault();
          if (await confirm.run("/api/v1/auth/break-glass/confirm", { body: { totp: code.replace(/\s/g, "") } })) onKlaar();
        }}
      >
        <Field id="totp-code" label="Code uit de authenticator-app" help="6 cijfers." error={fout}>
          {(a) => <input {...a} inputMode="numeric" autoComplete="one-time-code" pattern="[0-9 ]{6,7}" value={code} onChange={(e) => setCode(e.target.value)} />}
        </Field>
        {confirm.error && !fout ? <ErrorPanel error={confirm.error} /> : null}
        <div>
          <Button type="submit" variant="primair" bezig={confirm.busy} data-testid="totp-bevestigen">
            Code bevestigen
          </Button>
        </div>
      </form>
      <p className="text-sm">Verlaat je de pagina vóór de bevestiging, dan is het geheim weg en moet je opnieuw beginnen.</p>
    </div>
  );
}

function Instellen({ nood, onKlaar }: { nood: Nood; onKlaar: () => void }) {
  const bestaand = Boolean(nood.noodaccount);
  const [eigen, setEigen] = useState("");
  const [naam, setNaam] = useState("");
  const [pw, setPw] = useState("");
  const [duur, setDuur] = useState(60);
  const [totp, setTotp] = useState<Totp | null>(null);
  const act = useAction<{ totp: Totp }>();
  const tekort = pw.length > 0 && pw.length < 20 ? "Minstens 20 tekens." : undefined;
  // Contract 1.3 §5: een fout eigen wachtwoord binnen een geldige sessie is 422 (nooit 401) → veldfout bij dat veld;
  // andere 422's (bv. een te zwak noodwachtwoord) blijven een foutmelding onder het formulier.
  const eigenFout = act.error?.status === 422 && act.error.code === "invalid_credentials";
  if (totp) {
    return (
      <TotpStap
        totp={totp}
        onKlaar={() => {
          setTotp(null);
          onKlaar();
        }}
      />
    );
  }
  return (
    <form
      className="form"
      onSubmit={async (e) => {
        e.preventDefault();
        if (pw.length < 20) return;
        const r = bestaand
          ? await act.run("/api/v1/auth/break-glass/rotate", { body: { huidig_wachtwoord: eigen, nieuw_wachtwoord: pw, sessieduur_minuten: duur } })
          : await act.run("/api/v1/auth/break-glass/setup", { body: { huidig_wachtwoord: eigen, username: naam.trim().toLowerCase(), password: pw, sessieduur_minuten: duur } });
        if (r) {
          setEigen("");
          setPw("");
          setTotp(r.totp);
        }
      }}
      data-testid="noodaccount-instellen"
    >
      <h3>Stap 1 van 2 · {bestaand ? "Nieuw wachtwoord" : "Account en wachtwoord"}</h3>
      {bestaand ? (
        <Melding soort="info">
          <p>Tot je de nieuwe code bevestigt, werkt de noodlogin niet.</p>
        </Melding>
      ) : null}
      <Field id="nood-eigen" label="Je eigen wachtwoord" help="Wijzigen vraagt je eigen wachtwoord." error={eigenFout ? act.error?.message : undefined}>
        {(a) => <input {...a} type="password" autoComplete="current-password" value={eigen} onChange={(e) => setEigen(e.target.value)} required />}
      </Field>
      {!bestaand ? (
        <Field id="nood-naam" label="Gebruikersnaam van het noodaccount" help="Kleine letters, cijfers, punt of streepje.">
          {(a) => <input {...a} autoComplete="off" autoCapitalize="none" value={naam} onChange={(e) => setNaam(e.target.value)} required />}
        </Field>
      ) : null}
      <Field id="nood-pw" label="Nieuw noodwachtwoord" help="Minstens 20 tekens, niet de gebruikersnaam." error={tekort}>
        {(a) => <input {...a} type="password" autoComplete="new-password" value={pw} onChange={(e) => setPw(e.target.value)} required minLength={20} />}
      </Field>
      <Field id="nood-duur" label="Sessieduur (minuten)" help="5–240. Een noodsessie is niet te verlengen.">
        {(a) => <input {...a} type="number" min={5} max={240} value={duur} onChange={(e) => setDuur(Number(e.target.value))} />}
      </Field>
      {act.error && !eigenFout ? <ErrorPanel error={act.error} title="Instellen mislukt" /> : null}
      <div>
        <Button type="submit" variant="primair" bezig={act.busy} data-testid="nood-volgende">
          <KeyRound aria-hidden="true" />
          Volgende: authenticator-app
        </Button>
      </div>
    </form>
  );
}

/** Contract 1.3 §4.1: 100.64.0.0/10 standaard niet privé; alleen een beheerder kan het toestaan (audit). */
function CgnatInstelling({ cgnat, onKlaar }: { cgnat: NonNullable<Nood["cgnat"]>; onKlaar: () => void }) {
  const [bevestigd, setBevestigd] = useState(false);
  const act = useAction<Nood>();
  const zet = async (toestaan: boolean) => {
    if (await act.run("/api/v1/auth/break-glass/cgnat", { method: "PUT", body: { toestaan } })) {
      setBevestigd(false);
      onKlaar();
    }
  };
  return (
    <section className="card" aria-labelledby="cgnat-titel" data-testid="noodaccount-cgnat">
      <h2 id="cgnat-titel" className="flex items-center gap-2">
        <Network aria-hidden="true" className="size-5 text-muted-foreground" />
        Tailscale en CGNAT (100.64.0.0/10)
      </h2>
      <div className="flex flex-wrap gap-2">
        {cgnat.toegestaan ? (
          <StatusBadge view={{ tone: "neutral", label: "Telt als privé", icon: "ingesteld" }} testId="cgnat-stand" />
        ) : (
          <StatusBadge view={{ tone: "gate", label: "Telt niet als privé" }} testId="cgnat-stand" />
        )}
      </div>
      <p>
        Adressen in 100.64.0.0/10 tellen standaard niet als privé voor de noodlogin.
        {cgnat.gewijzigd_op ? ` Laatst gewijzigd door ${cgnat.gewijzigd_door ?? "onbekend"} op ${formatDateTime(cgnat.gewijzigd_op)}.` : ""}
      </p>
      <Melding soort="beperkt">
        <p>{cgnat.waarschuwing}</p>
      </Melding>
      {cgnat.toegestaan ? (
        <div>
          <Button bezig={act.busy} onClick={() => void zet(false)} data-testid="cgnat-uit">
            Niet meer als privé tellen
          </Button>
        </div>
      ) : (
        <form
          className="form"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            if (bevestigd) void zet(true);
          }}
        >
          <label className="keuze">
            <input type="checkbox" checked={bevestigd} onChange={(e) => setBevestigd(e.target.checked)} data-testid="cgnat-bevestig" />
            <span>Ik deel Tailscale met niemand anders.</span>
          </label>
          <div>
            <Button type="submit" uit={!bevestigd} aria-describedby={!bevestigd ? "cgnat-nodig" : undefined} bezig={act.busy} data-testid="cgnat-aan">
              Als privé laten tellen
            </Button>
            {!bevestigd ? (
              <p id="cgnat-nodig" className="help">
                Vink eerst aan dat je Tailscale met niemand deelt.
              </p>
            ) : null}
          </div>
        </form>
      )}
      {act.error ? <ErrorPanel error={act.error} title="Wijzigen mislukt" /> : null}
    </section>
  );
}

export function NoodaccountScreen() {
  const role = useRole();
  const admin = hasRole(role, "admin");
  const nood = useApi<Nood>(admin ? "/api/v1/auth/break-glass" : null);
  const selftest = useAction<Selftest>();
  const n = nood.data;
  const a = n?.noodaccount;
  const waarom = n ? reden(n) : null;
  const adres = typeof window !== "undefined" ? `${window.location.origin}/inloggen/nood` : "/inloggen/nood";
  const herbevestig = a?.laatst_bevestigd ? new Date(Date.parse(a.laatst_bevestigd) + 90 * 86_400_000).toISOString() : null;
  const failed = selftest.result?.controles.filter((c) => c.naam !== "bron_ip" && c.status !== "ok").length ?? 0;
  return (
    <>
      <InstellingenKop titel="Noodaccount" intro="Noodlogin voor als inloggen via SSO niet werkt: wachtwoord plus TOTP, alleen vanaf je eigen netwerk, elke keer vastgelegd en gemeld." />
      {!admin ? (
        <RolMelding>Het noodaccount beheren kan alleen een beheerder.</RolMelding>
      ) : !n ? (
        nood.error ? <ErrorPanel error={nood.error} onRetry={() => void nood.reload()} alert={false} /> : <Loading />
      ) : (
        <div className="grid items-start gap-4 xl:grid-cols-2">
          <div className="flex flex-col gap-4">
            <section className="card" aria-labelledby="nood-status-titel" data-testid="noodaccount-status">
              <h2 id="nood-status-titel" className="flex items-center gap-2">
                <LifeBuoy aria-hidden="true" className="size-5 text-muted-foreground" />
                Status
              </h2>
              <div className="flex flex-wrap gap-2">
                {a ? <StatusBadge view={{ tone: "neutral", label: "Ingesteld", icon: "ingesteld" }} /> : <StatusBadge view={{ tone: "unknown", label: "Niet ingesteld" }} />}
                {a?.totp_wacht_op_bevestiging ? <StatusBadge view={{ tone: "info", label: "Rotatie loopt" }} /> : a?.rotatie_vereist ? <StatusBadge view={{ tone: "info", label: "Rotatie vereist" }} /> : null}
              </div>
              {!n.werkend ? (
                <Melding soort="onbekend" data-testid="nood-werkt-niet">
                  <p>Noodlogin werkt nu niet: {waarom ?? "onbekende reden."}</p>
                </Melding>
              ) : (
                <p data-testid="nood-werkt">Noodlogin is ingesteld en bevestigd.</p>
              )}
              {a ? (
                <dl className="kv">
                  <dt>Account</dt>
                  <dd>
                    <code>{a.username}</code>
                  </dd>
                  <dt>Rol</dt>
                  <dd>Beheerder (vast)</dd>
                  <dt>Sessieduur</dt>
                  <dd>{a.sessieduur_minuten} min, niet te verlengen</dd>
                  <dt>Laatst gebruikt</dt>
                  <dd>{a.laatst_gebruikt ? `${formatDateTime(a.laatst_gebruikt)} (incident gemeld)` : "nooit"}</dd>
                  <dt>Herbevestiging</dt>
                  <dd>
                    {herbevestig ? `Volgende uiterlijk ${formatDate(herbevestig)}. ` : ""}Elke 90 dagen een melding, nooit een blokkade.
                    {a.herbevestiging_nodig ? " Nu nodig." : ""}
                  </dd>
                  <dt>Inloggen kan</dt>
                  <dd>
                    Alleen vanaf privé-adressen (LAN of VPN), nooit vanaf internet.
                    {n.cgnat?.toegestaan ? " 100.64.0.0/10 telt mee (toegestaan door een beheerder)." : " 100.64.0.0/10 telt niet mee."}
                  </dd>
                </dl>
              ) : null}
            </section>
            <section className="card" aria-labelledby="nood-instellen-titel">
              <h2 id="nood-instellen-titel">{a ? "Wachtwoord en TOTP vernieuwen" : "Noodaccount instellen"}</h2>
              <Instellen nood={n} onKlaar={() => void nood.reload()} />
            </section>
          </div>
          <div className="flex flex-col gap-4">
            <section className="card" aria-labelledby="zelftest-titel" data-testid="zelftest">
              <h2 id="zelftest-titel">Zelftest</h2>
              <p className="text-sm">Controleert de noodlogin zonder in te loggen en zonder Authentik of het netwerk te gebruiken. Er verandert niets.</p>
              <div>
                <Button bezig={selftest.busy} onClick={() => void selftest.run("/api/v1/auth/break-glass/selftest")} data-testid="zelftest-uitvoeren">
                  <ListChecks aria-hidden="true" />
                  Zelftest uitvoeren
                </Button>
              </div>
              {selftest.error ? <ErrorPanel error={selftest.error} /> : null}
              {selftest.result ? (
                <>
                  <p role="status" data-testid="zelftest-samenvatting">
                    Uitkomst om {formatTime(selftest.result.gemeten_op)}:{" "}
                    {selftest.result.resultaat === "ok" ? "noodlogin werkt nu." : `noodlogin werkt nu niet (${failed} ${failed === 1 ? "controle" : "controles"} mislukt).`}
                  </p>
                  <Controles items={selftestControles(selftest.result)} testId="zelftest-controles" />
                </>
              ) : null}
            </section>
            {n.cgnat ? <CgnatInstelling cgnat={n.cgnat} onKlaar={() => void nood.reload()} /> : null}
            <section className="card" aria-labelledby="gebruik-titel">
              <h2 id="gebruik-titel">Noodlogin gebruiken</h2>
              <KopieerVeld label="Adres van de noodlogin (zet dit in je herstelkit)" waarde={adres} testId="noodlogin-adres" />
              <p className="text-sm">
                Wijzigen vraagt je eigen wachtwoord. Dit zijn geen acties voor de AI: die kan het noodaccount niet zien, voorstellen of wijzigen.
              </p>
            </section>
          </div>
        </div>
      )}
    </>
  );
}
