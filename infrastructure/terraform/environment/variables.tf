# Every input Terraform needs. Values live in terraform.tfvars.
# All Inputs Validated For Protection

# Points to the correct login to use
variable "openstack_cloud" {
  description = "Cloud name inside ~/.config/openstack/clouds.yaml."
  type        = string
  validation {
    condition     = length(var.openstack_cloud) > 0 && !strcontains(var.openstack_cloud, "<")
    error_message = "Set openstack_cloud to the name under 'clouds:' in clouds.yaml."
  }
}

# Connecting edge node to external network and reserving its ip address
variable "external_network_name" {
  description = "Provider network for the router and floating IP."
  type        = string
  validation {
    condition     = !strcontains(var.external_network_name, "<")
    error_message = "Replace the <...> placeholder for external_network_name."
  }
}

# Selects the correct Linux Distro
variable "image_name" {
  description = "Exact Rocky Linux 9 image name (from openstack image list)."
  type        = string
  validation {
    condition     = !strcontains(var.image_name, "<")
    error_message = "Replace the <...> placeholder for image_name."
  }
}

# Add's team captain's ssh key to all VMs
variable "ssh_public_key" {
  description = "Operator's PUBLIC key, installed for the default user on every VM."
  type        = string
  validation {
    condition     = startswith(var.ssh_public_key, "ssh-")
    error_message = "ssh_public_key must be a public key line starting with 'ssh-'."
  }
}

# One variable to rule them all!!
variable "flavors" {
  description = "Exact flavor names for each machine instance type."
  type = object({
    edge          = string # ~4 vCPU / 10 GB
    api_lb        = string # ~2 vCPU / 4 GB
    control_plane = string # ~4 vCPU / 8 GB
    worker        = string # ~8 vCPU / 16 GB
  })
  validation {
    condition     = alltrue([for f in values(var.flavors) : length(f) > 0 && !strcontains(f, "<")])
    error_message = "Every flavor needs a real name from 'openstack flavor list'."
  }
}

# Range of all private addressed for the management network
variable "mgmt_cidr" {
  description = "Management network (edge-01)."
  type        = string
  validation {
    condition     = can(cidrhost(var.mgmt_cidr, 250))
    error_message = "mgmt_cidr must be a valid CIDR of /24 or larger."
  }
}

# Same as above but for the Kubernetes network addresses
variable "k8s_cidr" {
  description = "Kubernetes node network."
  type        = string
  validation {
    condition     = can(cidrhost(var.k8s_cidr, 250))
    error_message = "k8s_cidr must be a valid CIDR of /24 or larger, e.g. 10.151.0.0/24."
  }
}

# On first boot, VM finds what DNS server to use
variable "dns_nameservers" {
  description = "DNS resolvers handed to the VMs."
  type        = list(string)
  validation {
    condition     = length(var.dns_nameservers) > 0 && alltrue([for ip in var.dns_nameservers : can(cidrhost("${ip}/32", 0))])
    error_message = "dns_nameservers must be a list of IP addresses."
  }
}

# Rest of teams ssh keys
variable "bootstrap_ssh_cidrs" {
  description = "Team members' public IPs as /32, allowed to SSH to edge-01 until the VPN works."
  type        = list(string)
  validation {
    condition     = alltrue([for c in var.bootstrap_ssh_cidrs : can(cidrnetmask(c)) && c != "0.0.0.0/0"])
    error_message = "Use real addresses like 203.0.113.7/32."
  }
}

# Defaults needed for terraform
variable "enable_bootstrap_ssh" {
  description = "Public SSH to edge-01. Set to false once EVERY member has working WireGuard access."
  type        = bool
  default     = true
}

# Defaults needed for terraform
variable "name_prefix" {
  description = "Prefix for every OpenStack resource name."
  type        = string
  default     = "inference-fabric"
}