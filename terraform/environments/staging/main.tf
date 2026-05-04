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
      version = ">= 0.11.0"
    }
    aws = { 
        source = "hashicorp/aws"
        version = "~> 6.0" 
    }
  }
}

# Variables mapped from Terragrunt
variable "project_name" { type = string }
variable "environment" { type = string }
variable "vpc_cidr" { type = string }
variable "azs_count" { type = number }

variable "cluster_name" { type = string }
variable "cluster_version" { type = string }

variable "db_name" { type = string }
variable "db_user" { type = string }
variable "db_password" {
  type      = string
  sensitive = true
}
variable "db_instance_class" { type = string }
variable "db_allocated_storage" { type = number }

variable "redis_node_type" { type = string }

variable "chat_history_table_name" { type = string }
variable "automq_data_bucket_name" { type = string }
variable "automq_ops_bucket_name" { type = string }

variable "secret_manager_name" { type = string }

variable "raw_secrets" {
  type      = string
  sensitive = true
}

data "aws_availability_zones" "available" {
  state = "available"
}

module "networking" {
  source       = "../../../.cache-terraform/staging/networking"
  vpc_name     = "harmony-${var.environment}-vpc"
  environment  = var.environment
  project_name = var.project_name
  vpc_cidr     = var.vpc_cidr
  azs          = slice(data.aws_availability_zones.available.names, 0, var.azs_count)
  cluster_name = var.cluster_name
}

module "secrets" {
  source              = "../../../.cache-terraform/staging/secrets"
  environment         = var.environment
  cluster_name        = var.cluster_name
  secret_manager_name = var.secret_manager_name
  raw_secrets         = var.raw_secrets
  project_name        = var.project_name
  depends_on          = [module.compute]
}

module "stateful" {
  source                     = "../../../.cache-terraform/staging/stateful"
  environment                = var.environment
  project_name               = var.project_name
  vpc_id                     = module.networking.vpc_id
  database_subnet_group_name = module.networking.database_subnet_group_name
  database_subnet_ids        = module.networking.database_subnet_ids
  private_subnet_cidrs       = module.networking.private_subnets_cidr_blocks

  db_name              = var.db_name
  db_username          = var.db_user
  db_password          = var.db_password
  db_instance_class    = var.db_instance_class
  db_allocated_storage = var.db_allocated_storage
  redis_node_type      = var.redis_node_type
}

module "storage" {
  source                  = "../../../.cache-terraform/staging/storage"
  environment             = var.environment
  project_name            = var.project_name
  chat_history_table_name = var.chat_history_table_name
  automq_data_bucket_name = var.automq_data_bucket_name
  automq_ops_bucket_name  = var.automq_ops_bucket_name
}

module "compute" {
  source             = "../../../.cache-terraform/staging/compute"
  environment        = var.environment
  project_name       = var.project_name
  vpc_id             = module.networking.vpc_id
  private_subnet_ids = module.networking.private_subnet_ids
  cluster_name       = var.cluster_name
  cluster_version    = var.cluster_version
}

resource "aws_ssm_parameter" "rds_endpoint" {
  name  = "/harmony/${var.environment}/rds_endpoint"
  type  = "String"
  value = module.stateful.rds_endpoint
}

resource "aws_ssm_parameter" "redis_endpoint" {
  name  = "/harmony/${var.environment}/redis_endpoint"
  type  = "String"
  value = module.stateful.redis_endpoint
}

# Neeed some way to get k8s auth info from the EKS module to bootstrap ArgoCD. This is a solution that needs to be found later, for now its non functional and just for demo purposes.
### Bootstrap ArgoCD on the EKS cluster
locals {
  k8s_auth = {
    host                   = module.compute.cluster_endpoint
    cluster_ca_certificate = base64decode(module.compute.cluster_certificate_authority_data)
    exec = {
      api_version = "client.authentication.k8s.io/v1beta1"
      command     = "aws"
      args        = ["eks", "get-token", "--cluster-name", var.cluster_name]
    }
  }
}

# Provider Configuration
provider "helm" {
  kubernetes = local.k8s_auth
}

provider "kubectl" {
  host                   = local.k8s_auth.host
  cluster_ca_certificate = local.k8s_auth.cluster_ca_certificate
  exec {
    api_version = local.k8s_auth.exec.api_version
    command     = local.k8s_auth.exec.command
    args        = local.k8s_auth.exec.args
  }
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