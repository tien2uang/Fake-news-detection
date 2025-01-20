variable "resource_group_name" {
  type        = string
  description = "fnd-rg"
  default     = "fnd_rg"
}

variable "acr_name" {
  type        = string
  description = "fnd-acr"
  default     = "fndacr"
}

variable "aks_cluster_name" {
  type        = string
  description = "fnd-cluster"
  default     = "fnd_cluster"
}

variable "aks_node_count" {
  type        = number
  default     = 1
}

variable "location" {
  type        = string
  default     = "Southeast Asia"
}

variable "vm_name" {
  type        = string
  default     = "jenkins-vm"
  description = "Tên của Azure VM để cài Jenkins"
}

