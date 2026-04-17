#!/bin/bash
set -e

VERSION=$1
CACHE_DIR=$2
REPO_URL=$3

if [[ -d "$VERSION" ]]; then
    echo "Using local infra from $VERSION..."
    rm -rf "$CACHE_DIR"
    mkdir -p "$CACHE_DIR"
    cp -r "$VERSION/"* "$CACHE_DIR/"
    echo "local" > "$CACHE_DIR/.version"
    exit 0
fi

echo "Fetching infra v$VERSION from $REPO_URL..."
rm -rf .cache/temp_extract
mkdir -p .cache/temp_extract

DOWNLOAD_URL="${REPO_URL%/}/archive/refs/tags/${VERSION}.tar.gz"
TEMP_TAR=".cache/infra.tar.gz"

curl -sL "$DOWNLOAD_URL" -o "$TEMP_TAR"
tar xzf "$TEMP_TAR" -C .cache/temp_extract

# Find the infra directory inside the extracted content
INFRA_SRC=$(find .cache/temp_extract -type d -name "infra" | head -n 1)

rm -rf "$CACHE_DIR"
mv "$INFRA_SRC" "$CACHE_DIR"

# Cleanup
rm -rf .cache/temp_extract "$TEMP_TAR"
echo "$VERSION" > "$CACHE_DIR/.version"
