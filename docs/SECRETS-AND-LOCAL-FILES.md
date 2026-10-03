# Secrets and local-only files

Never commit:

- OpenStack credential files/application secrets;
- Terraform state or private `.tfvars` containing environment secrets;
- SSH/WireGuard private keys;
- kubeconfigs;
- unsealed Kubernetes Secret YAML;
- Sealed Secrets controller private key;
- database passwords;
- model/API keys;
- Discord bot tokens;
- raw credentials copied from A100/H200 providers.

Use the instructor-approved private/local paths, Ansible Vault where provided, and `kubeseal` with the cluster public certificate. Before every push run `git status` and inspect `git diff --cached`.
