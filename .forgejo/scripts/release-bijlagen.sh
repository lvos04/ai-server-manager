#!/usr/bin/env bash
# Werk uitsluitend aan een concept voor de bestaande tag. Een herstart mag een gepubliceerde versie overslaan.
set -euo pipefail
api="https://git.medialeon.nl/api/v1/repos/leon/ai-server-manager"
werk=$(mktemp -d "$RUNNER_TEMP/release-bijlagen.XXXXXXXX")
trap 'rm -rf -- "$werk"' EXIT
verzoek() {
  curl --silent --show-error --header @<(printf 'Authorization: token %s\n' "$RELEASE_TOKEN") "$@"
}

namen=(digests.json sbom-ai-server-manager.spdx.json sbom-ai-server-manager-executor.spdx.json)
tag=$(jq -rn --arg naam "$GITHUB_REF_NAME" '$naam|@uri')
verzoek --fail "$api/tags/$tag" | jq -e --arg sha "$RELEASE_COMMIT" '.commit.sha == $sha' > /dev/null
code=$(verzoek -o "$werk/release" -w '%{http_code}' "$api/releases/tags/$tag")
case "$code" in
  200)
    if jq -e '.draft == false' "$werk/release" > /dev/null; then
      for naam in "${namen[@]}"; do
        jq -e --arg naam "$naam" 'any(.assets[]; .name == $naam and .size > 0)' "$werk/release" > /dev/null
      done
      if [[ ${1:-} == --controle ]]; then echo 'publiceren=false' >> "$GITHUB_OUTPUT"; fi
      exit 0
    fi
    ;;
  404) ;;
  *) echo "Opvragen van de release gaf HTTP $code" >&2; exit 1 ;;
esac
if [[ ${1:-} == --controle ]]; then echo 'publiceren=true' >> "$GITHUB_OUTPUT"; exit 0; fi

if [[ $code == 404 ]]; then
  tekst="Images voor versie $VERSION: $IMAGE_PREFIX:$VERSION en $IMAGE_PREFIX-executor:$VERSION. De digests in deze bijlage horen bij het Forgejo-register. Zie CHANGELOG.md en deploy/truenas/CUSTOM_APP.md."
  jq -n --arg tag "$GITHUB_REF_NAME" --arg body "$tekst" --arg sha "$RELEASE_COMMIT" \
    '{tag_name:$tag, target_commitish:$sha, name:$tag, body:$body, draft:true}' > "$werk/concept"
  verzoek --fail -H 'Content-Type: application/json' --data-binary "@$werk/concept" "$api/releases" > "$werk/release"
fi

id=$(jq -er 'select(.draft == true) | .id | numbers' "$werk/release")
bijlagen="$api/releases/$id/assets"
verzoek --fail "$bijlagen" > "$werk/bijlagen"
for naam in "${namen[@]}"; do
  # Na een onderbroken build kan de nieuwe SBOM een andere digest of tijdstempel bevatten.
  oud=$(jq -r --arg naam "$naam" '.[] | select(.name == $naam) | .id' "$werk/bijlagen")
  if [[ -n $oud ]]; then verzoek --fail -X DELETE "$bijlagen/$oud" > /dev/null; fi
  test -s "release/$naam"
  nieuw=$(verzoek --fail -F "attachment=@release/$naam" "$bijlagen?name=$naam" | jq -er '.id | numbers')
  verzoek --fail "$bijlagen/$nieuw" | jq -e --arg naam "$naam" --argjson bytes "$(stat -c %s "release/$naam")" \
    '.name == $naam and .size == $bytes' > /dev/null
done
verzoek --fail -X PATCH -H 'Content-Type: application/json' --data '{"draft":false}' \
  "$api/releases/$id" | jq -e '.draft == false' > /dev/null
