output "edge_floating_ip" {
  description = "Public address of edge-01 (SSH during bootstrap, WireGuard endpoint)."
  value       = openstack_networking_floatingip_v2.edge.address
}

output "private_ips" {
  description = "Fixed private IP of every machine."
  value       = { for name, node in local.nodes : name => node.ip }
}

output "bootstrap_ssh_open" {
  description = "Whether public SSH to edge-01 is currently allowed."
  value       = var.enable_bootstrap_ssh
}

output "security_rules" {
  description = "Every cloud firewall rule name."
  value       = sort(keys(local.rules))
}

# Standard-ish ansible inventory file
output "inventory_hosts" {
  value = <<-EOT
    edge_nodes:
      hosts:
        edge-01:
          ansible_host: "${openstack_networking_floatingip_v2.edge.address}"
          private_ip: "${local.edge_ip}"
    private_nodes:
      vars:
        ansible_ssh_common_args: "-o ProxyJump=rocky@${openstack_networking_floatingip_v2.edge.address}"
      children:
        api_lb:
          hosts:
            api-lb-01: {ansible_host: "${local.api_lb_ip}"}
        control_plane:
          hosts:
            k8s-cp-01: {ansible_host: "${local.nodes["k8s-cp-01"].ip}"}
        workers:
          hosts:
            k8s-worker-01: {ansible_host: "${local.nodes["k8s-worker-01"].ip}"}
            k8s-worker-02: {ansible_host: "${local.nodes["k8s-worker-02"].ip}"}
  EOT
}