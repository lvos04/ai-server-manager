# Ontwikkelmachine opzetten (Ubuntu 24.04, passwordless sudo)

Dit is de **ontwikkel-/testmachine** voor de bouwer (Claude Code via SSH), niet de TrueNAS. Niets hiervan draait op de NAS.
Controleer de Ubuntu-versie met `lsb_release -a`; bij 22.04 zijn de PGDG- en NodeSource-repos verplicht (zie onder).

```bash
set -euo pipefail
sudo apt-get update
sudo apt-get install -y git curl wget ca-certificates gnupg lsb-release build-essential jq unzip zip \
  python3.12 python3.12-venv python3-pip openjdk-21-jdk cmake ninja-build pkg-config redis-server

# GitHub CLI
sudo mkdir -p -m 755 /etc/apt/keyrings
wget -qO- https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg >/dev/null
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
  | sudo tee /etc/apt/sources.list.d/github-cli.list >/dev/null
sudo apt-get update && sudo apt-get install -y gh

# Docker Engine + buildx + compose (officiële repo)
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
sudo apt-get update && sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker "$USER"   # daarna opnieuw inloggen of: newgrp docker

# PostgreSQL 16 + pgvector (PGDG-repo, werkt op 22.04 en 24.04)
curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo gpg --dearmor -o /etc/apt/keyrings/pgdg.gpg
echo "deb [signed-by=/etc/apt/keyrings/pgdg.gpg] https://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" \
  | sudo tee /etc/apt/sources.list.d/pgdg.list >/dev/null
sudo apt-get update && sudo apt-get install -y postgresql-16 postgresql-16-pgvector
# Alleen voor lokale tests: rol postgres zonder wachtwoord, uitsluitend via 127.0.0.1 (de testsuites verwachten
# postgresql+psycopg://postgres@127.0.0.1:5432/...). Niet gebruiken op een machine die anderen kunnen bereiken.
PGHBA=$(sudo -u postgres psql -tAc "show hba_file")
sudo sed -i '1i host all postgres 127.0.0.1/32 trust' "$PGHBA"
sudo sed -i "s/^#\?max_connections.*/max_connections = 400/" /etc/postgresql/16/main/postgresql.conf
sudo systemctl restart postgresql
psql -h 127.0.0.1 -U postgres -c "create extension if not exists vector; select extversion from pg_extension where extname='vector';"

# Node 22 + pnpm
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt-get install -y nodejs
sudo corepack enable && corepack prepare pnpm@latest --activate   # pnpm-versie per repo vastzetten via packageManager

# Playwright + Chromium (voor de Hub-PWA-tests)
npx -y playwright@1 install --with-deps chromium

# .NET 9 voor jelly-leon: via container (geen installatie nodig)
docker pull mcr.microsoft.com/dotnet/sdk:9.0

# Optioneel: Android SDK command-line tools voor jelly-leon-clients (android/androidtv)
# https://developer.android.com/studio#command-line-tools-only → uitpakken in ~/android-sdk/cmdline-tools/latest
# export ANDROID_HOME=~/android-sdk; sdkmanager "platform-tools" "platforms;android-36" "build-tools;36.0.0"

# Controle
nproc; free -g; df -h ~; docker info | grep -E 'Server Version|CPUs|Total Memory'; python3.12 --version; node --version; java -version
```

## Repos klonen

```bash
mkdir -p ~/truenas-v2 && cd ~/truenas-v2
gh auth status || gh auth login        # schrijfrechten op lvos04/*
gh auth setup-git
for r in ai-server-manager home-control-hub appstore-en-fork jelly-leon-platform zoeken-en-persoonlijke-ai \
         media-guard-ultimate media-source-optimizer my_house; do
  git clone -b ccr-c133d7a0-kuz1cv https://github.com/lvos04/$r.git
done
for r in jelly-leon jelly-leon-web jelly-leon-clients; do
  git clone --filter=blob:none -b ccr-c133d7a0-kuz1cv https://github.com/lvos04/$r.git
done
git -C jelly-leon remote add upstream https://github.com/jellyfin/jellyfin.git
git -C jelly-leon-web remote add upstream https://github.com/jellyfin/jellyfin-web.git
git config --global user.name  >/dev/null || git config --global user.name  "<naam>"
```

## Verschillen met de oude sandbox

- Geen proxy/CA meer nodig: haal in de workflow-scripts het proxy-/CA-deel uit het `OMGEVING:`-blok. De Dockerfiles houden hun
  optionele BuildKit-secret `ca_bundle` (schadeloos als die ontbreekt).
- GHCR-images en -blobs waren in de sandbox geblokkeerd (403 op pkg-containers.githubusercontent.com); hier normaal te pullen
  (voor privépakketten: `echo $(gh auth token) | docker login ghcr.io -u <gebruiker> --password-stdin`).
- Android-SDK en Gradle-downloads waren geblokkeerd; hier kunnen de Android-builds echt lokaal gedraaid worden.
- De sandbox had 4 CPU's (workflow-limiet 2 agents tegelijk). Stem parallelle agents en zware builds af op `nproc` hier.
