"use client";

import { ROLE_LABEL, useSession } from "@/lib/session";
import { InstellingenKop, LogoutButton, PasswordForm, SessionsSection, ThemeSection } from "../delen";

export function AccountScreen() {
  const { state } = useSession();
  const me = state.status === "auth" ? state.me.user : undefined;
  return (
    <>
      <InstellingenKop titel="Account" />
      <div className="stack">
        <section className="card" id="account" aria-labelledby="account-titel">
          <h2 id="account-titel">Jouw account</h2>
          {me ? (
            <dl className="kv">
              <dt>Gebruikersnaam</dt>
              <dd>{me.username}</dd>
              <dt>Weergavenaam</dt>
              <dd>{me.display_name || "—"}</dd>
              <dt>Rol</dt>
              <dd>{ROLE_LABEL[me.role]}</dd>
              <dt>Aanmelden</dt>
              <dd>{me.break_glass ? "Noodaccount" : me.auth_bron === "oidc" ? "SSO" : "Lokaal wachtwoord"}</dd>
            </dl>
          ) : null}
          {me?.auth_bron !== "oidc" ? <PasswordForm /> : <p className="meta">Je wachtwoord beheer je in Authentik (SSO).</p>}
          <div>
            <LogoutButton />
          </div>
        </section>
        <ThemeSection />
        <SessionsSection />
      </div>
    </>
  );
}
