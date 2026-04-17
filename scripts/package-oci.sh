#!/usr/bin/env bash
set -e

# Usage: ./scripts/package-oci.sh <manifest_dir> <chart_name> <chart_version> <registry_url>

MANIFEST_DIR=$1
CHART_NAME=$2
CHART_VERSION=$3
REGISTRY_URL=$4

TAR_FILE="dist/${CHART_NAME}-${CHART_VERSION}.tar.gz"
IMAGE_REF="${REGISTRY_URL}/${CHART_NAME}:${CHART_VERSION}"

cd "$(dirname "$0")/.." # Ensure we are in config-repo root

package_manifests() {
    echo "Packaging ${CHART_NAME}:${CHART_VERSION}..."
    mkdir -p dist
    tar -czf "$TAR_FILE" -C "$MANIFEST_DIR" .
}

push_to_registry() {
    echo "Pushing ${IMAGE_REF} to OCI registry..."
    # Argo CD requires exactly one OCI layer with this specific media type for raw manifests
    oras push "$IMAGE_REF" \
        "$TAR_FILE:application/vnd.oci.image.layer.v1.tar+gzip"
}

package_manifests
push_to_registry
echo "✅ Successfully published OCI artifact."
