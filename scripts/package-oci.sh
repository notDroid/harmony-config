#!/bin/bash
set -e

MANIFEST_DIR=$1
CHART_NAME=$2
CHART_VERSION=$3
REGISTRY_URL=$4

echo "Packaging $CHART_NAME:$CHART_VERSION as raw OCI manifests..."
cd "$(dirname "$0")/.." # Go to config-repo root

mkdir -p dist

TAR_FILE="dist/${CHART_NAME}-${CHART_VERSION}.tar.gz"

# 1. Convert Helm hooks to ArgoCD hooks recursively in place
# (ArgoCD directory sources ignore helm.sh/hook annotations)
find "$MANIFEST_DIR" -type f -name "*.yaml" | while read -r file; do
    if grep -q "helm.sh/hook" "$file"; then
        echo "  Converting Helm hook in $file to ArgoCD Sync hook..."
        # Replace helm.sh/hook with argocd.argoproj.io/hook (handling optional quotes)
        sed -i '' 's/.*helm.sh\/hook.*/    argocd.argoproj.io\/hook: Sync/' "$file"
        # Also handle hook-delete-policy
        sed -i '' 's/.*helm.sh\/hook-delete-policy.*/    argocd.argoproj.io\/hook-delete-policy: BeforeHookCreation/' "$file"
    fi
done

# 2. Package the entire directory as a single tarball
# (Argo CD requires exactly one OCI layer for raw manifests)
tar -czf "$TAR_FILE" -C "$MANIFEST_DIR" .

# 2. Push directly to the OCI registry using oras
# We explicitly set the media type that Argo CD expects for raw manifests
oras push "${REGISTRY_URL}/${CHART_NAME}:${CHART_VERSION}" \
    "$TAR_FILE:application/vnd.oci.image.layer.v1.tar+gzip"

echo "Successfully pushed $CHART_NAME:$CHART_VERSION to OCI registry."
