"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";
import { activeDesktopHref, activeMobileHref, DESKTOP_NAV, MOBILE_NAV, normalizePath, PUBLIC_PATHS } from "@/lib/nav";
import { useOnline, useServiceWorker } from "@/lib/pwa";
import { ROLE_LABEL, SessionProvider, useSession } from "@/lib/session";
import { ErrorPanel } from "./ErrorPanel";
import { Icon } from "./Icon";
import { Loading } from "./Loading";

function Brand() {
  return (
    <Link href="/" className="brand">
      <span className="brand-mark" aria-hidden="true">
        <Icon name="server" size={20} />
      </span>
      <span className="brand-text">AI Server Manager</span>
    </Link>
  );
}

function OfflineBanner() {
  const online = useOnline();
  if (online) return null;
  return (
    <div className="offline-banner tone-warn" role="status" aria-live="polite" data-testid="offline-banner">
      Offline — geen verbinding met de Hub. Gegevens zijn nu onbekend en wijzigen kan niet.
    </div>
  );
}

function UserBox({ compact }: { compact?: boolean }) {
  const { state, logout } = useSession();
  const router = useRouter();
  if (state.status !== "auth") return null;
  const u = state.me.user;
  const doLogout = async () => {
    await logout();
    router.replace("/inloggen");
  };
  return (
    <div className={compact ? "topbar-user" : "stack"} data-testid="user-box">
      <span className="name">
        {u.display_name || u.username} <span className="muted">({ROLE_LABEL[u.role]})</span>
      </span>
      <button type="button" className="btn" onClick={() => void doLogout()} data-testid="logout">
        <Icon name="logout" /> Uitloggen
      </button>
    </div>
  );
}

function Navigation({ pathname }: { pathname: string }) {
  const desktopActive = activeDesktopHref(pathname);
  const mobileActive = activeMobileHref(pathname);
  return (
    <>
      <aside className="sidebar" data-testid="sidebar">
        <Brand />
        <nav aria-label="Hoofdmenu">
          <ul>
            {DESKTOP_NAV.map((item) => (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className="nav-link"
                  aria-current={desktopActive === item.href ? "page" : undefined}
                >
                  <Icon name={item.icon} />
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
        <div className="sidebar-foot">
          <UserBox />
        </div>
      </aside>
      <nav className="bottom-nav" aria-label="Hoofdmenu" data-testid="bottom-nav">
        <ul>
          {MOBILE_NAV.map((item) => (
            <li key={item.href}>
              <Link href={item.href} aria-current={mobileActive === item.href ? "page" : undefined}>
                <span className="nav-icon">
                  <Icon name={item.icon} />
                </span>
                {item.label}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
    </>
  );
}

function Guard({ children }: { children: ReactNode }) {
  const pathname = normalizePath(usePathname() || "/");
  const router = useRouter();
  const { state, refresh } = useSession();
  const isPublic = PUBLIC_PATHS.includes(pathname);

  useEffect(() => {
    if (isPublic) return;
    if (state.status === "setup") router.replace("/eerste-start");
    else if (state.status === "anon") {
      // Na bewust uitloggen of vanaf Home: gewoon naar inloggen; anders terug naar de pagina waar je was.
      const plain = state.uitgelogd || pathname === "/";
      router.replace(plain ? "/inloggen" : `/inloggen?terug=${encodeURIComponent(pathname)}`);
    }
  }, [state, isPublic, pathname, router]);

  if (isPublic) {
    return (
      <div className="shell-public">
        <OfflineBanner />
        <main id="inhoud" tabIndex={-1}>
          {children}
        </main>
      </div>
    );
  }

  let content: ReactNode;
  if (state.status === "auth") content = children;
  else if (state.status === "error")
    content = <ErrorPanel error={state.error} onRetry={() => void refresh()} title="De Hub is niet bereikbaar" />;
  else content = <Loading text={state.status === "loading" ? "Aanmelding controleren…" : "Doorsturen…"} />;

  return (
    <div className="shell">
      <a className="skip-link" href="#inhoud">
        Naar de inhoud
      </a>
      <Navigation pathname={pathname} />
      <div className="main-col">
        <OfflineBanner />
        <header className="topbar">
          <Brand />
          <UserBox compact />
        </header>
        <main id="inhoud" tabIndex={-1}>
          {content}
        </main>
      </div>
    </div>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  useServiceWorker();
  return (
    <SessionProvider>
      <Guard>{children}</Guard>
    </SessionProvider>
  );
}
