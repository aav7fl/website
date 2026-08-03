#!/bin/sh

# Install the version of Bundler.
if [ -f Gemfile.lock ] && grep "BUNDLED WITH" Gemfile.lock > /dev/null; then
    cat Gemfile.lock | tail -n 2 | grep -C2 "BUNDLED WITH" | tail -n 1 | xargs gem install bundler -v
fi

# If there's a Gemfile, then run `bundle install`
# It's assumed that the Gemfile will install Jekyll too
if [ -f Gemfile ]; then
    bundle install
fi

# Chromium, used headlessly by mermaid-cli to pre-render diagrams to SVG.
# Puppeteer has no linux/arm64 Chromium build, so Debian's package is what
# PUPPETEER_EXECUTABLE_PATH points at (see devcontainer.json).
# fonts-liberation gives Chromium metric-compatible stand-ins for the Arial and
# Verdana that Mermaid's default font stack asks for.
if ! command -v chromium > /dev/null 2>&1; then
    SUDO=""
    [ "$(id -u)" -ne 0 ] && SUDO="sudo"
    export DEBIAN_FRONTEND=noninteractive
    $SUDO apt-get update
    $SUDO apt-get install -y --no-install-recommends chromium fonts-liberation
    $SUDO rm -rf /var/lib/apt/lists/*
fi

# Node dependencies (mermaid-cli).
if [ -f package-lock.json ]; then
    npm ci
fi