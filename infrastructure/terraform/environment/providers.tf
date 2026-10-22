# Terraform and OpenStack plugin to use - pinned for uniformity across team
terraform {
  required_version = ">= 1.9.0"

  required_providers {
    openstack = {
      source  = "terraform-provider-openstack/openstack"
      version = "3.4.0"
    }
  }
}

# Credentials from ~/.config/openstack/clouds.yaml (set in terraform.tfvars)
provider "openstack" {
  cloud = var.openstack_cloud
}