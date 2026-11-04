#!/bin/sh
set -e # Halt on errors so failures don't cascade silently

# Setup SUDO and non-interactive apt-get
SUDO=""
[ "$(id -u)" -ne 0 ] && SUDO="sudo"
export DEBIAN_FRONTEND=noninteractive

# Extra CA certificates (optional, gitignored). On a machine whose network does
# TLS inspection (corporate proxy/VPN), export the root CA from the host into
# .devcontainer/certs/*.crt so gem, npm, pip and apt can reach the internet.
# This must run before anything below touches the network.
# macOS: security find-certificate -c "<Root CA name>" -p /Library/Keychains/System.keychain > .devcontainer/certs/<name>.crt
for cert in .devcontainer/certs/*.crt .devcontainer/certs/*.pem; do
    [ -f "$cert" ] || continue
    $SUDO mkdir -p /usr/local/share/ca-certificates/local
    $SUDO cp "$cert" "/usr/local/share/ca-certificates/local/$(basename "$cert" .pem).crt"
    EXTRA_CERTS=1
done
if [ -n "$EXTRA_CERTS" ]; then
    $SUDO update-ca-certificates
fi

# Install the version of Bundler.
if [ -f Gemfile.lock ] && grep "BUNDLED WITH" Gemfile.lock > /dev/null; then
    cat Gemfile.lock | tail -n 2 | grep -C2 "BUNDLED WITH" | tail -n 1 | xargs gem install bundler -v
fi

# If there's a Gemfile, then run `bundle install`
# It's assumed that the Gemfile will install Jekyll too
if [ -f Gemfile ]; then
    bundle install
fi

# Update package lists once
$SUDO apt-get update

# Chromium, used headlessly by mermaid-cli to pre-render diagrams to SVG.
if ! command -v chromium > /dev/null 2>&1; then
    $SUDO apt-get install -y --no-install-recommends --fix-missing chromium fonts-liberation
fi

# System dependencies for bird image processing & EXIF stripping
$SUDO apt-get install -y --no-install-recommends --fix-missing \
  libimage-exiftool-perl \
  imagemagick \
  python3 \
  python3-venv \
  python3-pip

# Clean up apt caches to save space in the container
$SUDO rm -rf /var/lib/apt/lists/*

# Node dependencies (mermaid-cli).
if [ -f package-lock.json ]; then
    npm ci
fi

# Create isolated Python venv for the bird pipeline.
# It lives outside the workspace so Jekyll's file watcher doesn't have to crawl
# its thousands of directories over the bind mount (that cost ~45s per serve).
VENV=/opt/venv-birds
# Check if pip exists, rather than just the directory, to avoid partial-build issues
if [ ! -f "$VENV/bin/pip" ]; then
  echo "Virtual environment missing or broken. Rebuilding..."
  rm -rf "$VENV"
  python3 -m venv "$VENV"
fi

# Installs from the lock files: the exact versions that last passed the checks
# (pip included). scripts/birds/update_deps.py keeps them up to date automatically.
# Core pipeline (required): the container setup fails if this fails
"$VENV/bin/pip" install -r scripts/birds/requirements.txt

# AI suggestions (optional): a failure here only disables suggestions; imports
# still work with fuzzy search. `rake birds:doctor` shows what's wrong.
if ! "$VENV/bin/pip" install -r scripts/birds/requirements-ai.txt; then
  echo "WARNING: AI suggestions unavailable (requirements-ai.txt failed to install)."
  echo "         Imports still work with fuzzy search. Run 'rake birds:doctor' for details."
fi
