#!/usr/bin/env bash
set -e

# Usage: ./scripts/fetch-infra.sh <version> <cache_dir> <repo_url>

VERSION=$1
CACHE_DIR=$2
REPO_URL=$3

copy_local_infra() {
    echo "Using local infra from $LOCAL_INFRA_PATH..."
    rm -rf "$CACHE_DIR"
    mkdir -p "$CACHE_DIR"
    cp -r "$LOCAL_INFRA_PATH/"* "$CACHE_DIR/"
    echo "local" > "$CACHE_DIR/.version"
}

download_remote_infra() {
    if [[ -z "$VERSION" || -z "$REPO_URL" ]]; then
        echo "Error: VERSION and REPO_URL are required if LOCAL_INFRA_PATH is not set or invalid."
        exit 1
    fi

    echo "Fetching infra $VERSION from $REPO_URL..."
    local extract_dir=".cache/temp_extract"
    local temp_tar=".cache/infra.tar.gz"
    local download_url="${REPO_URL%/}/archive/refs/tags/${VERSION}.tar.gz"

    rm -rf "$extract_dir"
    mkdir -p "$extract_dir"

    curl -sL "$download_url" -o "$temp_tar"
    tar xzf "$temp_tar" -C "$extract_dir"

    local infra_src
    infra_src=$(find "$extract_dir" -type d -name "infra" | head -n 1)

    rm -rf "$CACHE_DIR"
    mv "$infra_src" "$CACHE_DIR"

    rm -rf "$extract_dir" "$temp_tar"
    echo "$VERSION" > "$CACHE_DIR/.version"
}

if [[ -n "$LOCAL_INFRA_PATH" && -d "$LOCAL_INFRA_PATH" ]]; then
    copy_local_infra
else
    download_remote_infra
fi
