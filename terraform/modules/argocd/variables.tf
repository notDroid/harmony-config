variable repo_url {
  type        = string
  description = "The URL of the Git repository containing the ArgoCD manifests"
  default     = "https://github.com/notDroid/harmony-config.git"
}

variable target_revision {
  type        = string
  description = "The Git revision (branch, tag, or commit) to deploy from"
  default     = "main"
}

variable appset_path {
  type        = string
  description = "The path to the ApplicationSet manifest"
  default     = "environments/local"
}

variable appset_name {
  type        = string
  description = "The name of the ApplicationSet manifest"
  default     = "appset.yaml"
}