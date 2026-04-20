# Harmony Config Repo

This repository manages the environment-specific configurations, secrets, and GitOps deployment logic for the Harmony Chat application.

## Prerequisites

- [Task](https://taskfile.dev/)
- [Kind](https://kind.sigs.k8s.io/)
- [Kubectl](https://kubernetes.io/docs/tasks/tools/)
- [SOPS](https://github.com/getsops/sops)
- [Age](https://github.com/FiloSottile/age)
- [GH CLI](https://cli.github.com/) (for remote release testing)

## Local Development & Testing

To test the GitOps setup locally using Kind and ArgoCD:

### 1. Initial Setup
Ensure you have an age key for SOPS. If not, generate one:
```bash
age-keygen -o keys.txt
# Followed by setting up SOPS with that key
task secrets:setup
```

### 2. Create Kind Cluster & Install ArgoCD
```bash
task kind:setup
```
This command creates the cluster, installs ArgoCD, and creates the necessary namespaces.

### 3. Build and Load Application Images
From the `app-repo`:
```bash
task image:load:kind
```

### 4. Publish Manifests to Local Registry
We use `ttl.sh` as an ephemeral local OCI registry for testing. You can use the local infra from the `app-repo`:
```bash
LOCAL_INFRA_PATH=../app-repo/infra task infra:publish CHART_VERSION=0.0.1
```

### 5. Deploy with ArgoCD
```bash
# Deploy the application pointing to the OCI artifact version
TARGET_REVISION=0.0.1 task argocd:deploy
```

### 6. Remote Testing (GHCR.io)
To test releases published to GHCR:
1. Ensure your changes are pushed to `main` to trigger the release workflow.
2. Configure ArgoCD with your GitHub credentials (requires `gh` CLI):
   ```bash
   task argocd:repo:creds
   ```
3. Deploy the specific version (check GitHub Actions for the version number, e.g., `1.0.10`):
   ```bash
   REGISTRY_BASE=ghcr.io/your-username TARGET_REVISION=1.0.10 task argocd:deploy
   ```

### 7. Verify and Test
Wait for pods to be ready:
```bash
kubectl get pods -n harmony -w
```

Run integration tests from the `app-repo`:
```bash
# First port-forward the API
kubectl port-forward -n harmony service/api 8000:8000 &
# Then run tests
task test:integration
```

## Repository Structure

- `environments/`: Environment-specific values and secrets.
  - `local/`: Configuration for local Kind cluster.
  - `staging/`: Configuration for the remote staging environment.
- `scripts/`: Helper scripts for fetching k8s components, packaging OCI artifacts, and injecting sync waves.
- `terraform/`: Infrastructure as Code for provisioning remote environments.

## Automated Releases
Pushes to the `main` branch trigger a GitHub Action that packages the rendered manifests and pushes them to GitHub Container Registry (GHCR). ArgoCD in remote clusters is configured to track these OCI artifacts for automated deployment.
