#!/usr/bin/env bash
# Rooktest van beide images (CI en lokaal): starten, healthy, kernchecks, netjes stoppen. Geen echte NAS.
set -euo pipefail
HUB_IMAGE="${1:?hub-image}"
EXEC_IMAGE="${2:?executor-image}"
WORK="$(mktemp -d)"
cleanup() { docker rm -f asm-smoke-hub asm-smoke-exec >/dev/null 2>&1 || true; rm -rf "$WORK" 2>/dev/null || sudo rm -rf "$WORK" 2>/dev/null || true; }
trap cleanup EXIT
mkdir -p "$WORK/hub" "$WORK/exec"

wait_healthy() {
  local name="$1"
  for _ in $(seq 1 60); do
    s="$(docker inspect -f '{{.State.Health.Status}}' "$name")"
    [ "$s" = healthy ] && return 0
    sleep 2
  done
  docker logs "$name" || true
  echo "FOUT: $name werd niet healthy (status $s)" >&2
  return 1
}

docker run -d --name asm-smoke-hub -p 127.0.0.1:30400:30400 -v "$WORK/hub:/appdata" "$HUB_IMAGE" >/dev/null
docker run -d --name asm-smoke-exec -p 127.0.0.1:30410:30410 -v "$WORK/exec:/appdata" "$EXEC_IMAGE" >/dev/null
wait_healthy asm-smoke-hub
wait_healthy asm-smoke-exec

expect() {  # expect <omschrijving> <tekst> <patroon>  (geen grep -q in pipes: pipefail + SIGPIPE)
  if ! printf '%s' "$2" | grep -F -- "$3" >/dev/null; then echo "FOUT: $1: '$3' niet gevonden in: $2" >&2; exit 1; fi
  echo "ok: $1"
}
expect "hub healthz" "$(curl -fsS --noproxy '*' http://127.0.0.1:30400/healthz)" '"status":"ok"'
expect "hub readyz" "$(curl -fsS --noproxy '*' http://127.0.0.1:30400/readyz)" '"status":"ready"'
expect "setup vereist" "$(curl -fsS --noproxy '*' http://127.0.0.1:30400/api/v1/setup/status)" '"setup_vereist":true'
expect "setupcode in de log" "$(docker logs asm-smoke-hub 2>&1)" 'SETUPCODE (eenmalig'
# Web-UI op dezelfde poort (Next.js), Nederlands, met beveiligingsheaders; API alleen via de doorgang.
expect "web-UI eerste start" "$(curl -fsS --noproxy '*' http://127.0.0.1:30400/eerste-start)" 'lang="nl"'
expect "web-UI CSP" "$(curl -fsS --noproxy '*' -D - -o /dev/null http://127.0.0.1:30400/inloggen)" "frame-ancestors 'none'"
expect "PWA-manifest" "$(curl -fsS --noproxy '*' http://127.0.0.1:30400/manifest.webmanifest)" '"lang": "nl"'
expect "API-fout via web-poort (NL)" "$(curl -sS --noproxy '*' http://127.0.0.1:30400/api/v1/auth/me)" '"code":"unauthorized"'
expect "executor niet gekoppeld" "$(curl -fsS --noproxy '*' http://127.0.0.1:30410/readyz)" '"gekoppeld":false'
test "$(curl -s --noproxy '*' -o /dev/null -w '%{http_code}' -X POST -H 'content-type: application/json' \
  -d '{"action_id":"app.restart"}' http://127.0.0.1:30410/api/v1/execute)" = 403
# Geen root-processen meer en de AI-runner als aparte gebruiker:
uids="$(docker exec -u 568 asm-smoke-hub sh -c 'for p in /proc/[0-9]*; do awk "/^Uid:/{print \$2}" $p/status 2>/dev/null; done' | sort -u | tr '\n' ' ')"
echo "uid's in de Hub-container: $uids"
case " $uids" in *" 0 "*) echo "FOUT: er draait nog een root-proces" >&2; exit 1;; esac
case " $uids" in *" 569 "*) ;; *) echo "FOUT: AI-runner draait niet als aparte gebruiker 569" >&2; exit 1;; esac
# PostgreSQL zonder TCP-poort; naar buiten alleen 30400 (web-UI), de API alleen op 127.0.0.1:8400.
socks="$(docker exec -u 568 asm-smoke-hub sh -c 'cat /proc/net/tcp /proc/net/tcp6 2>/dev/null | awk "NR>1 && \$4==\"0A\" {print \$2}"' | sort -u | tr '\n' ' ')"
echo "luisterende sockets (hex ip:poort): $socks"
test "$socks" = "00000000:76C0 0100007F:20D0 "
# no-new-privileges (contract §10; het standaardformulier kan dat niet zetten, de images doen het zelf). Processen van
# 'docker exec' zelf (deze shell en zijn kinderen) tellen niet mee.
nnp() {
  docker exec -u 568 "$1" sh -c 'me=$$; for p in /proc/[0-9]*; do pid=${p#/proc/}; [ "$pid" = "$me" ] && continue;
    pp=$(awk "/^PPid:/{print \$2}" $p/status 2>/dev/null); [ "$pp" = "$me" ] && continue; [ "$pp" = 0 ] && [ "$pid" != 1 ] && continue;
    awk "/^NoNewPrivs:/{print \$2}" $p/status 2>/dev/null; done' | sort -u | tr '\n' ' '
}
for c in asm-smoke-hub asm-smoke-exec; do
  v="$(nnp "$c")"; echo "NoNewPrivs in $c: $v"
  test "$v" = "1 " || { echo "FOUT: niet alle processen in $c hebben no-new-privileges" >&2; exit 1; }
done

# Herstart zonder dataverlies: eerste beheerder via de setupcode uit de log, dan herstart en harde kill.
CODE="$(docker logs asm-smoke-hub 2>&1 | awk '/SETUPCODE \(eenmalig/ {c=$NF} END {print c}')"
test -n "$CODE"
PW='Rooktest-Wachtwoord-123!'
api() { curl -sS --noproxy '*' -o /dev/null -w '%{http_code}' -H 'content-type: application/json' "$@"; }
test "$(api -X POST -d "{\"setup_code\":\"$CODE\",\"username\":\"beheerder\",\"password\":\"$PW\"}" \
  http://127.0.0.1:30400/api/v1/setup/admin)" = 200 && echo "ok: eerste beheerder aangemaakt via de webpoort"
test "$(api -X POST -d "{\"setup_code\":\"$CODE\",\"username\":\"tweede\",\"password\":\"$PW\"}" \
  http://127.0.0.1:30400/api/v1/setup/admin)" = 409 && echo "ok: setupcode is eenmalig"
EXEC_ID="$(curl -fsS --noproxy '*' http://127.0.0.1:30410/api/v1/status | python3 -c 'import json,sys; print(json.load(sys.stdin)["identiteit"]["x"])')"
for how in restart kill; do
  if [ "$how" = restart ]; then docker restart -t 30 asm-smoke-hub asm-smoke-exec >/dev/null
  else docker kill -s KILL asm-smoke-hub asm-smoke-exec >/dev/null; docker start asm-smoke-hub asm-smoke-exec >/dev/null; fi
  wait_healthy asm-smoke-hub
  wait_healthy asm-smoke-exec
  expect "na $how: setup blijft afgerond" "$(curl -fsS --noproxy '*' http://127.0.0.1:30400/api/v1/setup/status)" '"setup_vereist":false'
  test "$(api -X POST -d "{\"username\":\"beheerder\",\"password\":\"$PW\"}" http://127.0.0.1:30400/api/v1/auth/login)" = 200 \
    && echo "ok: na $how: inloggen met het bestaande account"
  n="$(docker logs asm-smoke-hub 2>&1 | grep -c 'SETUPCODE (eenmalig' || true)"
  test "$n" = 1 || { echo "FOUT: na $how verscheen een nieuwe setupcode ($n)" >&2; exit 1; }
  test "$(curl -fsS --noproxy '*' http://127.0.0.1:30410/api/v1/status | python3 -c 'import json,sys; print(json.load(sys.stdin)["identiteit"]["x"])')" = "$EXEC_ID" \
    && echo "ok: na $how: executor-identiteit ongewijzigd (geheimen niet overschreven)"
done
expect "harde kill: oude postmaster.pid opgeruimd" "$(docker logs asm-smoke-hub 2>&1)" 'oude postmaster.pid'

docker stop -t 30 asm-smoke-hub >/dev/null
expect "netjes gestopt" "$(docker logs asm-smoke-hub 2>&1 | tail -n 5)" '[hub] gestopt'
echo "rooktest geslaagd"
