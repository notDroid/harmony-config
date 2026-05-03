terraform {
  required_version = ">= 1.0.0"
  required_providers {
    helm = {
      source  = "hashicorp/helm"
      version = "~> 3.0"
    }
    kubectl = {
      source  = "gavinbunney/kubectl"
      version = ">= 1.19.0"
    }
    kind = {
      source  = "tehcyx/kind"
      version = "0.11.0"
    }
  }
}

# Kind Cluster

provider "kind" {}

variable "cluster_name" {
  type        = string
  description = "The name of the Kind cluster to create"
  default     = "harmony-local"

}

resource "kind_cluster" "k8s_cluster" {
  name           = var.cluster_name
  wait_for_ready = true

  kind_config {
    kind        = "Cluster"
    api_version = "kind.x-k8s.io/v1alpha4"

    node {
      role = "control-plane"

      extra_port_mappings {
        container_port = 8000
        host_port      = 8000
      }
    }
  }
}

locals {
  k8s_auth = {
    host                   = kind_cluster.k8s_cluster.endpoint
    cluster_ca_certificate = kind_cluster.k8s_cluster.cluster_ca_certificate
    client_certificate     = kind_cluster.k8s_cluster.client_certificate
    client_key             = kind_cluster.k8s_cluster.client_key
  }
}

# Provider Configuration
provider "helm" {
  kubernetes = local.k8s_auth
}

provider "kubectl" {
  host                   = local.k8s_auth.host
  cluster_ca_certificate = local.k8s_auth.cluster_ca_certificate
  client_certificate     = local.k8s_auth.client_certificate
  client_key             = local.k8s_auth.client_key
  load_config_file       = false
}

# Install ArgoCD
resource "helm_release" "argocd" {
  name             = "argocd"
  repository       = "https://argoproj.github.io/argo-helm"
  chart            = "argo-cd"
  namespace        = "argocd"
  create_namespace = true
  version          = "7.3.11"

  values = [
    yamlencode({
      configs = {
        params = {
          "applicationsetcontroller.enable.progressive.syncs" = "true"
        }
      }
    })
  ]
}

# Bootstrap ArgoCD

# ArgoCD Bootstrap Application
resource "kubectl_manifest" "argocd_bootstrap" {
  depends_on = [helm_release.argocd]

  yaml_body = yamlencode({
    apiVersion = "argoproj.io/v1alpha1"
    kind       = "Application"
    metadata = {
      name      = "root-bootstrap"
      namespace = "argocd"
    }
    spec = {
      project = "default"
      source = {
        repoURL        = "https://github.com/notDroid/harmony-config.git"
        targetRevision = "main"
        path           = "environments/local"
        directory = {
          include = "appset.yaml"
        }
      }
      destination = {
        server    = "https://kubernetes.default.svc"
        namespace = "argocd"
      }
      syncPolicy = {
        automated = {
          prune    = true
          selfHeal = true
        }
      }
    }
  })
}

output "kubeconfig" {
  value     = kind_cluster.k8s_cluster.kubeconfig
  sensitive = true
}
