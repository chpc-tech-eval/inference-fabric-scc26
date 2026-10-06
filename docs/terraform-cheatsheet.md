# Terraform dictionary

A quick reference for the syntax and ideas used in `infrastructure/terraform/`. Examples come from our own files.

## Core concepts

| Term | Meaning |
| --- | --- |
| **Infrastructure as Code** | Describing infrastructure in text files that a tool makes real |
| **Declarative** | You describe the end result; Terraform works out the steps and their order |
| **Provider** | A plugin that talks to one platform. Ours is `openstack` |
| **Resource** | Something Terraform creates and manages (a network, a machine) |
| **Data source** | Something that already exists, which Terraform only looks up |
| **Variable** | An input, filled in from `terraform.tfvars` |
| **Local** | A helper value worked out once and reused |
| **Output** | A value printed after `apply` |
| **State** | Terraform's record of what it built (`terraform.tfstate`). Never committed |
| **Plan** | A preview of the changes needed to make reality match the files |
| **Apply** | Carrying out a plan |
| **Drift** | Differences caused by changes made outside Terraform |
| **Idempotent** | Running it again changes nothing if nothing changed |

## Blocks

Almost everything is a **block**: a keyword, labels, then settings in `{ }`.

```hcl
resource "openstack_networking_router_v2" "main" {   # keyword "type" "our name"
  name = "inference-fabric-router"                   # argument = value
}
```

| Block | Purpose | Example |
| --- | --- | --- |
| `terraform { }` | Settings for Terraform itself | required version, providers |
| `provider "x" { }` | Configure a plugin | `provider "openstack" { cloud = var.openstack_cloud }` |
| `resource "type" "name" { }` | Create something | `resource "openstack_compute_instance_v2" "node"` |
| `data "type" "name" { }` | Look something up | `data "openstack_images_image_v2" "rocky"` |
| `variable "name" { }` | Declare an input | `variable "k8s_cidr"` |
| `locals { }` | Define helper values | `locals { edge_ip = cidrhost(var.mgmt_cidr, 10) }` |
| `output "name" { }` | Declare a result to print | `output "edge_floating_ip"` |
| Nested block | A block inside a resource | `allocation_pool { ... }`, `fixed_ip { ... }` |

## Types of value

| Type | Written as | Example |
| --- | --- | --- |
| string | `"text"` | `"Rocky 9"` |
| number | `42` | `51820` |
| bool | `true` / `false` | `enable_bootstrap_ssh = true` |
| list | `[a, b]` (ordered) | `["1.1.1.1", "1.0.0.1"]` |
| map | `{ key = value }` | `{ mgmt = var.mgmt_cidr, k8s = var.k8s_cidr }` |
| object | a map with fixed, typed keys | `object({ edge = string, worker = string })` |
| set | a list with no duplicates or order | `toset(["edge", "api-lb"])` |
| null | "no value; leave this setting out" | `port_range_min = null` |

## Referring to things

| Syntax | Means | Example |
| --- | --- | --- |
| `var.name` | A variable's value | `var.k8s_cidr` |
| `local.name` | A local value | `local.edge_ip` |
| `type.name.attribute` | An attribute of a resource | `openstack_networking_router_v2.main.id` |
| `data.type.name.attribute` | An attribute of a data source | `data.openstack_images_image_v2.rocky.id` |
| `thing["key"]` | One copy of a `for_each` resource | `openstack_networking_port_v2.node["edge-01"]` |
| `list[0]` | Item by position (from 0) | `each.value[0]` |
| `map.key` | Item by name | `var.flavors.edge` |

Referring to another block also makes Terraform build that block **first**.

## Expressions

| Syntax | Meaning | Example |
| --- | --- | --- |
| `"${...}"` | Insert a value into text | `"${var.name_prefix}-router"` |
| `a ? b : c` | If `a` then `b`, else `c` | `var.enable_bootstrap_ssh ? {...} : {}` |
| `[for x in list : expr]` | Build a list from a list | `[for f in values(var.flavors) : length(f) > 0]` |
| `{ for x in list : k => v }` | Build a map | `{ for cidr in var.bootstrap_ssh_cidrs : "edge-ssh-..." => [...] }` |
| `==`, `!=` | Equal, not equal | `var.mgmt_cidr != var.k8s_cidr` |
| `&&`, `\|\|`, `!` | And, or, not | `length(x) > 0 && !strcontains(x, "<")` |
| `<<-EOT ... EOT` | Multi-line text (heredoc) | the `inventory_hosts` output |
| `#` | Comment | `# Router's address` |

## Meta-arguments

Special settings that work on any resource.

| Argument | Meaning | Example |
| --- | --- | --- |
| `for_each` | Make one copy per item in a map or set | `for_each = local.nodes` |
| `each.key` / `each.value` | The current item's name / value inside `for_each` | `name = each.key` |
| `depends_on` | Force an order Terraform can't see | instances wait for router interfaces |
| `lifecycle { precondition { } }` | A check run during `plan` | `mgmt_cidr != k8s_cidr` |

## Variables

```hcl
variable "k8s_cidr" {
  description = "Kubernetes node network"
  type        = string
  default     = "10.151.0.0/24"            # optional: makes the variable optional
  validation {
    condition     = can(cidrhost(var.k8s_cidr, 250))
    error_message = "Must be a /24 or larger."
  }
}
```

| Part | Meaning |
| --- | --- |
| `description` | Human note |
| `type` | Allowed kind of value |
| `default` | Used when `terraform.tfvars` doesn't set it |
| `validation` | `condition` must be true, or Terraform stops with `error_message` |

Values go in `terraform.tfvars` as `name = value`, one per line.

## Functions we use

| Function | Returns | Example → result |
| --- | --- | --- |
| `cidrhost(range, n)` | The nth address in a range | `cidrhost("10.151.0.0/24", 11)` → `"10.151.0.11"` |
| `cidrnetmask(range)` | The range's netmask (errors if invalid) | `cidrnetmask("1.2.3.4/32")` → `"255.255.255.255"` |
| `can(expr)` | `true` if `expr` works, `false` if it errors | `can(cidrhost("bad", 1))` → `false` |
| `length(x)` | Characters in text, or items in a list | `length(["a", "b"])` → `2` |
| `strcontains(s, sub)` | Whether text contains something | `strcontains("<x>", "<")` → `true` |
| `startswith(s, prefix)` | Whether text starts with something | `startswith("ssh-ed25519 ...", "ssh-")` → `true` |
| `replace(s, from, to)` | Swap text | `replace("1.2.3.4", ".", "-")` → `"1-2-3-4"` |
| `alltrue(list)` | Whether every item is true | `alltrue([true, false])` → `false` |
| `values(map)` | A map's values as a list | `values({a = 1, b = 2})` → `[1, 2]` |
| `keys(map)` | A map's keys as a list | `keys({a = 1, b = 2})` → `["a", "b"]` |
| `merge(a, b)` | Two maps combined | `merge(local.base_rules, local.bootstrap_rules)` |
| `sort(list)` | The list in alphabetical order | `sort(["b", "a"])` → `["a", "b"]` |
| `toset(list)` | The list as a set | `toset(["edge", "api-lb"])` |

## Commands

| Command | Does |
| --- | --- |
| `terraform init` | Download the provider |
| `terraform validate` | Check syntax and variable rules |
| `terraform plan` | Preview (`+` create, `~` change, `-` destroy, `-/+` replace) |
| `terraform apply` | Build |
| `terraform output` | Print outputs |
| `terraform state list` | List managed resources |