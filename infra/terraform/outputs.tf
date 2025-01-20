output "aks_cluster_name" {
  value = azurerm_kubernetes_cluster.aks.name
}

output "kube_admin_config" {
  value     = azurerm_kubernetes_cluster.aks.kube_admin_config_raw
  sensitive = true
}

output "jenkins_vm_ip" {
  value = azurerm_public_ip.jenkins_public_ip.ip_address
  description = "Địa chỉ IP công khai của Jenkins VM"
}

# Xuất thông tin IP VM, kubeconfig,...
output "jenkins_public_ip" {
  description = "Public IP cho Jenkins VM"
  value       = azurerm_public_ip.jenkins_public_ip.ip_address
}
