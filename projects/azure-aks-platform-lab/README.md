# Azure AKS platform lab
A new portfolio design demonstrating private cluster access, managed identities, Entra authorization and validation-only delivery. Not a record of employer infrastructure or a deployed production platform.

## Architecture and security decisions
- Private Kubernetes API and private DNS linked to the node VNet. Public API FQDN, local admin accounts and Run Command are disabled. Administration needs private network connectivity and Entra credentials.
- User-assigned control-plane identity gets Network Contributor only on this lab VNet and Private DNS Zone Contributor only on this lab zone. These are proposed Terraform role assignments, not changes made to any account. Deployment credentials would require permission to create them.
- Entra groups control bootstrap administration; Azure RBAC is enabled. Review group membership and assign narrower user roles before adoption. No kubeconfig, token or secret outputs.
- OIDC and workload identity are enabled. Workloads receive no Azure permissions by default: create explicitly scoped identities and federated service-account subjects separately after review.
- Azure CNI overlay: VNet 10.40.0.0/16, nodes 10.40.0.0/22, pods 10.244.0.0/16, services 10.96.0.0/16. Check all peered/on-premises ranges before deployment. Calico enables enforcement; application default-deny policies still must be installed.
- Two system nodes, one surge node for upgrades. This is not a multi-zone availability claim. Standard load-balancer outbound allows internet egress: **private API does not mean network isolation**. No firewall, NAT gateway or ingress controller is provisioned.

## Validation
From this directory, with Terraform 1.6+:
```sh
terraform fmt -check -recursive
terraform init -backend=false -input=false
terraform validate
```
`azure-pipelines.yml` is a validation-only pipeline for a preconfigured `PortfolioValidation` agent pool with Terraform and Python. Import that YAML path in Azure DevOps. It has no cloud service connection and never runs plan/apply. Initialization downloads providers. The committed `.terraform.lock.hcl` selects AzureRM 4.81.0 with registry-provided checksums. Review provider upgrades explicitly and use `terraform init -lockfile=readonly` in CI.

Local Terraform 1.9.8 formatting checks and HCL/YAML parsing passed. Provider initialization succeeded with signed AzureRM 4.81.0. `terraform validate` was attempted but could not load the provider schema: the local provider process failed its plugin handshake. Provider validation, Azure pipeline execution, plans and deployment therefore remain unverified. Syntax parsing does not establish provider compatibility or deployability.

## Before any separately authorized deployment
Choose a supported regional Kubernetes version, set subscription/tenant/group IDs privately, review cost/quota and all Terraform changes. Free control-plane tier still incurs VM, disk and network charges. Establish encrypted remote state, restricted access and locking; the lab intentionally does not create a backend or cloud credentials. Review federation for deployment authentication; avoid long-lived client secrets. Never commit state or tfvars.

## Operations and recovery
Use an approved VPN/peered administration network; configure private DNS forwarding/linkage for clients and runners. A public hosted runner cannot administer this API. Verify DNS resolution first, then Entra group access and Azure RBAC propagation. Never re-enable local accounts as a routine workaround.

Before upgrades, review regional version support, node quota, disruption budgets and workloads' readiness probes; test drain and rollback procedures in a non-production environment. Monitor pending pods, node readiness, API failures, disk capacity and identity authorization failures. Restore application data in an isolated namespace and retain integrity evidence; this Terraform does not implement workload backups or observability storage.

For cleanup, review a destroy plan from the same state after exporting required application data. Remove workloads and external dependencies first. Confirm lab resources and disks are gone and review residual costs. No destroy or provisioning was executed for this portfolio.

## References
- [AzureRM AKS resource](https://registry.terraform.io/providers/hashicorp/azurerm/4.40.0/docs/resources/kubernetes_cluster)
- [AKS private clusters](https://learn.microsoft.com/en-us/azure/aks/private-clusters)
- [AKS managed identities](https://learn.microsoft.com/en-us/azure/aks/managed-identity-overview)
