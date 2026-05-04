terraform {
  required_version = ">= 1.5.0"
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

# Boostrap ArgoCD
module "argocd" {
  source = "../../modules/argocd"

  repo_url = "https://github.com/notDroid/harmony-config.git"
  target_revision = "main"
  appset_path = "environments/local"
  appset_name = "appset.yaml"
}

output "kubeconfig" {
  value     = kind_cluster.k8s_cluster.kubeconfig
  sensitive = true
}
