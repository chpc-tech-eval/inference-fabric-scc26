# =============================================================================
# FIXED ADDRESSES
# =============================================================================
locals { # Helper Values
  edge_ip   = cidrhost(var.mgmt_cidr, 10)
  api_lb_ip = cidrhost(var.k8s_cidr, 100)

  networks = { mgmt = var.mgmt_cidr, k8s = var.k8s_cidr }

  # Looping over the map - master list
  # Key                 ip                  flavour                     firewall group  net type            
  nodes = {
    "edge-01"       = { ip = local.edge_ip, flavor = var.flavors.edge, group = "edge", net = "mgmt" }
    "api-lb-01"     = { ip = local.api_lb_ip, flavor = var.flavors.api_lb, group = "api-lb", net = "k8s" }
    "k8s-cp-01"     = { ip = cidrhost(var.k8s_cidr, 11), flavor = var.flavors.control_plane, group = "k8s-control-plane", net = "k8s" }
    "k8s-worker-01" = { ip = cidrhost(var.k8s_cidr, 21), flavor = var.flavors.worker, group = "k8s-worker", net = "k8s" }
    "k8s-worker-02" = { ip = cidrhost(var.k8s_cidr, 22), flavor = var.flavors.worker, group = "k8s-worker", net = "k8s" }
  }
}

# =============================================================================
# LOOK-UPS
# =============================================================================
data "openstack_networking_network_v2" "external" {
  name = var.external_network_name
}

data "openstack_images_image_v2" "rocky" {
  name        = var.image_name
  most_recent = true
}

# =============================================================================
# NETWORKS + ROUTER
# =============================================================================
# Builds the networks
resource "openstack_networking_network_v2" "net" {
  for_each = local.networks
  name     = "${var.name_prefix}-${each.key}"
}

# Creating subnet - ie assigning networks addresses
resource "openstack_networking_subnet_v2" "net" {
  for_each        = local.networks
  name            = "${var.name_prefix}-${each.key}-subnet"
  network_id      = openstack_networking_network_v2.net[each.key].id
  cidr            = each.value              # Address Range
  gateway_ip      = cidrhost(each.value, 1) # Router's Address
  dns_nameservers = var.dns_nameservers

  # Ensuring no automatic grabbing of 0.10 or .100
  allocation_pool {
    start = cidrhost(each.value, 200)
    end   = cidrhost(each.value, 250)
  }

  lifecycle {
    precondition {
      condition     = var.mgmt_cidr != var.k8s_cidr
      error_message = "mgmt_cidr and k8s_cidr must be different networks."
    }
  }
}

# Creating one router
resource "openstack_networking_router_v2" "main" {
  name                = "${var.name_prefix}-router"
  external_network_id = data.openstack_networking_network_v2.external.id
}

# Plugging router into both subnets
resource "openstack_networking_router_interface_v2" "net" {
  for_each  = openstack_networking_subnet_v2.net
  router_id = openstack_networking_router_v2.main.id
  subnet_id = each.value.id
}

# =============================================================================
# CLOUD FIREWALL
# =============================================================================
locals {
  M = var.mgmt_cidr
  K = var.k8s_cidr

  # Dear lord this took so long... 
  # Jist is: Accepting traffic on different networks to different ports and specifying comms protocol
  # Will need to add rules for kubernetes
  base_rules = {
    # name               = [security group,      protocol, from,  to,    source]
    edge-dns-udp-mgmt = ["edge", "udp", 53, 53, local.M]
    edge-dns-tcp-mgmt = ["edge", "tcp", 53, 53, local.M]
    edge-dns-udp-k8s  = ["edge", "udp", 53, 53, local.K]
    edge-dns-tcp-k8s  = ["edge", "tcp", 53, 53, local.K]
    edge-wireguard    = ["edge", "udp", 51820, 51820, "0.0.0.0/0"]
    edge-icmp-k8s     = ["edge", "icmp", 0, 0, local.K]
    api-lb-ssh        = ["api-lb", "tcp", 22, 22, local.M]
    api-lb-icmp       = ["api-lb", "icmp", 0, 0, local.M]
    cp-ssh            = ["k8s-control-plane", "tcp", 22, 22, local.M]
    cp-icmp           = ["k8s-control-plane", "icmp", 0, 0, local.M]
    worker-ssh        = ["k8s-worker", "tcp", 22, 22, local.M]
    worker-icmp       = ["k8s-worker", "icmp", 0, 0, local.M]
  }

  # Temporary public SSH to edge-01 (disappears when enable_bootstrap_ssh = false)
  bootstrap_rules = var.enable_bootstrap_ssh ? {
    for cidr in var.bootstrap_ssh_cidrs :
    "edge-ssh-bootstrap-${replace(replace(cidr, ".", "-"), "/", "_")}" => ["edge", "tcp", 22, 22, cidr]
  } : {}

  rules = merge(local.base_rules, local.bootstrap_rules)
}

# Security Groups
resource "openstack_networking_secgroup_v2" "group" {
  for_each    = toset(["edge", "api-lb", "k8s-control-plane", "k8s-worker"])
  name        = "${var.name_prefix}-${each.key}"
  description = "Managed by Terraform"
}

resource "openstack_networking_secgroup_rule_v2" "rule" {
  for_each          = local.rules
  description       = each.key
  direction         = "ingress"
  ethertype         = "IPv4"
  security_group_id = openstack_networking_secgroup_v2.group[each.value[0]].id
  protocol          = each.value[1]
  port_range_min    = each.value[1] == "icmp" ? null : each.value[2]
  port_range_max    = each.value[1] == "icmp" ? null : each.value[3]
  remote_ip_prefix  = each.value[4]
}

# =============================================================================
# THE FIVE MACHINES (one fixed-IP port + one instance each)
# =============================================================================
# Uploading Admin's Key (Open stack has one primary key pair)
resource "openstack_compute_keypair_v2" "operator" {
  name       = "${var.name_prefix}-operator"
  public_key = var.ssh_public_key
}

resource "openstack_networking_port_v2" "node" {
  for_each           = local.nodes
  name               = "${each.key}-port"
  network_id         = openstack_networking_network_v2.net[each.value.net].id
  security_group_ids = [openstack_networking_secgroup_v2.group[each.value.group].id]

  fixed_ip {
    subnet_id  = openstack_networking_subnet_v2.net[each.value.net].id
    ip_address = each.value.ip
  }
}

# Creating the instances
resource "openstack_compute_instance_v2" "node" {
  for_each    = local.nodes
  name        = each.key
  image_id    = data.openstack_images_image_v2.rocky.id
  flavor_name = each.value.flavor
  key_pair    = openstack_compute_keypair_v2.operator.name
  tags        = ["project=scc26", "role=${each.value.group}"]

  network {
    port = openstack_networking_port_v2.node[each.key].id
  }

  # The router must be connected so the VM can reach package mirrors on first boot.
  depends_on = [openstack_networking_router_interface_v2.net]
}

# Only one public address (for the edge node)
resource "openstack_networking_floatingip_v2" "edge" {
  pool        = var.external_network_name
  description = "${var.name_prefix} edge-01"
}

resource "openstack_networking_floatingip_associate_v2" "edge" {
  floating_ip = openstack_networking_floatingip_v2.edge.address
  port_id     = openstack_networking_port_v2.node["edge-01"].id
}