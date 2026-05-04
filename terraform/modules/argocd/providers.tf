terraform {
  required_version = ">= 1.5.0"
  required_providers {
    helm = {
      source  = "hashicorp/helm"
    }
    kubectl = {
      source  = "gavinbunney/kubectl"
    }
  }
}
