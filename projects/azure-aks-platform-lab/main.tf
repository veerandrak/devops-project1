terraform {
  required_version = ">= 1.6, < 2.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 5.8"
    }
  }
}
provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
}
resource "azurerm_resource_group" "lab" {
  name     = "${var.name}-rg"
  location = var.location
  tags     = { purpose = "portfolio-lab", owner = "Sai Veerandra Kurakula" }
}
resource "azurerm_virtual_network" "lab" {
  name                = "${var.name}-vnet"
  location            = azurerm_resource_group.lab.location
  resource_group_name = azurerm_resource_group.lab.name
  address_space       = ["10.40.0.0/16"]
}
resource "azurerm_subnet" "nodes" {
  name                 = "aks-nodes"
  resource_group_name  = azurerm_resource_group.lab.name
  virtual_network_name = azurerm_virtual_network.lab.name
  address_prefixes     = ["10.40.0.0/22"]
}
resource "azurerm_user_assigned_identity" "cluster" {
  name                = "${var.name}-identity"
  location            = azurerm_resource_group.lab.location
  resource_group_name = azurerm_resource_group.lab.name
}
resource "azurerm_role_assignment" "network" {
  scope                = azurerm_virtual_network.lab.id
  role_definition_name = "Network Contributor"
  principal_id         = azurerm_user_assigned_identity.cluster.principal_id
}
resource "azurerm_private_dns_zone" "api" {
  name                = "privatelink.${var.location}.azmk8s.io"
  resource_group_name = azurerm_resource_group.lab.name
}
resource "azurerm_private_dns_zone_virtual_network_link" "api" {
  name                  = "aks-api-link"
  resource_group_name   = azurerm_resource_group.lab.name
  private_dns_zone_name = azurerm_private_dns_zone.api.name
  virtual_network_id    = azurerm_virtual_network.lab.id
  registration_enabled  = false
}
resource "azurerm_role_assignment" "dns" {
  scope                = azurerm_private_dns_zone.api.id
  role_definition_name = "Private DNS Zone Contributor"
  principal_id         = azurerm_user_assigned_identity.cluster.principal_id
}
resource "azurerm_kubernetes_cluster" "lab" {
  name                                = var.name
  location                            = azurerm_resource_group.lab.location
  resource_group_name                 = azurerm_resource_group.lab.name
  dns_prefix                          = var.name
  kubernetes_version                  = var.kubernetes_version
  private_cluster_enabled             = true
  private_cluster_public_fqdn_enabled = false
  private_dns_zone_id                 = azurerm_private_dns_zone.api.id
  local_account_disabled              = true
  role_based_access_control_enabled   = true
  run_command_enabled                 = false
  oidc_issuer_enabled                 = true
  workload_identity_enabled           = true
  sku_tier                            = "Free"
  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.cluster.id]
  }
  azure_active_directory_role_based_access_control {
    tenant_id              = var.tenant_id
    azure_rbac_enabled     = true
    admin_group_object_ids = var.admin_group_object_ids
  }
  default_node_pool {
    name           = "system"
    node_count     = 2
    vm_size        = "Standard_D4s_v5"
    vnet_subnet_id = azurerm_subnet.nodes.id
    upgrade_settings {
      max_surge = "1"
    }
  }
  network_profile {
    network_plugin      = "azure"
    network_plugin_mode = "overlay"
    network_policy      = "calico"
    pod_cidr            = "10.244.0.0/16"
    service_cidr        = "10.96.0.0/16"
    dns_service_ip      = "10.96.0.10"
    load_balancer_sku   = "standard"
    outbound_type       = "loadBalancer"
  }
  depends_on = [azurerm_role_assignment.network, azurerm_role_assignment.dns,
  azurerm_private_dns_zone_virtual_network_link.api]
}
output "cluster_id" {
  value = azurerm_kubernetes_cluster.lab.id
}
output "oidc_issuer_url" {
  value = azurerm_kubernetes_cluster.lab.oidc_issuer_url
}
