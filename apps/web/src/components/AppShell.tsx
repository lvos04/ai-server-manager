"use client";

import { Bot, CircleUserRound, Inbox, KeyRound, LifeBuoy, LogOut, Server, WifiOff } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, type ReactNode } from "react";
import {
  activeDesktopHref,
  activeMobileHref,
  DESKTOP_NAV,
  isKindPath,
  KIND_NAV,
  MOBILE_NAV,
  normalizePath,
  PRODUCT,
  PUBLIC_PATHS,
} from "@/lib/nav";
import { useOnline, useServiceWorker } from "@/lib/pwa";
import { hasRole, ROLE_LABEL, SessionProvider, useSession } from "@/lib/session";
import { useApi } from "@/lib/use-api";
import { cn } from "@/lib/utils";
import { Aftellen } from "./Aftellen";
import { ErrorPanel } from "./ErrorPanel";
import { Loading } from "./Loading";
import { Validatielabel } from "./StatusBadge";
import { Menu, MenuContent, MenuItem, MenuLabel, MenuPortal, MenuSeparator, MenuTrigger } from "./ui/dropdown-menu";
import { buttonVariants } from "./ui/button";
import { NAV_ICON } from "./nav-icons";


const VERSION = process.env.NEXT_PUBLIC_HUB_VERSION ?? "0.0.0-dev";

function Brand({ compact }: { compact?: boolean }) {
  return (
    <Link
      href="/"
      className={cn("flex min-h-touch items-center gap-3 font-bold text-foreground no-underline", compact ? "max-w-[12rem]" : "")}
      data-testid="merk"
    >
      <span
        className={cn("inline-flex shrink-0 items-center justify-center rounded-lg bg-foreground text-background", compact ? "size-9" : "size-10")}
        aria-hidden="true"
      >
        <Server className="size-5" />
      </span>
      <span className={cn(compact ? "max-w-[8.5rem] text-base leading-5" : "text-lg leading-6")}>{PRODUCT}</span>
    </Link>
  );
}

/** VerbindingsBanner (C-16, T-10): offline. Lezen blijft; gegevens zijn niet actueel; acties uit. */
function OfflineBanner() {
  const online = useOnline();
  if (online) return null;
  return (
    <div
      className="flex items-start gap-2 border-b-2 border-dashed border-unknown bg-unknown-bg px-4 py-3 text-unknown-ink"
      role="status"
      aria-live="polite"
      data-testid="offline-banner"
    >
      <WifiOff aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-unknown" />
      <p>Je bent offline. Gegevens zijn niet actueel; acties zijn uitgeschakeld. Zodra de verbinding terug is, halen we alles opnieuw op.</p>
    </div>
  );
}

interface OwnSession {
  items: { id: string; verloopt: string; huidige: boolean }[];
}

/** Vaste balk tijdens een noodsessie (S-003): eindtijd + aftellen, niet te verlengen, rotatieplicht. */
function NoodsessieBalk() {
  const { state } = useSession();
  const nood = state.status === "auth" && state.me.user.break_glass;
  const sessions = useApi<OwnSession>(nood ? "/api/v1/auth/sessions" : null, 60_000);
  if (!nood) return null;
  const current = sessions.data?.items.find((s) => s.huidige);
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b-2 border-info bg-info-bg px-4 py-2 text-info-ink" role="status" data-testid="noodsessie-balk">
      <LifeBuoy aria-hidden="true" className="size-5 shrink-0 text-info" />
      <span className="font-semibold">
        Noodsessie
        {current ? (
          <>
            {" "}
            — eindigt over <Aftellen tot={current.verloopt} />. Niet te verlengen.
          </>
        ) : (
          " — niet te verlengen."
        )}
      </span>
      <Link href="/instellingen/noodaccount" className="font-semibold text-current">
        Wachtwoord en TOTP vernieuwen (verplicht na gebruik)
      </Link>
    </div>
  );
}

function UserMenu() {
  const { state, logout } = useSession();
  const router = useRouter();
  if (state.status !== "auth") return null;
  const u = state.me.user;
  const kind = u.role === "kind";
  const doLogout = async () => {
    await logout();
    router.replace("/inloggen");
  };
  return (
    // Niet-modaal: een modaal menu zet aria-hidden op de rest van de pagina terwijl daar focusbare elementen blijven
    // (axe aria-hidden-focus). Esc, Tab en klikken buiten het menu sluiten het gewoon.
    <Menu modal={false}>
      <MenuTrigger className={buttonVariants({ variant: "stil" })} data-testid="gebruikersmenu">
        <CircleUserRound aria-hidden="true" />
        <span className="max-w-[9rem] truncate max-sm:sr-only">{u.display_name || u.username}</span>
        <span className="sr-only"> — gebruikersmenu</span>
      </MenuTrigger>
      <MenuPortal>
        <MenuContent data-testid="user-box">
          <MenuLabel>
            {u.display_name || u.username} ({ROLE_LABEL[u.role]})
          </MenuLabel>
          <MenuSeparator />
          <MenuItem asChild>
            <Link href={kind ? "/ik" : "/instellingen/account"}>
              <KeyRound aria-hidden="true" />
              {kind ? "Ik" : "Account en thema"}
            </Link>
          </MenuItem>
          <MenuItem onSelect={() => void doLogout()} data-testid="logout">
            <LogOut aria-hidden="true" />
            Uitloggen
          </MenuItem>
        </MenuContent>
      </MenuPortal>
    </Menu>
  );
}

interface Samenvatting {
  actief: number;
}

/** Problemen-teller in de kopbalk: inkt, nooit rood; > 99 = "99+", exact getal in de sr-tekst. */
function ProblemenTeller({ count }: { count: number | null }) {
  if (count === null || count === 0) return null;
  return (
    <>
      <span className="inline-flex h-6 min-w-6 items-center justify-center rounded-full bg-foreground px-1.5 text-sm leading-none font-bold text-background" aria-hidden="true">
        {count > 99 ? "99+" : count}
      </span>
      <span className="sr-only">, {count} actief</span>
    </>
  );
}

function useProblemen(): number | null {
  const { state } = useSession();
  const ok = state.status === "auth" && hasRole(state.me.user.role, "viewer");
  const s = useApi<Samenvatting>(ok ? "/api/v1/incidents/samenvatting" : null, 60_000);
  return s.data && !s.stale ? s.data.actief : null;
}

function Navigation({ pathname, problemen }: { pathname: string; problemen: number | null }) {
  const desktopActive = activeDesktopHref(pathname);
  const mobileActive = activeMobileHref(pathname);
  return (
    <>
      <aside
        className="fixed inset-y-0 left-0 z-nav hidden w-sidebar flex-col gap-4 border-r border-border bg-sidebar px-3 py-4 lg:flex"
        data-testid="sidebar"
      >
        <div className="px-1">
          <Brand />
        </div>
        {/* Scrollkader iets ruimer dan de items: de focusring (3 px + 2 px spleet) valt anders aan de randen weg. */}
        <nav aria-label="Hoofdmenu" className="-mx-1.5 flex-1 overflow-y-auto px-1.5 py-1.5">
          <ul className="m-0 flex list-none flex-col gap-1 p-0">
            {DESKTOP_NAV.map((item) => {
              const Icon = NAV_ICON[item.icon];
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className="flex min-h-touch items-center gap-3 rounded-lg px-3 font-medium text-foreground no-underline hover:bg-accent aria-[current=page]:bg-accent aria-[current=page]:font-bold aria-[current=page]:shadow-[inset_4px_0_0_var(--primary)] [&_svg]:size-5 [&_svg]:shrink-0 [&_svg]:text-muted-foreground aria-[current=page]:[&_svg]:text-foreground"
                    aria-current={desktopActive === item.href ? "page" : undefined}
                  >
                    <Icon aria-hidden="true" />
                    {item.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
        <div className="flex flex-col gap-2 border-t border-border px-1 pt-3 text-sm text-muted-foreground">
          <span>Hub {VERSION}</span>
          <Validatielabel>Sim-getest</Validatielabel>
        </div>
      </aside>
      <nav
        className="fixed inset-x-0 bottom-0 z-nav border-t border-border bg-card pb-[env(safe-area-inset-bottom,0px)] lg:hidden"
        aria-label="Hoofdmenu"
        data-testid="bottom-nav"
      >
        <ul className="m-0 flex list-none p-0">
          {MOBILE_NAV.map((item) => {
            const Icon = NAV_ICON[item.icon];
            return (
              <li key={item.href} className="flex min-w-touch flex-auto">
                {/* Peil 1.1.1 (C-01, E16): items op labelbreedte, actief zonder extra gewicht; labels breken nooit in een woord. */}
                <Link
                  href={item.href}
                  aria-current={mobileActive === item.href ? "page" : undefined}
                  className="relative flex min-h-16 min-w-touch flex-auto flex-col items-center justify-center gap-0.5 px-1 text-sm font-medium break-keep text-muted-foreground no-underline aria-[current=page]:text-foreground aria-[current=page]:shadow-[inset_0_3px_0_var(--primary)] [&_svg]:size-6"
                >
                  <span className="relative inline-flex">
                    <Icon aria-hidden="true" />
                    {item.href === "/problemen" && problemen ? (
                      <span className="absolute -top-1.5 left-4 inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-foreground px-1 text-sm leading-none font-bold text-background" aria-hidden="true">
                        {problemen > 99 ? "99+" : problemen}
                      </span>
                    ) : null}
                  </span>
                  {item.label}
                  {item.href === "/problemen" && problemen ? <span className="sr-only">, {problemen} actief</span> : null}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </>
  );
}

function Header({ problemen }: { problemen: number | null }) {
  const pathname = normalizePath(usePathname() || "/");
  return (
    <header className="sticky top-0 z-sticky flex h-16 items-center justify-between gap-2 border-b border-border bg-card px-4 sm:px-6 lg:px-8">
      <div className="lg:hidden">
        <Brand compact />
      </div>
      <div className="hidden min-w-0 flex-1 lg:block" />
      <div className="flex items-center gap-1">
        <Link
          href="/problemen"
          className="hidden min-h-touch items-center gap-2 rounded-lg px-3 font-semibold text-foreground no-underline hover:bg-accent aria-[current=page]:bg-accent aria-[current=page]:shadow-[inset_0_-3px_0_var(--primary)] lg:inline-flex [&_svg]:size-5"
          aria-current={pathname.startsWith("/problemen") ? "page" : undefined}
          data-testid="kop-problemen"
        >
          <Inbox aria-hidden="true" />
          Problemen
          <ProblemenTeller count={problemen} />
        </Link>
        <Link
          href="/ai"
          className="hidden min-h-touch items-center gap-2 rounded-lg px-3 font-semibold text-foreground no-underline hover:bg-accent lg:inline-flex [&_svg]:size-5"
          aria-current={pathname === "/ai" ? "page" : undefined}
        >
          <Bot aria-hidden="true" />
          AI
        </Link>
        <UserMenu />
      </div>
    </header>
  );
}

/** Na een routewissel (niet bij de eerste weergave): focus naar de h1, zodat schermlezers de nieuwe pagina horen. */
function useFocusH1OnRouteChange(pathname: string) {
  const first = useRef(true);
  useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    let tries = 0;
    const t = setInterval(() => {
      const h1 = document.querySelector<HTMLElement>("main h1");
      if (h1 || ++tries > 20) {
        clearInterval(t);
        if (h1) {
          h1.tabIndex = -1;
          h1.focus({ preventScroll: false });
        }
      }
    }, 50);
    return () => clearInterval(t);
  }, [pathname]);
}

const MAIN_CLS = "mx-auto w-full max-w-content px-4 pt-6 pb-10 sm:px-6 lg:px-8";

function SkipLink() {
  return (
    <a className={cn(buttonVariants({ variant: "primair" }), "verborgen-tot-focus")} href="#inhoud">
      Naar de inhoud
    </a>
  );
}

/** Kindschil (C-01 kindvariant): kop met merk + gebruikersmenu, ondernavigatie Home · Kijken · Zoeken · Ik overal. */
function KindShell({ pathname, children }: { pathname: string; children: ReactNode }) {
  const allowed = isKindPath(pathname);
  return (
    <div className="relative min-h-dvh pb-[calc(4rem+env(safe-area-inset-bottom,0px))]" data-schil="kind">
      <SkipLink />
      <header className="sticky top-0 z-sticky flex h-16 items-center justify-between gap-2 border-b border-border bg-card px-4">
        <Brand compact />
        <UserMenu />
      </header>
      <OfflineBanner />
      <main id="inhoud" tabIndex={-1} className={MAIN_CLS}>
        {allowed ? children : <KindNietVoorJou />}
      </main>
      <nav className="fixed inset-x-0 bottom-0 z-nav border-t border-border bg-card pb-[env(safe-area-inset-bottom,0px)]" aria-label="Hoofdmenu" data-testid="kind-nav">
        <ul className="m-0 mx-auto flex max-w-xl list-none p-0">
          {KIND_NAV.map((item) => {
            const Icon = NAV_ICON[item.icon];
            return (
              <li key={item.href} className="flex min-w-touch flex-auto">
                <Link
                  href={item.href}
                  aria-current={normalizePath(pathname) === item.href ? "page" : undefined}
                  className="flex min-h-16 min-w-touch flex-auto flex-col items-center justify-center gap-0.5 text-sm font-medium break-keep text-muted-foreground no-underline aria-[current=page]:text-foreground aria-[current=page]:shadow-[inset_0_3px_0_var(--primary)] [&_svg]:size-6"
                >
                  <Icon aria-hidden="true" />
                  {item.label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </div>
  );
}

/** Kindvriendelijke 403 (de API weigert kind al op elke beheerroute; de UI is nooit de poortwachter). */
function KindNietVoorJou() {
  // De routetitel ("Server — …") is een beheerterm; een kind ziet in de tab dezelfde woorden als op het scherm.
  useEffect(() => {
    document.title = "Niet voor jou — TrueNAS Home Platform";
  }, []);
  return (
    <section className="flex flex-col gap-4" data-testid="kind-403">
      <h1 className="text-2xl font-bold">Dit scherm is niet voor jou</h1>
      <p>Ga terug naar Home.</p>
      <p>
        <Link href="/" className={buttonVariants({ variant: "primair" })}>
          Naar Home
        </Link>
      </p>
      <details>
        <summary className="min-h-touch cursor-pointer py-2 font-semibold">Details voor een volwassene</summary>
        <p>
          Code <code>forbidden</code> · deze pagina is alleen voor beheerders, operators en kijkers.
        </p>
      </details>
    </section>
  );
}

function Guard({ children }: { children: ReactNode }) {
  const pathname = normalizePath(usePathname() || "/");
  const router = useRouter();
  const { state, refresh } = useSession();
  const isPublic = PUBLIC_PATHS.includes(pathname);
  const problemen = useProblemen();
  useFocusH1OnRouteChange(pathname);

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
      <div className="min-h-dvh">
        <OfflineBanner />
        <header className="flex h-16 items-center border-b border-border bg-card px-4 sm:px-6">
          <Brand compact />
        </header>
        <main id="inhoud" tabIndex={-1} className={MAIN_CLS}>
          {children}
        </main>
      </div>
    );
  }

  if (state.status === "auth" && state.me.user.role === "kind") {
    return <KindShell pathname={pathname}>{children}</KindShell>;
  }

  let content: ReactNode;
  if (state.status === "auth") content = isKindPath(pathname) && pathname !== "/" ? <NietVoorRol /> : children;
  else if (state.status === "error")
    content = <ErrorPanel error={state.error} onRetry={() => void refresh()} title="De Hub is niet bereikbaar" />;
  else content = <Loading text={state.status === "loading" ? "Aanmelding controleren…" : "Doorsturen…"} />;

  return (
    <div className="relative min-h-dvh pb-[calc(4rem+env(safe-area-inset-bottom,0px))] lg:pb-0">
      <SkipLink />
      <Navigation pathname={pathname} problemen={problemen} />
      <div className="flex min-w-0 flex-col lg:pl-sidebar">
        <Header problemen={problemen} />
        <OfflineBanner />
        <NoodsessieBalk />
        <main id="inhoud" tabIndex={-1} className={MAIN_CLS}>
          {content}
        </main>
      </div>
    </div>
  );
}

/** Kindroutes (/kijken, /zoeken, /ik) bestaan alleen in de kindschil. */
function NietVoorRol() {
  return (
    <section className="flex flex-col gap-3">
      <h1 className="text-2xl font-bold">Pagina niet gevonden</h1>
      <p>Deze pagina hoort bij het kinderprofiel.</p>
      <p>
        <Link href="/" className={buttonVariants({ variant: "secundair" })}>
          Naar Home
        </Link>
      </p>
    </section>
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
