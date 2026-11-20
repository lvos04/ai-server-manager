#!/usr/bin/env bash
# De buildengine vraagt de registergegevens via de omgevingsvariabelen van deze stap.
set -euo pipefail
: "${REGISTRY_USER:?}" "${REGISTRY_TOKEN:?}"
werk=$(mktemp -d "$RUNNER_TEMP/release-images.XXXXXXXX")
export DOCKER_CONFIG="$werk/docker"
mkdir -p "$DOCKER_CONFIG" release
export PATH="$werk:$PATH"
cat > "$werk/docker-credential-forgejo" <<'HELPER'
#!/bin/sh
set -eu
test "$1" = get && test "$(cat)" = "$REGISTRY" || exit 1
jq -nc '{Username:env.REGISTRY_USER, Secret:env.REGISTRY_TOKEN}'
HELPER
chmod 700 "$werk/docker-credential-forgejo"
jq -n --arg registry "$REGISTRY" '{credHelpers:{($registry):"forgejo"}}' > "$DOCKER_CONFIG/config.json"

bouwer="asm-release-${GITHUB_RUN_ID}-${werk##*.}"
trap 'docker buildx rm "$bouwer" >/dev/null 2>&1 || true; rm -rf -- "$werk"' EXIT
docker buildx create --name "$bouwer" --driver docker-container
for app in ai-server-manager ai-server-manager-executor; do
  map=allinone
  if [[ $app == ai-server-manager-executor ]]; then map=executor; fi
  repository="$REGISTRY/leon/$app"
  docker buildx build --builder "$bouwer" --platform linux/amd64 --push \
    --sbom=true --provenance=mode=max --metadata-file "$werk/$app.json" \
    --build-arg VERSION="$VERSION" --build-arg REVISION="$RELEASE_COMMIT" \
    -f "deploy/$map/Dockerfile" -t "$repository:$VERSION" .
  digest=$(jq -er '.["containerimage.digest"] | select(test("^sha256:[0-9a-f]{64}$"))' "$werk/$app.json")
  docker buildx imagetools inspect "$repository@$digest" --format '{{json .SBOM}}' |
    jq -e '(.SPDX // .["linux/amd64"].SPDX) | select(.spdxVersion | startswith("SPDX-"))' \
      > "release/sbom-$app.spdx.json"
  jq -n --arg app "$app" --arg repository "$repository" --arg tag "$VERSION" --arg digest "$digest" \
    '{($app): {$repository, $tag, $digest}}' > "$werk/image-$app.json"
done
jq -s --arg version "$VERSION" --arg commit "$RELEASE_COMMIT" \
  '{version:$version, commit:$commit, images:add}' "$werk"/image-*.json > release/digests.json
