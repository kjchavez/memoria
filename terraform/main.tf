terraform {
  required_version = ">= 1.5"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  # Backend will be configured per environment
  # terraform init -backend-config="bucket=memoria-tfstate-{project}"
  backend "gcs" {}
}

provider "google" {
  project = var.project_id
  region  = var.region
}
