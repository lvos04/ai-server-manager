# shellcheck shell=bash
# Controles van de rooktest (deploy/smoke.sh), los zodat de tegenproeven ze zonder Docker kunnen toetsen
# (apps/api/tests/unit/test_rooktest_controles.py). Elke controle vergelijkt exact en geeft bij een afwijking exit-status 1.

# gelijk <omschrijving> <werkelijk> <verwacht>: exacte tekstvergelijking (geen deeltekst).
gelijk() {
  if [ "$2" != "$3" ]; then echo "FOUT: $1: '$2' in plaats van '$3'" >&2; return 1; fi
  echo "ok: $1"
}

# exacte_regel <omschrijving> <tekst> <regel>: <regel> staat als hele regel in <tekst> ("Uid<tab>5680" ≠ "Uid<tab>568").
exacte_regel() {
  if ! printf '%s\n' "$2" | grep -Fx -- "$3" >/dev/null; then echo "FOUT: $1: regel '$3' ontbreekt" >&2; return 1; fi
  echo "ok: $1"
}

# uids_toegestaan <omschrijving> <regels "reële effectieve"> <uid>...: elk proces heeft een reële én effectieve UID
# die numeriek exact in de lijst staat; een lege of onleesbare lijst is fout.
uids_toegestaan() {
  local oms="$1" regels="$2" r e rest u goed n=0
  shift 2
  while read -r r e rest; do
    [ -z "$r$e$rest" ] && continue
    n=$((n + 1))
    if ! [[ $r =~ ^[0-9]+$ && $e =~ ^[0-9]+$ && -z $rest ]]; then
      echo "FOUT: $oms: onleesbare UID-regel '$r $e $rest'" >&2; return 1
    fi
    for x in "$r" "$e"; do
      goed=0
      for u in "$@"; do [ "$((10#$x))" -eq "$u" ] && goed=1; done
      [ "$goed" = 1 ] || { echo "FOUT: $oms: proces met UID $r/$e (toegestaan: $*)" >&2; return 1; }
    done
  done <<<"$regels"
  [ "$n" -gt 0 ] || { echo "FOUT: $oms: geen processen gelezen" >&2; return 1; }
  echo "ok: $oms"
}

# uid_aanwezig <omschrijving> <regels "reële effectieve"> <uid>: minstens één proces draait reëel én effectief als <uid>.
uid_aanwezig() {
  local r e _
  while read -r r e _; do
    [[ $r =~ ^[0-9]+$ && $e =~ ^[0-9]+$ ]] && [ "$((10#$r))" -eq "$3" ] && [ "$((10#$e))" -eq "$3" ] && { echo "ok: $1"; return 0; }
  done <<<"$2"
  echo "FOUT: $1: geen proces als UID $3" >&2
  return 1
}
