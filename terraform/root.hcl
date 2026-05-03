locals {
  # Get the environment name from the child directory (e.g. "staging")
  # path_relative_to_include() returns "environments/staging"
  env = basename(path_relative_to_include())

  # Load environment-specific values from the shared config directory
  values_path = "${get_repo_root()}/environments/${local.env}/values.yaml"

  values = yamldecode(local.values_path)

  project_name = local.values.project_name
  region       = local.values.infra.aws.region
  account_id   = get_aws_account_id()
}

generate "provider" {
  path      = "provider.tf"
  if_exists = "overwrite_terragrunt"
  contents  = <<EOF
provider "aws" {
  region = "${local.region}"
  default_tags {
    tags = {
      Project     = "${local.project_name}"
      Environment = "${local.env}"
      ManagedBy   = "Terragrunt"
    }
  }
}
EOF
}

remote_state {
  backend = "s3"
  generate = {
    path      = "backend.tf"
    if_exists = "overwrite_terragrunt"
  }
  config = {
    bucket         = "harmony-chat-tf-state-${local.account_id}"
    key            = "${path_relative_to_include()}/terraform.tfstate"
    region         = "${local.region}"
    encrypt        = true
    dynamodb_table = "harmony-chat-tf-locks-${local.account_id}"
  }
}