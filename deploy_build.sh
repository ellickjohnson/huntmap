#!/bin/bash
# Build huntmap on the docker host and publish to GHCR.
set -euo pipefail

SRC=/opt/appdata/huntmap/src
TOK=$(cat /root/.gh_token)
GH_USER=ellickjohnson
IMG=ghcr.io/ellickjohnson/huntmap:latest

echo "== fetch source =="
if [ -d "$SRC/.git" ]; then
  cd "$SRC"
  git remote set-url origin "https://${TOK}@github.com/ellickjohnson/huntmap.git"
  git fetch --quiet origin main
  git reset --hard --quiet origin/main
else
  rm -rf "$SRC"
  git clone --quiet "https://${TOK}@github.com/ellickjohnson/huntmap.git" "$SRC"
  cd "$SRC"
fi
echo "HEAD: $(git rev-parse --short HEAD) $(git log -1 --pretty=%s)"

echo "== ghcr login =="
echo "$TOK" | docker login ghcr.io -u "$GH_USER" --password-stdin >/dev/null

echo "== build =="
docker build -q -t "$IMG" "$SRC" | tail -1

echo "== push =="
docker push "$IMG" 2>&1 | tail -3

docker logout ghcr.io >/dev/null 2>&1 || true
echo "== image =="
docker image inspect "$IMG" --format '{{.Id}} created={{.Created}}'
