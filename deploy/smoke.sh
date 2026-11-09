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
expect "executor niet gekoppeld" "$(curl -fsS --noproxy '*' http://127.0.0.1:30410/readyz)" '"gekoppeld":false'
test "$(curl -s --noproxy '*' -o /dev/null -w '%{http_code}' -X POST -H 'content-type: application/json' \
  -d '{"action_id":"app.restart"}' http://127.0.0.1:30410/api/v1/execute)" = 403
# Geen root-processen meer en de AI-runner als aparte gebruiker:
uids="$(docker exec -u 568 asm-smoke-hub sh -c 'for p in /proc/[0-9]*; do awk "/^Uid:/{print \$2}" $p/status 2>/dev/null; done' | sort -u | tr '\n' ' ')"
echo "uid's in de Hub-container: $uids"
case " $uids" in *" 0 "*) echo "FOUT: er draait nog een root-proces" >&2; exit 1;; esac
case " $uids" in *" 569 "*) ;; *) echo "FOUT: AI-runner draait niet als aparte gebruiker 569" >&2; exit 1;; esac
# PostgreSQL zonder TCP-poort: alleen 30400 luistert.
ports="$(docker exec -u 568 asm-smoke-hub sh -c 'cat /proc/net/tcp /proc/net/tcp6 2>/dev/null | awk "NR>1 && \$4==\"0A\" {print \$2}"' | sed 's/.*://' | sort -u | tr '\n' ' ')"
echo "luisterende poorten (hex): $ports"
test "$ports" = "76C0 "
docker stop -t 30 asm-smoke-hub >/dev/null
expect "netjes gestopt" "$(docker logs asm-smoke-hub 2>&1)" '[hub] gestopt'
echo "rooktest geslaagd"
