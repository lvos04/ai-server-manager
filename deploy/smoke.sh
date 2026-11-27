#!/usr/bin/env bash
# Rooktest van beide images (CI en lokaal): starten, healthy, kernchecks, netjes stoppen. Geen echte NAS.
set -euo pipefail
HUB_IMAGE="${1:?hub-image}"
EXEC_IMAGE="${2:?executor-image}"
WORK=$(mktemp -d "${TMPDIR:-/tmp}/asm-smoke.XXXXXXXX")
cleanup() {
  for bestand in "$WORK"/*.cid; do
    if [[ -s $bestand ]]; then docker rm -fv "$(cat "$bestand")" >/dev/null || true; fi
  done
  rm -rf -- "$WORK"
}
trap cleanup EXIT

wait_healthy() {
  local name="$1"
  for _ in $(seq 1 60); do
    s="$(docker inspect -f '{{.State.Health.Status}}' "$name")"
    [ "$s" = healthy ] && return 0
    sleep 2
  done
  docker inspect -f '{{range .State.Health.Log}}{{println .ExitCode}}{{end}}' "$name" >&2 || true
  echo "FOUT: $name werd niet healthy (status $s)" >&2
  return 1
}

# De buildengine kan op een andere host draaien. Docker beheert de testvolumes en kent elke
# container een eigen ID toe. De HTTP-client bereikt beide images zonder gepubliceerde hostpoorten.
hub=$(docker run -d --name "asm-smoke-hub-${WORK##*.}" --cidfile "$WORK/hub.cid" --network bridge "$HUB_IMAGE")
executor=$(docker run -d --name "asm-smoke-exec-${WORK##*.}" --cidfile "$WORK/executor.cid" --network bridge "$EXEC_IMAGE")
client=$(docker run -d --cidfile "$WORK/client.cid" --network bridge --tmpfs /proef:mode=1777 \
  --entrypoint sleep docker.io/curlimages/curl:8.20.0@sha256:b3f1fb2a51d923260350d21b8654bbc607164a987e2f7c84a0ac199a67df812a 3600)
hub_url=http://localhost:30400
executor_url=http://localhost:30410
testadressen() {
  hub_adres=$(docker inspect -f '{{.NetworkSettings.Networks.bridge.IPAddress}}' "$hub")
  executor_adres=$(docker inspect -f '{{.NetworkSettings.Networks.bridge.IPAddress}}' "$executor")
  test -n "$hub_adres" && test -n "$executor_adres"
}
rook_curl() {
  docker exec -i "$client" curl --connect-to "localhost:30400:$hub_adres:30400" \
    --connect-to "localhost:30410:$executor_adres:30410" "$@"
}
testadressen
wait_healthy "$hub"
wait_healthy "$executor"

# De pakketlaag bevat alleen verwijzingen. Een ongeopende installatie heeft nog geen websleutels.
docker run --rm --network none --read-only --entrypoint python "$HUB_IMAGE" -c '
import json
from pathlib import Path
p = Path("/opt/hub-web/.next")
for naam in ("prerender-manifest.json", "server/preview-props.json",
             "server/server-reference-manifest.json", "server/server-reference-manifest.js"):
    assert (p/naam).is_symlink() and not (p/naam).exists()
assert "preview" not in json.loads((p/"hub-prerender.json").read_bytes())
'

# shellcheck source=deploy/smoke-controles.sh
. "$(dirname "${BASH_SOURCE[0]}")/smoke-controles.sh"
expect() {  # expect <omschrijving> <tekst> <patroon>  (geen grep -q in pipes: pipefail + SIGPIPE)
  if ! printf '%s' "$2" | grep -F -- "$3" >/dev/null; then echo "FOUT: $1: '$3' niet gevonden" >&2; exit 1; fi
  echo "ok: $1"
}
# Beleid (ADR-0030 besluit 2; S-P2-010, R-TECH-2): de Hub-image, de executor-image en policy/ in de repo geven dezelfde
# policy_hash. Verschillen Hub en executor, dan weigert de executor alles (policy_hash_verschilt); verschilt een image
# van de repo, dan draait er ander beleid dan wat in de repo staat (bv. een vierde yaml die de Dockerfile niet kopieert).
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HASH_PY='from asm_policy import load_policy; print(load_policy().hash)'
hub_hash="$(docker exec -u 568 "$hub" python -c "$HASH_PY")"
exec_hash="$(docker exec -u 568 "$executor" python -c "$HASH_PY")"
docker cp "$REPO_DIR/policy" "$executor:/repo-policy"
repo_hash="$(docker exec -u 568 "$executor" python -c \
  'from pathlib import Path; from asm_policy import policy_hash; print(policy_hash(Path("/repo-policy")))')"
echo "policy_hash: hub $hub_hash, executor $exec_hash, repo $repo_hash"
controleer_policy_hash "$hub_hash" "$exec_hash" "$repo_hash" || exit 1
expect "hub healthz" "$(rook_curl -fsS --noproxy '*' "$hub_url/healthz")" '"status":"ok"'
expect "hub readyz" "$(rook_curl -fsS --noproxy '*' "$hub_url/readyz")" '"status":"ready"'
expect "setup vereist" "$(rook_curl -fsS --noproxy '*' "$hub_url/api/v1/setup/status")" '"setup_vereist":true'
expect "setupcode in de log" "$(docker logs "$hub" 2>&1)" 'SETUPCODE (eenmalig'
# Web-UI op dezelfde poort (Next.js), Nederlands, met beveiligingsheaders; API alleen via de doorgang.
expect "web-UI eerste start" "$(rook_curl -fsS --noproxy '*' "$hub_url/eerste-start")" 'lang="nl"'
expect "web-UI CSP" "$(rook_curl -fsS --noproxy '*' -D - -o /dev/null "$hub_url/inloggen")" "frame-ancestors 'none'"
expect "PWA-manifest" "$(rook_curl -fsS --noproxy '*' "$hub_url/manifest.webmanifest")" '"lang": "nl"'
# Peil (ADR-0024): productnaam, Tailwind-CSS met de Peil-tokens in de build, noodlogin-pagina publiek.
expect "web-UI productnaam" "$(rook_curl -fsS --noproxy '*' "$hub_url/inloggen")" 'TrueNAS Home Platform'
expect "PWA-manifest productnaam" "$(rook_curl -fsS --noproxy '*' "$hub_url/manifest.webmanifest")" '"short_name": "Home Platform"'
css_pad="$(rook_curl -fsS --noproxy '*' "$hub_url/inloggen" | grep -o '/_next/static/[^"]*\.css' | head -1)"
expect "Peil-tokens in de CSS" "$(rook_curl -fsS --noproxy '*' "${hub_url}${css_pad}")" '--healthy-ink'
expect "noodlogin-pagina" "$(rook_curl -fsS --noproxy '*' "$hub_url/inloggen/nood")" 'Noodlogin'
expect "executor-statuspagina in Peil" "$(rook_curl -fsS --noproxy '*' "$executor_url/")" 'Onderdeel van TrueNAS Home Platform'
# ADR-0026 (N-01): same-origin, zodat de browser bij het koppelformulier de echte Origin stuurt (niet `null`).
expect "executor-statuspagina Referrer-Policy" "$(rook_curl -fsS --noproxy '*' -D - -o /dev/null "$executor_url/")" \
  'referrer-policy: same-origin'
expect "API-fout via web-poort (NL)" "$(rook_curl -sS --noproxy '*' "$hub_url/api/v1/auth/me")" '"code":"unauthorized"'
expect "executor niet gekoppeld" "$(rook_curl -fsS --noproxy '*' "$executor_url/readyz")" '"gekoppeld":false'
expect "executor weigert Hub-JWT zonder koppeling (contract 1.3 §4.7)" \
  "$(rook_curl -sS --noproxy '*' -H 'Authorization: Bearer a.b.c' "$executor_url/connector/v1/hub-link")" '"reason":"not_linked"'
expect "enroll-schema: oud verzoek zonder verplichte velden → 422" "$(rook_curl -sS --noproxy '*' -H 'content-type: application/json' \
  -d '{"app_id":"home-control-hub","enrollment_token":"x"}' "$hub_url/api/v1/services/enroll")" '"code":"validation_error"'
expect "sleutelrotaties: lege lijst" "$(rook_curl -fsS --noproxy '*' "$hub_url/api/v1/auth/key-rotations")" '"items":[]'
# Contract 1.3 §4.7: eerst authenticatie — een niet-gekoppelde executor weigert /execute met 401 not_linked.
expect "executor: execute vraagt eerst aanmelding (contract 1.3 §4.7)" "$(rook_curl -sS --noproxy '*' -X POST \
  -H 'content-type: application/json' -d '{"action_id":"app.restart"}' "$executor_url/api/v1/execute")" \
  '"reason":"not_linked"'
# Contract 1.3 §5: > 1 MiB → 413 vóór routering en aanmelding, ook chunked (zonder Content-Length). Hub via de webpoort
# (Node-doorgang → API), executor rechtstreeks; beide op een route zonder aanmelding.
big413() {  # big413 <url> <bytes> → HTTP-status van een chunked POST van <bytes> bytes
  head -c "$2" /dev/zero | rook_curl -sS --noproxy '*' -o /proef/413.json -w '%{http_code}' -X POST \
    -H 'Transfer-Encoding: chunked' -H 'content-type: application/json' --data-binary @- "$1" || true
}
# Ook een veel grotere body, een paar keer: een vroeg 413-antwoord mag via de doorgang nooit een 502 worden.
for url in "$hub_url/api/v1/services/00000000-0000-4000-8000-000000000000/rotate" \
           "$executor_url/connector/v1/hub-link/unlink"; do
  for size in 1048577 3000000 3000000 3000000 3000000 3000000; do
    code="$(big413 "$url" "$size")"
    test "$code" = 413 || { echo "FOUT: chunked $size bytes naar $url gaf $code i.p.v. 413" >&2; exit 1; }
    expect "413 chunked $size bytes ($url)" "$(docker exec "$client" cat /proef/413.json)" '"max_bytes":1048576'
  done
  code="$(head -c 1048577 /dev/zero | rook_curl -sS --noproxy '*' -o /proef/413.json -w '%{http_code}' -X POST \
    -H 'content-type: application/json' --data-binary @- "$url" || true)"
  test "$code" = 413 || { echo "FOUT: Content-Length > 1 MiB naar $url gaf $code i.p.v. 413" >&2; exit 1; }
done
# PostgreSQL zonder TCP-poort; naar buiten alleen 30400 (web-UI), de API alleen op 127.0.0.1:8400.
socks="$(docker exec -u 568 "$hub" sh -c 'cat /proc/net/tcp /proc/net/tcp6 2>/dev/null | awk "NR>1 && \$4==\"0A\" {print \$2}"' | sort -u | tr '\n' ' ')"
echo "luisterende sockets (hex ip:poort): $socks"
test "$socks" = "00000000:76C0 0100007F:20D0 "
# no-new-privileges en geen capabilities (contract 1.3 §2.2/§10; het standaardformulier zet geen no-new-privileges en
# geen cap_drop, de images doen het zelf). Voor elk proces, ook PID 1. Processen van 'docker exec' zelf (deze shell en
# zijn kinderen) tellen niet mee.
privs() {  # privs <container> <veld>: unieke waarden van <veld> in /proc/<pid>/status over alle processen
  docker exec -u 568 "$1" sh -c 'me=$$; for p in /proc/[0-9]*; do pid=${p#/proc/}; [ "$pid" = "$me" ] && continue;
    pp=$(awk "/^PPid:/{print \$2}" $p/status 2>/dev/null); [ "$pp" = "$me" ] && continue; [ "$pp" = 0 ] && [ "$pid" != 1 ] && continue;
    awk -v f="$0:" "\$1==f{print \$2}" $p/status 2>/dev/null; done' "$2" | sort -u | tr '\n' ' '
}
uid_paren() {  # uid_paren <container>: unieke "reële effectieve" UID per blijvend proces (zelfde uitsluiting als privs)
  docker exec -u 568 "$1" sh -c 'me=$$; for p in /proc/[0-9]*; do pid=${p#/proc/}; [ "$pid" = "$me" ] && continue;
    pp=$(awk "/^PPid:/{print \$2}" $p/status 2>/dev/null); [ "$pp" = "$me" ] && continue; [ "$pp" = 0 ] && [ "$pid" != 1 ] && continue;
    awk "/^Uid:/{print \$2, \$3}" $p/status 2>/dev/null; done' | sort -u
}
# Geen root-processen: de Hub draait als 568 met de AI-runner apart als 569, de executor alleen als 568 (exact numeriek).
v="$(uid_paren "$hub")"; echo "uid's (reëel effectief) in de Hub-container: ${v//$'\n'/ | }"
uids_toegestaan "Hub: elk proces reëel en effectief 568 of 569" "$v" 568 569 || exit 1
uid_aanwezig "Hub: AI-runner als aparte gebruiker 569" "$v" 569 || exit 1
# Onderscheid een geweigerde opening als 569 van een ontbrekend bestand. De proef leest geen sleutelinhoud.
docker exec -u 568:568 "$hub" test -s /appdata/secrets/vault.key
docker exec -i -u 569:569 "$hub" python - < "$REPO_DIR/tests/rooktest_airunner.py"
v="$(uid_paren "$executor")"; echo "uid's (reëel effectief) in de executor-container: ${v//$'\n'/ | }"
uids_toegestaan "executor: elk proces reëel en effectief 568" "$v" 568 || exit 1
# Contract 1.3 §2.2 (C1.3-ASM-01): ook CapPrm en CapAmb 0 en — bij een start als root — een lege bounding set.
for c in "$hub" "$executor"; do
  v="$(privs "$c" NoNewPrivs)"; echo "NoNewPrivs in $c: $v"
  test "$v" = "1 " || { echo "FOUT: niet alle processen in $c hebben no-new-privileges" >&2; exit 1; }
  for f in CapEff CapPrm CapAmb CapBnd; do
    v="$(privs "$c" "$f")"; echo "$f in $c: $v"
    test "$v" = "0000000000000000 " || { echo "FOUT: een proces in $c heeft $f ≠ 0 ($v)" >&2; exit 1; }
  done
done
# De healthcheck apart (§2.2): hetzelfde commando met de controlevlag, als root gestart zoals Docker dat doet; na de
# wissel Uid 568, geen capabilities, lege bounding set en no_new_privs.
for pair in "$hub /usr/local/lib/hub/healthcheck.py" "$executor /usr/local/lib/executor/healthcheck.py"; do
  # shellcheck disable=SC2086
  set -- $pair
  out="$(docker exec "$1" python "$2" --controle)"
  for want in $'Uid\t568' $'CapEff\t0000000000000000' $'CapPrm\t0000000000000000' $'CapAmb\t0000000000000000' \
              $'CapBnd\t0000000000000000' $'NoNewPrivs\t1'; do
    exacte_regel "healthcheck $1 na de wissel: ${want/$'\t'/ }" "$out" "$want" || exit 1
  done
done
# "Custom User 568" aangevinkt: geen eigenaarschapsstap en geen lege bounding set mogelijk; CapEff/CapPrm/CapAmb 0 en
# NoNewPrivs 1 blijven verplicht (§2.2).
executor568=$(docker run -d --cidfile "$WORK/executor568.cid" --network none -u 568:568 "$EXEC_IMAGE")
wait_healthy "$executor568"
v="$(privs "$executor568" NoNewPrivs)"; test "$v" = "1 " || { echo "FOUT: Custom User 568 zonder no_new_privs" >&2; exit 1; }
uids_toegestaan "Custom User 568: elk proces reëel en effectief 568" "$(uid_paren "$executor568")" 568 || exit 1
for f in CapEff CapPrm CapAmb; do
  v="$(privs "$executor568" "$f")"
  test "$v" = "0000000000000000 " || { echo "FOUT: Custom User 568: $f ≠ 0 ($v)" >&2; exit 1; }
done
echo "ok: executor als Custom User 568: geen capabilities, no_new_privs"

# De netwerkloze executor krijgt een eigen testkoppeling. Het dienst-JWT is geldig, alleen de
# handtekening onder het uitvoeringsverzoek ontbreekt. De gewone executor houdt zijn eigen koppelstatus.
for bestand in executorhub.py policyhelpers.py rooktest_executor.py; do
  docker cp "$REPO_DIR/tests/$bestand" "$executor568:/appdata/$bestand"
done
docker exec -u 568:568 "$executor568" python /appdata/rooktest_executor.py

# Herstart zonder dataverlies: eerste beheerder via de setupcode uit de log, dan herstart en harde kill.
CODE="$(docker logs "$hub" 2>&1 | awk '/SETUPCODE \(eenmalig/ {c=$NF} END {print c}')"
test -n "$CODE"
PW='Rooktest-Wachtwoord-123!'
api() { rook_curl -sS --noproxy '*' -o /dev/null -w '%{http_code}' -H 'content-type: application/json' "$@"; }
# Elke vergelijking via gelijk … || exit 1: onder set -e breekt een mislukte test in een en-lijst het script niet af.
gelijk "eerste beheerder aangemaakt via de webpoort" "$(api -X POST -d "{\"setup_code\":\"$CODE\",\"username\":\"beheerder\",\"password\":\"$PW\"}" \
  "$hub_url/api/v1/setup/admin")" 200 || exit 1
gelijk "setupcode is eenmalig" "$(api -X POST -d "{\"setup_code\":\"$CODE\",\"username\":\"tweede\",\"password\":\"$PW\"}" \
  "$hub_url/api/v1/setup/admin")" 409 || exit 1
exec_id() { rook_curl -fsS --noproxy '*' "$executor_url/api/v1/status" | python3 -c 'import json,sys; print(json.load(sys.stdin)["identiteit"]["x"])'; }
EXEC_ID="$(exec_id)"
test -n "$EXEC_ID" || { echo "FOUT: geen executor-identiteit gelezen" >&2; exit 1; }
for how in restart kill; do
  if [ "$how" = restart ]; then docker restart -t 30 "$hub" "$executor" >/dev/null
  else docker kill -s KILL "$hub" "$executor" >/dev/null; docker start "$hub" "$executor" >/dev/null; fi
  testadressen
  wait_healthy "$hub"
  wait_healthy "$executor"
  expect "na $how: setup blijft afgerond" "$(rook_curl -fsS --noproxy '*' "$hub_url/api/v1/setup/status")" '"setup_vereist":false'
  gelijk "na $how: inloggen met het bestaande account" \
    "$(api -X POST -d "{\"username\":\"beheerder\",\"password\":\"$PW\"}" "$hub_url/api/v1/auth/login")" 200 || exit 1
  n="$(docker logs "$hub" 2>&1 | grep -c 'SETUPCODE (eenmalig' || true)"
  test "$n" = 1 || { echo "FOUT: na $how verscheen een nieuwe setupcode ($n)" >&2; exit 1; }
  gelijk "na $how: executor-identiteit ongewijzigd (geheimen niet overschreven)" "$(exec_id)" "$EXEC_ID" || exit 1
done
expect "harde kill: oude postmaster.pid opgeruimd" "$(docker logs "$hub" 2>&1)" 'oude postmaster.pid'

# P1 (ADR-0021): migraties 0003–0005 in de image, periodieke worker-taken draaien, zonder NAS alles 'unknown'.
JAR=/proef/cookies
test "$(api -c "$JAR" -X POST -d "{\"username\":\"beheerder\",\"password\":\"$PW\"}" \
  "$hub_url/api/v1/auth/login")" = 200
for _ in $(seq 1 30); do
  st="$(rook_curl -fsS --noproxy '*' -b "$JAR" "$hub_url/api/v1/monitoring/status")"
  case "$st" in *'"naam":"meldingen_versturen"'*'"status":"ok"'*) break ;; esac
  sleep 2
done
expect "worker: periodieke taken draaien" "$st" '"status":"ok"'
expect "catalogus zonder NAS: leeg en alleen-lezen" \
  "$(rook_curl -fsS --noproxy '*' -b "$JAR" "$hub_url/api/v1/apps")" '"alleen_lezen":true'
expect "observability zonder NAS: unknown (geen bron)" \
  "$(rook_curl -fsS --noproxy '*' -b "$JAR" "$hub_url/api/v1/observability/nas")" '"reden":"geen_bron"'
expect "standaard-alertregels gezaaid" \
  "$(rook_curl -fsS --noproxy '*' -b "$JAR" "$hub_url/api/v1/alerts/rules")" '"standaard_sleutel":"app-down"'

# P1 deel 2 (ADR-0022/0023): migraties 0006–0009, incidenten, runbooks, auditketting, out-of-band, SSO standaard uit.
expect "incidenten-inbox bereikbaar" \
  "$(rook_curl -fsS --noproxy '*' -b "$JAR" "$hub_url/api/v1/incidents/samenvatting")" '"per_status"'
expect "runbooks: acht scenario's met hash" \
  "$(rook_curl -fsS --noproxy '*' -b "$JAR" "$hub_url/api/v1/runbooks")" '"runbook_hash"'
for _ in $(seq 1 15); do
  st="$(rook_curl -fsS --noproxy '*' -b "$JAR" "$hub_url/api/v1/monitoring/status")"
  case "$st" in *'"naam":"audit_verankeren"'*) break ;; esac
  sleep 2
done
expect "auditketting intact" \
  "$(rook_curl -fsS --noproxy '*' -b "$JAR" "$hub_url/api/v1/audit/verify")" '"status":"intact"'
# Het eerste anker komt pas na het interval (15 min) na de eerste auditrij; bestaat het, dan 568 en 0600.
if docker exec "$hub" test -f /appdata/audit/anker.jsonl; then
  [ "$(docker exec "$hub" stat -c '%u %a' /appdata/audit/anker.jsonl)" = "568 600" ] \
    || { echo "FOUT: auditanker niet van 568 met 0600"; exit 1; }
  echo "ok: auditanker in /appdata/audit (568, 0600)"
else
  echo "ok: nog geen auditanker (eerste anker na het interval)"
fi
expect "out-of-band: Hub niet in het meldpad, NAS-uitval niet gedekt" \
  "$(rook_curl -fsS --noproxy '*' -b "$JAR" "$hub_url/api/v1/monitoring/out-of-band")" '"hub_in_meldpad":false'
expect "SSO standaard uit" \
  "$(rook_curl -fsS --noproxy '*' "$hub_url/api/v1/auth/oidc/beschikbaar")" '"ingeschakeld":false'
expect "SSO-login uit → terug naar inloggen" \
  "$(rook_curl -sS --noproxy '*' -D - -o /dev/null "$hub_url/api/v1/auth/oidc/login")" 'sso_fout=sso_uit'

docker stop -t 30 "$hub" >/dev/null
expect "netjes gestopt" "$(docker logs "$hub" 2>&1 | tail -n 5)" '[hub] gestopt'
echo "rooktest geslaagd"
