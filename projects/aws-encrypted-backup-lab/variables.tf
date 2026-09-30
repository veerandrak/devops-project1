variable "region" {
  type    = string
  default = "ap-south-1"
}

variable "bucket_name" {
  type        = string
  description = "A globally unique, DNS-compatible S3 bucket name for your own lab."
  validation {
    condition     = length(var.bucket_name) >= 3 && length(var.bucket_name) <= 63 && can(regex("^[a-z0-9][a-z0-9-]*[a-z0-9]$", var.bucket_name))
    error_message = "Use 3–63 lowercase letters, digits or hyphens; start and end with a letter or digit."
  }
}
