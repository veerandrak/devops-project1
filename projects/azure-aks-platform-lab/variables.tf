variable "subscription_id" {
  type        = string
  description = "Target subscription; no default or credentials committed."
}
variable "tenant_id" {
  type        = string
  description = "Microsoft Entra tenant UUID."
}
variable "name" {
  type    = string
  default = "svk-aks-lab"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,30}$", var.name))
    error_message = "Use 3–31 lowercase letters, digits or hyphens, starting with a letter."
  }
}
variable "location" {
  type    = string
  default = "centralindia"
}
variable "kubernetes_version" {
  type        = string
  description = "Choose a currently supported version in the target region; intentionally no stale default."
  validation {
    condition     = can(regex("^1\\.[0-9]+(\\.[0-9]+)?$", var.kubernetes_version))
    error_message = "Provide a supported Kubernetes version such as 1.MINOR.PATCH."
  }
}
variable "admin_group_object_ids" {
  type        = list(string)
  description = "Existing, tightly controlled Entra admin groups; no identities created by this lab."
  validation {
    condition = length(var.admin_group_object_ids) > 0 && alltrue([
      for id in var.admin_group_object_ids : can(regex("^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$", id))
    ])
    error_message = "At least one valid Entra group object UUID is required."
  }
}
