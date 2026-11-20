#!/usr/bin/env bash
# Publiceer de conceptrelease pas nadat de drie bijlagen vanaf Forgejo zijn teruggelezen.
set -euo pipefail
api="https://git.medialeon.nl/api/v1/repos/leon/ai-server-manager"
werk=$(mktemp -d "$RUNNER_TEMP/release-bijlagen.XXXXXXXX")
trap 'rm -rf -- "$werk"' EXIT
verzoek() {
  curl --silent --show-error --header @<(printf 'Authorization: token %s\n' "$RELEASE_TOKEN") "$@"
}

tag=$(jq -rn --arg naam "$GITHUB_REF_NAME" '$naam|@uri')
verzoek --fail "$api/tags/$tag" | jq -e --arg sha "$GITHUB_SHA" '.commit.sha == $sha' > /dev/null
code=$(verzoek -o "$werk/release" -w '%{http_code}' "$api/releases/tags/$tag")
case "$code" in
  200) ;;
  404)
    tekst="Images voor versie $VERSION: $IMAGE_PREFIX:$VERSION en $IMAGE_PREFIX-executor:$VERSION. De digests in deze bijlage horen bij het Forgejo-register. Zie CHANGELOG.md en deploy/truenas/CUSTOM_APP.md."
    jq -n --arg tag "$GITHUB_REF_NAME" --arg body "$tekst" \
      '{tag_name:$tag, name:$tag, body:$body, draft:true}' > "$werk/concept"
    verzoek --fail -H 'Content-Type: application/json' --data-binary "@$werk/concept" \
      "$api/releases" > "$werk/release"
    ;;
  *) echo "Opvragen van de release gaf HTTP $code" >&2; exit 1 ;;
esac

id=$(jq -er '.id | numbers' "$werk/release")
for naam in digests.json sbom-ai-server-manager.spdx.json sbom-ai-server-manager-executor.spdx.json; do
  bijlagen="$api/releases/$id/assets"
  url=$(verzoek --fail "$bijlagen" | jq -r --arg naam "$naam" '.[] | select(.name == $naam) | .browser_download_url')
  if [[ -z $url ]]; then
    url=$(verzoek --fail -F "attachment=@release/$naam" "$bijlagen?name=$naam" | jq -er '.browser_download_url')
  fi
  # De authenticatieheader gaat uitsluitend naar de eigen Forgejo-server.
  [[ $url == "https://git.medialeon.nl/"* ]]
  verzoek --fail --location --proto-redir "=https" "$url" -o "$werk/bijlage"
  cmp "release/$naam" "$werk/bijlage"
done
verzoek --fail -X PATCH -H 'Content-Type: application/json' --data '{"draft":false}' \
  "$api/releases/$id" | jq -e '.draft == false' > /dev/null
